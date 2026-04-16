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

"""This test script performs unit tests on functions and methods in the usb_port_map module."""
from unittest import mock
from gazoo_device import errors
from gazoo_device import usb_port_map
from gazoo_device.auxiliary_devices import cambrionix
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.utility import usb_config
from gazoo_device.utility import usb_utils


GDM_CONFIG = {
}

CONFLICT_CONFIG = {
}

GDM_CONFIG_OTHER_DEVICES = {
    "yepkit-1624": {
        "persistent": {
            "hub_port_name": "YK21624",
            "name": "yepkit-1624",
            "total_ports": 3,
            "device_type": "yepkit",
            "serial_number": "YK21624",
            "model": "yepkit"
        },
        "options": {
            "alias": None
        }
    },
    "cambrionix-i36k": {
        "persistent": {
            "console_port_name": "/dev/serial/by-id/usb-FTDI_FT230X"
                                 "_Basic_UART_DN00I36K-if00-port0",
            "ftdi_serial_number": "DN00I36K",
            "name": "cambrionix-i36k",
            "total_ports": 15,
            "device_type": "cambrionix",
            "serial_number": "DN00I36K",
            "model": "PP15S"
        },
        "options": {
            "alias": None
        }
    },
    "cambrionix-ab5d": {
        "persistent": {
            "console_port_name": "/dev/serial/by-id/usb-FTDI_FT230X"
                                 "_Basic_UART_DN00AB5D-if00-port0",
            "ftdi_serial_number": "DN00AB5D",
            "name": "cambrionix-ab5d",
            "total_ports": 8,
            "device_type": "cambrionix",
            "serial_number": "DN00AB5D",
            "model": "PP8S"
        },
        "options": {
            "alias": None
        }
    }
}

FAKE_CAMBRIONIX_MODES = ["sync"] * 13 + ["charge", "off"]

SERIAL_CONNECTIONS = [
    "FTDI_FT230X_Basic_UART_DN00AB5D", "FTDI_FT230X_Basic_UART_DN00I36K"
]

cambrionix_port_map = usb_config.CAMBRIONIX_PORT_MAP


class FakeUsbHubPower:

  def get_all_ports_mode(self):
    return FAKE_CAMBRIONIX_MODES


class FakeCambrionix:
  """A mock of Cambrionix."""

  def __init__(self):
    self._switch_power = FakeUsbHubPower()

  def get_detection_info(self):
    pass

  @property
  def total_ports(self):
    return 15

  @property
  def switch_power(self):
    return self._switch_power

  def close(self):
    pass


# A non-GDM device
non_gdm_device_info = usb_config.UsbInfo(
    **{
        "product_id":
            "b5c1",
        "vendor_id":
            "04f2",
        "serial_number":
            "123456",
        "product_name":
            "Chicony_Electronics_Co._Ltd._Integrated_Camera",
        "address":
            "/dev/serial/by-id/usb-Chicony_Electronics_Co._Ltd._Integrated_Camera",
        "usb_hub_address":
            None,
        "usb_hub_port":
            None
    })
# cambrionix-i36k
cambrionix_one_device_info = usb_config.UsbInfo(
    **{
        "product_id":
            "6015",
        "vendor_id":
            "0403",
        "product_name":
            "FT230X Basic UART",
        "serial_number":
            "DN00I36K",
        "address":
            "/dev/serial/by-id/usb-FTDI_FT230X_Basic_UART_DN00I36K-if00-port0",
        "usb_hub_address":
            None,
        "usb_hub_port":
            None
    })
# cambrionix-ab5d
cambrionix_two_device_info = usb_config.UsbInfo(
    **{
        "product_id": "6015",
        "vendor_id": "0403",
        "serial_number": "DN00AB5D",
        "address": "/dev/serial/by-id/usb-FTDI_FT230X_Basic_UART_DN00AB5D",
        "usb_hub_port": None,
        "usb_hub_address": None
    })


