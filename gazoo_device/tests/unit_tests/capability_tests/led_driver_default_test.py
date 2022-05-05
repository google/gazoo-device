"""Unit tests for the led_driver_default capability."""
from unittest import mock

from gazoo_device import errors
from gazoo_device.capabilities import led_driver_default
from gazoo_device.tests.unit_tests.utils import unit_test_case

import pyvisa

_COMMANDS = led_driver_default._COMMANDS


class LedDriverDefaultTest(unit_test_case.UnitTestCase):
  """Test class for led_driver_default capability."""

  def setUp(self):
    super().setUp()
    self.device_name = "dc2200-3456"
    self.serial_number = "123456"
    self.mock_pyvisa_inst = mock.create_autospec(
        pyvisa.resources.usb.USBInstrument)
    self.resource_manager_mock = mock.create_autospec(pyvisa.ResourceManager)
    self.enter_context(
        mock.patch.object(pyvisa,
                          "ResourceManager",
                          autospec=True,
                          return_value=self.resource_manager_mock))
    self.resource_manager_mock.open_resource.return_value = (
        self.mock_pyvisa_inst)

    self.uut = led_driver_default.LedDriverDefault(
        device_name=self.device_name,
        serial_number=self.serial_number,
    )
    self.uut.health_check()
    self.mock_pyvisa_inst.reset_mock()

  def test_setup_device(self):
    """Tests device gets configured for remote use."""
    self.uut._healthy = None  # Re-run health check.
    self.uut.health_check()
    self.mock_pyvisa_inst.write.assert_has_calls([
        mock.call(_COMMANDS["CLEAR_STATUS"]),
        mock.call(_COMMANDS["ENABLE_REMOTE"])])

  def test_set_frequency(self):
    """Tests set_frequency."""
    self.uut.set_frequency(100)
    self.mock_pyvisa_inst.write.assert_called_with(
        _COMMANDS["SET_FREQUENCY"].format(freq=100))

  def test_get_frequency(self):
    """Tests get_frequency."""
    self.uut.get_frequency()
    self.mock_pyvisa_inst.query.assert_called_with(_COMMANDS["GET_FREQUENCY"])

  def test_set_modulation_function_error(self):
    """Tests set_modulation_function without valid input."""
    with self.assertRaisesRegex(
        errors.DeviceError, "not a valid modulation function"):
      self.uut.set_modulation_function("invalid")

  def test_set_modulation_function(self):
    """Tests set_modulation_function with valid input."""
    self.uut.set_modulation_function("sinusoid")
    self.mock_pyvisa_inst.write.assert_called_with(
        _COMMANDS["SET_MODULATION_FUNCTION"].format(func="sinusoid"))

  def test_get_max_brightness(self):
    """Tests get_max_brightness."""
    self.uut.get_max_brightness()
    self.mock_pyvisa_inst.query.assert_called_with(
        _COMMANDS["GET_MAX_BRIGHTNESS"])

  def test_get_min_brightness(self):
    """Tests get_min_brightness."""
    self.uut.get_min_brightness()
    self.mock_pyvisa_inst.query.assert_called_with(
        _COMMANDS["GET_MIN_BRIGHTNESS"])

  def test_set_max_brightness(self):
    """Tests set_max_brightness."""
    self.uut.set_max_brightness(100)
    self.mock_pyvisa_inst.write.assert_called_with(
        _COMMANDS["SET_MAX_BRIGHTNESS"].format(val=100))

  def test_set_min_brightness(self):
    """Tests set_min_brightness."""
    self.uut.set_min_brightness(20)
    self.mock_pyvisa_inst.write.assert_called_with(
        _COMMANDS["SET_MIN_BRIGHTNESS"].format(val=20))

  def test_get_output_state(self):
    """Tests get_output_state."""
    self.assertIsInstance(self.uut.get_output_state(), bool)
    self.mock_pyvisa_inst.query.assert_called_with(
        _COMMANDS["GET_LED_OUTPUT_STATE"])

  def test_set_output_state(self):
    """Tests set_output_state."""
    self.uut.set_output_state(True)
    self.mock_pyvisa_inst.write.assert_called_with(
        _COMMANDS["SET_LED_OUTPUT_STATE"].format(state=1))

if __name__ == "__main__":
  unit_test_case.main()
