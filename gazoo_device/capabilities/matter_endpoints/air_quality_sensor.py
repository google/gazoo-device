# Copyright 2024 Google LLC
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

"""Matter Air Quality Sensor endpoint.

This endpoint module corresponds to the
"Air Quality Sensor" Matter device type which defines required and optional
clusters in the Matter spec 1.0.
"""
from gazoo_device import decorators
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters import air_quality_pw_rpc
from gazoo_device.capabilities.matter_endpoints.interfaces import air_quality_sensor_base


class AirQualitySensorEndpoint(air_quality_sensor_base.AirQualitySensorBase):
  """Matter Air Quality Sensor endpoint."""

  @decorators.CapabilityDecorator(air_quality_pw_rpc.AirQualityClusterPwRpc)
  def air_quality(self) -> air_quality_pw_rpc.AirQualityClusterPwRpc:
    """Matter Air Quality cluster instance."""
    return self.cluster_lazy_init(matter_enums.AirQualityCluster.ID)
