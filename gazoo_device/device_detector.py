# Copyright 2023 Google LLC
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
import logging
import os
import re
import time
import typing
from typing import Any, Callable, Collection, Mapping, Optional, Union
import weakref

from gazoo_device import config
from gazoo_device import custom_types
from gazoo_device import data_types
from gazoo_device import device_types
from gazoo_device import errors
from gazoo_device import extensions
from gazoo_device import gdm_logger
from gazoo_device.base_classes import auxiliary_device_base
from gazoo_device.capabilities.interfaces import switchboard_base
from gazoo_device.detect_criteria import base_detect_criteria
from gazoo_device.switchboard.communication_types import ssh_comms
from gazoo_device.utility import common_utils
from gazoo_device.utility import host_utils

WIKI_URL = (
    "https://github.com/google/gazoo-device/blob/master/docs/device_setup")
_LOG_FORMAT = "<%(asctime)s> %(filename)-20s:%(lineno)d: %(message)s"

_DeviceClassType = type[device_types.Device]

logger = gdm_logger.get_logger()


def _setup_logger(log_file_path: str) -> logging.Logger:
  """Set up a logger to log device interactions to the detect file."""
  detect_logger = logging.getLogger(log_file_path)
  detect_logger.setLevel(logging.DEBUG)
  handler = logging.FileHandler(log_file_path)
  formatter = logging.Formatter(_LOG_FORMAT)
  handler.setFormatter(formatter)
  detect_logger.addHandler(handler)
  return detect_logger


def _get_detect_query_response(
    address: str, communication_type: str, detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> dict[base_detect_criteria.QueryEnum, Union[bool, str]]:
  """Gathers device responses for all queries of that communication type.

  Args:
    address: communication_address
    communication_type: category of communication.
    detect_logger: logs device interactions.
    create_switchboard_func: Method to create the switchboard.

  Returns:
    Device responses keyed by query enum member.
  """
  query_responses = {}
  detect_queries = extensions.detect_criteria[communication_type]
  for query_name, query in detect_queries.items():
    try:
      query_responses[query_name] = query(
          address=address,
          detect_logger=detect_logger,
          create_switchboard_func=create_switchboard_func)
      detect_logger.info("%s response from %s: %r",
                         query_name, address, query_responses[query_name])
    except Exception as err:  # pylint: disable=broad-except
      detect_logger.info("%s failed for %s: %r", query_name, address, err,
                         exc_info=True)
      query_responses[query_name] = repr(err)

    if not isinstance(query_responses[query_name], (str, bool)):
      detect_logger.warning(
          "%s returned invalid response type %s for %s!",
          query_name, type(query_responses[query_name]), address)

  return query_responses


def _matches_criteria(
    responses: Mapping[base_detect_criteria.QueryEnum, Union[bool, str]],
    match_criteria: Mapping[base_detect_criteria.QueryEnum, Union[bool, str]]
) -> bool:
  """Checks if response dict matches match criteria.

  There are two categories of values in match_criteria: bool and regexp/str.
  Bools must match exactly, while regexp must find a match in the response
  value.

  Args:
    responses: Device responses keyed by query name.
    match_criteria: Match values keyed by query name.

  Returns:
    Whether or not responses meets match criteria
  """
  for entry, value in match_criteria.items():
    if entry not in responses:
      # The detection criterion of the device class didn't have an associated
      # response. This can happen if the device class had not been registered
      # before detection was called.
      return False
    if isinstance(value, bool):
      if responses[entry] != value:
        return False
    else:
      if not re.search(value, responses[entry]):
        return False
  return True


def _find_matching_device_class(
    address: str, communication_type: str, detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase],
    device_classes: Collection[_DeviceClassType]) -> list[_DeviceClassType]:
  """Returns all classes where the device responses match the detect criteria.

  Args:
    address: communication_address.
    communication_type: category of communication.
    detect_logger: logs device interactions.
    create_switchboard_func: Method to create the switchboard.
    device_classes: device classes whose match criteria must be compared to.

  Returns:
    list: classes where the device responses match the detect criteria.
  """
  matching_classes = []
  responses = _get_detect_query_response(address, communication_type,
                                         detect_logger, create_switchboard_func)
  detect_logger.info(
      "Possible %s device types: %s",
      communication_type,
      [device_class.DEVICE_TYPE for device_class in device_classes])
  for device_class in device_classes:
    if not all(
        detect_criterion in responses
        for detect_criterion in device_class.DETECT_MATCH_CRITERIA.keys()):
      detect_logger.info(
          "\t%s: No Match. Not all detect criteria had a response. "
          "The device class likely hasn't been registered.\n"
          "%'s detect criteria: %s\n"
          "Collected responses: %s",
          device_class.DEVICE_TYPE,
          list(device_class.DETECT_MATCH_CRITERIA.keys()),
          list(responses.keys())
      )
      continue
    if _matches_criteria(responses, device_class.DETECT_MATCH_CRITERIA):
      matching_classes.append(device_class)
      detect_logger.info("\t%s: Match.", device_class.DEVICE_TYPE)
    else:
      detect_logger.info("\t%s: No Match.", device_class.DEVICE_TYPE)
  return matching_classes


