"""Unit tests for dc2200 auxiliary device."""
from unittest import mock

from gazoo_device.auxiliary_devices import dc2200
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.utility import usb_utils

import immutabledict
import pyvisa


_PERSISTENT_PROPERTIES = immutabledict.immutabledict({
    "console_port_name": "123456",
    "device_type": "dc2200",
    "model": "dc2200",
    "name": "dc2200-3456",
    "serial_number": "123456",
    "product_name": "dc2200",
    "usb_product_id": 0x1313,
    "usb_vendor_id": 0x80c8,
})

_GET_DETECTION_PROPS = immutabledict.immutabledict({
    "console_port_name": "123456",
    "model": "dc2200",
    "serial_number": "123456",
})


class DC2200Test(fake_device_test_case.FakeDeviceTestCase):
  """DC2200 LED Driver unit test class."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements(_PERSISTENT_PROPERTIES["name"])
    self.device_config["persistent"] = dict(_PERSISTENT_PROPERTIES)
    self.device = dc2200.DC2200(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory,
        log_file_name=None)

  @mock.patch.object(
      usb_utils, "get_usb_device_from_serial_number", return_value=None)
  def test_is_connected_fails(self, get_device_fn):
    """Tests is_connected method fails."""
    self.assertFalse(
        self.device.is_connected(self.device_config),
        "Device should fail to be found")

  @mock.patch.object(
      usb_utils, "get_usb_device_from_serial_number", return_value="123456")
  def test_is_connected_succeeds(self, get_device_fn):
    """Tests is_connected method succeeds."""
    self.assertTrue(
        self.device.is_connected(self.device_config),
        "Device not being properly found")

  def test_get_detection_info(self):
    """Tests get_detection_info method."""
    self.assertIsInstance(self.device.get_detection_info(), tuple,
                          "get_detection_info isn't a tuple")
    self._test_get_detection_info(
        _GET_DETECTION_PROPS["console_port_name"],
        dc2200.DC2200,
        _GET_DETECTION_PROPS)

  @mock.patch.object(pyvisa, "ResourceManager", autospec=True)
  def test_test_init_close_led_driver_capability(self, resource_manager):
    """Tests initializing and closing led_driver."""
    self.device.led_driver.close()


if __name__ == "__main__":
  fake_device_test_case.main()
