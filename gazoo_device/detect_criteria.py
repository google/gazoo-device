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
    "UNIFI_PRODUCT_NAME": "mca-cli-op info",
    "DLI_PRODUCT_NAME": "http://{address}/restapi/config/=brand_name/",
    "RPI_PRODUCT_NAME": "cat /proc/device-tree/model",
})

_UNIFI_MODEL_PREFIXES = ("USW-", "US-")


@functools.total_ordering
class QueryEnum(enum.Enum):
  """Allows comparison of enum properties for sorting purposes."""

  def __lt__(self, other):
    return self.name < other.name  # pylint: disable=comparison-with-callable


class AdbQuery(QueryEnum):
  pass


class DockerQuery(QueryEnum):
  product_name = "product_name"


class GenericQuery(QueryEnum):
  always_true = "always_true"


class PtyProcessQuery(QueryEnum):
  product_name = "product_name"


class SerialQuery(QueryEnum):
  product_name = "usb info product_name"


class SshQuery(QueryEnum):
  """Query names for detection for SshComms Devices."""
  is_dli = "is_dli_power_switch"
  is_rpi = "is_raspberry_pi"
  is_unifi = "is_unifi_switch"


class PigweedQuery(QueryEnum):
  """Query names for detection for PigweedSerialComms Devices."""
  app_type = "app_type"
  product_name = "usb info product_name"
  manufacturer_name = "usb info manufacturer_name"


def _docker_product_name_query(
    address: str,
    detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> str:
  """Gets product name from docker device."""
  del create_switchboard_func  # Unused by _docker_product_name_query
  try:
    name = subprocess.check_output(
        _DOCKER_COMMANDS["PRODUCT_NAME"].format(address).split())
    name = name.decode()
  except subprocess.CalledProcessError as err:
    detect_logger.info("_docker_product_name_query failure: " + repr(err))
    return ""
  detect_logger.info("_docker_product_name_query response: {}".format(name))
  return name


def _always_true_query(
    address: str,
    detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> bool:
  """Used when there is just one type of device for a communication type."""
  del address, create_switchboard_func  # Unused: query always returns True
  detect_logger.info("_always_true_query response: True")
  return True


def _is_dli_query(
    address: str,
    detect_logger: logging.Logger,
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
    detect_logger.info("_is_dli_query failure: " + repr(err))
    return False
  detect_logger.info("_is_dli_query response: {!r}".format(name))
  return "Power Switch" in name


def _is_rpi_query(
    address: str,
    detect_logger: logging.Logger,
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
    detect_logger.info("_is_rpi_query failure: " + repr(err))
    return False
  detect_logger.info("_is_rpi_query response: {!r}".format(name))
  return "Raspberry Pi" in name


def _is_unifi_query(
    address: str,
    detect_logger: logging.Logger,
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
    detect_logger.info("_is_unifi_query failure: " + repr(err))
    return False
  detect_logger.info("_is_unifi_query response: {!r}".format(mca_info))

  for model_prefix in _UNIFI_MODEL_PREFIXES:
    if model_prefix in mca_info:
      return True
  return False


def _pty_process_name_query(
    address: str,
    detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> str:
  """Returns product name from pty process comms address directory.

  Args:
    address: The communication address.
    detect_logger: The logger of device interactions.
    create_switchboard_func: Method to create the switchboard.
  """
  del create_switchboard_func  # Unused by _pty_process_name_query
  detect_logger.info("pty_process_name_query response: {}".format(address))
  return address


def usb_product_name_query(
    address: str,
    detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> str:
  """Gets product name from usb_info."""
  del create_switchboard_func  # Unused by usb_product_name_query
  product_name = usb_utils.get_product_name_from_path(address).lower()
  detect_logger.info(
      "usb_product_name_query response: {}".format(product_name))
  return product_name


def _manufacturer_name_query(
    address: str,
    detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> str:
  """Gets manufacturer name from usb_info."""
  del create_switchboard_func  # Unused by _manufacturer_name_query
  manufacturer = usb_utils.get_device_info(address).manufacturer.lower()
  detect_logger.info(
      "_manufacturer_name_query response: {}".format(manufacturer))
  return manufacturer


def _pigweed_application_query(
    address: str,
    detect_logger: logging.Logger,
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
  app_type = pwrpc_utils.get_application_type(address,
                                              log_path,
                                              create_switchboard_func)
  detect_logger.info(f"_pigweed_application_query response {app_type}")
  return app_type


GENERIC_QUERY_DICT = immutabledict.immutabledict({
    GenericQuery.always_true: _always_true_query,
})

ADB_QUERY_DICT = immutabledict.immutabledict({
})

DOCKER_QUERY_DICT = immutabledict.immutabledict({
    DockerQuery.product_name: _docker_product_name_query,
})

PTY_PROCESS_QUERY_DICT = immutabledict.immutabledict({
    PtyProcessQuery.product_name: _pty_process_name_query,
})

SERIAL_QUERY_DICT = immutabledict.immutabledict({
    SerialQuery.product_name: usb_product_name_query,
})

SSH_QUERY_DICT = immutabledict.immutabledict({
    SshQuery.is_dli: _is_dli_query,
    SshQuery.is_rpi: _is_rpi_query,
    SshQuery.is_unifi: _is_unifi_query,
})

PIGWEED_QUERY_DICT = immutabledict.immutabledict({
    PigweedQuery.app_type: _pigweed_application_query,
    PigweedQuery.product_name: usb_product_name_query,
    PigweedQuery.manufacturer_name: _manufacturer_name_query,
})

DETECT_CRITERIA = immutabledict.immutabledict({
    "AdbComms": ADB_QUERY_DICT,
    "DockerComms": DOCKER_QUERY_DICT,
    "JlinkSerialComms": SERIAL_QUERY_DICT,
    "PtyProcessComms": PTY_PROCESS_QUERY_DICT,
    "SerialComms": SERIAL_QUERY_DICT,
    "SshComms": SSH_QUERY_DICT,
    "YepkitComms": GENERIC_QUERY_DICT,
    "PigweedSerialComms": PIGWEED_QUERY_DICT,
})


def determine_device_class(
    address: str,
    communication_type: str,
    log_file_path: str,
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
    address: str,
    communication_type: str,
    detect_logger: logging.Logger,
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
  for device_class in device_classes:
    if _matches_criteria(responses, device_class.DETECT_MATCH_CRITERIA):
      matching_classes.append(device_class)
      detect_logger.info("{}: Match.".format(device_class.DEVICE_TYPE))
    else:
      detect_logger.info("{}: No Match.".format(device_class.DEVICE_TYPE))
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
    address: str,
    communication_type: str,
    detect_logger: logging.Logger,
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
    except Exception as err:
      detect_logger.debug(
          f"failed getting detect query response for {address}: {err!r}")
      query_responses[query_name] = repr(err)

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
