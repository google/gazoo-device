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

"""Matter Speaker endpoint.

This endpoint module corresponds to the
"Speaker" Matter device type which defines required and optional clusters
in the Matter spec 1.0.

A Speaker enpoint houses an instance of Speaker Matter device type with
the following defined clusters on this endpoint:

The required clusters for this endpoint: OnOff and Level.
"""
from typing import Union

from gazoo_device import decorators
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters import level_control_chip_tool
from gazoo_device.capabilities.matter_clusters import level_control_pw_rpc
from gazoo_device.capabilities.matter_clusters import on_off_chip_tool
from gazoo_device.capabilities.matter_clusters import on_off_pw_rpc
from gazoo_device.capabilities.matter_endpoints.interfaces import speaker_base


class SpeakerEndpoint(speaker_base.SpeakerBase):
  """Matter Speaker endpoint."""

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
