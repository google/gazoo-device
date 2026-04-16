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

"""Pigweed ueries sent to devices during detection to determine their device type."""
import logging
import typing
from typing import Callable
from gazoo_device.capabilities.interfaces import switchboard_base
from gazoo_device.detect_criteria import base_detect_criteria
from gazoo_device.detect_criteria import serial_detect_criteria
from gazoo_device.utility import pwrpc_utils
from gazoo_device.utility import usb_utils
import immutabledict


class PigweedQuery(base_detect_criteria.QueryEnum):
  """Query names for detection for PigweedSerialComms Devices."""
  IS_MATTER = "is_matter"
  IS_NRF_OPENTHREAD = "is_nrf_openthread"
  PRODUCT_NAME = "usb info product_name"
  MANUFACTURER_NAME = "usb info manufacturer_name"


def _is_matter_device_query(
    address: str, detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> bool:
  """Returns True if the device is a Matter device.

  Args:
    address: The communication address.
    detect_logger: The logger of device interactions.
    create_switchboard_func: Method to create the switchboard.

  Returns:
    True if the device is a Matter device, False otherwise.
  """
  file_handler = typing.cast(logging.FileHandler, detect_logger.handlers[0])
  log_path = file_handler.baseFilename
  return pwrpc_utils.is_matter_device(
      address, log_path, create_switchboard_func, detect_logger
  )


def _manufacturer_name_query(
    address: str, detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> str:
  """Gets manufacturer name from usb_info."""
  del create_switchboard_func, detect_logger  # Unused.
  return usb_utils.get_device_info(address).manufacturer.lower()


PIGWEED_QUERY_DICT = immutabledict.immutabledict({
    PigweedQuery.IS_MATTER: _is_matter_device_query,
    PigweedQuery.IS_NRF_OPENTHREAD: serial_detect_criteria.is_nrf_openthread,
    PigweedQuery.PRODUCT_NAME: serial_detect_criteria.usb_product_name_query,
    PigweedQuery.MANUFACTURER_NAME: _manufacturer_name_query,
})
