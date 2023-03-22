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

"""Matter Fan endpoint.

This endpoint module corresponds to the
"Fan" Matter device type which defines required and optional clusters
in the Matter spec 1.0.

A Fan enpoint houses an instance of Fan Matter device type with
the following defined clusters on this endpoint:

The required clusters for this endpoint: Identify, Groups and FanControl
"""
from gazoo_device import decorators
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters import fan_control_pw_rpc
from gazoo_device.capabilities.matter_endpoints.interfaces import fan_base


class FanEndpoint(fan_base.FanBase):
  """Matter Fan endpoint."""

  @decorators.CapabilityDecorator(fan_control_pw_rpc.FanControlClusterPwRpc)
  def fan_control(self) -> fan_control_pw_rpc.FanControlClusterPwRpc:
    """Matter Fan Control cluster instance."""
    return self.cluster_lazy_init(matter_enums.FanControlCluster.ID)
