"""This test suite verifies device_power capability."""
from typing import Type
from gazoo_device.tests.functional_tests.utils import gdm_test_base


class DevicePowerTestSuite(gdm_test_base.GDMTestBase):
  """Test suite for the device_power capability."""

  @classmethod
  def is_applicable_to(cls, device_type: str,
                       device_class: Type[gdm_test_base.DeviceType],
                       device_name: str) -> bool:
    """Determine if this test suite can run on the given device."""
    if not device_class.has_capabilities(["device_power"]):
      return False
    props = ["device_power.hub_name", "device_power.port_number"]
    return cls.check_properties_set(device_name, props)

  @classmethod
  def requires_pairing(cls) -> bool:
    """Returns True if the device must be paired to run this test suite."""
    return False

  def test_device_power_on_off(self):
    """Verifies on() and off() methods work."""
    original_mode = self.device.device_power.port_mode

    try:
      self.device.device_power.off()
      self.assertEqual(
          self.device.device_power.port_mode, "off",
          f"{self.device.name} port {self.device.device_power.port_number} "
          "should have been set to off")
      self.device.device_power.on()
      on_modes = ["on", "charge", "sync"]
      self.assertIn(
          self.device.device_power.port_mode, on_modes,
          f"{self.device.name} port {self.device.device_power.port_number} "
          f"should have been set to one of {on_modes}")

    finally:
      if original_mode == "off":
        self.logger.info(
            "Restoring device power back to its original mode 'off'")
        self.device.device_power.off()


if __name__ == "__main__":
  gdm_test_base.main()
