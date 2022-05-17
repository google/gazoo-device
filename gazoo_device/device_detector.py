# Copyright 2022 Google LLC
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

"""Device detector module."""
import copy
import os
import time
import typing
from typing import Any, Collection, Dict, List, Optional, Tuple
import weakref

from gazoo_device import config
from gazoo_device import custom_types
from gazoo_device import detect_criteria
from gazoo_device import extensions
from gazoo_device import gdm_logger
from gazoo_device.base_classes import auxiliary_device_base
from gazoo_device.switchboard import communication_types
from gazoo_device.utility import common_utils
from gazoo_device.utility import pty_process_utils

WIKI_URL = (
    "https://github.com/google/gazoo-device/blob/master/docs/device_setup")
logger = gdm_logger.get_logger()


class DeviceDetector:
  """Class for detecting devices.

  Class scans systems for all connections, filters out known connections,
  then attempts to assign connection to right device classes and create
  entry in configs for persistent info (such as ID and serial_number)
  """

  def __init__(
      self,
      manager: Any,
      log_directory: str,
      persistent_configs: custom_types.PersistentConfigsDict,
      options_configs: custom_types.OptionalConfigsDict,
      supported_auxiliary_device_classes: List[
          auxiliary_device_base.AuxiliaryDeviceBase]):
    """Initializes the device detector.

    Args:
        manager: instance of Manager.
        log_directory: location of logs.
        persistent_configs: devices known to the manager.
        options_configs: device options known to the manager.
        supported_auxiliary_device_classes: list of auxiliary device
            classes.
    """
    self.manager_weakref = weakref.ref(manager)
    self.log_directory = log_directory
    self.auxiliary_classes = supported_auxiliary_device_classes
    self.persistent_configs = copy.deepcopy(persistent_configs)
    self.options_configs = copy.deepcopy(options_configs)
    self.known_connections = self._create_known_connections()

  def detect_all_new_devices(
      self, static_ips: Optional[List[str]] = None,
      comm_types: Optional[Collection[str]] = None
    ) -> Tuple[
        custom_types.PersistentConfigsDict,
        custom_types.OptionalConfigsDict]:
    """Finds all possible new connections and detects devices.

    Args:
      static_ips: Static ips not otherwise detectable.
      comm_types: Limit detection to specific communication types.

    Returns:
      (Dicts of persistent props, dict of optional props).
    """
    logger.info(
        "\n##### Step 1/3: Detecting potential new communication addresses. #####\n"
    )
    all_connections_dict = communication_types.detect_connections(
        static_ips=static_ips, comm_types=comm_types)
    return self.detect_new_devices(all_connections_dict)

  def detect_new_devices(
      self, connections_dict: Dict[str, List[str]]
    ) -> Tuple[
        custom_types.PersistentConfigsDict,
        custom_types.OptionalConfigsDict]:
    """Detects the devices for given connections.

    --> Filters out known connections
    --> Determine device type
    --> Detects persistent info
    --> Updates persistent and optional configs
    --> Tracks errors and unidentified connections and Writes a summary

    Args:
        connections_dict: connection device paths grouped by connection name.
            The connection name corresponds with connection class names
            in communication_types.py

    Returns:
        (persistent_configs, options_configs) for all devices (new and old).
    """

    connections_dict = self._filter_out_known_connections(
        connections_dict, self.known_connections)

    possible_device_tuples, errs, no_id_cons = self._identify_connection_device_class(
        connections_dict)
    new_names = []
    logger.info(
        "\n##### Step 3/3: Extract Persistent Info from Detected Devices. #####\n"
    )
    for device_class, connection in possible_device_tuples:
      try:
        name, persistent_props, optional_props = self._detect_get_info(
            device_class, connection)
        new_names.append(name)
        self._add_to_configs(device_class, name, persistent_props,
                             optional_props)
      except Exception as err:  # pylint: disable=broad-except
        msg = "Error extracting info from {} {!r}. Err: {!r}".format(
            device_class.DEVICE_TYPE, connection, err)
        errs.append(msg)
        no_id_cons.append(connection)

    self._print_summary(new_names, errs, no_id_cons)
    return self.persistent_configs, self.options_configs

  def _add_to_configs(
      self,
      device_class: custom_types.Device,
      name: str,
      persistent_props: custom_types.DeviceConfig,
      optional_props: custom_types.DeviceConfig) -> None:
    """Adds newly detect info to appropriate location in config.

    Args:
        device_class: device class
        name: name of device
        persistent_props: dict of device's persistent props
        optional_props: dict of device's optional props
    """

    if device_class in self.auxiliary_classes:
      ind = 1
      more_props = {key: None for key in config.HUB_OPTION_ATTRIBUTES}
    else:
      ind = 0
      more_props = {key: None for key in config.DEVICE_OPTION_ATTRIBUTES}

    # Add generic props to options
    optional_props.update(more_props)

    self.persistent_configs[config.DEVICES_KEYS[ind]][name] = persistent_props
    self.options_configs[config.OPTIONS_KEYS[ind]][name] = optional_props

  def _create_known_connections(self) -> List[str]:
    """Returns all known connections.

    Returns:
       Known connection paths.
    """
    known_connections = []

    for entry in self.persistent_configs["devices"].values():
      identifier = entry.get("console_port_name")
      if not identifier:
        # Use the IP address instead of the ADB port for ADB over IP
        identifier = typing.cast(str, entry["adb_serial"]).replace(":5555", "")
      known_connections.append(typing.cast(str, identifier))
    for entry in self.persistent_configs["other_devices"].values():
      identifier = entry.get("console_port_name")
      if not identifier:
        identifier = entry["hub_port_name"]
      known_connections.append(typing.cast(str, identifier))

    return known_connections

  def _detect_get_info(
      self, device_class: custom_types.Device, connection: str
  ) -> Tuple[str, custom_types.DeviceConfig, custom_types.DeviceConfig]:
    """Returns name, persistent and optional info from device communication.

    Note: Any errors raised will be caught in parent method.

    Args:
        device_class: device class with get_detection_info method.
        connection: path to communication

    Returns:
        (Name, dict of persistent props, dict of options props).
    """
    device_type = device_class.DEVICE_TYPE
    detect_file = self._get_detect_log_file_name(connection, device_type)
    device_config = {
        "persistent": {
            "console_port_name": connection,
            "device_type": device_type,
            "name": "\t{}_detect".format(device_type)
        },
        "options": {},
        "make_device_ready": "on"
    }
    logger.info("Getting info from communication port {} for {}".format(
        connection, device_type))

    if device_class.COMMUNICATION_TYPE == "PtyProcessComms":
      device_config["persistent"]["console_port_name"] = (
          pty_process_utils.get_launch_command(
              connection, **device_class.PTY_PROCESS_COMMAND_CONFIG))

    device = device_class(
        manager=self.manager_weakref(),
        device_config=device_config,
        log_directory=self.log_directory,
        log_file_name=detect_file)
    try:
      device.make_device_ready()
      persistent_props, options_props = device.get_detection_info()
    finally:
      device.close()

    name = self._generate_name(device_type, persistent_props["serial_number"],
                               device_class)
    persistent_props["name"] = name
    return name, persistent_props, options_props

  def _filter_out_known_connections(
      self, con_dict: Dict[str, List[str]], known_cons: List[str]
  ) -> Dict[str, List[str]]:
    """Filters out already known connections.

    Args:
        con_dict: dictionary of detected connections by
            connection class name as defined in communication_types.py
        known_cons: list of known connections paths.

    Returns:
        Filtered dictionary of unknown connections by connection class name.
    """
    new_con_dict = {}
    for key, con_list in con_dict.items():
      new_con_dict[key] = [
          con for con in con_list
          if con.replace(u":5555", u"") not in known_cons
      ]
      if new_con_dict[key]:
        logger.info("Found {} possible {} connections:".format(
            len(new_con_dict[key]), key))
        logger.info(u"\t" + u"\n\t".join(new_con_dict[key]))
    return new_con_dict

  def _generate_name(
      self,
      device_type: str,
      serial_number: str,
      device_class: custom_types.Device) -> str:
    """Generates name from last four digits of serial_number.

    Note: If there is a conflict with a different device it will generate a
        longer name.

    Args:
        device_type: device type.
        serial_number: device serial number.
        device_class: identifying class

    Returns:
        str: name of device

    Raises:
        RuntimeError: if serial number is too short.
    """
    if len(serial_number) < 4:
      raise RuntimeError("{} serial number {} is too short.".format(
          device_type, serial_number))
    name = "{}-{}".format(device_type, serial_number[-4:].lower())

    # Check if name already exists
    if device_class in self.auxiliary_classes:
      key = "other_devices"
    else:
      key = "devices"
    if name in self.persistent_configs[key]:
      # Check if its the same device or not
      if serial_number != self.persistent_configs[key][name]["serial_number"]:
        name = "{}-{}".format(device_type, serial_number[-8:].lower())
    return name

  def _get_detect_log_file_name(
      self, address: str, comm_type_or_device_type: str) -> str:
    name = common_utils.extract_posix_portable_characters(
        address.replace("/", "_"))
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    return f"{name}_{comm_type_or_device_type}_detect_{timestamp}.txt"

  def _identify_connection_device_class(
      self, connections_dict: Dict[str, List[str]]
  ) -> Tuple[
      List[Tuple[custom_types.Device, str]],
      List[str],
      List[str]]:
    """Detects all connections' appropriate device class.

    Args:
        connections_dict: dictionary of connections by communication type

    Returns:
        (List of (class, connection), errs, connections). not id'd
    """
    possible_device_tuples = []
    errs = []
    no_id_cons = []
    logger.info("\n##### Step 2/3 Identify Device Type of Connections. #####\n")

    for communication_type in sorted(connections_dict.keys()):
      if not connections_dict[communication_type]:
        # No connections of that type.
        continue
      logger.info("Identifying {} devices..".format(communication_type))
      for connection in connections_dict[communication_type]:
        detect_log = os.path.join(
            self.log_directory,
            self._get_detect_log_file_name(connection, communication_type))
        matching_classes = detect_criteria.determine_device_class(
            connection,
            communication_type,
            detect_log,
            # pytype: disable=attribute-error
            self.manager_weakref().create_switchboard
            # pytype: enable=attribute-error
        )
        if len(matching_classes) > 1:
          device_types = [
              device_class.DEVICE_TYPE for device_class in matching_classes
          ]
          logger.warning(
              "Warning: Multiple device classes matched connection {}. "
              "This is a bug in the registered extension packages ({}). "
              "Returning {}.".format(device_types,
                                     extensions.get_registered_package_info(),
                                     device_types[0]))
        if matching_classes:
          logger.info("\t{} is a {}. See {} for details.".format(
              connection, matching_classes[0].DEVICE_TYPE, detect_log))
          possible_device_tuples.append((matching_classes[0], connection))
        else:
          logger.info("\t{} responses did not match a known {} device type. "
                      "See {} for details.".format(connection,
                                                   communication_type,
                                                   detect_log))
          no_id_cons.append(connection)
      logger.info(
          "\t{} device_type detection complete.".format(communication_type))
    return possible_device_tuples, errs, no_id_cons

  def _print_summary(
      self, names: List[str], errs: List[str], no_id_cons: List[str]) -> None:
    """Prints summary of detection events.

    Args:
        names: list of detected names.
        errs: list of errors.
        no_id_cons: list of undetected connections.
    """
    logger.info("\n##### Detection Summary #####\n")
    logger.info("\t%d new devices detected:%s", len(names),
                "\n\t\t" + "\n\t\t".join(names))
    if errs:
      logger.info("\n\t%d errors/warnings:%s", len(errs),
                  "\n\t\t" + "\n\t\t".join(errs))
    if no_id_cons:
      logger.info("\n\t%d connections found but not detected:%s",
                  len(no_id_cons), "\n\t\t" + "\n\t\t".join(no_id_cons))
    if errs or no_id_cons:
      logger.info("\nIf a connection failed detection, check %s for tips\n",
                  WIKI_URL)
