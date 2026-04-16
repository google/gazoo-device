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

"""SSH queries sent to devices during detection to determine their device type."""
import logging
from typing import Callable
from gazoo_device.capabilities.interfaces import switchboard_base
from gazoo_device.detect_criteria import base_detect_criteria
from gazoo_device.keys import raspberry_pi_key
from gazoo_device.keys import unifi_poe_switch_key
from gazoo_device.utility import host_utils
from gazoo_device.utility import http_utils
from gazoo_device.utility import pwrpc_utils
import immutabledict
import requests

_HTTP_ENDPOINTS = immutabledict.immutabledict({
    "DLI_PRODUCT_NAME": "http://{address}/restapi/config/=brand_name/"
})

_SSH_COMMANDS = immutabledict.immutabledict({
    "CURRENT_USER": ("whoami",),
    "IS_CHIP_TOOL_PRESENT": ("which", "chip-tool"),
    "UNIFI_PRODUCT_NAME": ("mca-cli-op", "info"),
    "RPI_PRODUCT_NAME": ("cat", "/proc/device-tree/model"),
    "IS_MATTER_LINUX_APP_RUNNING": (
        "pgrep",
        "-f",
        pwrpc_utils.MATTER_LINUX_APP_NAME,
    ),
})

_UNIFI_MODEL_PREFIXES = ("USW-", "US-")


class SshQuery(base_detect_criteria.QueryEnum):
  """Query names for detection for SshComms Devices."""
  IS_DLI = "is_dli_power_switch"
  IS_RASPBIAN_RPI = "is_raspbian_raspberry_pi"
  IS_UBUNTU_RPI = "is_ubuntu_raspberry_pi"
  IS_UNIFI = "is_unifi_switch"
  IS_CHIP_TOOL_PRESENT = "is_chip_tool_installed_on_rpi"
  IS_MATTER_LINUX_APP_RUNNING = "is_matter_linux_app_running_on_rpi"


def _is_dli_query(
    address: str, detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> bool:
  """Determines if address belongs to dli power switch."""
  del create_switchboard_func  # Unused by _is_dli_query
  try:
    response = http_utils.send_http_get(
        _HTTP_ENDPOINTS["DLI_PRODUCT_NAME"].format(address=address),
        auth=requests.auth.HTTPDigestAuth("admin", "1234"),
        headers={"Accept": "application/json"},
        valid_return_codes=[200, 206, 207],
        timeout=1)
    name = response.text
  except RuntimeError as err:
    detect_logger.info("_is_dli_query failed for %s: %r", address, err,
                       exc_info=True)
    return False
  return "Power Switch" in name


def _is_raspbian_rpi_query(
    address: str, detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> bool:
  """Determines if address belongs to raspberry pi."""
  del create_switchboard_func  # Unused by _is_raspbian_rpi_query
  pi_user = "pi"

  try:
    name = host_utils.ssh_command(
        address,
        command=_SSH_COMMANDS["RPI_PRODUCT_NAME"],
        user=pi_user,
        key_info=raspberry_pi_key.SSH_KEY_PRIVATE,
    )
  except RuntimeError as err:
    detect_logger.info("_is_raspbian_rpi_query failed for %s: %r", address, err,
                       exc_info=True)
    return False

  try:
    user = host_utils.ssh_command(
        address,
        command=_SSH_COMMANDS["CURRENT_USER"],
        user=pi_user,
        key_info=raspberry_pi_key.SSH_KEY_PRIVATE,
    )
  except RuntimeError as err:
    detect_logger.info(
        "_is_raspbian_rpi_query failed for %s: %r",
        address,
        err,
        exc_info=True,
    )
    return False

  return user.strip() == pi_user and "Raspberry Pi" in name


def _is_ubuntu_rpi_query(
    address: str, detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> bool:
  """Determines if address belongs to raspberry pi Ubuntu."""
  del create_switchboard_func  # Unused by _is_ubuntu_rpi_query
  try:
    host_utils.ssh_command(
        address,
        command=_SSH_COMMANDS["RPI_PRODUCT_NAME"],
        user="ubuntu",
        key_info=raspberry_pi_key.SSH_KEY_PRIVATE)
  except RuntimeError as err:
    detect_logger.info(
        "_is_ubuntu_rpi_query failed for %s: %r", address, err,
        exc_info=True)
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
        key_info=unifi_poe_switch_key.SSH_KEY_PRIVATE)
  except RuntimeError as err:
    detect_logger.info("_is_unifi_query failed for %s: %r", address, err,
                       exc_info=True)
    return False

  for model_prefix in _UNIFI_MODEL_PREFIXES:
    if model_prefix in mca_info:
      return True
  return False


def _is_chip_tool_installed_on_rpi_query(
    address: str,
    detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase],
) -> bool:
  """Determines whether chip-tool is installed on an RPI."""
  del create_switchboard_func  # Unused.
  try:
    host_utils.ssh_command(
        address,
        command=_SSH_COMMANDS["IS_CHIP_TOOL_PRESENT"],
        user="ubuntu",
        key_info=raspberry_pi_key.SSH_KEY_PRIVATE)
  except RuntimeError as err:
    detect_logger.info(
        "_is_chip_tool_installed_on_rpi_query failed for %s: %r",
        address,
        err,
        exc_info=True,
    )
    return False
  return True


def _is_matter_app_running_query(
    address: str, detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> bool:
  """Determines whether Matter linux app is running on an RPi."""
  del create_switchboard_func  # Unused by _is_matter_app_running_query
  try:
    host_utils.ssh_command(
        address,
        command=_SSH_COMMANDS["IS_MATTER_LINUX_APP_RUNNING"],
        user="ubuntu",
        key_info=raspberry_pi_key.SSH_KEY_PRIVATE)
  except RuntimeError as err:
    detect_logger.info(
        "_is_matter_app_running_query failed for %s: %r", address, err,
        exc_info=True)
    return False
  return True

SSH_QUERY_DICT: immutabledict.immutabledict[
    SshQuery, base_detect_criteria.DetectQueryCallable
] = immutabledict.immutabledict({
    SshQuery.IS_DLI: _is_dli_query,
    SshQuery.IS_RASPBIAN_RPI: _is_raspbian_rpi_query,
    SshQuery.IS_UBUNTU_RPI: _is_ubuntu_rpi_query,
    SshQuery.IS_UNIFI: _is_unifi_query,
    SshQuery.IS_CHIP_TOOL_PRESENT: _is_chip_tool_installed_on_rpi_query,
    SshQuery.IS_MATTER_LINUX_APP_RUNNING: _is_matter_app_running_query,
})
