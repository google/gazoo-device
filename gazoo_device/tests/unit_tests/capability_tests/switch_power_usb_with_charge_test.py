"""Unit tests for the switch_power_usb_with_charge capability."""
from unittest import mock

from gazoo_device import errors
from gazoo_device.auxiliary_devices import cambrionix
from gazoo_device.capabilities import switch_power_usb_with_charge
from gazoo_device.tests.unit_tests.utils import unit_test_case


class SwitchPowerUsbWithChargeCapabilityTests(unit_test_case.UnitTestCase):
  """Test class to verify the behavior of the SwitchPowerUsbWithCharge capability."""

  def setUp(self):
    super().setUp()
    self.add_time_mocks()
    self._total_ports = 15
    self._shell_func = mock.Mock()
    self._regex_shell_func = mock.Mock()
    self.uut = switch_power_usb_with_charge.SwitchPowerUsbWithCharge(
        shell_fn=self._shell_func,
        regex_shell_fn=self._regex_shell_func,
        command_dict=cambrionix.COMMANDS.copy(),
        regex_dict=cambrionix.REGEXES.copy(),
        device_name="cambrionix-1234",
        serial_number="1234567890",
        total_ports=self._total_ports)

  def test_001_power_on(self):
    """Verifies power on is successful."""
    self.uut.power_on(port=1)
    self.assertIn("sync 1", self._shell_func.call_args_list[0][0][0],
                  "Expected _shell_func to be called using port 1")

  def test_002_power_off(self):
    """Verifies power off is successful."""
    self.uut.power_off(port=1)
    self.assertIn("off 1", self._shell_func.call_args_list[0][0][0],
                  "Expected _shell_func to be called using port 1")

  def test_003_set_all_ports_mode_off(self):
    """Verifies set_all_ports_mode 'off' is successful."""
    self.uut.set_all_ports_mode("off")
    self.assertEqual(
        self.uut._shell_fn.call_count, self._total_ports,
        "Expected _shell_fn to be called {} times".format(self._total_ports))

  def test_004_set_all_ports_mode_sync(self):
    """Verifies set_all_ports_mode 'sync' is successful."""
    self.uut.set_all_ports_mode("sync")
    self.assertEqual(
        self.uut._shell_fn.call_count, self._total_ports,
        "Expected power_on to be called {} times".format(self._total_ports))

  def test_005_get_all_ports_mode_on_off(self):
    """Verifies if ports are on or off get_all_ports_mode is successful."""
    self._regex_shell_func.return_value = "S"
    result = self.uut.get_all_ports_mode()
    all_on = all(port == "sync" for port in result[1:])
    self.assertTrue(
        all_on, "Expected {} ports in 'sync' mode".format(self._total_ports))
    self._regex_shell_func.return_value = "O"
    result = self.uut.get_all_ports_mode()
    all_on = all(port == "off" for port in result[1:])
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
    bad_port = 19
    with self.assertRaisesRegex(errors.DeviceError, "Port 19 is invalid"):
      self.uut.set_mode("off", bad_port)

  def test_009_power_off_bad_port(self):
    """Verifies power_off using bad port causes error."""
    bad_port = 19
    with self.assertRaisesRegex(errors.DeviceError, "Port 19 is invalid"):
      self.uut.power_off(bad_port)

  def test_010_power_on_bad_port(self):
    """Verifies power_on using bad port causes error."""
    bad_port = 19
    with self.assertRaisesRegex(errors.DeviceError, "Port 19 is invalid"):
      self.uut.power_on(bad_port)

  def test_011_get_mode_bad_port(self):
    """Verifies get_mode using bad port causes error."""
    bad_port = 19
    with self.assertRaisesRegex(errors.DeviceError, "Port 19 is invalid"):
      self.uut.get_mode(bad_port)

  def test_012_power_on_data_sync_false(self):
    """Verifies with valid port and data_sync set to False power_on is successful."""
    self.uut.power_on(port=1, data_sync=False)  # 'charge'
    self.assertIn("charge 1", self._shell_func.call_args_list[0][0][0],
                  "Expected _shell_func to be called using charge 1")

  def test_050_supported_modes(self):
    """Verify the supported_modes property returns off and sync."""
    modes = self.uut.supported_modes
    self.assertTrue("off" and "sync" and "charge" in modes)

  @mock.patch.object(
      switch_power_usb_with_charge.SwitchPowerUsbWithCharge, "set_mode")
  def test_set_all_ports_mode(self, mock_set_mode):
    self.uut.set_all_ports_mode("off")
    mock_set_mode.assert_has_calls([
        mock.call(mode="off", port=port)
        for port in range(1, self._total_ports + 1)
    ])


if __name__ == "__main__":
  unit_test_case.main()