def _get_communication_type_classes(
    communication_type: str) -> list[_DeviceClassType]:
  """Returns classes with that communication type.

  Args:
    communication_type: category of communication.

  Returns:
    list: classes with that communication type.
  """
  all_classes = copy.copy(extensions.auxiliary_devices)
  all_classes += copy.copy(extensions.primary_devices)
  all_classes += copy.copy(extensions.virtual_devices)
  matching_classes = []
  for device_class in all_classes:
    if device_class.COMMUNICATION_TYPE.__name__ == communication_type:
      matching_classes.append(device_class)
  return matching_classes


def _determine_device_class(
    address: str, communication_type: str, log_file_path: str,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> list[_DeviceClassType]:
  """Returns the device class(es) that matches the address' responses.

  Compares the device_classes DETECT_MATCH_CRITERIA to the device responses.

  Args:
    address: communication_address.
    communication_type: category of communication.
    log_file_path: local path to write log messages to.
    create_switchboard_func: Method to create the switchboard.

  Returns:
    list: classes where the device responses match the detect criteria.
  """
  detect_logger = _setup_logger(log_file_path)
  try:
    device_classes = _get_communication_type_classes(communication_type)
    return _find_matching_device_class(address, communication_type,
                                       detect_logger, create_switchboard_func,
                                       device_classes)
  finally:
    file_handler = detect_logger.handlers[0]
    file_handler.close()
    detect_logger.removeHandler(file_handler)


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
      supported_auxiliary_device_classes:
      list[type[auxiliary_device_base.AuxiliaryDeviceBase]]):
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
      self, static_ips: Optional[list[str]] = None,
      comm_types: Optional[Collection[str]] = None,
      addresses: Optional[Collection[str]] = None
    ) -> tuple[
        custom_types.PersistentConfigsDict,
        custom_types.OptionalConfigsDict]:
    """Finds all possible new connections and detects devices.

    Args:
      static_ips: Static ips not otherwise detectable.
      comm_types: Limit detection to specific communication types.
      addresses: Limit detection to specific communication addresses.

    Returns:
      (Dicts of persistent props, dict of optional props).
    """
    logger.info(
        "\n##### Step 1/3: "
        "Detecting potential new communication addresses. #####\n"
    )
    all_connections_dict = detect_connections(
        static_ips=static_ips, comm_types=comm_types, addresses=addresses)
    return self.detect_new_devices(all_connections_dict)

  def detect_new_devices(
      self, connections_dict: dict[str, list[str]]
    ) -> tuple[
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

    possible_device_tuples, errs, no_id_cons = (
        self._identify_connection_device_class(connections_dict))
    new_names = []
    logger.info(
        "\n##### "
        "Step 3/3: Extract Persistent Info from Detected Devices. #####\n"
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
      device_class: _DeviceClassType,
      name: str,
      persistent_props: custom_types.DeviceConfig,
      optional_props: custom_types.DeviceConfig) -> None:
    """Adds newly detect info to appropriate location in config.

    Args:
        device_class: device class
        name: name of device
        persistent_props: dict of device's persistent props
        optional_props: dict of device's optional props

    Raises:
        DetectionOvewriteConfigError: if device name already is
            in persistent config.
    """

    if device_class in self.auxiliary_classes:
      ind = 1
      more_props = {key: None for key in config.HUB_OPTION_ATTRIBUTES}
    else:
      ind = 0
      more_props = {key: None for key in config.DEVICE_OPTION_ATTRIBUTES}
    devices_config_key = config.DEVICES_KEYS[ind]

    # Add generic props to options
    optional_props.update(more_props)

    if name in self.persistent_configs[devices_config_key]:
      raise errors.DetectionOvewriteConfigError(
          name,
          persistent_props["console_port_name"],
          self.persistent_configs[devices_config_key][name]["console_port_name"]
          )

    self.persistent_configs[devices_config_key][name] = persistent_props
    self.options_configs[config.OPTIONS_KEYS[ind]][name] = optional_props

  def _create_known_connections(self) -> list[str]:
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
      self, device_class: _DeviceClassType, connection: str
  ) -> tuple[str, custom_types.DeviceConfig, custom_types.DeviceConfig]:
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
    logger.info("Getting info from communication port %s for %s",
                connection, device_type)
    device = device_class(  # pytype: disable=not-instantiable
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
      self, con_dict: dict[str, list[str]], known_cons: list[str]
  ) -> dict[str, list[str]]:
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
      new_con_dict[key] = []
      discarded_connections = []
      for con in con_list:
        if con.replace(":5555", "") not in known_cons:
          new_con_dict[key].append(con)
        else:
          discarded_connections.append(con)
      if discarded_connections:
        logger.info("Discarded %d known %s connections:",
                    len(discarded_connections), key)
        logger.info("\t" + "\n\t".join(sorted(discarded_connections)))
      if new_con_dict[key]:
        logger.info("Found %d new possible %s connections:",
                    len(new_con_dict[key]), key)
        logger.info("\t" + "\n\t".join(sorted(new_con_dict[key])))
    return new_con_dict

  def _generate_name(
      self,
      device_type: str,
      serial_number: str,
      device_class: _DeviceClassType) -> str:
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
      # Check if it's the same device or not
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
      self, connections_dict: dict[str, list[str]]
  ) -> tuple[
      list[tuple[_DeviceClassType, str]],
      list[str],
      list[str]]:
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
      logger.info("Identifying %s devices..", communication_type)
      for connection in sorted(connections_dict[communication_type]):
        detect_log = os.path.join(
            self.log_directory,
            self._get_detect_log_file_name(connection, communication_type))
        matching_classes = _determine_device_class(
            connection,
            communication_type,
            detect_log,
            # Don't use Manager for type annotation to avoid a circular import.
            typing.cast(
                Any, self.manager_weakref()).create_switchboard
        )
        if len(matching_classes) > 1:
          matching_device_types = [
              device_class.DEVICE_TYPE for device_class in matching_classes
          ]
          warning_msg = (
              "Warning: Multiple device types matched connection "
              f"{connection}: {matching_device_types}. "
              "This is a bug in the registered extension packages: "
              f"{extensions.get_registered_package_info()}. "
              f"Returning {matching_device_types[0]}.")
          logger.warning(warning_msg)
          errs.append(warning_msg)
        if matching_classes:
          logger.info("\t%s is a %s. See %s for details.",
                      connection, matching_classes[0].DEVICE_TYPE, detect_log)
          possible_device_tuples.append((matching_classes[0], connection))
        else:
          info_msg = (
              f"\t{connection} responses did not match a known "
              f"{communication_type} device type. "
              f"See {detect_log} for details.")
          logger.info(info_msg)
          errs.append(info_msg)
          no_id_cons.append(connection)
      logger.info("\t%s device_type detection complete.", communication_type)
    return possible_device_tuples, errs, no_id_cons

  def _print_summary(
      self, names: list[str], errs: list[str], no_id_cons: list[str]) -> None:
    """Prints summary of detection events.

    Args:
        names: list of detected names.
        errs: list of errors.
        no_id_cons: list of undetected connections.
    """
    logger.info("\n##### Detection Summary #####\n")
    logger.info("\t%d new devices detected:%s", len(names),
                "\n\t\t" + "\n\t\t".join(sorted(names)))
    if errs:
      logger.info("\n\t%d errors/warnings:%s", len(errs),
                  "\n\t\t" + "\n\t\t".join(errs))
    if no_id_cons:
      logger.info("\n\t%d connections found but not detected:%s",
                  len(no_id_cons), "\n\t\t" + "\n\t\t".join(sorted(no_id_cons)))
    if errs or no_id_cons:
      logger.info("\nIf a connection failed detection, check %s for tips\n",
                  WIKI_URL)


