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
"""Queries sent to devices during detection to determine their device type."""
import copy
import enum
import functools
import logging
import re
import subprocess
import typing
from typing import Any, Callable, Collection, Dict, List, Union

from gazoo_device import config
from gazoo_device import errors
from gazoo_device import extensions
from gazoo_device.base_classes import auxiliary_device_base
from gazoo_device.base_classes import primary_device_base
from gazoo_device.capabilities.interfaces import switchboard_base
from gazoo_device.utility import host_utils
from gazoo_device.utility import http_utils
from gazoo_device.utility import pwrpc_utils
from gazoo_device.utility import usb_utils
import immutabledict
import requests

_DeviceClassType = Union[auxiliary_device_base.AuxiliaryDeviceBase,
                         primary_device_base.PrimaryDeviceBase]
_LOG_FORMAT = "<%(asctime)s> GDM-M: %(message)s"

_ADB_COMMANDS = immutabledict.immutabledict({})

_DOCKER_COMMANDS = immutabledict.immutabledict({
    "PRODUCT_NAME": "docker ps --filter id={} --format {{{{.Names}}}}",
})

_SSH_COMMANDS = immutabledict.immutabledict({
    "IS_CHIP_TOOL_PRESENT": "which chip-tool",
    "UNIFI_PRODUCT_NAME": "mca-cli-op info",
    "DLI_PRODUCT_NAME": "http://{address}/restapi/config/=brand_name/",
    "RPI_PRODUCT_NAME": "cat /proc/device-tree/model",
})

_GET_DLINK_MODEL_SNMP_COMMAND = (
    "snmpget -v 2c -c private {ip_address}:161 1.3.6.1.2.1.1.1.0")
_MODEL_RESPONSE_REG_EX = r"DGS-1100.+? Gigabit Ethernet Switch"
_SNMP_TIMEOUT_S = 10

_UNIFI_MODEL_PREFIXES = ("USW-", "US-")


@functools.total_ordering
class QueryEnum(enum.Enum):
  """Allows comparison of enum properties for sorting purposes."""

  def __lt__(self, other):
    return self.name < other.name  # pylint: disable=comparison-with-callable


class AdbQuery(QueryEnum):
  is_serial_number = "is_serial_number"


class DockerQuery(QueryEnum):
  product_name = "product_name"


class GenericQuery(QueryEnum):
  always_true = "always_true"


class PigweedQuery(QueryEnum):
  """Query names for detection for PigweedSerialComms Devices."""
  app_type = "app_type"
  product_name = "usb info product_name"
  manufacturer_name = "usb info manufacturer_name"


class PtyProcessQuery(QueryEnum):
  product_name = "product_name"


class SerialQuery(QueryEnum):
  product_name = "usb info product_name"
  serial_number = "usb serial_numer"
  vendor_product_id = "VENDOR_ID:PRODUCT_ID"


class SnmpQuery(QueryEnum):
  """Query names for detection of SnmpComms Devices."""
  is_dlink = "is_dlink_power_switch"


class SshQuery(QueryEnum):
  """Query names for detection for SshComms Devices."""
  is_dli = "is_dli_power_switch"
  is_rpi = "is_raspberry_pi"
  is_unifi = "is_unifi_switch"
  is_chip_tool_present = "is_chip_tool_installed_on_rpi"


class UsbQuery(QueryEnum):
  product_name = "usb product name"
  serial_number = "serial_number"
  vendor_product_id = "VENDOR_ID:PRODUCT_ID"


