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

"""USB queries sent to devices during detection to determine their device type."""
import logging
from typing import Callable
from gazoo_device.capabilities.interfaces import switchboard_base
from gazoo_device.detect_criteria import base_detect_criteria
from gazoo_device.utility import usb_utils
import immutabledict


class UsbQuery(base_detect_criteria.QueryEnum):
  PRODUCT_NAME = "usb product name"
  SERIAL_NUMBER = "serial_number"
  VENDOR_PRODUCT_ID = "VENDOR_ID:PRODUCT_ID"


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


USB_QUERY_DICT: immutabledict.immutabledict[
    UsbQuery, base_detect_criteria.DetectQueryCallable] = (
        immutabledict.immutabledict({
            UsbQuery.PRODUCT_NAME: _usb_product_name_from_serial_number,
            UsbQuery.SERIAL_NUMBER:
                base_detect_criteria.get_communication_address,
            UsbQuery.VENDOR_PRODUCT_ID: _usb_vendor_product_id_query,
        })
    )
