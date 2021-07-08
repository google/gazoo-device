# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Manager module.

  - detects devices
  - creates devices
  - get props and sets optional props
"""
import atexit
import copy
import datetime
import difflib
import fnmatch
import inspect
import json
import logging
import multiprocessing
import os
import queue
import re
import shutil
import signal
import subprocess
import textwrap
import time
from typing import Dict, Optional, Union

from gazoo_device import config
from gazoo_device import custom_types
from gazoo_device import device_detector
from gazoo_device import errors
from gazoo_device import extensions
from gazoo_device import gdm_logger

from gazoo_device.capabilities import event_parser_default
from gazoo_device.log_parser import LogParser
from gazoo_device.switchboard import communication_types
from gazoo_device.switchboard import switchboard

from gazoo_device.usb_port_map import UsbPortMap
from gazoo_device.utility import common_utils
from gazoo_device.utility import host_utils
from gazoo_device.utility import parallel_utils
from gazoo_device.utility import usb_utils

logger = gdm_logger.get_logger()


class Manager():
  """Manages the setup and communication of smart devices."""

  def __init__(self,
               device_file_name=None,
               device_options_file_name=None,
               testbeds_file_name=None,
               gdm_config_file_name=config.DEFAULT_GDM_CONFIG_FILE,
               log_directory=None,
               gdm_log_file=None,
               gdm_log_formatter=None,
               adb_path=None,
               debug_level=logging.DEBUG,
               stream_debug=False,
               stdout_logging=True,
               max_log_size=100000000):

    self._open_devices = {}
    self.max_log_size = max_log_size
    # b/141476623: exception queue must not share multiprocessing.Manager()
    common_utils.run_before_fork()
    self._exception_queue_manager = multiprocessing.Manager()
    common_utils.run_after_fork_in_parent()
    self._exception_queue = self._exception_queue_manager.Queue()

    # Backwards compatibility for older debug_level=string style __init__
    if not isinstance(debug_level, int):
      if debug_level in ["debug", "developer"]:
        debug_level = logging.DEBUG
      else:
        debug_level = logging.INFO
    logger.level = debug_level

    if stream_debug:
      gdm_logger.stream_debug()

    if not stdout_logging:
      gdm_logger.silence_progress_messages()

    if gdm_log_file:
      if not gdm_log_formatter:
        gdm_log_formatter = logging.Formatter(
            gdm_logger.FMT, datefmt=gdm_logger.DATEFMT)

      self.gdm_log_handler = logging.FileHandler(gdm_log_file)
      self.gdm_log_handler.setLevel(debug_level)
      self.gdm_log_handler.setFormatter(gdm_log_formatter)
      gdm_logger.add_handler(self.gdm_log_handler)

    self.device_file_name = None
    self.device_options_file_name = None
    self.testbeds_file_name = None
    self.log_directory = None
    self._load_configuration(device_file_name, device_options_file_name,
                             testbeds_file_name, gdm_config_file_name,
                             log_directory, adb_path)

    # Register USR1 signal to get exception messages from exception_queue
    signal.signal(signal.SIGUSR1,
                  common_utils.MethodWeakRef(self._process_exceptions))
    atexit.register(common_utils.MethodWeakRef(self.close))

  def backup_configs(self):
    """Backs up existing configuration files to a timestamped directory.

    Raises:
      DeviceError: unable to overwrite config files.

    Notes:
      Backs up configuration files to 'backup'
    """
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    if not os.path.exists(config.BACKUP_PARENT_DIRECTORY) or not os.access(
        config.BACKUP_PARENT_DIRECTORY, os.X_OK):
      raise errors.DeviceError(
          "Device overwrite error. "
          "Directory {} does not exist or is not executable. "
          "Unable to overwrite configs".format(config.BACKUP_PARENT_DIRECTORY))
    self.backup_directory = os.path.join(config.BACKUP_PARENT_DIRECTORY,
                                         "backup-%s" % str(timestamp))
    logger.info("Moving config files to the backup directory " +
                self.backup_directory)
    if not os.path.exists(self.backup_directory):
      os.makedirs(self.backup_directory)

    shutil.copyfile(self.device_file_name,
                    os.path.join(self.backup_directory, "devices.json"))
    shutil.copyfile(self.device_options_file_name,
                    os.path.join(self.backup_directory, "device_options.json"))
    shutil.copyfile(self.testbeds_file_name,
                    os.path.join(self.backup_directory, "testbeds.json"))
    shutil.copyfile(self.gdm_config_file_name,
                    os.path.join(self.backup_directory, "gdm.json"))

  def close(self):
    """Stops logger and closes all devices."""
    self.close_open_devices()
    gdm_logger.flush_queue_messages()
    gdm_logger.silence_progress_messages()

    if hasattr(self, "gdm_log_handler") and self.gdm_log_handler:
      gdm_logger.remove_handler(self.gdm_log_handler)
      self.gdm_log_handler.close()
      del self.gdm_log_handler

    if hasattr(self, "_exception_queue"):
      del self._exception_queue
    if hasattr(self, "_exception_queue_manager"):
      self._exception_queue_manager.shutdown()
      del self._exception_queue_manager

  def close_open_devices(self):
    """Closes all open devices."""
    for device in list(self._open_devices.values()):
      device.close()

  def close_device(self, identifier):
    """Closes open device via identifier.

    Args:
      identifier (str): device identifier. Name, serial_number, etc
    """
    device_name = self._get_device_name(identifier, raise_error=True)
    if device_name not in self._open_devices:
      return
    else:
      self._open_devices[device_name].close()

  def create_device(self,
                    identifier,
                    new_alias=None,
                    log_file_name=None,
                    log_directory=None,
                    log_to_stdout=None,
                    skip_recover_device=False,
                    make_device_ready="on",
                    filters=None,
                    log_name_prefix="") -> custom_types.Device:
    """Returns created device object by identifier specified.

    Args:
      identifier (str): The identifier string to identify a single device.
        For simulators, the identifier can be the simulator device type
      new_alias (str): A string to replace device's alias kept in file.
      log_file_name (str): A string log file name to use for log results.
      log_directory (str): A directory path to use for storing log file.
      log_to_stdout (bool): Enable streaming of log results to stdout
        (DEPRECATED).
      skip_recover_device (bool): Don't recover device if it fails ready
        check.
      make_device_ready (str): "on", "check_only", "off". Toggles
        make_device_ready.
      filters (list): paths to custom Parser filter files or directories to
        use.
      log_name_prefix (str): string to prepend to log filename.

    Returns:
      The device found and created by the identifier specified.

    Raises:
      ValueError: If identifier specified does not match a known device or
                  device is not currently connected.
      DeviceError: Device not connected
    """
    logger.debug("In create_device")

    if identifier.endswith("sim"):
      return self.create_device_sim(
          device_type=identifier,
          log_file_name=log_file_name,
          log_directory=log_directory,
          skip_recover_device=skip_recover_device,
          make_device_ready="off",
          filters=filters,
          log_name_prefix=log_name_prefix)

    if log_to_stdout is not None:
      logger.warn(
          "DEPRECATION WARNING: Support for the log_to_stdout argument is "
          "ending soon. To continue seeing the same output, please set "
          "debug_level to logging.INFO and remove log_to_stdout")

    if log_file_name is not None:
      logger.warn(
          "DEPRECATION WARNING: Support for log_file_name argument is "
          "ending soon. Please start using log_name_prefix argument instead.")

    self._type_check("identifier", identifier)
    device_name = self._get_device_name(identifier, raise_error=True)
    if device_name in self._open_devices:
      raise errors.DeviceError(
          "Device {name} already created. Call manager.get_open_device('{name}')."
          .format(name=device_name))
    if new_alias is not None:
      self.set_prop(device_name, "alias", new_alias)
    device_config = self.get_device_configuration(device_name)
    self._update_device_config(device_config, skip_recover_device,
                               make_device_ready, log_name_prefix, filters)
    device_type = device_config["persistent"]["device_type"]
    if not log_directory:
      # sets the device log directory to manager's log_directory
      log_directory = self.log_directory

    logger.info("Creating {}".format(device_name))
    device_class = self.get_supported_device_class(device_type)
    track_device = device_type not in self.get_supported_auxiliary_device_types(
    )
    device_inst = self._get_device_class(device_class, device_config,
                                         log_file_name, log_directory,
                                         track_device)
    try:
      device_inst.make_device_ready(make_device_ready)

    except errors.DeviceError:
      # ensure connections are closed down.
      device_inst.close()
      raise
    return device_inst

  def create_device_sim(self,
                        device_type,
                        log_file_name=None,
                        log_directory=None,
                        skip_recover_device=False,
                        make_device_ready="off",
                        filters=None,
                        log_name_prefix="",
                        build_info_kwargs=None):
    """Returns created simulated object by device_type specified.

    Args:
      device_type (str): The device type of the simulator.
      log_file_name (str): A string log file name to use for log results.
      log_directory (str): A directory path to use for storing log file.
      skip_recover_device (bool): Don't recover device if it fails ready
        check.
      make_device_ready (str): "on", "check_only", "off". Toggles
        make_device_ready.
      filters (list): paths to custom Parser filter files or directories to
        use.
      log_name_prefix (str): string to prepend to log filename.
      build_info_kwargs (dict): build info args by name to pass to upgrade
        method.

    Returns:
      Object: The device found and created by the device_type specified.

    Raises:
      ValueError: If identifier specified does not match a known device_type
      DeviceError: Device not connected
    """
    logger.info("In create_device_sim")
    if not log_directory:
      # sets the device log directory to manager's log_directory
      log_directory = self.log_directory

    device_config = {}
    self._update_device_config(device_config, skip_recover_device,
                               make_device_ready, log_name_prefix, filters)

    supported_device_class = self.get_supported_device_class(device_type)
    device_class = self._get_device_sim_class(supported_device_class,
                                              device_config, log_file_name,
                                              log_directory, build_info_kwargs)
    return device_class

  def create_devices(self,
                     device_list=None,
                     device_type=None,
                     log_to_stdout=None,
                     category="gazoo",
                     make_device_ready="on",
                     log_name_prefix=""):
    """Returns list of created device objects from device_list or connected devices.

    Args:
      device_list (list): list of mobly configs.
      device_type (str): filter to just return device instances of list
        type.
      log_to_stdout (bool): Enable streaming of log results to stdout
        (DEPRECATED).
      category (str): 'gazoo', 'other' or 'all' to filter connected devices.
      make_device_ready (str): "on", "check_only", "off". Toggles
        make_device_ready.
      log_name_prefix (str): string to prepend to log filename.

    Returns:
      list: device instances successfully created.

    Raises:
      ValueError: If an identifier specified does not match a known device
      or device is not currently connected.
    """
    logger.debug("In create_devices")
    if log_to_stdout is not None:
      logger.warn(
          "DEPRECATION WARNING: Support for the log_to_stdout argument is "
          "ending soon. To continue seeing the same output, please set "
          "debug_level to logging.INFO and remove log_to_stdout")

    devices = []

    if device_list is None:
      device_list = self.get_connected_devices(category)

    alias = None
    identifier = None
    for args in device_list:
      if isinstance(args, dict):  # translating potential mobly arguments
        if "id" in args:
          identifier = args["id"]
        elif "name" in args:
          identifier = args["name"]
        if "label" in args:
          alias = args["label"]
        elif "alias" in args:
          alias = args["alias"]

      elif isinstance(args, str):
        identifier = args

      # check if this device is the right type:
      if device_type is None or device_type.lower() == self.get_device_prop(
          identifier, "device_type"):
        devices.append(
            self.create_device(
                identifier,
                alias,
                make_device_ready=make_device_ready,
                log_name_prefix=log_name_prefix))
    return devices

  def create_log_parser(self, log_filename, filter_list=None):
    """Creates a LogParser object given a specified device type and filter list.

    Args:
        log_filename (str): filename containing raw, log event data
        filter_list (list): List of files or directories containing JSON
          filter files.

    Returns:
        LogParser: object which creates an event file by parsing a log file
        of the device type specified using the provided filter list
    """
    parser = event_parser_default.EventParserDefault(
        filters=filter_list,
        event_file_path="unknown.txt",
        device_name="unknown")
    return LogParser(parser, log_filename)

  def create_switchboard(
      self,
      communication_address,
      communication_type,
      device_name="unknown",
      log_path=None,
      force_slow=False,
      event_parser=None,
      **kwargs):
    """Creates a switchboard instance.

    Args:
      communication_address (str): primary device address for communication.
        For example, "123.45.56.123", ADB serial number, or serial port path.
      communication_type (str): identifier for the type of communication.
      device_name (str): device identifier. Used in stdout.
      log_path (str): path to write GDM device logs to.
      force_slow (bool): send device input at human speed. Used for devices with
        input speed limitations.
      event_parser (Parser): parses log stream into events and saves them to
        event file.
      **kwargs (dict): additional kwargs to pass onto the communication setup.

    Returns:
      SwitchboardDefault: instance of SwitchboardDefault.

    Raises:
      SwitchboardCreationError: if communication type not recognized.
    """
    if communication_type == "GENERIC_PROCESS":
      # Backwards compatibility with VDM
      communication_type = "PtyProcessComms"
    if communication_type not in extensions.communication_types:
      raise errors.SwitchboardCreationError(
          device_name,
          "Communication type {!r} is not in supported types: {}".format(
              communication_type, extensions.communication_types.keys()))

    if not log_path:
      log_path = self.create_log_path(device_name)

    logger.info("{} logging to file {}", device_name, log_path)

    comm_type_class = extensions.communication_types[communication_type]

    method_args = inspect.getfullargspec(
        comm_type_class.__init__).args[1:]  # remove self
    bad_keys = set(kwargs.keys()) - set(method_args)
    if bad_keys:
      raise errors.SwitchboardCreationError(
          device_name,
          "Communication Type {} does not support args {}. Supported: {}"
          .format(communication_type, bad_keys, method_args))

    try:
      comm_inst = comm_type_class(communication_address, **kwargs)
      switchboard_kwargs = comm_inst.get_switchboard_kwargs()
      additional_kwargs = {
          "device_name": device_name,
          "log_path": log_path,
          "force_slow": force_slow,
          "parser": event_parser,
          "exception_queue": self._exception_queue,
          "max_log_size": self.max_log_size,
      }
      switchboard_kwargs.update(additional_kwargs)

      return switchboard.SwitchboardDefault(**switchboard_kwargs)
    except Exception as err:
      raise errors.SwitchboardCreationError(device_name, repr(err))

  def delete(self, device_name, save_changes=True):
    """Delete the device from config dict and file.

    Args:
        device_name (str): name, serial_number, alias, or adb_serial of the
          device.
        save_changes (bool): if True, updates the config files.

    Raises:
        DeviceError: Device not found.

    Returns:
        None: if save_changes is True.
        tuple[dict, dict]: if save_changes is False, returns the new device
        configs: (devices, device_options).
    """
    devices = copy.deepcopy(self.persistent_dict)
    device_options = copy.deepcopy(self.options_dict)
    other_devices = copy.deepcopy(self.other_persistent_dict)
    other_device_options = copy.deepcopy(self.other_options_dict)
    device_name_arg = device_name
    device_name = self._get_device_name(device_name, raise_error=True)
    if device_name in devices and device_name in device_options:
      del devices[device_name]
      del device_options[device_name]
    elif device_name in other_devices and device_name in other_device_options:
      del other_devices[device_name]
      del other_device_options[device_name]
    else:
      raise errors.DeviceError(
          "Unable to find device {}".format(device_name_arg))

    device_config, device_options_config = self._make_device_configs(
        devices, other_devices, device_options, other_device_options)
    if save_changes:  # save and reload the config.
      self._save_config_to_file(device_config, self.device_file_name)
      self._save_config_to_file(device_options_config,
                                self.device_options_file_name)
      self.reload_configuration()
      logger.info("Deleted {}".format(device_name_arg))
    else:
      return (device_config, device_options_config)

  def detect(self,
             force_overwrite=False,
             static_ips=None,
             log_directory=None,
             save_changes=True,
             device_configs=None):
    """Detect new devices not present in config files.

    Args:
       force_overwrite (bool): Erase the current configs completely and
         re-detect everything.
       static_ips (list): list of static ips to detect.
       log_directory (str): alternative location to store log from default.
       save_changes (bool): if True, updates the config files.
       device_configs (None or tuple[dict, dict]): device configs
         (persistent, options) to pass to the device detector. If None, uses
         the current Manager configs.

    Returns:
        None: if save_changes is True.
        tuple[dict, dict]: if save_changes is False, returns
            the new device configs: (devices, device_options).

    Note:
       Overwrite saves the files to a backup directory.
    """
    if device_configs is None:
      device_config, options_config = self._make_device_configs(
          self.persistent_dict, self.other_persistent_dict, self.options_dict,
          self.other_options_dict)
    else:
      device_config, options_config = device_configs

    if not static_ips:
      static_ips = []
    elif isinstance(static_ips, str):
      static_ips = [ip_addr for ip_addr in static_ips.split(",") if ip_addr]
    if not log_directory:
      log_directory = self.log_directory

    if force_overwrite:
      comm_ports = [
          a_dict["persistent"].get("console_port_name", "")
          for name, a_dict in self._devices.items()
      ]
      static_ips += [
          comm_port for comm_port in comm_ports
          if host_utils.is_static_ip(comm_port)
      ]
      if save_changes:
        self.overwrite_configs()
      device_config, options_config = self._make_device_configs({}, {}, {}, {})

    detector = device_detector.DeviceDetector(
        manager=self,
        log_directory=log_directory,
        persistent_configs=device_config,
        options_configs=options_config,
        supported_auxiliary_device_classes=self
        .get_supported_auxiliary_device_classes())

    new_device_config, new_options_config = detector.detect_all_new_devices(
        static_ips)
    if save_changes:
      self._save_config_to_file(new_device_config, self.device_file_name)
      self._save_config_to_file(new_options_config,
                                self.device_options_file_name)
      self.reload_configuration()
      self.devices()
    else:
      return (new_device_config, new_options_config)

  def devices(self):
    """Prints a summary of device info.
    """

    self._print_device_info_by_category("gazoo")
    self._print_device_info_by_category("other")

    logger.info("{} total Gazoo device(s) available.".format(
        len(self.get_connected_devices())))

  def download_keys(self):
    """Downloads all required GDM keys if they don't exist locally."""
    for key_info in extensions.keys:
      host_utils.verify_key(key_info)

  @classmethod
  def get_all_supported_capabilities(cls):
    """Returns a map of all capability names supported by GDM.

    Returns:
        dict: map from capability name (str) to capability interface name
        (str).
              Example: {"file_transfer": "filetransferbase"}.
    """
    return copy.copy(extensions.capabilities)

  @classmethod
  def get_all_supported_capability_interfaces(cls):
    """Returns a map of all capability interface classes supported by GDM.

    Returns:
        dict: map from interface name (str) to capability interface class
        (type).
              Example: {"filetransferbase": <class FileTransferBase>}.
    """
    return copy.copy(extensions.capability_interfaces)

  @classmethod
  def get_all_supported_capability_flavors(cls):
    """Returns a map of all capability flavor classes supported by GDM.

    Returns:
        dict: map from flavor name (str) to capability flavor class (type).
              Example: {"filetransferscp": <class FileTransferScp>}.
    """
    return copy.copy(extensions.capability_flavors)

  @classmethod
  def get_all_supported_device_classes(cls):
    """Returns a list of all supported primary, sim, and auxiliary devices.

    Returns:
      list: All supported device types. Returns just categories asked for if
      requested.
    """
    all_classes = copy.copy(extensions.auxiliary_devices)
    all_classes += copy.copy(extensions.primary_devices)
    all_classes += copy.copy(extensions.virtual_devices)
    return all_classes

  def get_connected_devices(self, category="gazoo"):
    """Retrieve a list of connected devices for the category specified.

    Args:
      category (str): device category ('gazoo', 'other', or 'all') to
        retrieve.

    Returns:
      list: List of known connected devices.

    Note:
      If category is not specified then a list of all devices will be
      returned.
    """
    devices = self.get_devices(category)
    connected_devices = []
    for name in devices:
      if self.is_device_connected(name, category):
        connected_devices.append(name)
    return connected_devices

  def get_device_configuration(self, identifier, category="all"):
    """Returns the configuration for the device.

    Args:
        identifier (str): Name or alias to search for.
        category (str): device category ('gazoo', 'other' or 'all') to
          retrieve.

    Returns:
      dict: Configuration obtained for the device found.

    Raises:
      DeviceError: If identifier does not unique identify the device.

    Note:
      If category is not specified then all devices will be used to find
      the matching identifier.
    """
    # returns the device configuration
    device_name = self._get_device_name(identifier, category, raise_error=True)
    return self._get_device_configuration(device_name, category)

  def get_open_device_names(self):
    """Returns a list of open device names.

    Returns:
      list: open device names
    """
    return list(self._open_devices.keys())

  def get_open_device(self, identifier):
    """Returns device object if device is open.

    Args:
      identifier (str): device name, serial_number etc.

    Returns:
      GazooDeviceBase: device object

    Raises:
      DeviceError: if device not currently open
    """
    device_name = self._get_device_name(identifier, raise_error=True)
    if device_name not in self._open_devices:
      raise errors.DeviceError(
          "Device {} is not currently open".format(identifier))
    else:
      return self._open_devices[device_name]

  def get_open_devices(self):
    """Returns list of device objects."""
    return list(self._open_devices.values())

  def get_device_prop(self, device_name, prop=None):
    """Gets an prop's value for device or GDM configuration depends on identifier.

    Args:
        device_name (str): "manager", name, serial_number, alias, or
          adb_serial of the device.
        prop (str): Public prop available in device_options.json or gdm.json.
          Default is None.

    Returns:
      dict: device properties dicts if prop is None
      value: value of valid prop
    """

    if self._is_manager_config(device_name):
      return self._get_config_prop(prop)
    else:
      return self._get_device_prop(device_name, prop)

  @classmethod
  def get_supported_auxiliary_device_classes(cls):
    return copy.copy(extensions.auxiliary_devices)

  @classmethod
  def get_supported_auxiliary_device_types(cls):
    return [
        a_cls.DEVICE_TYPE
        for a_cls in cls.get_supported_auxiliary_device_classes()
    ]

  @classmethod
  def get_supported_device_capabilities(cls, device_type):
    """Returns a list of names of capabilities supported by the device type.

    This is a wrapper around GazooDeviceBase.get_supported_capabilities() to
    allow specifying device_type as a string.

    Args:
        device_type (str): device type to query for supported capabilities.

    Returns:
        list: list of capability names supported by this device type.
              For example, (["file_transfer", "usb_hub"]).
    """
    device_class = cls.get_supported_device_class(device_type)
    return device_class.get_supported_capabilities()

  @classmethod
  def get_supported_device_capability_flavors(cls, device_type):
    """Returns a set of all capability flavor classes supported by the device type.

    This is a wrapper around GazooDeviceBase.get_supported_capability_flavors()
    to allow specifying device_type as a string.

    Args:
      device_type (str): device type to query for supported capability flavors.

    Returns:
      set: capability flavor classes supported by this device type.
      Example: {<class 'DevicePowerDefault'>, <class 'FileTransferScp'>}.
    """
    device_class = cls.get_supported_device_class(device_type)
    return device_class.get_supported_capability_flavors()

  @classmethod
  def get_supported_device_class(cls, device_type):
    """Converts device type to device class.

    Args:
      device_type (str): device type.

    Returns:
       class: GazooDeviceBase-based class.

    Raises:
      DeviceError: if unknown type.
    """
    classes = [
        device_class for device_class in cls.get_all_supported_device_classes()
        if device_class.DEVICE_TYPE == device_type
    ]
    if classes:
      return classes[0]
    else:
      close_matches = difflib.get_close_matches(
          device_type, cls.get_supported_device_types())
      raise errors.DeviceError(
          "Device type {} is not known. Close matches: {}".format(
              device_type, ", ".join(close_matches)))

  @classmethod
  def get_supported_device_types(cls):
    """Returns a list of all supported device types.

    Returns:
      list: All supported device types.
    """
    return [
        a_cls.DEVICE_TYPE for a_cls in cls.get_all_supported_device_classes()
    ]

  @classmethod
  def get_supported_primary_device_classes(cls):
    return copy.copy(extensions.primary_devices)

  @classmethod
  def get_supported_primary_device_types(cls):
    return [
        a_cls.DEVICE_TYPE
        for a_cls in cls.get_supported_primary_device_classes()
    ]

  @classmethod
  def get_supported_virtual_device_classes(cls):
    return copy.copy(extensions.virtual_devices)

  @classmethod
  def get_supported_virtual_device_types(cls):
    return [
        a_cls.DEVICE_TYPE
        for a_cls in cls.get_supported_virtual_device_classes()
    ]

  def is_device_connected(self, identifier, category="all"):
    """Determine if device match identifier provided is connected for the category specified.

    Args:
      identifier (str): Name or alias to search for.
      category (str): device category ('gazoo', 'other', or 'all') to
        retrieve.

    Returns:
      bool: True if the matching devices is connected. False otherwise.

    Raises:
      ValueError: Identifier does not unique identify the device.

    Note:
      If category is not specified then the list of all devices will be used
      to find the matching identifier.
    """
    device_name = self._get_device_name(identifier, category, raise_error=True)

    device_config = self._get_device_configuration(device_name, category)
    device_type = device_config["persistent"]["device_type"].lower()
    try:
      device_class = self.get_supported_device_class(device_type)
      return device_class.is_connected(device_config)
    # Device configs might have devices listed that aren't supported
    except errors.DeviceError as err:
      logger.debug(err)
      return False

  def overwrite_configs(self):
    """Overwrite device configs.

    Raises:
      DeviceError: Device overwrite error.

    Note:
      Backs up existing configuration files and writes empty config files.
      Then reloads manager().
    """
    self.backup_configs()

    with open(self.device_file_name, "w") as open_file:
      json.dump({"devices": {}, "other_devices": {}}, open_file)
    with open(self.device_options_file_name, "w") as open_file:
      json.dump({"device_options": {}, "other_device_options": {}}, open_file)
    with open(self.testbeds_file_name, "w") as open_file:
      json.dump({"testbeds": {}}, open_file)
    with open(self.gdm_config_file_name, "w") as open_file:
      json.dump({}, open_file)

    self.reload_configuration()

  def get_usb_hub_props(self, device_identifier):
    """Dictionary of usb_hub information.

    Args:
        device_identifier (str): the device identifier.

    Returns:
        list: a dictionary of usb_hub props.

    Note: A usb hub will return an empty dictionary.
    Use port_map to see the devices connected to it.
    """
    props_dict = self.get_device_configuration(device_identifier)["persistent"]
    return {key: value for key, value in props_dict.items() if "usb" in key}

  def port_map(self):
    """Prints the USB Port Map.
    """
    usb_port_map = UsbPortMap(self)
    usb_port_map.print_port_map()

  def issue_devices(self,
                    devices,
                    method_name,
                    timeout=parallel_utils.TIMEOUT_PROCESS,
                    **kwargs):
    """Execute a device method in parallel for multiple devices.

    Args:
        devices (list): list of device identifiers.
        method_name (str): name of device method to execute in parallel.
        timeout (int): maximum amount of seconds to allow parallel methods
          to complete.
        **kwargs (dict): arguments to pass to device method.

    Returns:
        list: list of results from parallel calls.
    """
    if isinstance(devices, str):
      devices = devices.split(",")

    return self._issue_devices(devices, method_name, timeout, **kwargs)

  def issue_devices_all(self,
                        method_name,
                        timeout=parallel_utils.TIMEOUT_PROCESS,
                        **kwargs):
    """Execute a device method in parallel for all connected devices.

    Args:
        method_name (str): name of device method to execute in parallel.
        timeout (int): maximum amount of seconds to allow parallel methods
          to complete.
        **kwargs (dict): arguments to pass to device method.

    Returns:
        list: list of results from parallel calls.

    Raises:
        DeviceError: if no devices are connected.
    """
    devices = self.get_connected_devices()
    if not devices:
      raise errors.DeviceError("No devices are connected.")

    return self._issue_devices(devices, method_name, timeout, **kwargs)

  def issue_devices_match(self,
                          match,
                          method_name,
                          timeout=parallel_utils.TIMEOUT_PROCESS,
                          **kwargs):
    """Execute a device method in parallel for connected devices that match a given string.

    Args:
      match (str): wildcard-supported string to match against device
        names, i.e. "raspberrypi*" will call provided method on all connected
        Raspberry Pis.
      method_name (str): name of device method to execute in parallel.
      timeout (int): maximum amount of seconds to allow parallel methods
        to complete.
      **kwargs (dict): arguments to pass to device method.

    Returns:
      list: results from parallel calls.

    Raises:
      DeviceError: if provided wildcard does not match any connected devices.
    """
    devices = fnmatch.filter(self.get_connected_devices(), match)
    if not devices:
      raise errors.DeviceError('No devices match "{}".'.format(match))

    return self._issue_devices(devices, method_name, timeout, **kwargs)

  def redetect(self, device_name, log_directory=None):
    """Delete a device from the device configuration and then do a detect to find it again.

    Args:
        device_name (str): identifier for device.
        log_directory (str): alternative location to store log from default.

    Raises:
        DeviceError: if device is not found.
    """
    device_name = self._get_device_name(device_name, raise_error=True)
    static_ips = None
    try:
      hub_name, hub_port = self._get_device_usb_hub_name_and_port(device_name)
      logger.debug("{} before redetect, found device_usb_hub_name: {}, "
                   "device_usb_port: {}".format(device_name, hub_name,
                                                hub_port))
      comms_port = self.get_device_configuration(
          device_name)["persistent"]["console_port_name"]
      if host_utils.is_static_ip(comms_port):
        static_ips = [comms_port]
    except errors.DeviceError as err:
      logger.info(err)
    usb_hub = None
    original_power_mode = None
    if hub_name and hub_port:
      usb_hub = self.create_device(hub_name)
      original_power_mode = usb_hub.switch_power.get_mode(hub_port)
      if original_power_mode != "sync":
        usb_hub.switch_power.set_mode("sync", hub_port)

    device_configs_after_delete = self.delete(device_name, save_changes=False)
    new_device_config, new_options_config = self.detect(
        static_ips=static_ips,
        log_directory=log_directory,
        save_changes=False,
        device_configs=device_configs_after_delete)
    if usb_hub and original_power_mode != "sync":
      usb_hub.switch_power.set_mode(original_power_mode, hub_port)

    if (device_name not in new_device_config["devices"] and
        device_name not in new_device_config["other_devices"]):
      # Either the device changed its name (if it was physically replaced),
      # or detection of that device failed.
      raise errors.DeviceError(
          "Device {device_name} was not successfully redetected. "
          "Keeping the old device configs. "
          "If you replaced the device, use 'gdm delete {device_name}' "
          "and then 'detect' instead of 'redetect'.".format(
              device_name=device_name))

    # Preserve optional properties set by users
    if device_name in new_options_config["device_options"]:
      new_options_config["device_options"][device_name] = (
          self.options_dict[device_name])
    if device_name in new_options_config["other_device_options"]:
      new_options_config["other_device_options"][device_name] = (
          self.other_options_dict[device_name])

    self._save_config_to_file(new_device_config, self.device_file_name)
    self._save_config_to_file(new_options_config, self.device_options_file_name)
    self.reload_configuration()
    logger.info("Re-detected {}".format(device_name))

  def reload_configuration(self,
                           device_file_name=None,
                           options_file_name=None,
                           testbeds_file_name=None,
                           gdm_config_file_name=None,
                           log_directory=None,
                           adb_path=None):
    """Used when a config file or setting is changed.

    Args:
      device_file_name (str): Device file name.
      options_file_name (str): Device options file name.
      testbeds_file_name (str): Testbeds file name.
      gdm_config_file_name (str): GDM config file name.
      log_directory (str): Log directory.
      adb_path (str): adb path.
    """
    if device_file_name is None:
      device_file_name = self.device_file_name
    if options_file_name is None:
      options_file_name = self.device_options_file_name
    if testbeds_file_name is None:
      testbeds_file_name = self.testbeds_file_name
    if gdm_config_file_name is None:
      gdm_config_file_name = self.gdm_config_file_name

    self._load_configuration(device_file_name, options_file_name,
                             testbeds_file_name, gdm_config_file_name,
                             log_directory, adb_path)

  def _add_correct_value_to_config(self, key, value, default):
    """Add new attribute to self.config dict.

    Args:
      key (str): key's name. if there is no such key, a new key will be
        created.
      value (str): key's corresponding value. If value is not None, the
        value is used.
      default (str): default value for key

    Raises:
      DeviceError: if set attribute is None.

    Notes:
      The value is a arbitrary string and there is no check for such string.
      i.e. This function won't check if the value is a existing path.
    """
    if value is not None:
      self.config[key] = value

    elif key not in self.config:
      self.config[key] = default

    final_value = self.config[key]
    if final_value is None:
      raise errors.DeviceError(
          "Final value for {} should not be None".format(key))

    setattr(self, key, final_value)

  def _add_correct_path_to_config(self, key, path, default):
    """Add new path configuration to self.config dict.

    Args:
      key (str): key's name. if there is no such key, a new key will be
        created.
      path (str): key's corresponding value. If value is not None, this
        value is used.
      default (str): default value for key.

    Raises:
      DeviceError: if final value is none or directory doesn't exist.

    Notes:
      The path is a string represent path, and the function check if the
      path exist or not.
      If there exist such path, the key and value are added into dict.
    """
    if path is not None:
      self.config[key] = path
    elif key not in self.config:
      self.config[key] = default

    final_value = self.config[key]
    if final_value is None:
      raise errors.DeviceError(
          "Final value for {} should not be None".format(key))
    if "/" in final_value and not os.path.isdir(os.path.dirname(final_value)):
      raise errors.DeviceError(
          "Parent directory of {} for {} doesn't exist".format(
              final_value, key))
    if ".json" not in final_value and not os.path.exists(final_value):
      raise errors.DeviceError("File {} for {} doesn't exist".format(
          final_value, key))
    setattr(self, key, final_value)

  def _combine_devices_and_device_options(self, devices_dict,
                                          device_options_dict):
    """Loads the "persistent" items and "optional" items from json file.

    Args:
      devices_dict (dict): Contains "persistent" items of device.
      device_options_dict (dict): Contains "optional" items of device.

    Returns:
      tuple: (aliases, devices, persistent, options)

    Notes:
      This is called once when the manager is initialized. It iterates thru the
      devices.json dictionary, loading the "persistent" items from there, and
      the "optional" items from the  device_options.json file.

      When it is finished: self._devices is a tree-shaped dict.  Each key is the
      name of a device, and the "value" is another dict with "persistent" and
      "optional" sub-dicts). self.persistent_dict has JUST the persistent info
      (subset of the info in self._devices). self.options_dict has JUST the
      optional info (subset of the info in self._devices). TODO: Perhaps
      refactor to remove self.persistent_dict and self.options_dict and just use
      self._devices?
    """
    aliases = self._create_aliases(devices_dict, device_options_dict)
    devices = {}
    persistent = {}
    options = {}
    for name in devices_dict:
      persistent_dict = devices_dict[name]
      persistent_dict["name"] = name
      options_dict = device_options_dict[name]
      new_device_config = {
          "persistent": persistent_dict,
          "options": options_dict
      }
      devices[name] = new_device_config
      persistent[name] = persistent_dict
      options[name] = options_dict
    return aliases, devices, persistent, options

  def _create_aliases(self, devices_dict, devices_options_dict):
    """Creates a dictionary of aliases of Devices.

    Args:
      devices_dict (dict): Contains devices info.
      devices_options_dict (dict): Contains devices options info.

    Returns:
      dict: aliases with keys(name, adb_serial, serial_number, alias from
      device options).

    Notes:
      Maps the lowercase versions of the name, adb_serial, serial_number to
      the device's name.
    """
    aliases = {}
    alias_props = [
        "serial_number", "console_port_name", "alias", "adb_serial",
        "hub_port_name", "secondary_communication_address", "ip_address"
    ]
    for name in devices_dict:
      aliases[name.lower()] = name
      all_props = dict(devices_dict[name], **devices_options_dict[name])

      for prop in alias_props:
        alias = all_props.get(prop, None)
        if alias:
          aliases[alias.lower()] = name
    return aliases

  def create_log_path(self, device_name, name_prefix=""):
    """Returns the full path of log filename using the information provided.

    Args:
        device_name (str): to use in the log filename
        name_prefix (str): string to prepend to the start of the log file.

    Returns:
        str: Path to log filename using the information provided.
    """
    log_timestamp = time.strftime("%Y%m%d-%H%M%S")
    if name_prefix:
      log_file_name = "{}-{}-{}.txt".format(name_prefix, device_name,
                                            log_timestamp)
    else:
      log_file_name = "{}-{}.txt".format(device_name, log_timestamp)
    return os.path.join(self.log_directory, log_file_name)

  @classmethod
  def device_has_capabilities(cls, device_type, capability_names):
    """Check whether a device type supports all of the given capabilities.

    This is a wrapper around GazooDeviceBase.has_capabilities() to allow
        specifying device_type as a string.

    Args:
        device_type (str): device type to query for supported capabilities.
        capability_names (list): list of capability names.
            Capability names are strings. They can be:
                - capability names ("file_transfer"),
                - capability interface names ("filetransferbase"),
                - capability flavor names ("filetransferscp").
            If an interface name or capability name is specified, the behavior
            is identical: any capability flavor which implements the given
            interface will match. If a flavor name is specified, only that
            capability flavor will match. Different kinds of capability names
            can be used together (["usb_hub", "filetransferscp"]).

    Returns:
        bool: True if all capabilities are supported by the device type,
        False otherwise.
    """
    device_class = cls.get_supported_device_class(device_type)
    return device_class.has_capabilities(capability_names)

  def _get_aliases(self, category):
    """Returns a dict of all device name aliases for the category specified.

    Args:
      category (str): Indicates the device category ('gazoo', 'other', or
        'all') to retrieve.

    Returns:
      dict: Device name aliases for the category.
    """
    aliases = {}
    aliases.update(self.aliases if category in ["all", "gazoo"] else {})
    aliases.update(self.other_aliases if category in ["all", "other"] else {})
    return aliases

  def _get_config_prop(
      self, prop: Optional[str] = None
  ) -> Union[custom_types.PropertyValue,
             Dict[str, Dict[str, custom_types.PropertyValue]]]:
    """Returns the value of an GDM config property.

    Args:
      prop: Manager property available in gdm.json.

    Returns:
      GDM config property value.

    Raises:
      DeviceError: Property is not present in the config file.
    """
    if prop:
      if prop not in self.config:
        raise errors.DeviceError(
            "Unable to find prop {} in manager config".format(prop))
      return self.config[prop]
    else:  # return dict of all props
      return {"settable": self.config.copy()}

  def _get_device_configuration(self, name, category):
    """Returns the configuration for the device.

    Args:
      name (str): Key to use for obtaining device configuration.
      category (str): Indicates the device category ('gazoo', 'other' or
        'all') to retrieve.

    Returns:
      dict: Configuration obtained for the device found
      None: if device not found.

    Notes:
      If category is not specified then all devices will be used to find the
      matching identifier.
    """
    devices = self.get_devices(category)
    if name in devices:
      return devices[name]
    else:
      logger.debug("Unable to find device {}", name)
      return None

  def _get_device_name(self, identifier, category="all", raise_error=False):
    """Returns the device key name for the device.

    Args:
        identifier (str): Name or alias to search for.
        category (str): Device category. Options: ('gazoo', 'other', or
          'all') Default: 'all'.
        raise_error (bool): raise error if unable to find device. Default:
          False

    Returns:
      str: Device key name to use for the identifier specified.
      None: If device not found and raise_error is false.

    Raises:
      DeviceError: If identifier is not string/unicode or device does not
      exist

    Notes:
      If category is not specified then all devices will be used to find
      the matching identifier.
    """
    if not isinstance(identifier, str):
      raise errors.DeviceError("Device identifier '{}' should be a string. "
                               "but instead it is a {}".format(
                                   str(identifier), str(type(identifier))))
    aliases = self._get_aliases(category)
    identifier = identifier.lower()
    if identifier not in aliases:
      logger.debug("Unable to find device {}", identifier)
      if not raise_error:
        return None
      close_matches = difflib.get_close_matches(identifier, aliases)
      raise errors.DeviceError(
          "Device {} is not known. Close matches: {}".format(
              identifier, ", ".join(close_matches)))
    return aliases[identifier]

  def _get_device_usb_hub_name_and_port(self, device_name):
    """Returns the hub_name and port for the USB hub configured for the device.

    Args:
        device_name (str): device identifier.

    Returns:
        tuple: usb_hub_name, usb_port These will be set to None if the
        device or the
                                      property are not defined.
    """
    hub_name = None
    hub_port = None
    if device_name in self.options_dict:
      hub_name = self.options_dict[device_name].get("usb_hub", None)
      hub_port = self.options_dict[device_name].get("usb_port", None)
    if device_name in self.persistent_dict:
      hub_name = self.persistent_dict[device_name].get("device_usb_hub_name",
                                                       hub_name)
      hub_port = self.persistent_dict[device_name].get("device_usb_port",
                                                       hub_port)
    if hub_port:
      hub_port = int(hub_port)
    return hub_name, hub_port

  def get_devices(self, category):
    """Returns a dict of all devices for the category specified.

    Args:
        category (str): device category (gazoo, other, or all) to retrieve

    Returns:
        dict: device_name, device_instance
    """
    devices = {}
    devices.update(self._devices if category in ["all", "gazoo"] else {})
    devices.update(self.other_devices if category in ["all", "other"] else {})
    return devices

  def _get_device_prop(self, identifier, prop=None):
    """Gets a prop's value for a device if the device and the prop exist.

    Args:
      identifier (str): name, serial_number, alias, or adb_serial of the
        device.
      prop (str): Name of a single property to fetch.

    Returns:
      dict: if prop is None.  The full device_config
      value: The value of that prop if prop specified.

    Raises:
      DeviceError: if device doesn't exist or not queryable
      ValueError: if property not available

    Note: The full device config is a multi-level dict.  Top level keys are
        "persistent", "optional", "dynamic", with prop_value pairs in the
        next level. If device is connected it will fill out dynamic properties.
    """
    # Validate the prop input.
    self._type_check("Prop", prop, allowed_types=(type(None), str))

    logger.debug("Getting prop for identifier: {} Attr: {}".format(
        identifier, prop))
    close_device = True
    device_name = self._get_device_name(identifier, raise_error=True)
    if device_name in self.get_open_device_names():
      close_device = False
      device = self.get_open_device(device_name)
    else:
      device = self.create_device(identifier, make_device_ready="off")
    try:
      if prop:  # Return a specific property.
        prop = prop.lower()
        if prop in ["communication_type", "device_type"]:
          prop = prop.upper()
        # Don't need to activate device:
        offline_props = list(device.get_persistent_property_names())
        offline_props += list(device.get_optional_property_names())
        offline_props += list(device.props["optional"].keys())
        if prop in offline_props:
          return device.get_property(prop)
        device.make_device_ready()
        return device.get_property(prop, raise_error=True)

      # prop is None, so return the whole list of props
      device_config = {}
      device_config["persistent"] = device.get_persistent_properties()
      device_config["optional"] = device.get_optional_properties()
      if device.connected:
        try:
          device.make_device_ready()
          device_config["dynamic"] = device.get_dynamic_properties()
        except errors.DeviceError:
          device_config["dynamic"] = {"connected": True, "status": "Unhealthy."}

      else:
        device_config["dynamic"] = {"connected": False}
      return device_config
    finally:
      if close_device:
        device.close()

  def _get_attributes_list(self, device_config, just_props=False):
    """Return public attributes of class.

    Args:
      device_config (dict): device configuration dict
      just_props (bool): If just_props, returns non-method attributes.

    Returns:
      list: attributes
    """
    device_type = device_config["persistent"]["device_type"]
    this_class = self.get_supported_device_class(device_type)
    all_attributes = [a for a in dir(this_class) if not a.startswith("_")]
    if just_props:
      all_props = [
          a for a in all_attributes
          if not inspect.isroutine(hasattr(this_class, a))
      ]
      return all_props
    return all_attributes

  def _get_device_class(self,
                        device_class,
                        device_config,
                        log_file_name,
                        log_directory,
                        track_device=True):
    """Returns the device class after adding it to the list of shared resources."""
    device = device_class(
        self,
        device_config,
        log_file_name=log_file_name,
        log_directory=log_directory)
    if track_device:
      self._open_devices[device.name] = device
    return device

  def _get_device_sim_class(self, device_class, device_config, log_file_name,
                            log_directory, build_info_kwargs):
    """Returns the device class after adding it to the list of shared resources."""
    device = device_class(
        self,
        device_config,
        log_file_name=log_file_name,
        log_directory=log_directory,
        build_info_kwargs=build_info_kwargs)
    self._open_devices[device.name] = device
    return device

  def _issue_devices(self,
                     devices,
                     method_name,
                     timeout=parallel_utils.TIMEOUT_PROCESS,
                     **kwargs):
    """Execute a device method in parallel for multiple devices.

    Args:
        devices (list): list of device identifiers.
        method_name (str): name of device method to execute in parallel.
        timeout (int): maximum amount of seconds to allow parallel methods
          to complete.
        **kwargs (dict): arguments to pass to device method.

    Returns:
        list: list of results from parallel calls, if any.

    Raises:
        DeviceError: if a provided device does not have a method with name
        method_name.
    """
    device_names = []
    parameter_dicts = {}
    for device_id in devices:

      # collect names of devices that support method
      device_name = self._get_device_name(device_id, raise_error=True)
      device_type = self.get_device_configuration(
          device_name)["persistent"]["device_type"]
      device_class = self.get_supported_device_class(device_type)
      if not hasattr(device_class, method_name):
        raise errors.DeviceError("Device {} does not support method {}".format(
            device_id, method_name))
      else:
        device_names.append(device_name)
        parameter_dicts[device_type] = kwargs

    # create device instances
    device_instances = [
        self.create_device(device_name, make_device_ready="off")
        for device_name in device_names
    ]

    # execute device methods in parallel using parallel_utils
    try:
      results = parallel_utils.issue_devices_parallel(method_name,
                                                      device_instances,
                                                      parameter_dicts, timeout)
    finally:
      for device in device_instances:
        device.close()

    if results:
      return results

  def _load_configuration(self,
                          device_file_name=None,
                          device_options_file_name=None,
                          testbeds_file_name=None,
                          gdm_config_file_name=None,
                          log_directory=None,
                          adb_path=None):
    """Loads GDM configuration.

    Args:
        device_file_name (str): Device file name.
        device_options_file_name (str): Device options file name.
        testbeds_file_name (str): Testbeds file name.
        gdm_config_file_name (str): GDM config file name.
        log_directory (str): Log directory.
        adb_path (str): "adb" binary path.

    Raises:
        DeviceError: failed to load Manager config.
    """
    self.gdm_config_file_name = gdm_config_file_name

    # create and configure self.config from gdm.conf
    self._load_gdm_configuration()

    # configure self.config from parameters
    self._add_correct_path_to_config("device_file_name", device_file_name,
                                     config.DEFAULT_DEVICE_FILE)

    self._add_correct_path_to_config("device_options_file_name",
                                     device_options_file_name,
                                     config.DEFAULT_OPTIONS_FILE)

    self._add_correct_path_to_config("testbeds_file_name", testbeds_file_name,
                                     config.DEFAULT_TESTBEDS_FILE)

    self._add_correct_path_to_config("log_directory", log_directory,
                                     config.DEFAULT_LOG_DIRECTORY)
    self._add_correct_value_to_config(config.ADB_BIN_PATH_CONFIG, adb_path, "")

    self._load_devices()
    self._load_other_devices()
    self._load_testbeds()

  def _load_devices(self):
    devices = self._load_config(self.device_file_name, config.DEVICES_KEYS[0])
    device_options = self._load_config(self.device_options_file_name,
                                       config.OPTIONS_KEYS[0])
    (self.aliases, self._devices, self.persistent_dict,
     self.options_dict) = self._combine_devices_and_device_options(
         devices, device_options)

  def _load_other_devices(self):
    other_devices = self._load_config(self.device_file_name,
                                      config.DEVICES_KEYS[1])
    other_device_options = self._load_config(self.device_options_file_name,
                                             config.OPTIONS_KEYS[1])
    (self.other_aliases, self.other_devices, self.other_persistent_dict,
     self.other_options_dict) = self._combine_devices_and_device_options(
         other_devices, other_device_options)

  def _load_testbeds(self):
    self.testbeds = self._load_config(self.testbeds_file_name,
                                      config.TESTBED_KEYS[0])

  def _load_gdm_configuration(self):
    self._generate_config_files()
    self.config = self._load_config(self.gdm_config_file_name, None)

  def _generate_config_files(self):
    """Generate config files if files or folders are missing.

    Raises:
      DeviceError: if unable to access files.
    """
    # Ensure all folders exist and have correct permissions.
    expected_permissions = "755"
    for folder in config.REQUIRED_FOLDERS:
      if not os.path.exists(folder):
        os.makedirs(folder)
      permissions = oct(os.stat(folder).st_mode)[-3:]
      if permissions != expected_permissions:
        try:
          os.chmod(folder, int(expected_permissions, 8))
        except OSError:
          raise errors.DeviceError(
              f"Unable to set correct permissions on {folder} without "
              f"sudo. Current permissions: {permissions}. Please run "
              f"sudo chmod -R {expected_permissions} {folder}'")

    # Ensure all files exist and are correctly populated
    config_info = {
        "device_file_name": config.DEFAULT_DEVICE_FILE,
        "device_options_file_name": config.DEFAULT_OPTIONS_FILE,
        "testbeds_file_name": config.DEFAULT_TESTBEDS_FILE,
        "log_directory": config.DEFAULT_LOG_DIRECTORY,
        "cli_extension_packages": [],
    }
    self._create_dict_if_doesnt_exist(config_info,
                                      config.DEFAULT_GDM_CONFIG_FILE)
    self._create_dict_if_doesnt_exist({key: {} for key in config.DEVICES_KEYS},
                                      config.DEFAULT_DEVICE_FILE)
    self._create_dict_if_doesnt_exist({key: {} for key in config.OPTIONS_KEYS},
                                      config.DEFAULT_OPTIONS_FILE)
    self._create_dict_if_doesnt_exist({key: {} for key in config.TESTBED_KEYS},
                                      config.DEFAULT_TESTBEDS_FILE)

  def _create_dict_if_doesnt_exist(self, a_dict, file_path):
    """Populates a file if it doesn't yet exist."""
    if not os.path.exists(file_path):
      with open(file_path, "w+") as open_file:
        json.dump(a_dict, open_file)

  def _load_config(self, file_name, key=None):
    """Loads a json config from a file into a dict and returns the dict.

    Args:
      file_name (str): The json file path.
      key (str): Indicates which dict entry caller is interested in.

    Returns:
      dict: The return value depends on key value. If the key value is None,
            the whole dict will return to caller.
      str: If there's a key specified, returns just the entry from that key.

    Raises:
      DeviceError: Device load configuration failed.
    """
    if not os.path.exists(file_name):
      raise errors.DeviceError(
          "Device load configuration failed. "
          "File {} is not found. \n Current directory: {}".format(
              file_name, os.getcwd()))

    with open(file_name, "r") as open_file:
      for i in range(2):
        try:
          conf = json.load(open_file)
          break
        except Exception as err:
          msg = "Unable to parse GDM config file as a json file. {!r}".format(
              err)

          if i == 1:
            raise errors.DeviceError(msg)
          else:
            logger.debug(msg)

    if key is None:
      return conf
    if key not in conf:
      return {}
    else:
      return conf[key]

  def _make_device_configs(self, devices, other_devices, device_options,
                           other_device_options):
    """Creates device configs with the provided dictionaries."""
    device_config = {"devices": devices, "other_devices": other_devices}
    device_options_config = {
        "device_options": device_options,
        "other_device_options": other_device_options
    }
    return (device_config, device_options_config)

  def set_prop(self, device_name, prop, value):
    """Sets a property's value for device or GDM configuration depends on identifier.

    Args:
      device_name (str): "manager", name, serial_number, alias, or
        adb_serial of the device.
      prop (str): Public prop available in device_options.json or gdm.json.
      value (str): Input value for specific property.

    Returns:
      bool: True if set_prop operation success.
    """
    if self._is_manager_config(device_name):
      return self._set_config_prop(prop, value)
    else:
      return self._set_device_prop(device_name, prop, value)

  def remove_prop(self, identifier, prop):
    """Removes a property for device if it's an optional property.

    Args:
      identifier (str): device identifier.
      prop (str): name of device property

    Raises:
      DeviceError: Attempts to remove property from manager or non-optional
      property.
    """
    if self._is_manager_config(identifier):
      raise errors.DeviceError("Not configured for manager.")
    else:
      self._remove_device_prop(identifier, prop)

  def _is_manager_config(self, identifier):
    """Check if identifier belongs to manager or not.

    Args:
      identifier (str): To check if it belongs to manager configuration.

    Returns:
      bool: If identifier is "manager" return True, otherwise return False.
    """
    if identifier == "manager":
      return True
    else:
      return False

  def _print_device_info_by_category(self, category="gazoo"):
    """Logs the device info in a special format.

    Args:
      category (str): 'gazoo' or 'other'.
    """
    format_line = "{:26} {:15} {:20} {:20} {:10}"
    if category == "gazoo":
      device_dict = self._devices
      title = "Device"
      connected_title = "Connected"
      good_status = "connected"
    else:
      device_dict = self.other_devices
      title = "Other Devices"
      connected_title = "Available"
      good_status = "available"
    logger.info(
        format_line.format(title, "Alias", "Type", "Model", connected_title))
    logger.info(
        format_line.format("-" * 26, "-" * 15, "-" * 20, "-" * 20, "-" * 10))
    for name in sorted(device_dict.keys()):
      device_config = device_dict[name]
      device_type = device_config["persistent"]["device_type"]
      model = device_config["persistent"]["model"]
      alias = device_config["options"].get("alias",
                                           "<undefined>") or u"<undefined>"
      if self.is_device_connected(name, category):
        status = good_status
      else:
        status = "unavailable"

      logger.info(format_line.format(name, alias, device_type, model, status))
    logger.info("")

  def _process_exceptions(self, signum, frame):  # pylint: disable=unused-argument
    """Retrieves and raises exceptions in exception_queue from all subprocesses created.

    Args:
        signum (int): signal number provided to this signal handler
        frame (object): current stack frame provided to this signal handler

    Raises:
        DeviceError: containing exception information received
    """

    try:
      exception_message = self._exception_queue.get_nowait()
      self._exception_queue.task_done()
    except (queue.Empty, ValueError):
      exception_message = "Exception queue missing exception message on SIGUSR1"
    except AttributeError:
      exception_message = "Exception queue deleted by parent process"

    raise errors.DeviceError(exception_message)

  def _set_device_prop(self, identifier, prop, value):
    """Sets a property's value for device.

    Args:
      identifier (str): name, serial_number, alias, or adb_serial of the
        device.
      prop (str): Public prop available in device_options.json.
      value (str): Input value for specific property.

    Raises:
      DeviceError: Device not found.

    Returns:
      bool: True if _set_device_prop operation success.
    """
    self._type_check("Property name", prop)
    self._type_check(prop, value, allowed_types=(str, type(None), int))
    device_name = self._get_device_name(identifier, raise_error=True)
    close_device = True
    if device_name in self.get_open_device_names():
      close_device = False
      device = self.get_open_device(device_name)
    else:
      device = self.create_device(identifier, make_device_ready="off")
    try:
      if prop == "alias":
        self._realign_alias(value, device.alias, device.name)
      device.set_property(prop, value)
    finally:
      if close_device:
        device.close()
    if device_name in self._devices:
      a_dict = self._devices
    else:
      a_dict = self.other_devices
    a_dict[device_name]["options"][prop] = value
    self._save_config_to_file(
        {
            "device_options": self.options_dict,
            "other_device_options": self.other_options_dict
        }, self.device_options_file_name)
    return True

  def _remove_device_prop(self, identifier, prop):
    """Removes prop from device config dict and file if in 'options'.

    Args:
      identifier (str): name, serial_number, alias, or adb_serial of the
        device.
      prop (str): Public prop available in device_options.json.

    Raises:
      DeviceError: Device not found or property not optional.
    """
    device_config = self.get_device_configuration(identifier)
    if prop in device_config["options"]:
      del device_config["options"][prop]
      self._save_config_to_file(
          {
              "device_options": self.options_dict,
              "other_device_options": self.other_options_dict
          }, self.device_options_file_name)
    else:
      raise errors.DeviceError(
          "Property {} is not an optional property for {}.".format(
              prop, identifier))

  def _realign_alias(self, new_alias, old_alias, name):
    """Modifying self.aliases when device's alias changes.

    Args:
      new_alias (str): new alias for device.
      old_alias (str): old alias of device.
      name (str): device name.
    """
    if old_alias is not None:
      del self.aliases[old_alias.lower()]
    if new_alias is not None:
      self.aliases[new_alias.lower()] = name

  def _set_config_prop(self,
                       prop: str,
                       value: custom_types.PropertyValue) -> None:
    """Sets an GDM config property.

    Args:
      prop: Manager property available in gdm.json.
      value: Property value.
    """
    self._type_check("value", value, allowed_types=(str, type(None), int, list))
    self._type_check("prop", prop)
    self.config[prop] = value
    # save property to json file
    self._save_config_to_file(self.config, self.gdm_config_file_name)

  def _save_config_to_file(self, a_dict, file_path):
    """Saves the dictionary to the given file."""
    logger.debug("Overwriting {}", file_path)
    config_directory = os.path.dirname(file_path)
    temp_file_path = os.path.join(config_directory,
                                  "temp_config_{}.json".format(os.getpid()))
    with open(temp_file_path, "w") as open_file:
      json.dump(a_dict, open_file, sort_keys=True, indent=4)
    shutil.move(temp_file_path, file_path)

  def _type_check(self, name, value, allowed_types=(str,)):
    """Sanity checking of (string or None) input values.

    Args:
      name (str): Name of the item being checked (for error messages).
      value (str): The item being verified.
      allowed_types (tuple): Tuple of "types".

    Raises:
      DeviceError: if value doesn't pass type check.

    Notes:
      Verifies the type, and for string inputs confirms there are no spaces,
      tabs, non-ascii, carriage-returns.
    """
    if not isinstance(value, allowed_types):
      raise errors.DeviceError(
          "{} {}'s type is not one of {}, but a {!r} instead".format(
              name, value, [t.__name__ for t in allowed_types],
              type(value).__name__))
    if isinstance(value, str):
      if not value:
        raise errors.DeviceError("{} {}'s value is illegally empty".format(
            name, value))
      if len(value.encode("ascii", "ignore")) != len(value):
        raise errors.DeviceError(
            "{} {} contains illegal non-ascii characters.".format(name, value))

      if " " in value:
        raise errors.DeviceError("{} {} contains illegal spaces".format(
            name, value))
      if "\t" in value:
        raise errors.DeviceError("{} {} contains illegal tabs".format(
            name, value))
      if "\n" in value:
        raise errors.DeviceError("{} {} contains illegal returns".format(
            name, value))

  def _update_device_config(self, device_config, skip_recover_device,
                            make_device_ready, log_name_prefix, filters):
    """Updates the device config based on the input params."""
    device_config["skip_recover_device"] = skip_recover_device
    device_config["make_device_ready"] = make_device_ready
    device_config["log_name_prefix"] = log_name_prefix
    device_config["filters"] = filters
    if "persistent" and "options" in device_config:
      if "device_usb_hub_name" not in device_config["persistent"]:
        if "usb_hub" in device_config["options"] and device_config["options"][
            "usb_hub"]:
          device_config["persistent"]["device_usb_hub_name"] = \
              device_config["options"]["usb_hub"]
      if "device_usb_port" not in device_config["persistent"]:
        if "usb_port" in device_config["options"] and device_config["options"][
            "usb_port"]:
          device_config["persistent"]["device_usb_port"] = \
              device_config["options"]["usb_port"]

  def __del__(self):
    self.close()
