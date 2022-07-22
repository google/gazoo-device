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

"""Matter Humidity Sensor endpoint.

A humidity sensor (in most cases a Relative humidity sensor) reports humidity
measurements.

This endpoint module corresponds to the
"Humidity Sensor" Matter device type which defines required and optional
clusters in the Matter spec 1.0.
A Humidity Sensor endpoint houses an instance of Humidity Sensor Matter device
type with the following defined clusters on this endpoint:

The required clusters for this endpoint: Relative Humidity Measurement
"""
from gazoo_device import decorators
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters import relative_humidity_measurement_pw_rpc
from gazoo_device.capabilities.matter_endpoints.interfaces import humidity_sensor_base


class HumiditySensorEndpoint(humidity_sensor_base.HumiditySensorBase):
  """Matter Humidity Sensor endpoint."""

  @decorators.CapabilityDecorator(
      relative_humidity_measurement_pw_rpc.
      RelativeHumidityMeasurementClusterPwRpc)
  def relative_humidity_measurement(
      self) -> (relative_humidity_measurement_pw_rpc.
                RelativeHumidityMeasurementClusterPwRpc):
    """Matter Relative Humidity Measurement cluster instance."""
    return self.cluster_lazy_init(
        matter_enums.RelativeHumidityMeasurementCluster.ID)
