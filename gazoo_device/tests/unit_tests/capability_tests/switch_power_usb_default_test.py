"""Unit tests for the switch_power_usb_default capability."""
from unittest import mock

from gazoo_device import errors
from gazoo_device.auxiliary_devices import yepkit
from gazoo_device.capabilities import switch_power_usb_default
from gazoo_device.tests.unit_tests.utils import unit_test_case


class SwitchPowerUsbDefaultCapabilityTests(unit_test_case.UnitTestCase):
  """Test class to verify the behavior of the SwitchPowerUsbDefault capability."""

  def setUp(self):
    super().setUp()
    self.add_time_mocks()
    self._name = "yepkit-1234"
    self._total_ports = 3
    self._shell_func = mock.Mock()
    self._regex_shell_func = mock.Mock()
    self.uut = switch_power_usb_default.SwitchPowerUsbDefault(
        shell_fn=self._shell_func,
        regex_shell_fn=self._regex_shell_func,
        command_dict=yepkit.COMMANDS.copy(),
        regex_dict=yepkit.REGEXES.copy(),
        device_name=self._name,
        serial_number="1234567890",
        total_ports=self._total_ports)

  def test_001_power_on(self):
    """Verifies power on is successful."""
    self.uut.power_on(port=1)
    self.assertIn("-u 1", self._shell_func.call_args_list[0][0][0],
                  "Expected _shell_func to be called using port 1")

  def test_002_power_off(self):
    """Verifies power off is successful."""
    self.uut.power_off(port=1)
    self.assertIn("-d 1", self._shell_func.call_args_list[0][0][0],
                  "Expected _shell_func to be called using port 1")

  def test_003_set_all_ports_mode_off(self):
    """Verifies set_all_ports_mode 'off' is successful."""
    with mock.patch.object(self.uut, "power_off"):
      self.uut.set_all_ports_mode("off")
      self.assertEqual(
          self.uut.power_off.call_count, self._total_ports,
          "Expected power_off to be called {} times".format(self._total_ports))

  def test_004_set_all_ports_mode_sync(self):
    """Verifies set_all_ports_mode 'sync' is successful."""
    with mock.patch.object(self.uut, "power_on"):
      self.uut.set_all_ports_mode("sync")
      self.assertEqual(
          self.uut.power_on.call_count, self._total_ports,
          "Expected power_on to be called {} times".format(self._total_ports))

  def test_005_get_all_ports_mode_on_off(self):
    """Verifies if ports are on or off get_all_ports_mode is successful."""
    self._regex_shell_func.return_value = "ON"
    result = self.uut.get_all_ports_mode()
    all_on = all(port == "sync" for port in result)
    self.assertTrue(
        all_on, "Expected {} ports in 'sync' mode".format(self._total_ports))
    self._regex_shell_func.return_value = "OFF"
    result = self.uut.get_all_ports_mode()
    all_on = all(port == "off" for port in result)
    self.assertTrue(all_on,
                    "Expected {} ports in 'off' mode".format(self._total_ports))

  def test_006_set_all_ports_mode_bad_mode(self):
    """Verifies set_all_ports_mode using bad mode causes error."""
    with self.assertRaisesRegex(errors.DeviceError, "Mode surprise not found"):
      self.uut.set_all_ports_mode("surprise")

  def test_007_set_mode_bad_mode(self):
    """Verifies set_mode using bad mode causes error."""
    with self.assertRaisesRegex(errors.DeviceError, "Mode surprise not found"):
      self.uut.set_mode("surprise", 1)

  def test_008_set_mode_bad_port(self):
    """Verifies set_mode using bad port causes error."""
    bad_port = 8
    with self.assertRaisesRegex(errors.DeviceError, "Port 8 is invalid"):
      self.uut.set_mode("off", bad_port)

  def test_009_power_off_bad_port(self):
    """Verifies power_off using bad port causes error."""
    bad_port = 8
    with self.assertRaisesRegex(errors.DeviceError, "Port 8 is invalid"):
      self.uut.power_off(bad_port)

  def test_010_power_on_bad_port(self):
    """Verifies power_on using bad port causes error."""
    bad_port = 8
    with self.assertRaisesRegex(errors.DeviceError, "Port 8 is invalid"):
      self.uut.power_on(bad_port)

  def test_011_get_mode_bad_port(self):
    """Verifies get_mode using bad port causes error."""
    bad_port = 8
    with self.assertRaisesRegex(errors.DeviceError, "Port 8 is invalid"):
      self.uut.get_mode(bad_port)

  def test_012_power_on_unsupported_data_sync(self):
    """Verifies power_on using data_sync=False causes error."""
    with self.assertRaisesRegex(
        errors.DeviceError, "False not supported in default implementation"):
      self.uut.power_on(port=1, data_sync=False)

  def test_014_total_ports(self):
    """Verifies total_ports property returns the correct number of ports."""
    self.assertEqual(
        self.uut.total_ports,
        self._total_ports,
        f"Device {self._name} total_ports failed. The total ports returned were"
        f" {self.uut.total_ports} which does not match the specified"
        f"{self._total_ports}")

  def test_050_supported_modes(self):
    """Verify the supported_modes property returns off and sync."""
    modes = self.uut.supported_modes
    self.assertTrue("off" and "sync" in modes)


if __name__ == "__main__":
  unit_test_case.main()
