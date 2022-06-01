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

"""Matter Pressure Sensor endpoint.

A Pressure Sensor device measures and reports the pressure of a fluid.

This endpoint module corresponds to the
"Pressure Sensor" Matter device type which defines required and optional
clusters in the Matter spec 1.0.

A Pressure Sensor endpoint houses an instance of Pressure Sensor Matter device
type with the following defined clusters on this endpoint:

The required clusters for this endpoint: Pressure Measurement
"""
from gazoo_device import decorators
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters import pressure_measurement_pw_rpc
from gazoo_device.capabilities.matter_endpoints.interfaces import pressure_sensor_base


class PressureSensorEndpoint(pressure_sensor_base.PressureSensorBase):
  """Matter Pressure Sensor endpoint."""

  @decorators.CapabilityDecorator(
      pressure_measurement_pw_rpc.PressureMeasurementClusterPwRpc)
  def pressure_measurement(
      self) -> pressure_measurement_pw_rpc.PressureMeasurementClusterPwRpc:
    """Matter Pressure Measurement cluster instance."""
    return self.cluster_lazy_init(matter_enums.PressureMeasurementCluster.ID)
