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
from gazoo_device import errors
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
    return self._read_value(
        attribute_id=_PressureMeasurementCluster.ATTRIBUTE_MEASURED_VALUE)

  @measured_value.setter
  def measured_value(self, value: int) -> None:
    """Updates the MeasuredValue attribute with new value."""
    self._write_value(
        attribute_id=_PressureMeasurementCluster.ATTRIBUTE_MEASURED_VALUE,
        value=value)

  @decorators.DynamicProperty
  def min_measured_value(self) -> int:
    """The MinMeasuredValue attribute.

    The MinMeasuredValue attribute indicates the minimum value of MeasuredValue
    that is capable of being measured.

    Returns:
      The MinMeasuredValue attribute.
    """
    return self._read_value(
        attribute_id=_PressureMeasurementCluster.ATTRIBUTE_MIN_MEASURED_VALUE)

  @min_measured_value.setter
  def min_measured_value(self, value: int) -> None:
    """Updates the MinMeasuredValue attribute with new value."""
    self._write_value(
        attribute_id=_PressureMeasurementCluster.ATTRIBUTE_MIN_MEASURED_VALUE,
        value=value)

  @decorators.DynamicProperty
  def max_measured_value(self) -> int:
    """The MaxMeasuredValue attribute.

    The MaxMeasuredValue attribute indicates the maximum value of MeasuredValue
    that is capable of being measured.

    Returns:
      The MaxMeasuredValue attribute.
    """
    return self._read_value(
        attribute_id=_PressureMeasurementCluster.ATTRIBUTE_MAX_MEASURED_VALUE)

  @max_measured_value.setter
  def max_measured_value(self, value: int) -> None:
    """Updates the MaxMeasuredValue attribute with new value."""
    self._write_value(
        attribute_id=_PressureMeasurementCluster.ATTRIBUTE_MAX_MEASURED_VALUE,
        value=value)

  def _read_value(self, attribute_id: int) -> int:
    """Reads the value from the given attribute ID.

    Args:
      attribute_id: Attribute ID on PressureMeasurementCluster.

    Returns:
      The value read from the attribute.
    """
    value_data = self._read(
        endpoint_id=self._endpoint_id,
        cluster_id=_PressureMeasurementCluster.ID,
        attribute_id=attribute_id,
        attribute_type=INT16_ATTRIBUTE_TYPE)
    return value_data.data_int16

  def _write_value(self, attribute_id: int, value: int) -> None:
    """Writes the value to the given attribute ID.

    Args:
      attribute_id: Attribute ID on PressureMeasurementCluster.
      value: Value to write to the attribute.

    Raises:
      DeviceError when the attribute value doesn't change.
    """
    self._write(
        endpoint_id=self._endpoint_id,
        cluster_id=_PressureMeasurementCluster.ID,
        attribute_id=attribute_id,
        attribute_type=INT16_ATTRIBUTE_TYPE,
        data_int16=value)
    if self._read_value(attribute_id) != value:
      raise errors.DeviceError(
          f"Device {self._device_name} Attribute {attribute_id} didn't change"
          f" to {value}")