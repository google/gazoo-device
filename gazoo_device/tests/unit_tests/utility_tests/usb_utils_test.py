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

"""Tests the usb_utils.py module."""
import os
from unittest import mock

from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import usb_config
from gazoo_device.utility import usb_info_linux
from gazoo_device.utility import usb_info_mac
from gazoo_device.utility import usb_utils
import usb

CAMBRIONIX_SYMLINK = (
    "/dev/serial/by-id/usb-FTDI_FT230X_Basic_UART_DJ00JMN0-if00-port0")
CHILD_DEVICE_SYMLINK_3 = (
    "/dev/serial/by-id/usb-FTDI_ChildDevice_1234567-if03-port0")
CHILD_DEVICE_SYMLINK_0 = (
    "/dev/serial/by-id/usb-FTDI_ChildDevice_1234567-if00-port0")
CHILD_DEVICE_USB_SYMLINK = (
    "/dev/serial/by-id/usb-SomeCompany_Some_Child_Device_1234567890-if01")
LINUX_REAL_PATH = u"/dev/ttyUSB3"
MAC_PATH = "/dev/tty.usbserial-DJ00JMN0"
USB_INFO_DICT_LINUX = {
    CAMBRIONIX_SYMLINK:
        usb_config.UsbInfo(
            vendor_id="0403",
            ftdi_interface=0,
            product_name="FT230X Basic UART",
            manufacturer="FTDI",
            disk=LINUX_REAL_PATH,
            product_id="6015",
            serial_number="DJ00JMN0",
            address=CAMBRIONIX_SYMLINK,
            child_addresses=[
                CHILD_DEVICE_SYMLINK_0,
                CHILD_DEVICE_SYMLINK_3,
                CHILD_DEVICE_USB_SYMLINK,
                "360av3",
            ]),
    CHILD_DEVICE_SYMLINK_3:
        usb_config.UsbInfo(
            vendor_id="0403",
            ftdi_interface=3,
            product_name="ChildDevice",
            manufacturer="FTDI",
            disk=LINUX_REAL_PATH,
            product_id="1234",
            serial_number="1234567",
            address=CHILD_DEVICE_SYMLINK_3,
            usb_hub_address=CAMBRIONIX_SYMLINK,
            usb_hub_port=2),
    CHILD_DEVICE_SYMLINK_0:
        usb_config.UsbInfo(
            vendor_id="0403",
            ftdi_interface=0,
            product_name="ChildDevice",
            manufacturer="FTDI",
            disk=LINUX_REAL_PATH,
            product_id="1234",
            serial_number="1234567",
            address=CHILD_DEVICE_SYMLINK_0,
            usb_hub_address=CAMBRIONIX_SYMLINK,
            usb_hub_port=2),
    CHILD_DEVICE_USB_SYMLINK:
        usb_config.UsbInfo(
            vendor_id="1234",
            ftdi_interface=0,
            product_name="Some_Child_Device",
            manufacturer="SomeCompany",
            disk=LINUX_REAL_PATH,
            product_id="1234",
            serial_number="1234567",
            address=CHILD_DEVICE_USB_SYMLINK,
            usb_hub_address=CAMBRIONIX_SYMLINK,
            usb_hub_port=3),
    "360av3":
        usb_config.UsbInfo(
            serial_number="12345",
            address="360av3",
            product_name="Android",
            usb_hub_address=CAMBRIONIX_SYMLINK,
            usb_hub_port=4)
}
USB_INFO_DICT_MAC = {
    MAC_PATH:
        usb_config.UsbInfo(
            vendor_id="0403",
            ftdi_interface=0,
            product_name="FT230X Basic UART",
            manufacturer="FTDI",
            disk=LINUX_REAL_PATH,
            product_id="6015",
            serial_number="DJ00JMN0",
            address="/dev/tty.usbserial-DJ00JMN0"),
    "/dev/tty.usbserial-12345670":
        usb_config.UsbInfo(
            ftdi_interface=0,
            product_id="1234",
            serial_number="1234567",
            address="/dev/tty.usbserial-12345670"),
    "/dev/tty.usbserial-12345673":
        usb_config.UsbInfo(
            ftdi_interface=3,
            serial_number="1234567",
            address="/dev/tty.usbserial-12345673"),
    "360av3":
        usb_config.UsbInfo(
            serial_number="12345", address="360av3", product_name="Android")
}

METHOD_EXPECTED_MAP = {
    usb_utils.get_ftdi_interface_from_path: 0,
    usb_utils.get_serial_number_from_path: "DJ00JMN0",
    usb_utils.get_product_name_from_path: "FT230X Basic UART"
}


