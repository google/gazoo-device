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

"""Pigweed RPC implementation of Matter Pressure Measurement cluster capability.
"""
from gazoo_device import decorators
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters.interfaces import pressure_measurement_base
from gazoo_device.protos import attributes_service_pb2

INT16_ATTRIBUTE_TYPE = attributes_service_pb2.AttributeType.ZCL_INT16S_ATTRIBUTE_TYPE
_PressureMeasurementCluster = matter_enums.PressureMeasurementCluster


class PressureMeasurementClusterPwRpc(
    pressure_measurement_base.PressureMeasurementClusterBase):
  """Matter Pressure Measurement cluster capability."""

  @decorators.DynamicProperty
  def measured_value(self) -> int:
    """The MeasuredValue attribute.

    Returns:
      The MeasuredValue attribute.
    """
    measured_value_data = self._read(
        endpoint_id=self._endpoint_id,
        cluster_id=_PressureMeasurementCluster.ID,
        attribute_id=_PressureMeasurementCluster.ATTRIBUTE_MEASURED_VALUE,
        attribute_type=INT16_ATTRIBUTE_TYPE)
    return measured_value_data.data_int16

  @decorators.DynamicProperty
  def min_measured_value(self) -> int:
    """The MinMeasuredValue attribute.

    The MinMeasuredValue attribute indicates the minimum value of MeasuredValue
    that is capable of being measured.

    Returns:
      The MinMeasuredValue attribute.
    """
    min_measured_value_data = self._read(
        endpoint_id=self._endpoint_id,
        cluster_id=_PressureMeasurementCluster.ID,
        attribute_id=_PressureMeasurementCluster.ATTRIBUTE_MIN_MEASURED_VALUE,
        attribute_type=INT16_ATTRIBUTE_TYPE)
    return min_measured_value_data.data_int16

  @decorators.DynamicProperty
  def max_measured_value(self) -> int:
    """The MaxMeasuredValue attribute.

    The MaxMeasuredValue attribute indicates the maximum value of MeasuredValue
    that is capable of being measured.

    Returns:
      The MaxMeasuredValue attribute.
    """
    max_measured_value_data = self._read(
        endpoint_id=self._endpoint_id,
        cluster_id=_PressureMeasurementCluster.ID,
        attribute_id=_PressureMeasurementCluster.ATTRIBUTE_MAX_MEASURED_VALUE,
        attribute_type=INT16_ATTRIBUTE_TYPE)
    return max_measured_value_data.data_int16
