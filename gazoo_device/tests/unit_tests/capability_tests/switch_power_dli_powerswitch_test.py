"""Unit tests for the switch_power_dli_powerswitch capability."""
from unittest import mock

from gazoo_device import errors
from gazoo_device.auxiliary_devices import dli_powerswitch
from gazoo_device.capabilities import switch_power_dli_powerswitch
from gazoo_device.tests.unit_tests.utils import unit_test_case


class SwitchPowerDliPowerswitchCapabilityTests(unit_test_case.UnitTestCase):
  """Test class to verify the behavior of the switch_power_dli_powerswitch capability."""

  def setUp(self):
    super().setUp()
    self._name = "powerswitch-1234"
    self._ip_address = "12.34.56.78"
    mock_dli_powerswitch = mock.create_autospec(
        dli_powerswitch.DliPowerSwitch, instance=True)
    self._write_command = mock_dli_powerswitch._write_command
    self._total_ports = 8
    self.uut = switch_power_dli_powerswitch.SwitchPowerDliPowerswitch(
        http_fn=self._write_command,
        ip_address=self._ip_address,
        command_dict=dli_powerswitch.COMMANDS,
        headers_dict=dli_powerswitch.HEADERS,
        device_name=self._name,
        total_ports=self._total_ports)

  def test_001_power_on(self):
    """Verifies power on is successful."""
    self.uut.power_on(port=1)
    self._write_command.assert_called_once_with(
        "POST",
        f"http://{self._ip_address}/restapi/relay/outlets/=1/state/",
        headers={
            "Accept": "application/json",
            "X-CSRF": "x",
            "X-HTTP-Method": "PUT"
        },
        data={
            "value": "true"
        },
    )

  def test_002_power_off(self):
    """Verifies power off is successful."""
    self.uut.power_off(port=1)
    self._write_command.assert_called_once_with(
        "POST",
        f"http://{self._ip_address}/restapi/relay/outlets/=1/state/",
        headers={
            "Accept": "application/json",
            "X-CSRF": "x",
            "X-HTTP-Method": "PUT"
        },
        data={
            "value": "false"
        },
    )

  def test_003_set_all_ports_mode_off(self):
    """Verifies set_all_ports_mode 'off' is successful."""
    self.uut.set_all_ports_mode("off")
    self._write_command.assert_called_once_with(
        "POST",
        f"http://{self._ip_address}/restapi/relay/outlets/all;/state/",
        headers={
            "Accept": "application/json",
            "X-CSRF": "x",
            "X-HTTP-Method": "PUT"
        },
        data={
            "value": "false"
        },
    )

  def test_004_set_all_ports_mode_on(self):
    """Verifies set_all_ports_mode 'on' is successful."""
    self.uut.set_all_ports_mode("on")
    self._write_command.assert_called_once_with(
        "POST",
        f"http://{self._ip_address}/restapi/relay/outlets/all;/state/",
        headers={
            "Accept": "application/json",
            "X-CSRF": "x",
            "X-HTTP-Method": "PUT"
        },
        data={
            "value": "true"
        },
    )

  def test_005_get_all_ports_mode_on_off(self):
    """Verifies if ports are on or off get_all_ports_mode is successful."""
    self._write_command.return_value = "true,true,true,true,true,true,true,true"
    result = self.uut.get_all_ports_mode()
    self.assertEqual(result, ["on", "on", "on", "on", "on", "on", "on", "on"])

    self._write_command.return_value = (
        "false,false,false,false,false,false,false,false"
    )
    result = self.uut.get_all_ports_mode()
    self.assertEqual(
        result, ["off", "off", "off", "off", "off", "off", "off", "off"]
    )

  def test_006_get_mode_(self):
    """Verifies get_mode returns the ports status successfully."""
    self._write_command.return_value = "false"
    result = self.uut.get_mode(port=1)
    self.assertEqual(result, "off")

  def test_007_set_mode_on(self):
    """Verifies set_mode sets the ports to the specified mode."""
    self.uut.set_mode("on", 1)
    self._write_command.assert_called_once_with(
        "POST",
        f"http://{self._ip_address}/restapi/relay/outlets/=1/state/",
        headers={
            "Accept": "application/json",
            "X-CSRF": "x",
            "X-HTTP-Method": "PUT"
        },
        data={
            "value": "true"
        },
    )

  def test_008_set_mode_off(self):
    """Verifies set_mode sets the ports to the specified mode."""
    self.uut.set_mode("off", 1)
    self._write_command.assert_called_once_with(
        "POST",
        f"http://{self._ip_address}/restapi/relay/outlets/=1/state/",
        headers={
            "Accept": "application/json",
            "X-CSRF": "x",
            "X-HTTP-Method": "PUT"
        },
        data={
            "value": "false"
        },
    )

  def test_009_set_mode_bad_mode(self):
    """Verifies set_mode using bad mode causes error."""
    err_msg = "Mode surprise not found in supported modes"
    with self.assertRaisesRegex(errors.DeviceError, err_msg):
      self.uut.set_mode("surprise", 1)

  def test_010_set_all_ports_mode_bad_mode(self):
    """Verifies set_all_ports_mode using bad mode causes error."""
    err_msg = "Mode surprise not found in supported modes"
    with self.assertRaisesRegex(errors.DeviceError, err_msg):
      self.uut.set_all_ports_mode("surprise")

  def test_011_power_off_bad_port(self):
    """Verifies power_off using bad port causes error."""
    bad_port = 8
    err_msg = "Device {} power_off failed. Port {} is invalid.".format(
        self._name, bad_port)
    with self.assertRaisesRegex(errors.DeviceError, err_msg):
      self.uut.power_off(bad_port)

  def test_012_power_on_bad_port(self):
    """Verifies power_on using bad port causes error."""
    bad_port = 8
    err_msg = "Device {} power_on failed. Port {} is invalid.".format(
        self._name, bad_port)
    with self.assertRaisesRegex(errors.DeviceError, err_msg):
      self.uut.power_on(bad_port)

  def test_013_get_mode_bad_port(self):
    """Verifies get_mode using bad port causes error."""
    bad_port = 8
    err_msg = "Device {} get_mode failed. Port {} is invalid.".format(
        self._name, bad_port)
    with self.assertRaisesRegex(errors.DeviceError, err_msg):
      self.uut.get_mode(bad_port)

  def test_014_total_ports(self):
    """Verifies total_ports property returns the correct number of ports."""
    self.assertEqual(
        self.uut.total_ports,
        self._total_ports,
        f"Device {self._name} total_ports failed. The total ports returned were"
        f" {self.uut.total_ports} which does not match the specified"
        f"{self._total_ports}")


if __name__ == "__main__":
  unit_test_case.main()
