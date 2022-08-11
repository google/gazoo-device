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

"""Matter Light Sensor endpoint.

A Light Sensor device measures and reports the pressure of a fluid.

This endpoint module corresponds to the
"Light Sensor" Matter device type which defines required and optional
clusters in the Matter spec 1.0.

A Light Sensor endpoint houses an instance of Light Sensor Matter device
type with the following defined clusters on this endpoint:

The required clusters for this endpoint: Illuminance Measurement.
"""
from typing import Union

from gazoo_device import decorators
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters import illuminance_measurement_chip_tool
from gazoo_device.capabilities.matter_clusters import illuminance_measurement_pw_rpc
from gazoo_device.capabilities.matter_endpoints.interfaces import light_sensor_base


class LightSensorEndpoint(light_sensor_base.LightSensorBase):
  """Matter Light Sensor endpoint."""

  @decorators.CapabilityDecorator([
      illuminance_measurement_chip_tool.IlluminanceMeasurementClusterChipTool,
      illuminance_measurement_pw_rpc.IlluminanceMeasurementClusterPwRpc
  ])
  def illuminance_measurement(
      self
  ) -> Union[
      illuminance_measurement_chip_tool.IlluminanceMeasurementClusterChipTool,
      illuminance_measurement_pw_rpc.IlluminanceMeasurementClusterPwRpc]:
    """Matter Illuminance Measurement cluster instance."""
    return self.cluster_lazy_init(matter_enums.IlluminanceMeasurementCluster.ID)
