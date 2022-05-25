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
"""Built-in GDM communication types.

A communication type identifies all possible connections and maps them to
transports, buttons, data framers, and line identifiers.
"""
import abc
import os
import types
from typing import Any, Collection, Dict, List, Optional, Union

from gazoo_device import custom_types
from gazoo_device import data_types
from gazoo_device import errors
from gazoo_device import extensions
from gazoo_device import gdm_logger
from gazoo_device.switchboard import data_framer
from gazoo_device.switchboard import ftdi_buttons
from gazoo_device.switchboard import line_identifier
from gazoo_device.switchboard.transports import adb_transport
from gazoo_device.switchboard.transports import jlink_transport
from gazoo_device.switchboard.transports import pigweed_rpc_transport
from gazoo_device.switchboard.transports import pty_transport
from gazoo_device.switchboard.transports import serial_transport
from gazoo_device.switchboard.transports import ssh_transport
from gazoo_device.switchboard.transports import transport_base
from gazoo_device.utility import adb_utils
from gazoo_device.utility import host_utils
from gazoo_device.utility import usb_config
from gazoo_device.utility import usb_utils

logger = gdm_logger.get_logger()

JLINK_COMMS_PRODUCT_NAME = "J-Link"
CP2104_COMMS_PRODUCT_NAME = "CP2104"
USB_COMMS_PRODUCT_NAME = "USB Single Serial"
NRF_DK_COMMS_ADDRESS_LINUX = "SEGGER_J-Link"
NRF_DK_EFR32_COMMS_ADDRESS_MAC = "tty.usbmodem"
EFR32_COMMS_ADDRESS_LINUX = "Silicon_Labs_J-Link"
ESP32_M5STACK_CP2104_COMMS_ADDRESS_LINUX = "Silicon_Labs_CP2104"
ESP32_M5STACK_CP2104_COMMS_ADDRESS_MAC = "tty.usbserial"
ESP32_M5STACK_CH9102F_COMMS_ADDRESS_LINUX = "1a86_USB_Single_Serial"


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
    logger.warning(
        "Unknown communication types specified "
        f"{', '.join(invalid_comm_types)}. Known communication types "
        f"{', '.join(extensions.communication_types.keys())}.")

  return validated_comm_types


