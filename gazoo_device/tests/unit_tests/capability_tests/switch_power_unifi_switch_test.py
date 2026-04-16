"""Unit tests for the switch_power_unifi_switch capability."""
from gazoo_device import errors
from gazoo_device.auxiliary_devices import unifi_poe_switch
from gazoo_device.capabilities import switch_power_unifi_switch
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.tests.unit_tests.utils import unifi_poe_switch_device_logs


class SwitchPowerUnifiSwitchCapabilityTests(
    fake_device_test_case.FakeDeviceTestCase):
  """Test class to verify the behavior of the SwitchPowerUnifiSwitch capability."""

  def setUp(self):
    super().setUp()
    self._total_ports = 8
    self.setup_fake_device_requirements("unifi_switch-1234")
    self.fake_responder.behavior_dict = {
        **unifi_poe_switch_device_logs.TELNET_COMMAND_RESPONSES}
    self.uut = switch_power_unifi_switch.SwitchPowerUnifiSwitch(
        device_name=self.uut_name,
        command_dict=unifi_poe_switch.COMMANDS,
        regex_dict=unifi_poe_switch.REGEXES,
        total_ports=self._total_ports,
        send_and_expect_fn=self.mock_switchboard.send_and_expect,
        send_fn=self.mock_switchboard.send)

  def test_001_power_on(self):
    """Verifies power on is successful."""
    self.fake_responder.behavior_dict.update(
        unifi_poe_switch_device_logs.SHOW_POE_PORT_AUTO)
    self.uut.power_on(port=1)

  def test_002_power_off(self):
    """Verifies power off is successful."""
    self.fake_responder.behavior_dict.update(
        unifi_poe_switch_device_logs.SHOW_POE_PORT_SHUTDOWN)
    self.uut.power_off(port=1)

  def test_003_set_all_ports_mode_off(self):
    """Verifies set_all_ports_mode 'off' is successful."""
    self.fake_responder.behavior_dict.update(
        unifi_poe_switch_device_logs.SHOW_POE_PORT_SHUTDOWN)
    self.uut.set_all_ports_mode("off")

  def test_004_set_all_ports_mode_on(self):
    """Verifies set_all_ports_mode 'on' is successful."""
    self.fake_responder.behavior_dict.update(
        unifi_poe_switch_device_logs.SHOW_POE_PORT_AUTO)
    self.uut.set_all_ports_mode("on")

  def test_005_get_all_ports_mode_on_off(self):
    """Verifies if ports are on or off get_all_ports_mode is successful."""
    self.fake_responder.behavior_dict.update(
        unifi_poe_switch_device_logs.SHOW_POE_PORT_AUTO)
    result = self.uut.get_all_ports_mode()
    all_on = all(port == "on" for port in result)
    self.assertTrue(
        all_on,
        "Expected {} ports in 'on' mode".format(self._total_ports))

    self.fake_responder.behavior_dict.update(
        unifi_poe_switch_device_logs.SHOW_POE_PORT_SHUTDOWN)
    result = self.uut.get_all_ports_mode()
    all_off = all(port == "off" for port in result)
    self.assertTrue(
        all_off,
        "Expected {} ports in 'off' mode".format(self._total_ports))

  def test_006_get_mode_(self):
    """Verifies get_mode returns the ports status successfully."""
    self.fake_responder.behavior_dict.update(
        unifi_poe_switch_device_logs.SHOW_POE_PORT_AUTO)
    result = self.uut.get_mode(port=1)
    self.assertEqual(result, "on")

  def test_007_set_all_ports_mode_bad_mode(self):
    """Verifies set_all_ports_mode using bad mode causes error."""
    err_msg = "Mode surprise not found"
    with self.assertRaisesRegex(errors.DeviceError, err_msg):
      self.uut.set_all_ports_mode("surprise")

  def test_008_power_off_bad_port(self):
    """Verifies power_off using bad port causes error."""
    bad_port = 9
    err_msg = "Device {} power_off failed. Port {} is invalid.".format(
        self.uut_name, bad_port)
    with self.assertRaisesRegex(errors.DeviceError, err_msg):
      self.uut.power_off(bad_port)

  def test_009_power_on_bad_port(self):
    """Verifies power_on using bad port causes error."""
    bad_port = 9
    err_msg = "Device {} power_on failed. Port {} is invalid.".format(
        self.uut_name, bad_port)
    with self.assertRaisesRegex(errors.DeviceError, err_msg):
      self.uut.power_on(bad_port)

  def test_010_get_mode_bad_port(self):
    """Verifies get_mode using bad port causes error."""
    bad_port = 9
    err_msg = "Device {} get_mode failed. Port {} is invalid.".format(
        self.uut_name, bad_port)
    with self.assertRaisesRegex(errors.DeviceError, err_msg):
      self.uut.get_mode(bad_port)

  def test_011_enter_telnet(self):
    """Verifies enter telnet works."""
    self.uut._telnet_send(
        func=self.uut._poe_telnet_send_and_expect,
        func_args=([self.uut._command_dict["MAC_ADDRESS"]],
                   [self.uut._regex_dict["MAC_ADDRESS_REGEX"]]),
        func_kwargs={"regex_group": 1})

  def test_014_total_ports(self):
    """Verifies total_ports property returns the correct number of ports."""
    self.assertEqual(
        self.uut.total_ports,
        self._total_ports,
        f"Device {self.uut_name} total_ports failed. The total ports returned "
        f"were {self.uut.total_ports} which does not match the specified "
        f"{self._total_ports}")


if __name__ == "__main__":
  fake_device_test_case.main()
