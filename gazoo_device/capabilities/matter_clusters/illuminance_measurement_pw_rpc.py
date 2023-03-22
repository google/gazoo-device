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

"""Pigweed RPC implementation of Matter Illuminance Measurement cluster capability.
"""
from gazoo_device import decorators
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters.interfaces import measurement_base
from gazoo_device.protos import attributes_service_pb2


class IlluminanceMeasurementClusterPwRpc(measurement_base.MeasurementClusterBase
                                        ):
  """Matter Illuminance Measurement cluster capability."""

  CLUSTER_ID = matter_enums.IlluminanceMeasurementCluster.ID
  MATTER_CLUSTER = matter_enums.IlluminanceMeasurementCluster
  ATTRIBUTE_TYPE = (
      attributes_service_pb2.AttributeType.ZCL_INT16U_ATTRIBUTE_TYPE)

  @decorators.DynamicProperty
  def light_sensor_type(self) -> matter_enums.LightSensorType:
    """Fetches the LightSensorType attribute."""
    data = self._read(
        endpoint_id=self._endpoint_id,
        cluster_id=self.MATTER_CLUSTER.ID,
        attribute_id=self.MATTER_CLUSTER.ATTRIBUTE_LIGHT_SENSOR_TYPE,
        attribute_type=(
            attributes_service_pb2.AttributeType.ZCL_ENUM8_ATTRIBUTE_TYPE,))
    return matter_enums.LightSensorType(data.data_uint8)

  @light_sensor_type.setter
  def light_sensor_type(self, value: matter_enums.LightSensorType) -> None:
    """Updates the LightSensorType attribute with new value."""
    sensor_type = matter_enums.LightSensorType(value)
    self._write(
        endpoint_id=self._endpoint_id,
        cluster_id=self.MATTER_CLUSTER.ID,
        attribute_id=self.MATTER_CLUSTER.ATTRIBUTE_LIGHT_SENSOR_TYPE,
        attribute_type=(
            attributes_service_pb2.AttributeType.ZCL_ENUM8_ATTRIBUTE_TYPE),
        data_uint8=sensor_type)
