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

"""Matter Temperature Sensor endpoint.

A Temperature Sensor device reports measurements of temperature.

This endpoint module corresponds to the
"Temperature Sensor" Matter device type which defines required and optional
clusters in the Matter spec 1.0.

A Temperature Sensor endpoint houses an instance of Temperature Sensor Matter
device type with the following defined clusters on this endpoint:

The required clusters for this endpoint: Temperature Measurement
"""
from gazoo_device import decorators
from gazoo_device.capabilities.matter_clusters import temperature_measurement_pw_rpc
from gazoo_device.capabilities.matter_endpoints.interfaces import temperature_sensor_base


class TemperatureSensorEndpoint(temperature_sensor_base.TemperatureSensorBase):
  """Matter Temperature Sensor endpoint."""

  @decorators.CapabilityDecorator(
      temperature_measurement_pw_rpc.TemperatureMeasurementClusterPwRpc)
  def temperature_measurement(
      self
  ) -> temperature_measurement_pw_rpc.TemperatureMeasurementClusterPwRpc:
    """Matter Occupancy cluster instance."""
    return self.cluster_lazy_init(
        temperature_measurement_pw_rpc.TemperatureMeasurementClusterPwRpc)
