"""Interface for a Room Air Conditioner endpoint."""

import abc

from gazoo_device.capabilities.matter_clusters.interfaces import fan_control_base
from gazoo_device.capabilities.matter_clusters.interfaces import on_off_base
from gazoo_device.capabilities.matter_clusters.interfaces import thermostat_base
from gazoo_device.capabilities.matter_endpoints.interfaces import endpoint_base


class RoomAirConditionerBase(endpoint_base.EndpointBase, metaclass=abc.ABCMeta):
  """Matter Room Air Conditioner interface."""

  DEVICE_TYPE_ID = 0x0072
  DEVICE_TYPE_NAME = "RoomAirConditioner"

  @property
  @abc.abstractmethod
  def thermostat(self) -> thermostat_base.ThermostatClusterBase:
    """Required cluster: ZCL thermostat cluster."""

  @property
  @abc.abstractmethod
  def on_off(self) -> on_off_base.OnOffClusterBase:
    """Required cluster: ZCL on_off cluster."""

  @property
  @abc.abstractmethod
  def fan_control(self) -> fan_control_base.FanControlClusterBase:
    """Required cluster: ZCL Fan Control cluster."""