def detect_connections(
    static_ips: Optional[List[str]] = None,
    comm_types: Optional[Collection[str]] = None) -> Dict[str, List[str]]:
  """Detects all the communication addresses for the different devices.

  Args:
    static_ips: Static ip addresses.
    comm_types: Limit detection to specific communication types.

  Returns:
    Connections by connection class name from classes in this module
    and other registered classes in extensions.communication_types.
  """
  lowercase_comm_types = _validate_comm_types(comm_types)

  connections_dict = {}
  for comms_name, comms_class in extensions.communication_types.items():
    if lowercase_comm_types is not None:
      if comms_name.lower() not in lowercase_comm_types:
        logger.debug(
            f"Skipping detection for {comms_name} communication addresses.")
        continue

    logger.info(
        "\tdetecting potential {} communication addresses".format(comms_name))
    detection_method = comms_class.get_comms_addresses
    try:
      try:
        comms_addresses = detection_method(static_ips=static_ips)
      except TypeError:  # method does not accept static_ips
        comms_addresses = detection_method()
      connections_dict[comms_name] = comms_addresses
      logger.debug("Found {} potential communication addresses".format(
          len(comms_addresses)))

      # Verify ssh keys exist if ssh connections are detected
      if issubclass(comms_class, SshComms) and comms_addresses:
        missing_keys = []
        ssh_keys = [
            key_info for key_info in extensions.keys
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
          logger.warning("Found {} missing SSH keys:\n{}\n"
                         "Detection of SSH devices may not work correctly. "
                         "Run 'gdm download-keys'.".format(
                             len(missing_keys),
                             "\n".join(str(key) for key in missing_keys)))
    except Exception as err:  # pylint: disable=broad-except
      logger.warning(
          "Unable to detect {} communication addresses. Err: {!r}".format(
              comms_name, err))
  return connections_dict


def get_specific_serial_addresses(
    match_criteria: custom_types.MatchCriteria) -> List[str]:
  """Returns addresses for connections that match criteria.

  Excludes Android devices.
  Connections first excluded and then included.
  If there is no include regex, all instances that don't match exclude_regex
  are included.

  Dictionary entry: {'<key>':
  {'include_regex': <regex>, 'exclude_regex': '<regex>'}}

  Args:
    match_criteria: Criteria for finding a match.

  Returns:
    Addresses from UsbInfo instances that match criteria.
  """
  instances = usb_utils.find_matching_connections(match_criteria)
  accessible_instances = [
      instance for instance in instances
      if os.access(instance.address, os.R_OK | os.W_OK)
  ]
  inaccessible_addresses = [
      instance.address
      for instance in instances
      if instance not in accessible_instances
  ]
  if inaccessible_addresses:
    logger.warning(
        "No read/write permission for these serial address(es): {}".format(
            inaccessible_addresses))
  return [
      instance.address
      for instance in accessible_instances
      if instance.product_name not in usb_config.ANDROID_NAMES
  ]


class CommunicationType(abc.ABC):
  """Default settings for a communication type.

  Child classes should at minimum overwrite get_transport_list and
  get_comms_addresses.
  Child classes will likely overwrite init with their required args.
  """

  def __init__(self, comms_address: str) -> None:
    """Initiates args."""
    self.comms_address = comms_address

  def get_button_list(self) -> List[ftdi_buttons.FtdiButtons]:
    """Set ups the list of FTDI button instances as needed.

    For non-ftdi devices it just returns an empty list.

    Returns:
      FTDI button instances.
    """
    return []

  @classmethod
  @abc.abstractmethod
  def get_comms_addresses(cls) -> List[str]:
    """Detects the comms addresses that match this communication type.

    List can overlap those from other communication types.

    Returns:
      Potential communication addresses.
    """

  def get_data_framers(self,
                       num_transports: int) -> List[data_framer.DataFramer]:
    """Set up framers used to atomicize the raw output of the device.

    Deals with interwoven lines as well as tokenized output. Default
    is to use new line character to separate the lines.

    Args:
      num_transports: Number of declared transports.

    Returns:
      Data framers mapped to each transport.
    """
    return [data_framer.NewlineFramer()] * num_transports

  def get_identifier(self) -> line_identifier.AllUnknownIdentifier:
    """Setup identifiers used to distinguish loglines from responses.

    Defaults to labelling all as unknown.

    Returns:
      LineIdentifier: type of line identifier.
    """
    return line_identifier.AllUnknownIdentifier()

  def get_partial_line_timeout_list(self, num_transports: int) -> List[float]:
    """Time to wait before returning partial lines for a device.

    Args:
      num_transports: Number of declared transports.

    Returns:
      Timeouts for each transport.
    """
    return [.1] * num_transports

  def get_switchboard_kwargs(self) -> Dict[str, Any]:
    """Returns args needed to set up switchboard for this communication type.

    Returns:
      Dictionary of transport_list, identifier, framer_list, button_list.
    """
    transport_list = self.get_transport_list()
    num_transports = len(transport_list)
    return {
        "transport_list":
            transport_list,
        "identifier":
            self.get_identifier(),
        "framer_list":
            self.get_data_framers(num_transports),
        "button_list":
            self.get_button_list(),
        "partial_line_timeout_list":
            self.get_partial_line_timeout_list(num_transports),
    }

  @abc.abstractmethod
  def get_transport_list(self) -> List[transport_base.TransportBase]:
    """Setups up the transports which will communicate raw device io.

    Returns:
      list: Initiated transports.
    """


class AdbComms(CommunicationType):
  """Communication type for devices communicating over ADB.

  Commands/responses go over port 0 while logs are streamed over port 1.
  """

  def __init__(self,
               comms_address: str,
               log_cmd: str = "logcat -v threadtime",
               shell_cmd: str = "shell",
               event_log_cmd: Optional[str] = None) -> None:
    super().__init__(comms_address)
    self.log_cmd = log_cmd
    self.shell_cmd = shell_cmd
    self.event_log_cmd = event_log_cmd

  @classmethod
  def get_comms_addresses(cls) -> List[str]:
    """Returns ADB identifiers of available ADB devices."""
    return adb_utils.get_adb_devices()

  def get_transport_list(self) -> List[transport_base.TransportBase]:
    transports = [
        adb_transport.AdbTransport(
            comms_address=self.comms_address, command=self.shell_cmd),
        adb_transport.AdbTransport(
            comms_address=self.comms_address, command=self.log_cmd),
    ]
    if self.event_log_cmd:
      transports.append(
          adb_transport.AdbTransport(
              comms_address=self.comms_address, command=self.event_log_cmd))
    return transports

  def get_identifier(self) -> line_identifier.LineIdentifier:
    return line_identifier.PortLogIdentifier(log_ports=[1, 2])


class DockerComms(CommunicationType):
  """Communication type for VDL Docker devices."""

  def __init__(self,
               comms_address: str,
               secondary_comms_address: Optional[str] = None,
               secondary_log_pattern: Optional[str] = None) -> None:
    super().__init__(comms_address)
    self.secondary_comms_address = secondary_comms_address
    self.secondary_log_pattern = secondary_log_pattern

  @classmethod
  def get_comms_addresses(cls) -> List[str]:
    return host_utils.get_all_vdl_docker_connections()

  def get_transport_list(self) -> List[transport_base.TransportBase]:
    docker_exec_args = "exec -i {} /bin/bash".format(self.comms_address)
    docker_logs_args = "logs -f {}".format(self.comms_address)
    return [
        pty_transport.PtyTransport("docker", docker_exec_args),
        pty_transport.PtyTransport("docker", docker_logs_args)
    ]


class JlinkSerialComms(CommunicationType):
  """Communication type for JLINK and UART communication simultaneously.

  Serial is used for primary communication while jlink is used for log
  streaming.
  """

  @classmethod
  def get_comms_addresses(cls):
    return []

  def __init__(self, comms_address: str, baudrate: int = 115200) -> None:
    super().__init__(comms_address)
    self.secondary_address = usb_utils.get_serial_number_from_path(
        comms_address)
    self.baudrate = baudrate

  def get_transport_list(self) -> List[transport_base.TransportBase]:
    return [
        serial_transport.SerialTransport(
            comms_address=self.comms_address, baudrate=self.baudrate),
        jlink_transport.JLinkTransport(comms_address=self.secondary_address)
    ]

  def get_identifier(self) -> line_identifier.PortLogIdentifier:
    return line_identifier.PortLogIdentifier()


class PigweedSerialComms(CommunicationType):
  """Communication type for device communication over Pigweed RPC serial."""

  @classmethod
  def get_comms_addresses(cls) -> List[str]:
    include_product = [
        JLINK_COMMS_PRODUCT_NAME, CP2104_COMMS_PRODUCT_NAME,
        USB_COMMS_PRODUCT_NAME]
    include_address = [
        NRF_DK_COMMS_ADDRESS_LINUX, NRF_DK_EFR32_COMMS_ADDRESS_MAC,
        EFR32_COMMS_ADDRESS_LINUX, ESP32_M5STACK_CP2104_COMMS_ADDRESS_LINUX,
        ESP32_M5STACK_CP2104_COMMS_ADDRESS_MAC,
        ESP32_M5STACK_CH9102F_COMMS_ADDRESS_LINUX
    ]
    match_criteria = {
        "product_name": {
            "include_regex": "|".join(include_product)
        },
        "address": {
            "include_regex": "|".join(include_address)
        }
    }
    return get_specific_serial_addresses(match_criteria)

  def __init__(self,
               comms_address: str,
               protobufs: Collection[types.ModuleType],
               baudrate: int = serial_transport.DEFAULT_BAUDRATE):
    super().__init__(comms_address)
    self.protobufs = protobufs
    self.baudrate = baudrate

  def get_transport_list(self) -> List[transport_base.TransportBase]:
    protobuf_import_paths = [module.__name__ for module in self.protobufs]
    return [
        pigweed_rpc_transport.PigweedRPCTransport(
            comms_address=self.comms_address,
            protobuf_import_paths=protobuf_import_paths,
            baudrate=self.baudrate)
    ]


class PtyProcessComms(CommunicationType):
  """Communication type for communication with a process on the host machine.

  No detection provided.
  """

  @classmethod
  def get_comms_addresses(cls) -> List[str]:
    return host_utils.get_all_pty_process_directories()

  def __init__(self, comms_address: str) -> None:
    full_command_list = comms_address.split()
    comms_address = full_command_list[0]
    super().__init__(comms_address)
    self.args = " ".join(full_command_list[1:])

  def get_transport_list(self) -> List[pty_transport.PtyTransport]:
    return [pty_transport.PtyTransport(self.comms_address, args=self.args)]

  def get_identifier(self) -> line_identifier.AllUnknownIdentifier:
    return line_identifier.AllUnknownIdentifier()


class SshComms(CommunicationType):
  """Communication type for device communication over ssh.

  Login is handled by ssh-keys on machine (or device does not require
  password).

  Commands/responses are on port 0 while log streaming happens on port 1.
  """

  @classmethod
  def get_comms_addresses(cls, static_ips: List[str]) -> List[str]:
    return host_utils.get_all_ssh_ips(static_ips)

  def __init__(self,
               comms_address: str,
               log_cmd: str = "tail -F -n /var/log/messages",
               args: str = host_utils.DEFAULT_SSH_OPTIONS,
               key_info: Optional[data_types.KeyInfo] = None,
               username: str = "root") -> None:
    super().__init__(comms_address)
    self.log_cmd = log_cmd
    self.args = args
    self.username = username
    self.key_info = key_info

  def get_transport_list(self) -> List[ssh_transport.SSHTransport]:
    return [
        ssh_transport.SSHTransport(
            comms_address=self.comms_address,
            args=self.args,
            key_info=self.key_info,
            username=self.username),
        ssh_transport.SSHTransport(
            comms_address=self.comms_address,
            args=self.args,
            username=self.username,
            key_info=self.key_info,
            log_cmd=self.log_cmd)
    ]

  def get_identifier(self) -> line_identifier.PortLogIdentifier:
    return line_identifier.PortLogIdentifier(log_ports=[1])


class SnmpComms(CommunicationType):
  """Communication type for device communication over snmp protocol."""

  @classmethod
  def get_comms_addresses(cls, static_ips: List[str]) -> List[str]:
    return host_utils.get_all_snmp_ips(static_ips)

  def get_transport_list(self) -> List[transport_base.TransportBase]:
    # This comms type does not use Swtichboard so no transports exist.
    return []


class SerialComms(CommunicationType):
  """Communication type for device communication over basic serial."""

  def __init__(self,
               comms_address: str,
               log_line_regex: Optional[str] = None,
               baudrate: int = serial_transport.DEFAULT_BAUDRATE):

    super().__init__(comms_address)
    self.log_line_regex = log_line_regex
    self.baudrate = baudrate

  @classmethod
  def get_comms_addresses(cls) -> List[str]:
    exclude_products = [
        JLINK_COMMS_PRODUCT_NAME,
    ]
    exclude_product_ids = [
    ]

    match_criteria = {
        "product_name": {
            "exclude_regex": "|".join(exclude_products)
        },
        "product_id": {
            "exclude_regex": "|".join(exclude_product_ids)
        },
        "ftdi_interface": {
            "include_regex": "0|1"
        }
    }
    return get_specific_serial_addresses(match_criteria)

  def get_transport_list(self) -> List[serial_transport.SerialTransport]:
    return [
        serial_transport.SerialTransport(
            comms_address=self.comms_address, baudrate=self.baudrate)
    ]

  def get_identifier(
      self
  ) -> Union[line_identifier.AllUnknownIdentifier,
             line_identifier.RegexLogIdentifier]:
    if self.log_line_regex:
      return line_identifier.RegexLogIdentifier(self.log_line_regex)
    return super().get_identifier()


class UsbComms(CommunicationType):
  """Communication type for USB devices which don't leverage switchboard."""

  @classmethod
  def get_comms_addresses(cls) -> List[str]:
    devices = usb_utils.get_usb_devices_having_a_serial_number()
    return [d.serial_number for d in devices]

  def get_transport_list(self) -> List[transport_base.TransportBase]:
    return []


class YepkitComms(CommunicationType):
  """Communication type for yepkit devices.

  Currently supports just detection as communication does not yet work as
  expected.
  """

  @classmethod
  def get_comms_addresses(cls) -> List[str]:
    return host_utils.get_all_yepkit_serials()

  def get_transport_list(self) -> List[transport_base.TransportBase]:
    return []
