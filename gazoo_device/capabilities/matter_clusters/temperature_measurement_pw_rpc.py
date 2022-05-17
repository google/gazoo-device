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

"""RPC implementation of Matter Temperature Measurement cluster capability.
"""
from gazoo_device import decorators
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters.interfaces import temperature_measurement_base
from gazoo_device.protos import attributes_service_pb2

_MIN_MEASURED_UPPERBOUND = 32766
_MAX_MEASURED_UPPERBOUND = 32767
_ATTR_VAL_MAX = 1 << 16
_TempMeasurementCluster = matter_enums.TemperatureMeasurementCluster
INT16_ATTRIBUTE_TYPE = attributes_service_pb2.AttributeType.ZCL_INT16S_ATTRIBUTE_TYPE


def _convert_attribute_constraint_value(
    unsigned_value: int, upper_bound: int) -> int:
  """Converts the unsigned value to the attribute constraint value.

  The attribute values of temperature_measurement has constraint according to
  the spec: MinMeasuredValue has range from -27315 to 32766; MaxMeasuredValue
  has range from -27314 to 32767. However, the returned value from the Ember
  API call will always be an unsigned value (which is always >= 0), therefore
  we'll need to manually substract the 2^16 for complement. (ex: returned value
  = 38221 is actually 38221 - 2^16 = -27315 in spec)

  Args:
    unsigned_value: The unsigned value of attribute returned from Ember API.
    upper_bound: Upper bound value of attribute from spec.

  Returns:
    The actual attribute value.
  """
  if unsigned_value <= upper_bound:
    return unsigned_value
  return unsigned_value - _ATTR_VAL_MAX


class TemperatureMeasurementClusterPwRpc(
    temperature_measurement_base.TemperatureMeasurementClusterBase):
  """Matter Temperature Measurement cluster capability."""

  @decorators.DynamicProperty
  def measured_value(self) -> int:
    """The MeasuredValue attribute.

    Represents the temperature in degrees Celsius as follows:
    MeasuredValue = 100 x temperature [°C]
    Where -273.15°C ≤ temperature ≤ 327.67°C, with a resolution of 0.01°C.

    Returns:
      The MeasuredValue attribute.
    """
    measured_value_data = self._read(
        endpoint_id=self._endpoint_id,
        cluster_id=_TempMeasurementCluster.ID,
        attribute_id=_TempMeasurementCluster.ATTRIBUTE_MEASURED_VALUE,
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
        cluster_id=_TempMeasurementCluster.ID,
        attribute_id=_TempMeasurementCluster.ATTRIBUTE_MIN_MEASURED_VALUE,
        attribute_type=INT16_ATTRIBUTE_TYPE)
    return _convert_attribute_constraint_value(
        min_measured_value_data.data_int16, _MIN_MEASURED_UPPERBOUND)

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
        cluster_id=_TempMeasurementCluster.ID,
        attribute_id=_TempMeasurementCluster.ATTRIBUTE_MAX_MEASURED_VALUE,
        attribute_type=INT16_ATTRIBUTE_TYPE)
    return _convert_attribute_constraint_value(
        max_measured_value_data.data_int16, _MAX_MEASURED_UPPERBOUND)
