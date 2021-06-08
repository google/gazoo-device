"""Test suite that verifies that optional properties are retrievable."""
from typing import Type
from gazoo_device.tests.functional_tests.utils import gdm_test_base

_TESTED_PROPERTIES = ("ftdi_serial_number", "build_date")


class OptionalPropertiesTestSuite(gdm_test_base.GDMTestBase):
  """Test suite that verifies that optional properties are retrievable."""

  @classmethod
  def is_applicable_to(cls, device_type: str,
                       device_class: Type[gdm_test_base.DeviceType],
                       device_name: str) -> bool:
    """Determine if this test suite can run on the given device."""
    return any(hasattr(device_class, attr) for attr in _TESTED_PROPERTIES)

  @classmethod
  def requires_pairing(cls) -> bool:
    """Returns True if the device must be paired to run this test suite."""
    return False

  def test_get_ftdi_serial_number(self):
    """Tests retrieval of 'ftdi_serial_number' property."""
    if hasattr(type(self.device), "ftdi_serial_number"):
      ftdi_serial_number = self.device.ftdi_serial_number
      self.assertTrue(ftdi_serial_number)
      self.assertIsInstance(ftdi_serial_number, str)

  def test_get_build_date(self):
    """Tests retrieval of 'build_date' property."""
    if hasattr(type(self.device), "build_date"):
      build_date = self.device.build_date
      self.assertTrue(build_date)
      self.assertIsInstance(build_date, str)


if __name__ == "__main__":
  gdm_test_base.main()