class UsbUtilsTests(unit_test_case.UnitTestCase):
  """USB utility tests."""

  @mock.patch.object(os.path, "realpath", return_value=LINUX_REAL_PATH)
  @mock.patch("sys.platform", "linux")
  @mock.patch.object(
      usb_info_linux,
      "get_address_to_usb_info_dict",
      return_value=USB_INFO_DICT_LINUX)
  @mock.patch.object(
      usb_info_mac, "get_address_to_usb_info_dict", return_value=[])
  def test_001_usb_utils_values_work_on_linux(self, mock_mac_info,
                                              mock_linux_info, mock_realpath):
    """Test get_usb_interface_from_path returns correct interface."""
    for method, expected_value in METHOD_EXPECTED_MAP.items():
      value = method(CAMBRIONIX_SYMLINK)
      self.assertEqual(
          expected_value, value,
          "Expected linux {} to return {} found {}".format(
              method.__name__, expected_value, value))

  @mock.patch("sys.platform", "darwin")
  @mock.patch.object(
      usb_info_linux, "get_address_to_usb_info_dict", return_value=[])
  @mock.patch.object(
      usb_info_mac,
      "get_address_to_usb_info_dict",
      return_value=USB_INFO_DICT_MAC)
  def test_002_usb_utils_values_work_on_mac(self, mock_mac_info,
                                            mock_linux_info):
    """Test get_usb_interface_from_path returns correct interface."""
    for method, expected_value in METHOD_EXPECTED_MAP.items():
      value = method(MAC_PATH)
      self.assertEqual(
          expected_value, value, "Expected mac {} to return {} found {}".format(
              method.__name__, expected_value, value))

  @mock.patch("sys.platform", "darwin")
  @mock.patch.object(
      usb_info_mac,
      "get_address_to_usb_info_dict",
      return_value=USB_INFO_DICT_MAC)
  def test_003_bad_serial_path(self, mock_mac_info):
    """Returns empty dict."""
    product_name = usb_utils.get_product_name_from_path("/dev/bogus_path")
    self.assertFalse(product_name)

  @mock.patch("sys.platform", "darwin")
  @mock.patch.object(
      usb_info_mac,
      "get_address_to_usb_info_dict",
      return_value=USB_INFO_DICT_MAC)
  def test_005_get_other_ftdi_line_mac(self, mock_mac):
    """Test get_other_ftdi_line() on MacOS."""
    line = usb_utils.get_other_ftdi_line("/dev/tty.usbserial-12345670", 3)
    self.assertEqual(line, "/dev/tty.usbserial-12345673")

  @mock.patch.object(os.path, "realpath", return_value=LINUX_REAL_PATH)
  @mock.patch("sys.platform", "linux")
  @mock.patch.object(
      usb_info_linux,
      "get_address_to_usb_info_dict",
      return_value=USB_INFO_DICT_LINUX)
  def test_005_get_other_ftdi_line_linux(self, mock_usbinfo, mock_realpath):
    """Test get_other_ftdi_line() on Linux."""
    line = usb_utils.get_other_ftdi_line(CHILD_DEVICE_SYMLINK_0, 3)
    self.assertEqual(line, CHILD_DEVICE_SYMLINK_3)

  @mock.patch.object(os.path, "realpath", return_value=LINUX_REAL_PATH)
  @mock.patch("sys.platform", "linux")
  @mock.patch.object(
      usb_info_linux,
      "get_address_to_usb_info_dict",
      return_value=USB_INFO_DICT_LINUX)
  def test_011_get_usb_hub_info(self, mock_usbinfo, mock_realpath):
    """Test get_usb_hub_info() on Linux."""
    expected_dict = {
        "device_usb_port": 4,
        "device_usb_hub_name": CAMBRIONIX_SYMLINK
    }
    persistent_props_dict = usb_utils.get_usb_hub_info(device_address="360av3")
    self.assertEqual(persistent_props_dict, expected_dict)

  @mock.patch.object(usb_utils, "get_address_to_usb_info_dict", return_value={})
  def test_070_get_all_serial_connections_when_no_connections(
      self, mock_get_info):
    """Test get_all_serial_connections() finding no serial connections."""
    addresses = usb_utils.get_all_serial_connections()
    self.assertEqual(addresses, [])

  @mock.patch.object(
      usb_utils, "get_address_to_usb_info_dict", return_value=USB_INFO_DICT_MAC)
  def test_072_get_all_serial_connections(self, mock_list):
    """Test get_all_serial_connections() finding serial connections."""
    addresses = usb_utils.get_all_serial_connections()
    self.assertEqual(addresses, [
        MAC_PATH, "/dev/tty.usbserial-12345670", "/dev/tty.usbserial-12345673"
    ])

  def test_080_get_usb_devices_having_a_serial_number(self):
    """Tests get usb devices having a serial number."""
    with mock.patch.object(usb.core, "find") as usb_find:
      devices = usb_utils.get_usb_devices_having_a_serial_number()
      self.assertIsInstance(devices, list, "Return type is not a list.")
      usb_find.assert_called_once()

  def test_081_get_usb_device_from_serial_number(self):
    """Tests get usb device from a serial number."""
    with mock.patch.object(usb.core, "find") as usb_find:
      usb_utils.get_usb_device_from_serial_number("123")
      usb_find.assert_called_once()


if __name__ == "__main__":
  unit_test_case.main()