FAKE_LIST = [
    non_gdm_device_info,
    cambrionix_one_device_info,
]
FAKE_MAP = {dev.address: dev for dev in FAKE_LIST}

TWO_CAMBRIONIX_FAKE_LIST = [
    cambrionix_one_device_info,
    cambrionix_two_device_info,
]
TWO_CAMBRIONIX_FAKE_MAP = {dev.address: dev for dev in TWO_CAMBRIONIX_FAKE_LIST}
MISSING_DEVICES_FAKE_LIST = [
    cambrionix_one_device_info,
]
MISSING_DEVICES_FAKE_MAP = {
    dev.address: dev for dev in MISSING_DEVICES_FAKE_LIST
}


class UsbPortMapTests(fake_device_test_case.FakeDeviceTestCase):
  """Unit tests for usb_port_map.py."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements("cambrionix-0001")
    mock_sys = mock.patch("sys.platform", "linux")
    mock_sys.start()
    self.addCleanup(mock_sys.stop)

  def test_identify_device_not_on_cambrionix(self):
    """Verify that _identify_device returns a dict with device_data."""

    device_data = usb_port_map._identify_device(non_gdm_device_info)
    self.assertTrue(device_data,
                    "A device_data dict should have been returned.")

  @mock.patch.object(
      usb_utils, "get_address_to_usb_info_dict", return_value=FAKE_MAP)
  @mock.patch.object(cambrionix, "Cambrionix", return_value=FakeCambrionix())
  @mock.patch.object(
      usb_utils, "get_all_serial_connections", return_value=SERIAL_CONNECTIONS)
  def test_create_usb_port_map_object_mock_cambrionix(
      self, mock_serial_connections, mock_cambrionix, mock_pyudev):
    """Verify that a UsbPortMap object is created."""
    self.mock_manager._devices = GDM_CONFIG
    port_map = usb_port_map.UsbPortMap(self.mock_manager)
    self.assertTrue(port_map, "A port_map object should have been created.")
    port_map.print_port_map()

  @mock.patch.object(
      usb_utils,
      "get_address_to_usb_info_dict",
      return_value=TWO_CAMBRIONIX_FAKE_MAP)
  @mock.patch.object(cambrionix, "Cambrionix", return_value=FakeCambrionix())
  def test_create_usb_port_map_object_two_cambrionix_setup(
      self, mock_cambrionix, mock_pyudev):
    """Verify that a UsbPortMap object is created."""
    self.mock_manager._devices = GDM_CONFIG
    port_map = usb_port_map.UsbPortMap(self.mock_manager)
    self.assertEqual(
        len(port_map.cambrionix_info_list), 2,
        "Two Cambrionix hubs should have been discovered.")

  @mock.patch.object(
      usb_utils, "get_address_to_usb_info_dict", return_value=FAKE_MAP)
  @mock.patch.object(cambrionix, "Cambrionix", return_value=FakeCambrionix())
  def test_print_handles_missing_cambrionix(self, mock_cambrionix, mock_pyudev):
    """Verify that printing when a cambrionix is missing does not raise an exception."""
    self.mock_manager.create_device.side_effect = errors.DeviceError(
        "some error")
    self.mock_manager._devices = GDM_CONFIG
    port_map = usb_port_map.UsbPortMap(self.mock_manager)
    port_map.print_port_map()

  @mock.patch.object(
      usb_utils, "get_address_to_usb_info_dict", return_value=FAKE_MAP)
  @mock.patch.object(cambrionix, "Cambrionix", return_value=FakeCambrionix())
  def test_create_usb_port_map_check_port_count(self, mock_cambrionix,
                                                mock_pyudev):
    """Verify that a UsbPortMap object with correct port_count is created."""
    self.mock_manager._devices = GDM_CONFIG
    port_map = usb_port_map.UsbPortMap(self.mock_manager)
    self.assertTrue(port_map, "A port_map object should have been created.")
    self.assertEqual(port_map.cambrionix_info_list[0]["port_count"], 15)


if __name__ == "__main__":
  fake_device_test_case.main()
