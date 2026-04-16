"""Matter Room Air Conditioner endpoint."""

from typing import Union

from gazoo_device import decorators
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters import fan_control_pw_rpc
from gazoo_device.capabilities.matter_clusters import on_off_chip_tool
from gazoo_device.capabilities.matter_clusters import on_off_pw_rpc
from gazoo_device.capabilities.matter_clusters import thermostat_chip_tool
from gazoo_device.capabilities.matter_clusters import thermostat_pw_rpc
from gazoo_device.capabilities.matter_endpoints.interfaces import room_air_conditioner_base


class RoomAirConditionerEndpoint(
    room_air_conditioner_base.RoomAirConditionerBase
):
  """Matter Room Air Conditioner endpoint."""

  @decorators.CapabilityDecorator(
      [on_off_chip_tool.OnOffClusterChipTool, on_off_pw_rpc.OnOffClusterPwRpc]
  )
  def on_off(
      self,
  ) -> Union[
      on_off_chip_tool.OnOffClusterChipTool, on_off_pw_rpc.OnOffClusterPwRpc
  ]:
    """Matter OnOff cluster instance."""
    return self.cluster_lazy_init(matter_enums.OnOffCluster.ID)

  @decorators.CapabilityDecorator([
      thermostat_chip_tool.ThermostatClusterChipTool,
      thermostat_pw_rpc.ThermostatClusterPwRpc,
  ])
  def thermostat(
      self,
  ) -> Union[
      thermostat_chip_tool.ThermostatClusterChipTool,
      thermostat_pw_rpc.ThermostatClusterPwRpc,
  ]:
    """Matter Thermostat cluster instance."""
    return self.cluster_lazy_init(matter_enums.ThermostatCluster.ID)

  @decorators.CapabilityDecorator(fan_control_pw_rpc.FanControlClusterPwRpc)
  def fan_control(self) -> fan_control_pw_rpc.FanControlClusterPwRpc:
    """Matter Fan Control cluster instance."""
    return self.cluster_lazy_init(matter_enums.FanControlCluster.ID)
