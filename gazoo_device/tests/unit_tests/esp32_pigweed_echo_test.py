"""Unit tests for device class ESP32PigweedEcho."""
from gazoo_device.auxiliary_devices import esp32_pigweed_echo
from gazoo_device.tests.unit_tests.utils import fake_device_test_case


class ESP32PigweedEchoTests(fake_device_test_case.FakeDeviceTestCase):
  """Test module for device class ESP32PigweedEcho."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements("esp32pigweedecho-1234")
    self.device_config["persistent"]["console_port_name"] = "/dev/bus/usb/01/02"
    self.uut = esp32_pigweed_echo.ESP32PigweedEcho(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory)

  def test_001_firmware_version(self):
    """Verify the firmware_version."""
    self.assertEqual(self.uut.firmware_version, "NOT_IMPLEMENTED")

  def test_002_echo_rpc_capability(self):
    """Verify the initialization of pw_rpc_echo capability."""
    self.assertTrue(self.uut.pw_rpc_echo)


if __name__ == "__main__":
  fake_device_test_case.main()
