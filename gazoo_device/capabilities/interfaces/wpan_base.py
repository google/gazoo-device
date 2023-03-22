"""Wpan related functionality for devices running wpanctl.

Implemented in most Gazoo embedded linux devices.
"""
import abc
from gazoo_device.capabilities.interfaces import capability_base


class WpanBase(capability_base.CapabilityBase):
  """Class for interacting with wpanctl interface and getting props."""

  @classmethod
  def list_properties_dynamic(cls):
    """Returns a list of dynamic "gdm properties" for this class.

    Each element of the list is a string, with the name of the getter. getattr()
    can be used to read the value. Currently this returns all of the "@property"
    decorated methods. If we add setter properties we will want to revise this.

    Returns:
         list: "attributes" (which can be called by getattr and will return
         a value).
    """
    return [p for p in dir(cls) if isinstance(getattr(cls, p), property)]

  @property
  @abc.abstractmethod
  def ncp_channel(self) -> str:
    """NCP channel value."""

  @property
  @abc.abstractmethod
  def network_name(self) -> str:
    """Wpan network name."""
