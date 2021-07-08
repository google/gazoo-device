"""Unit tests for nrf52840 module."""
from unittest import mock

from gazoo_device import errors
from gazoo_device.auxiliary_devices import nrf52840
from gazoo_device.base_classes import nrf_connect_sdk_device
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
import immutabledict


_NRF_CONNECT_PERSISTENT_PROPERTIES = immutabledict.immutabledict({
    "os": "Zephyr RTOS",
    "platform": "nRF Connect",
    "serial_number": "123456",
})


class NRF52840DeviceTests(fake_device_test_case.FakeDeviceTestCase):
  """Test for base class NRF52840."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements("nrf52840-1234")
    self.device_config["persistent"]["console_port_name"] = (
        "/dev/bus/usb/001/002")
    jlink_patcher = mock.patch("pylink.JLink")
    jlink_patcher.start()
    self.addCleanup(jlink_patcher.stop)
    self.uut = nrf52840.NRF52840(
                self.mock_manager,
                self.device_config,
                log_directory=self.artifacts_directory)

  def test_001_create_nrf52840_device(self):
    """Verify create_device works as expected."""
    self.assertIsNotNone(self.uut)
    self.assertIsInstance(self.uut, nrf_connect_sdk_device.NRFConnectSDKDevice)

  def test_002_nrf52840_attributes(self):
    """Verify nrf52840 attributes."""
    self.assertEqual(self.uut.os, _NRF_CONNECT_PERSISTENT_PROPERTIES["os"])
    self.assertEqual(self.uut.platform,
                     _NRF_CONNECT_PERSISTENT_PROPERTIES["platform"])
    self.assertEqual(self.uut.serial_number,
                     _NRF_CONNECT_PERSISTENT_PROPERTIES["serial_number"])

  def test_003_get_detection_info(self):
    """Verify get_detection_info."""
    persistent_dict, _ = self.uut.get_detection_info()
    self.assertEqual(persistent_dict["name"], "nrf52840-1234")
    self.assertEqual(persistent_dict["device_type"], "nrf52840")

  def test_004_recover(self):
    """Verify recover method."""
    with self.assertRaises(errors.DeviceError):
      self.uut.recover(None)

  def test_005_switchboard(self):
    """Verify the deactive switchboard in nrf52840."""
    with self.assertRaises(errors.DeviceError):
      self.uut.switchboard.send()

  def test_006_jlink_flash_capability(self):
    """Verify the initialization of j_link_flash capability."""
    self.assertTrue(self.uut.flash_build)


if __name__ == "__main__":
  fake_device_test_case.main()
