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

"""Pigweed RPC implementation of the Matter Fan Control cluster capability.
"""
from typing import Union
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters.interfaces import fan_control_base
from gazoo_device.protos import attributes_service_pb2

FanControlCluster = matter_enums.FanControlCluster
ENUM8_ATTRIBUTE_TYPE = attributes_service_pb2.AttributeType.ZCL_ENUM8_ATTRIBUTE_TYPE
UINT8_ATTRIBUTE_TYPE = attributes_service_pb2.AttributeType.ZCL_INT8U_ATTRIBUTE_TYPE


class FanControlClusterPwRpc(fan_control_base.FanControlClusterBase):
  """Matter Fan Control cluster capability."""

  @decorators.DynamicProperty
  def fan_mode(self) -> matter_enums.FanMode:
    """The FanMode attribute."""
    return matter_enums.FanMode(self._read_attribute(
        attribute_id=FanControlCluster.ATTRIBUTE_FAN_MODE,
        attribute_type=ENUM8_ATTRIBUTE_TYPE))

  @fan_mode.setter
  def fan_mode(self, value: matter_enums.FanMode) -> None:
    """Sets the FanMode attribute."""
    self._write_attribute(
        attribute_id=FanControlCluster.ATTRIBUTE_FAN_MODE,
        value=value,
        attribute_type=ENUM8_ATTRIBUTE_TYPE)

  @decorators.DynamicProperty
  def fan_mode_sequence(self) -> matter_enums.FanModeSequence:
    """The FanModeSequence attribute."""
    return matter_enums.FanModeSequence(self._read_attribute(
        attribute_id=FanControlCluster.ATTRIBUTE_FAN_MODE_SEQUENCE,
        attribute_type=ENUM8_ATTRIBUTE_TYPE))

  @fan_mode_sequence.setter
  def fan_mode_sequence(self, value: matter_enums.FanModeSequence) -> None:
    """Sets the FanModeSequence attribute."""
    self._write_attribute(
        attribute_id=FanControlCluster.ATTRIBUTE_FAN_MODE_SEQUENCE,
        value=value,
        attribute_type=ENUM8_ATTRIBUTE_TYPE)

  @decorators.DynamicProperty
  def percent_setting(self) -> int:
    """The PercentSetting attribute."""
    return self._read_attribute(
        attribute_id=FanControlCluster.ATTRIBUTE_PERCENT_SETTING)

  @percent_setting.setter
  def percent_setting(self, value: int) -> None:
    """Sets the PercentSetting attribute."""
    self._write_attribute(
        attribute_id=FanControlCluster.ATTRIBUTE_FAN_MODE_SEQUENCE,
        value=value)

  @decorators.DynamicProperty
  def percent_current(self) -> int:
    """The PercentCurrent attribute."""
    return self._read_attribute(
        attribute_id=FanControlCluster.ATTRIBUTE_PERCENT_CURRENT)

  @percent_current.setter
  def percent_current(self, value: int) -> None:
    """Sets the PercentCurrent attribute."""
    self._write_attribute(
        attribute_id=FanControlCluster.ATTRIBUTE_PERCENT_CURRENT,
        value=value)

  @decorators.DynamicProperty
  def speed_max(self) -> int:
    """The SpeedMax attribute."""
    return self._read_attribute(
        attribute_id=FanControlCluster.ATTRIBUTE_SPEED_MAX)

  @speed_max.setter
  def speed_max(self, value: int) -> None:
    """Sets the SpeedMax attribute."""
    self._write_attribute(
        attribute_id=FanControlCluster.ATTRIBUTE_SPEED_MAX,
        value=value)

  @decorators.DynamicProperty
  def speed_setting(self) -> int:
    """The SpeedSetting attribute."""
    return self._read_attribute(
        attribute_id=FanControlCluster.ATTRIBUTE_SPEED_SETTING)

  @speed_setting.setter
  def speed_setting(self, value: int) -> None:
    """Sets the SpeedSetting attribute."""
    self._write_attribute(
        attribute_id=FanControlCluster.ATTRIBUTE_SPEED_SETTING,
        value=value)

  @decorators.DynamicProperty
  def speed_current(self) -> int:
    """The SpeedCurrent attribute."""
    return self._read_attribute(
        attribute_id=FanControlCluster.ATTRIBUTE_SPEED_CURRENT)

  @speed_current.setter
  def speed_current(self, value: int) -> None:
    """Sets the SpeedCurrent attribute."""
    self._write_attribute(
        attribute_id=FanControlCluster.ATTRIBUTE_SPEED_CURRENT,
        value=value)

  def _read_attribute(
      self, attribute_id: int, attribute_type: int = UINT8_ATTRIBUTE_TYPE
      ) -> int:
    """Reads the value from the attribute ID on the Fan Control cluster."""
    data = self._read(
        endpoint_id=self._endpoint_id,
        cluster_id=FanControlCluster.ID,
        attribute_id=attribute_id,
        attribute_type=attribute_type)
    return data.data_uint8

  def _write_attribute(
      self,
      attribute_id: int,
      value: Union[int, matter_enums.FanMode, matter_enums.FanModeSequence],
      attribute_type: int = UINT8_ATTRIBUTE_TYPE):
    """Writes the value to the attribute ID on the Fan Control cluster."""
    self._write(endpoint_id=self._endpoint_id,
                cluster_id=FanControlCluster.ID,
                attribute_id=attribute_id,
                attribute_type=attribute_type,
                data_uint8=value)
    if self._read_attribute(attribute_id, attribute_type) != value:
      raise errors.DeviceError(
          f"Device {self._device_name} attribute {attribute_id} didn't change "
          f"to {value}.")
