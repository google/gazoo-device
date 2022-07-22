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

"""Matter OnOff light endpoint.

This endpoint module corresponds to the
"On/Off Light" Matter device type which defines required and optional clusters
in the Matter spec 1.0.

A OnOff light enpoint houses an instance of On/Off Light Matter device type with
the following defined clusters on this endpoint:

The required clusters for this endpoint: Scenes, OnOff and Groups.
The optional clusters for this endpoint: Level and OccupancySensing.
"""
from typing import Union

from gazoo_device import decorators
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters import level_control_chip_tool
from gazoo_device.capabilities.matter_clusters import level_control_pw_rpc
from gazoo_device.capabilities.matter_clusters import occupancy_sensing_chip_tool
from gazoo_device.capabilities.matter_clusters import occupancy_sensing_pw_rpc
from gazoo_device.capabilities.matter_clusters import on_off_chip_tool
from gazoo_device.capabilities.matter_clusters import on_off_pw_rpc
from gazoo_device.capabilities.matter_endpoints.interfaces import on_off_light_base


class OnOffLightEndpoint(on_off_light_base.OnOffLightBase):
  """Matter OnOff light endpoint."""

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
  def level(
      self
  ) -> Union[level_control_chip_tool.LevelControlClusterChipTool,
             level_control_pw_rpc.LevelControlClusterPwRpc]:
    """Matter Level Control cluster instance."""
    return self.cluster_lazy_init(matter_enums.LevelControlCluster.ID)

  @decorators.CapabilityDecorator([
      occupancy_sensing_chip_tool.OccupancySensingClusterChipTool,
      occupancy_sensing_pw_rpc.OccupancySensingClusterPwRpc
  ])
  def occupancy_sensing(
      self
  ) -> Union[occupancy_sensing_chip_tool.OccupancySensingClusterChipTool,
             occupancy_sensing_pw_rpc.OccupancySensingClusterPwRpc]:
    """Matter Occupancy cluster instance."""
    return self.cluster_lazy_init(matter_enums.OccupancySensingCluster.ID)

  # TODO(b/209362086) Add the below clusters
  # def scenes(self):
  #   """Matter Scenes cluster instance."""
  #   # TODO(b/206741536): Implement Scenes cluster.
  #   raise NotImplementedError("Scenes cluster isn't implemented.")

  # def groups(self):
  #   """Matter Groups cluster instance."""
  #   # TODO(b/206741536): Implement Groups cluster.
  #   raise NotImplementedError("Groups cluster isn't implemented.")
