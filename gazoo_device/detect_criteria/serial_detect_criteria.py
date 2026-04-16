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

"""Serial queries sent to devices during detection to determine their device type."""
import logging
import os
import typing
from typing import Callable
from gazoo_device.capabilities.interfaces import switchboard_base
from gazoo_device.detect_criteria import base_detect_criteria
from gazoo_device.utility import usb_utils
import immutabledict

_NRF_DK_COMMS_ADDRESS_LINUX = "SEGGER_J-Link"
_NRF_DK_EFR32_COMMS_ADDRESS_MAC = "tty.usbmodem"


class SerialQuery(base_detect_criteria.QueryEnum):
  ADDRESS = "address"
  IS_NRF_OPENTHREAD = "is_nrf_openthread"
  PRODUCT_NAME = "usb info product_name"
  SERIAL_NUMBER = "usb serial_numer"
  VENDOR_PRODUCT_ID = "VENDOR_ID:PRODUCT_ID"


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


def is_nrf_board(address: str) -> bool:
  """Returns if the address belongs to a NRF board."""
  return (
      _NRF_DK_COMMS_ADDRESS_LINUX in address
      or _NRF_DK_EFR32_COMMS_ADDRESS_MAC in address
  )


def is_nrf_openthread(
    address: str,
    detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase],
) -> bool:
  """Returns True if the device is an NRF board with OpenThread CLI binary."""
  if not is_nrf_board(address):
    return False
  file_handler = typing.cast(logging.FileHandler, detect_logger.handlers[0])
  log_path = file_handler.baseFilename
  switchboard = create_switchboard_func(
      communication_address=address,
      communication_type="SerialComms",
      device_name=os.path.basename(log_path),
      log_path=log_path,
  )
  resp = switchboard.send_and_expect(
      command="invalid", pattern_list=[r".*InvalidCommand\n"], timeout=3
  )
  return resp.match is not None and not resp.timedout


def usb_product_name_query(
    address: str, detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> str:
  """Gets product name from usb_info."""
  del create_switchboard_func, detect_logger  # Unused.
  return usb_utils.get_product_name_from_path(address).lower()


SERIAL_QUERY_DICT: immutabledict.immutabledict[
    SerialQuery, base_detect_criteria.DetectQueryCallable
] = immutabledict.immutabledict({
    SerialQuery.ADDRESS: base_detect_criteria.get_communication_address,
    SerialQuery.IS_NRF_OPENTHREAD: is_nrf_openthread,
    SerialQuery.PRODUCT_NAME: usb_product_name_query,
    SerialQuery.SERIAL_NUMBER: _usb_serial_number_from_serial_port_path,
    SerialQuery.VENDOR_PRODUCT_ID: _usb_vendor_product_id_from_serial_port_path,
})
