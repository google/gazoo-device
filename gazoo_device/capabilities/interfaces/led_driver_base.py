"""LED driver capability interface."""
import abc

from gazoo_device.capabilities.interfaces import capability_base
from typing_extensions import Literal

ModFunc = Literal["sinusoid", "square", "triangle"]


class LedDriverBase(capability_base.CapabilityBase):
  """Abstract class for LED driver interface."""

  @abc.abstractmethod
  def get_frequency(self) -> float:
    """Gets the LED frequency in Hertz."""

  @abc.abstractmethod
  def set_frequency(self, freq_hz: float) -> None:
    """Sets the LED frequency.

    Args:
      freq_hz: Frequency to set (in Hertz). Min frequency for DC2200 is 20Hz.
    """

  @abc.abstractmethod
  def get_max_brightness(self) -> int:
    """Gets max brightness used for output in percentage 0-100."""

  @abc.abstractmethod
  def set_max_brightness(self, brightness: int) -> None:
    """Sets max brightness used for output in percentage 0-100."""

  @abc.abstractmethod
  def get_min_brightness(self) -> int:
    """Gets min brightness used for output in percentage 0-100."""

  @abc.abstractmethod
  def set_min_brightness(self, brightness: int) -> None:
    """Sets min brightness used for output in percentage 0-100."""

  @abc.abstractmethod
  def get_modulation_function(self) -> ModFunc:
    """Gets the modulation function name used by LED driver.

    Raises:
      ValueError: If unsupported function name provided.

    Returns:
      Name of modulation function.
        One of ["sinusoid", "square", "triangle"]
    """

  @abc.abstractmethod
  def set_modulation_function(self, func_name: ModFunc) -> None:
    """Sets the modulation function name used by LED driver.

    Args:
      func_name: Name of modulation function to use.
        One of ["sinusoid", "square", "triangle"].

    Raises:
      ValueError: If unsupported function name provided.
    """

  @abc.abstractmethod
  def get_output_state(self) -> bool:
    """Gets the LED state boolean - True means on and False means off."""

  @abc.abstractmethod
  def set_output_state(self, state: bool) -> None:
    """Sets the LED state boolean - True means on and False means off."""
