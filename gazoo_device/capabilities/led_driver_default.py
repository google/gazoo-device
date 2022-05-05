"""LED driver capability.

This capability interacts with the DC2200 from Thorlabs.
Currently supports a single primary LED source.
"""
import typing
from typing import Mapping, Optional

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import led_driver_base
from gazoo_device.utility import retry

import immutabledict
import pyvisa


logger = gdm_logger.get_logger()

_CONNECTION_ATTEMPT_TIMEOUT_S = 10

_COMMANDS = immutabledict.immutabledict({
    "SET_MAX_BRIGHTNESS": "SOURCE:IMOD:HIGH {val}",
    "SET_MIN_BRIGHTNESS": "SOURCE:IMOD:LOW {val}",
    "SET_FREQUENCY": "SOURCE:IMOD:FREQ {freq}",
    "SET_MODULATION_FUNCTION": "SOURCE:IMOD:FUNC {func}",
    "SET_LED_OUTPUT_STATE": "OUTPUT {state}",

    "GET_MAX_BRIGHTNESS": "SOURCE:IMOD:HIGH?",
    "GET_MIN_BRIGHTNESS": "SOURCE:IMOD:LOW?",
    "GET_FREQUENCY": "SOURCE:IMOD:FREQ?",
    "GET_MODULATION_FUNCTION": "SOURCE:IMOD:FUNC?",
    "GET_LED_OUTPUT_STATE": "OUTPUT?",

    "CLEAR_STATUS": "*CLS",
    "ENABLE_REMOTE": "SYSTEM:REMOTE",
})

_MOD_FUNC_SHORT_TO_LONG: Mapping[str, led_driver_base.ModFunc] = (
    immutabledict.immutabledict({
        "SQU": "square",
        "SIN": "sinusoid",
        "TRI": "triangle",
    }))


class LedDriverDefault(led_driver_base.LedDriverBase):
  """Class for LED driver capability."""

  def __init__(
      self,
      device_name: str,
      serial_number: str) -> None:
    """Initializes an instance of the LED driver.

    Args:
      device_name: Name of device. Usually accessible via self.name.
      serial_number: Serial number of the LED driver. This is used
        to identify the power supply and interface with it.
    """
    super().__init__(device_name=device_name)
    self._serial_number = serial_number

    # Note this doesn't hold on to any resources at this stage.
    self._resource_manager = pyvisa.ResourceManager()
    self._resource_string = self._resource_manager.list_resources(
        query=f"?*::{self._serial_number}::?*INSTR")[0]

    self._pyvisa_device_cache = None  # Gets set in health_check.

  def _setup_device(self) -> None:
    """Sets up device by clearing status and enabling remote control."""
    self._pyvisa_device_cache.write(_COMMANDS["CLEAR_STATUS"])
    self._pyvisa_device_cache.write(_COMMANDS["ENABLE_REMOTE"])

  @decorators.DynamicProperty
  def _pyvisa_device(self) -> Optional[pyvisa.resources.resource.Resource]:
    self.health_check()
    return self._pyvisa_device_cache

  @decorators.CapabilityLogDecorator(logger, level=decorators.DEBUG)
  def health_check(self) -> None:
    """Checks that the capability is ready to use.

    Raises:
      errors.CapabilityNotReadyError: If failed to connect after
        retrying for _CONNECTION_ATTEMPT_TIMEOUT_S seconds.
    """
    if not self._healthy:
      try:
        # The DC2200 can take a few attempts to open the resource.
        self._pyvisa_device_cache = retry.retry(
            func=self._resource_manager.open_resource,
            func_args=(self._resource_string,),
            exc_type=errors.DeviceError,
            reraise=False,
            timeout=_CONNECTION_ATTEMPT_TIMEOUT_S)
        self._setup_device()
        self._healthy = True
      except Exception as err:
        self._healthy = False
        raise errors.CapabilityNotReadyError(
            msg=repr(err), device_name=self._device_name) from err

  def get_frequency(self) -> float:
    """Gets the LED frequency in Hertz."""
    return float(self._pyvisa_device.query(_COMMANDS["GET_FREQUENCY"]))

  @decorators.CapabilityLogDecorator(logger)
  def set_frequency(self, freq_hz: float) -> None:
    """Sets the LED frequency.

    Args:
      freq_hz: Frequency to set (in Hertz). Min frequency for DC2200 is 20Hz.
    """
    self._pyvisa_device.write(_COMMANDS["SET_FREQUENCY"].format(freq=freq_hz))

  def get_max_brightness(self) -> float:
    """Gets max brightness used for output in percentage 0-100."""
    return float(self._pyvisa_device.query(_COMMANDS["GET_MAX_BRIGHTNESS"]))

  @decorators.CapabilityLogDecorator(logger)
  def set_max_brightness(self, brightness: float) -> None:
    """Sets max brightness used for output in percentage 0-100."""
    self._pyvisa_device.write(
        _COMMANDS["SET_MAX_BRIGHTNESS"].format(val=brightness))

  def get_min_brightness(self) -> float:
    """Gets min brightness used for output in percentage 0-100."""
    return float(self._pyvisa_device.query(_COMMANDS["GET_MIN_BRIGHTNESS"]))

  @decorators.CapabilityLogDecorator(logger)
  def set_min_brightness(self, brightness: float) -> None:
    """Sets min brightness used for output in percentage 0-100."""
    self._pyvisa_device.write(
        _COMMANDS["SET_MIN_BRIGHTNESS"].format(val=brightness))

  def get_modulation_function(self) -> led_driver_base.ModFunc:
    """Gets the modulation function name used by LED driver.

    Raises:
      ValueError: If unsupported function name provided.

    Returns:
      Name of modulation function.
        One of ["sinusoid", "square", "triangle"]
    """
    response = self._pyvisa_device.query(
        _COMMANDS["GET_MODULATION_FUNCTION"]).strip().upper()
    return typing.cast(
        led_driver_base.ModFunc, _MOD_FUNC_SHORT_TO_LONG[response])

  @decorators.CapabilityLogDecorator(logger)
  def set_modulation_function(self, func_name: led_driver_base.ModFunc) -> None:
    """Sets the modulation function name used by LED driver.

    Args:
      func_name: Name of modulation function to use.
        One of ["sinusoid", "square", "triangle"].

    Raises:
      errors.DeviceError: If function name provided is invalid.
    """
    if func_name not in _MOD_FUNC_SHORT_TO_LONG.values():
      raise errors.DeviceError(
          f"{func_name} is not a valid modulation function. "
          f"Please use one of {list(_MOD_FUNC_SHORT_TO_LONG.values())}")
    self._pyvisa_device.write(_COMMANDS["SET_MODULATION_FUNCTION"].format(
        func=func_name))

  def get_output_state(self) -> bool:
    """Gets the LED state boolean - True means on and False means off."""
    return bool(
        int(self._pyvisa_device.query(_COMMANDS["GET_LED_OUTPUT_STATE"])))

  @decorators.CapabilityLogDecorator(logger)
  def set_output_state(self, state: bool) -> None:
    """Sets the LED state boolean - True means on and False means off."""
    self._pyvisa_device.write(
        _COMMANDS["SET_LED_OUTPUT_STATE"].format(state=int(state)))
