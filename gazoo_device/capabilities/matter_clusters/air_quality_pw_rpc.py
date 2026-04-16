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

"""Pigweed RPC implementation of the Matter Air Quality cluster capability.
"""
from gazoo_device import decorators
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters.interfaces import air_quality_base
from gazoo_device.protos import attributes_service_pb2


class AirQualityClusterPwRpc(air_quality_base.AirQualityClusterBase):
  """Matter AirQuality cluster capability."""

  @decorators.DynamicProperty
  def air_quality(self) -> matter_enums.AirQualityEnum:
    """The AirQuality attribute."""
    data = self._read(
        endpoint_id=self._endpoint_id,
        cluster_id=matter_enums.AirQualityCluster.ID,
        attribute_id=matter_enums.AirQualityCluster.ATTRIBUTE_AIR_QUALITY,
        attribute_type=(
            attributes_service_pb2.AttributeType.ZCL_ENUM8_ATTRIBUTE_TYPE))
    return matter_enums.AirQualityEnum(data.data_uint8)

  @air_quality.setter
  def air_quality(self, value: matter_enums.AirQualityEnum) -> None:
    """Updates the AirQuality attribute to new value."""
    self._write(
        endpoint_id=self._endpoint_id,
        cluster_id=matter_enums.AirQualityCluster.ID,
        attribute_id=matter_enums.AirQualityCluster.ATTRIBUTE_AIR_QUALITY,
        attribute_type=(
            attributes_service_pb2.AttributeType.ZCL_ENUM8_ATTRIBUTE_TYPE),
        data_uint8=value.value)
