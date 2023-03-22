# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Matter Heating Cooling Unit endpoint.

A Heating/Cooling Unit is a device capable of heating or cooling a space in a
house. It is not mandatory to provide both functionalities (for example, the
device may just heat but not cool). It may be an indoor air handler.

This endpoint module corresponds to the "Heating Cooling Unit" Matter device
type which defines required and optional clusters in the Matter spec 1.0.
"""
from typing import Union

from gazoo_device import decorators
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters import fan_control_pw_rpc
from gazoo_device.capabilities.matter_clusters import level_control_chip_tool
from gazoo_device.capabilities.matter_clusters import level_control_pw_rpc
from gazoo_device.capabilities.matter_clusters import on_off_chip_tool
from gazoo_device.capabilities.matter_clusters import on_off_pw_rpc
from gazoo_device.capabilities.matter_endpoints.interfaces import heating_cooling_unit_base


class HeatingCoolingUnitEndpoint(
    heating_cooling_unit_base.HeatingCoolingUnitBase):
  """Matter Heating Cooling Unit endpoint."""

  @decorators.CapabilityDecorator(
      [on_off_chip_tool.OnOffClusterChipTool, on_off_pw_rpc.OnOffClusterPwRpc])
  def on_off(
      self
  ) -> Union[on_off_chip_tool.OnOffClusterChipTool,
             on_off_pw_rpc.OnOffClusterPwRpc]:
    """Matter OnOff cluster instance."""
    return self.cluster_lazy_init(matter_enums.OnOffCluster.ID)

  @decorators.CapabilityDecorator([
      level_control_chip_tool.LevelControlClusterChipTool,
      level_control_pw_rpc.LevelControlClusterPwRpc
  ])
  def level_control(
      self
  ) -> Union[level_control_chip_tool.LevelControlClusterChipTool,
             level_control_pw_rpc.LevelControlClusterPwRpc]:
    """Matter Level Control cluster instance."""
    return self.cluster_lazy_init(matter_enums.LevelControlCluster.ID)

  @decorators.CapabilityDecorator(fan_control_pw_rpc.FanControlClusterPwRpc)
  def fan_control(self) -> fan_control_pw_rpc.FanControlClusterPwRpc:
    """Matter Fan Control cluster instance."""
    return self.cluster_lazy_init(matter_enums.FanControlCluster.ID)
