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

"""Matter Window Covering endpoint.

This endpoint module corresponds to the
"Window Covering" Matter device type which defines required and optional
clusters in the Matter spec 1.0.

A Window Covering endpoint houses an instance of Window Covering Matter
device type with the following defined clusters on this endpoint:

The required clusters for this endpoint: Window Covering
"""
from gazoo_device import decorators
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters import window_covering_pw_rpc
from gazoo_device.capabilities.matter_endpoints.interfaces import window_covering_base


class WindowCoveringEndpoint(window_covering_base.WindowCoveringBase):
  """Matter Window Covering endpoint."""

  @decorators.CapabilityDecorator(
      window_covering_pw_rpc.WindowCoveringClusterPwRpc)
  def window_covering(
      self
  ) -> window_covering_pw_rpc.WindowCoveringClusterPwRpc:
    """Matter Window Covering cluster instance."""
    return self.cluster_lazy_init(matter_enums.WindowCoveringCluster.ID)