def _validate_comm_types(
    comm_types: Optional[Collection[str]] = None) -> Optional[Collection[str]]:
  """Validate that the communication types specified for detection are valid.

  A warning will be logged if a non-supported communication is included in
  the provided comm types.

  Args:
   comm_types: Specific communication types to use for detection.

  Returns:
    Lowercase supported communication types to use for detection.
  """
  if comm_types is None:
    return None

  lowercase_supported_types = [comm_type.lower() for comm_type in
                               extensions.communication_types.keys()]
  validated_comm_types = []
  invalid_comm_types = []
  for comm_type in comm_types:
    if comm_type.lower() in lowercase_supported_types:
      validated_comm_types.append(comm_type.lower())
    else:
      invalid_comm_types.append(comm_type)

  if invalid_comm_types:
    logger.warning("Unknown communication types specified %s. "
                   "Known communication types %s.",
                   ", ".join(invalid_comm_types),
                   ", ".join(extensions.communication_types.keys()))

  return validated_comm_types


def detect_connections(
    static_ips: Optional[Collection[str]] = None,
    comm_types: Optional[Collection[str]] = None,
    addresses: Optional[Collection[str]] = None) -> dict[str, list[str]]:
  """Detects all the communication addresses for the different devices.

  Args:
    static_ips: Static ip addresses.
    comm_types: Limit detection to specific communication types.
    addresses: Limit detection to specific communication addresses.

  Returns:
    Connections by connection class name from classes in this module
    and other registered classes in extensions.communication_types.
  """
  lowercase_comm_types = _validate_comm_types(comm_types)

  connections_dict = {comms_name: []
                      for comms_name in extensions.communication_types}
  for comms_name, comms_class in sorted(extensions.communication_types.items()):
    if lowercase_comm_types is not None:
      if comms_name.lower() not in lowercase_comm_types:
        logger.info(
            "Skipping detection for %s communication types.", comms_name)
        continue

    logger.info(
        "\tdetecting potential %s communication addresses", comms_name)
    detection_method = comms_class.get_comms_addresses
    try:
      try:
        comms_addresses = detection_method(static_ips=static_ips)
      except TypeError:  # method does not accept static_ips
        comms_addresses = detection_method()
      if comms_addresses:
        logger.info(
            "\tFound %d potential %s communication addresses.",
            len(comms_addresses), comms_name)
        logger.info("\t\t" + "\n\t\t".join(sorted(comms_addresses)))
      selected_comms_addresses = [
          addr for addr in comms_addresses
          if addresses is None or addr in addresses]
      not_selected_comms_addresses = list(
          set(comms_addresses) - set(selected_comms_addresses))
      connections_dict[comms_name] = selected_comms_addresses
      if not_selected_comms_addresses:
        logger.info(
            "Skipping detection for %s communication addresses.",
            not_selected_comms_addresses)

        # Verify ssh keys exist if ssh connections are detected
      if issubclass(comms_class, ssh_comms.SshComms) and comms_addresses:
        missing_keys = []
        ssh_keys = [
            key_info for key_info in extensions.key_to_download_function
            if key_info.type == data_types.KeyType.SSH
        ]
        for ssh_key in ssh_keys:
          try:
            host_utils.verify_key(ssh_key)
          except ValueError as err:  # Failed to set permissions on the key
            logger.warning(repr(err))
          except (errors.DownloadKeyError, FileNotFoundError, RuntimeError):
            missing_keys.append(ssh_key)
        if missing_keys:
          logger.warning("Found %d missing SSH keys:\n%s\n"
                         "Detection of SSH devices may not work correctly. "
                         "Run 'gdm download-keys'.",
                         len(missing_keys),
                         "\n".join(str(key) for key in missing_keys))
    except Exception as err:  # pylint: disable=broad-except
      logger.warning(
          "Unable to detect %s communication addresses. Err: %s",
          comms_name,
          err,
      )
  return connections_dict