def _docker_product_name_query(
    address: str, detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> str:
  """Gets product name from docker device."""
  del create_switchboard_func  # Unused by _docker_product_name_query
  try:
    name = subprocess.check_output(
        _DOCKER_COMMANDS["PRODUCT_NAME"].format(address).split())
    name = name.decode()
  except subprocess.CalledProcessError as err:
    detect_logger.info(
        "_docker_product_name_query failed for %s: %r", address, err)
    return ""
  return name


def _always_true_query(
    address: str, detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> bool:
  """Used when there is just one type of device for a communication type."""
  del address, create_switchboard_func, detect_logger  # Unused.
  return True


def _adb_is_serial_number_query(
    address: str,
    detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> bool:
  """Returns True if address is a serial number, False if it's an IP address."""
  del create_switchboard_func, detect_logger  # Unused.
  return not re.search(host_utils.IP_ADDRESS, address)


def _is_dli_query(
    address: str, detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> bool:
  """Determines if address belongs to dli power switch."""
  del create_switchboard_func  # Unused by _is_dli_query
  try:
    response = http_utils.send_http_get(
        _SSH_COMMANDS["DLI_PRODUCT_NAME"].format(address=address),
        auth=requests.auth.HTTPDigestAuth("admin", "1234"),
        headers={"Accept": "application/json"},
        valid_return_codes=[200, 206, 207],
        timeout=1)
    name = response.text
  except RuntimeError as err:
    detect_logger.info("_is_dli_query failed for %s: %r", address, err)
    return False
  return "Power Switch" in name


def get_dlink_model_name(ip_address: str) -> str:
  """Returns the model name of the Dlink switch at the ip_address."""
  command = _GET_DLINK_MODEL_SNMP_COMMAND.format(ip_address=ip_address)
  # Expected response for 5 port model should look like:
  # "DGS-1100-05 Gigabit Ethernet Switch"
  response = subprocess.check_output(
      command.split(), text=True, timeout=_SNMP_TIMEOUT_S)
  match = re.search(_MODEL_RESPONSE_REG_EX, response)
  if match:
    return match[0]
  raise errors.DeviceError(f"Failed to retrieve model name from dlink_switch "
                           f"with command: {command}\n"
                           f"Unexpected output: {response}")


def _is_dlink_query(
    address: str, detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> bool:
  """Determines if address belongs to dli power switch."""
  del create_switchboard_func  # Unused by _is_dlink_query
  try:
    model = get_dlink_model_name(ip_address=address)
    detect_logger.info(f"Got response to sysDescr SNMP query: {model}\n"
                       f"_is_dlink_query response: True")
  except (subprocess.CalledProcessError, errors.DeviceError) as err:
    detect_logger.info("_is_dlink_query failure: " + repr(err))
    return False
  return True


def _is_rpi_query(
    address: str, detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> bool:
  """Determines if address belongs to raspberry pi."""
  del create_switchboard_func  # Unused by _is_rpi_query
  try:
    name = host_utils.ssh_command(
        address,
        command=_SSH_COMMANDS["RPI_PRODUCT_NAME"],
        user="pi",
        key_info=config.KEYS["raspberrypi3_ssh_key"])
  except RuntimeError as err:
    detect_logger.info("_is_rpi_query failed for %s: %r", address, err)
    return False
  return "Raspberry Pi" in name


def _is_chip_tool_installed_query(
    address: str, detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> bool:
  """Determines whether chip-tool is installed on an RPI."""
  del create_switchboard_func  # Unused by _is_chip_tool_installed_query
  try:
    host_utils.ssh_command(
        address,
        command=_SSH_COMMANDS["IS_CHIP_TOOL_PRESENT"],
        user="pi",
        key_info=config.KEYS["raspberrypi3_ssh_key"])
  except RuntimeError as err:
    detect_logger.info(
        "_is_chip_tool_installed_query failed for %s: %r", address, err)
    return False
  return True


def _is_unifi_query(
    address: str, detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> bool:
  """Determines if address belongs to unifi poe switch."""
  del create_switchboard_func  # Unused by _is_unifi_query
  try:
    mca_info = host_utils.ssh_command(
        address,
        _SSH_COMMANDS["UNIFI_PRODUCT_NAME"],
        user="admin",
        key_info=config.KEYS["unifi_switch_ssh_key"])
  except RuntimeError as err:
    detect_logger.info("_is_unifi_query failed for %s: %r", address, err)
    return False

  for model_prefix in _UNIFI_MODEL_PREFIXES:
    if model_prefix in mca_info:
      return True
  return False


def _pty_process_name_query(
    address: str, detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> str:
  """Returns product name from pty process comms address directory.

  Args:
    address: The communication address.
    detect_logger: The logger of device interactions.
    create_switchboard_func: Method to create the switchboard.
  """
  del create_switchboard_func, detect_logger  # Unused.
  return address


def usb_product_name_query(
    address: str, detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> str:
  """Gets product name from usb_info."""
  del create_switchboard_func, detect_logger  # Unused.
  return usb_utils.get_product_name_from_path(address).lower()


def _usb_serial_number_from_serial_port_path(
    address: str, detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> str:
  """Gets serial number from serial port path."""
  del create_switchboard_func, detect_logger  # Unused.
  return usb_utils.get_serial_number_from_path(address)


def _usb_vendor_product_id_from_serial_port_path(
    address: str, detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> str:
  """Gets USB vendor ID and product ID from serial port path."""
  del create_switchboard_func, detect_logger  # Unused.
  device_info = usb_utils.get_device_info(address)
  return f"{device_info.vendor_id}:{device_info.product_id}"


def _usb_product_name_from_serial_number(
    address: str,
    detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> str:
  """Returns USB product name from serial number.

  Args:
    address: Serial number of the device. USB devices are addressed by their
      serial number.
    detect_logger: The logger of device interactions.
    create_switchboard_func: Method to create the switchboard.

  Returns:
    Product name from USB descriptor.
  """
  del create_switchboard_func  # Unused
  device = usb_utils.get_usb_device_from_serial_number(address)
  detect_logger.info(
      "_usb_product_name_from_serial_number: USB device is %r", device)
  return device.product if device else ""


def _usb_vendor_product_id_query(
    address: str, detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> str:
  """Returns USB vendor and product ID from serial number.

  Args:
    address: Serial number of the device. USB devices are addressed by their
      serial number.
    detect_logger: The logger of device interactions.
    create_switchboard_func: Method to create the switchboard.

  Returns:
    Vendor and product ID string of the USB device that has a matching
    serial number.
    Format of the string is VENDOR_ID:PRODUCT_ID in hex. E.g. '0ab1:fe23'.
    Returns empty string if address is not found.
  """
  del create_switchboard_func  # Unused by usb_vendor_product_id_query
  # Address contains serial number for USB devices
  device = usb_utils.get_usb_device_from_serial_number(address)
  detect_logger.info("_usb_vendor_product_id_query: USB device is %r", device)
  return f"{device.idVendor:04x}:{device.idProduct:04x}" if device else ""


def _usb_serial_number(
    address: str, detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> str:
  """Returns the serial number from a USB device.

  This detection criteria should be used in conjunction with
  _usb_vendor_product_id_query to narrow down a match.

  This function is particularly useful to matching FTDI manufacturer IDs
  which should be consistent between products that use FTDI chipsets. The
  manufacturer's ID is the first two characters in the serial number.
  See:
  https://www.ftdichip.com/Support/Knowledgebase/howistheautomaticserialnu.htm

  Args:
    address: Serial number of the device. USB devices are addressed by their
      serial number.
    detect_logger: The logger of device interactions.
    create_switchboard_func: Method to create the switchboard.

  Returns:
    Serial number.
  """
  del create_switchboard_func, detect_logger  # Unused.
  return address


def _manufacturer_name_query(
    address: str, detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> str:
  """Gets manufacturer name from usb_info."""
  del create_switchboard_func, detect_logger  # Unused.
  return usb_utils.get_device_info(address).manufacturer.lower()


def _pigweed_application_query(
    address: str, detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> str:
  """Gets Pigweed application type of the device.

  Args:
    address: The communication address.
    detect_logger: The logger of device interactions.
    create_switchboard_func: Method to create the switchboard.

  Returns:
    Pigweed application type.
  """
  file_handler = typing.cast(logging.FileHandler, detect_logger.handlers[0])
  log_path = file_handler.baseFilename
  return pwrpc_utils.get_application_type(
      address, log_path, create_switchboard_func)


GENERIC_QUERY_DICT = immutabledict.immutabledict({
    GenericQuery.always_true: _always_true_query,
})

ADB_QUERY_DICT = immutabledict.immutabledict({
    AdbQuery.is_serial_number: _adb_is_serial_number_query,
})

DOCKER_QUERY_DICT = immutabledict.immutabledict({
    DockerQuery.product_name: _docker_product_name_query,
})

PIGWEED_QUERY_DICT = immutabledict.immutabledict({
    PigweedQuery.app_type: _pigweed_application_query,
    PigweedQuery.product_name: usb_product_name_query,
    PigweedQuery.manufacturer_name: _manufacturer_name_query,
})

PTY_PROCESS_QUERY_DICT = immutabledict.immutabledict({
    PtyProcessQuery.product_name: _pty_process_name_query,
})

SERIAL_QUERY_DICT = immutabledict.immutabledict({
    SerialQuery.product_name: usb_product_name_query,
    SerialQuery.serial_number: _usb_serial_number_from_serial_port_path,
    SerialQuery.vendor_product_id: _usb_vendor_product_id_from_serial_port_path,
})

SNMP_QUERY_DICT = immutabledict.immutabledict({
    SnmpQuery.is_dlink: _is_dlink_query,
})

SSH_QUERY_DICT = immutabledict.immutabledict({
    SshQuery.is_dli: _is_dli_query,
    SshQuery.is_rpi: _is_rpi_query,
    SshQuery.is_unifi: _is_unifi_query,
    SshQuery.is_chip_tool_present: _is_chip_tool_installed_query,
})

USB_QUERY_DICT = immutabledict.immutabledict({
    UsbQuery.product_name: _usb_product_name_from_serial_number,
    UsbQuery.serial_number: _usb_serial_number,
    UsbQuery.vendor_product_id: _usb_vendor_product_id_query,
})

DETECT_CRITERIA = immutabledict.immutabledict({
    "AdbComms": ADB_QUERY_DICT,
    "DockerComms": DOCKER_QUERY_DICT,
    "JlinkSerialComms": SERIAL_QUERY_DICT,
    "PigweedSerialComms": PIGWEED_QUERY_DICT,
    "PtyProcessComms": PTY_PROCESS_QUERY_DICT,
    "SerialComms": SERIAL_QUERY_DICT,
    "SnmpComms": SNMP_QUERY_DICT,
    "SshComms": SSH_QUERY_DICT,
    "UsbComms": USB_QUERY_DICT,
    "YepkitComms": GENERIC_QUERY_DICT,
})


def determine_device_class(
    address: str, communication_type: str, log_file_path: str,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> List[_DeviceClassType]:
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
    device_classes = get_communication_type_classes(communication_type)
    return find_matching_device_class(address, communication_type,
                                      detect_logger, create_switchboard_func,
                                      device_classes)
  finally:
    file_handler = detect_logger.handlers[0]
    file_handler.close()
    detect_logger.removeHandler(file_handler)


def find_matching_device_class(
    address: str, communication_type: str, detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase],
    device_classes: Collection[_DeviceClassType]) -> List[_DeviceClassType]:
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
    if _matches_criteria(responses, device_class.DETECT_MATCH_CRITERIA):
      matching_classes.append(device_class)
      detect_logger.info("\t%s: Match.", device_class.DEVICE_TYPE)
    else:
      detect_logger.info("\t%s: No Match.", device_class.DEVICE_TYPE)
  return matching_classes


def get_communication_type_classes(
    communication_type: str) -> List[_DeviceClassType]:
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
    if device_class.COMMUNICATION_TYPE == communication_type:
      matching_classes.append(device_class)
  return matching_classes


def _get_detect_query_response(
    address: str, communication_type: str, detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> Dict[str, Any]:
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
      detect_logger.info("%s failed for %s: %r", query_name, address, err)
      query_responses[query_name] = repr(err)

    if not isinstance(query_responses[query_name], (str, bool)):
      detect_logger.warning(
          "%s returned invalid response type %s for %s!",
          query_name, type(query_responses[query_name]), address)

  return query_responses


def _matches_criteria(responses, match_criteria):
  """Checks if response dict matches match criteria.

  There are two categories of values in match_criteria: bool and regexp/str.
  Bools must match exactly, while regexp must find a match in the response
  value.

  Args:
    responses (dict): device responses keyed by query name.
    match_criteria (dict): match values keyed by query name.

  Returns:
    bool: whether or not responses meets match criteria
  """
  for entry, value in match_criteria.items():
    if isinstance(value, bool):
      if responses[entry] != value:
        return False
    else:
      if not re.search(value, responses[entry]):
        return False
  return True


def _setup_logger(log_file_path: str) -> logging.Logger:
  """Set up a logger to log device interactions to the detect file."""
  detect_logger = logging.getLogger(log_file_path)
  detect_logger.setLevel(logging.DEBUG)
  handler = logging.FileHandler(log_file_path)
  formatter = logging.Formatter(_LOG_FORMAT)
  handler.setFormatter(formatter)
  detect_logger.addHandler(handler)
  return detect_logger
