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

"""Matter Generic Switch endpoint.

This endpoint module corresponds to the
"Switch" Matter device type which defines required and optional clusters
in the Matter spec 1.0.

A Switch enpoint houses an instance of Switch Matter device type with
the following defined clusters on this endpoint:

The required clusters for this endpoint: Switch and Identify clusters.
"""

from gazoo_device import decorators
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters import switch_chip_tool
from gazoo_device.capabilities.matter_clusters import switch_pw_rpc
from gazoo_device.capabilities.matter_endpoints.interfaces import generic_switch_base


class GenericSwitchEndpoint(generic_switch_base.GenericSwitchBase):
  """Matter Switch endpoint."""

  @decorators.CapabilityDecorator(
      [switch_chip_tool.SwitchClusterChipTool, switch_pw_rpc.SwitchClusterPwRpc]
  )
  def switch(
      self,
  ) -> (
      switch_chip_tool.SwitchClusterChipTool | switch_pw_rpc.SwitchClusterPwRpc
  ):
    """Matter OnOff cluster instance."""
    return self.cluster_lazy_init(matter_enums.SwitchCluster.ID)
