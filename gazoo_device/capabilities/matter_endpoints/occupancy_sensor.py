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

"""Matter Occupancy Sensor endpoint.

An Occupancy Sensor is a measurement and sensing device that is capable of
measuring and reporting the occupancy state in a designated area.

A Occupancy Sensor endpoint houses an instance of Occupancy Sensor Matter device
type with the following defined clusters on this endpoint:

The required clusters for this endpoint: Occupancy Sensing
"""
from typing import Union

from gazoo_device import decorators
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters import occupancy_sensing_chip_tool
from gazoo_device.capabilities.matter_clusters import occupancy_sensing_pw_rpc
from gazoo_device.capabilities.matter_endpoints.interfaces import occupancy_sensor_base


class OccupancySensorEndpoint(occupancy_sensor_base.OccupancySensorBase):
  """Matter Occupancy Sensor endpoint."""

  @decorators.CapabilityDecorator([
      occupancy_sensing_chip_tool.OccupancySensingClusterChipTool,
      occupancy_sensing_pw_rpc.OccupancySensingClusterPwRpc
  ])
  def occupancy_sensing(
      self
  ) -> Union[occupancy_sensing_chip_tool.OccupancySensingClusterChipTool,
             occupancy_sensing_pw_rpc.OccupancySensingClusterPwRpc]:
    """Matter Occupancy Sensing cluster instance."""
    return self.cluster_lazy_init(matter_enums.OccupancySensingCluster.ID)
