"""Test suite for Switchboard capability on auxiliary devices."""
from typing import Tuple, Type

from gazoo_device.base_classes import auxiliary_device
from gazoo_device.tests.functional_tests.utils import gdm_test_base


class MockPowerSwitch:

  def __init__(self):
    self._is_on = False

  def turn_on_power(self):
    self._is_on = True

  def power_is_on(self):
    return self._is_on


class AuxiliaryDeviceSwitchboardTestSuite(gdm_test_base.GDMTestBase):
  """Test suite for Switchboard capability on auxiliary devices."""

  @classmethod
  def is_applicable_to(cls, device_type: str,
                       device_class: Type[gdm_test_base.DeviceType],
                       device_name: str) -> bool:
    """Determine if this test suite can run on the given device."""
    return (issubclass(device_class, auxiliary_device.AuxiliaryDevice)
            and device_class.has_capabilities(["switchboard"]))

  @classmethod
  def requires_pairing(cls) -> bool:
    """Returns True if the device must be paired to run this test suite."""
    return False

  @classmethod
  def required_test_config_variables(cls) -> Tuple[str, ...]:
    """Returns keys required to be present in the functional test config."""
    return ("shell_cmd", "expect")

  def test_send_and_expect(self):
    """Tests send_and_expect() method."""
    timeout = 10  # In seconds.
    response = self.device.switchboard.send_and_expect(
        self.test_config["shell_cmd"],
        self.test_config["expect"],
        timeout=timeout)
    self.assertFalse(
        response.timedout,
        "{} switchboard.send_and_expect failed for command {!r}. "
        "Did not find regex {!r} in {}s. Device output: {!r}"
        .format(self.device.name, self.test_config["shell_cmd"],
                self.test_config["expect"], timeout, response.before))

  def test_do_and_expect(self):
    """Tests switchboard.do_and_expect() method."""
    switch = MockPowerSwitch()
    expect_result = self.device.switchboard.do_and_expect(
        switch.turn_on_power, (), {},
        ["fake_string, won't match anything"],
        timeout=.1)
    self.assertTrue(
        expect_result.timedout,
        "Expected do_and_expect to time out, but timedout was False")
    self.assertTrue(switch.power_is_on,
                    "switch.turn_on_power() did not execute. "
                    "The power state is still off for switch.")

  def test_expect_with_bogus_logline(self):
    """Tests switchboard.expect() method for a log line that doesn't exist."""
    phrase = "garblygookand more"
    response = self.device.switchboard.expect([phrase], timeout=2)
    self.assertTrue(response.timedout,
                    "Response should have timed out, but it didn't. "
                    f"Requested log line regex: {phrase!r}. "
                    f"Device output: {response.before!r}")


if __name__ == "__main__":
  gdm_test_base.main()

