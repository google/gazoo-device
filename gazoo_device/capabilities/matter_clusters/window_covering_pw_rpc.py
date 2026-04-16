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

"""RPC implementation of Matter Window Covering cluster capability.
"""

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters.interfaces import window_covering_base
from gazoo_device.protos import attributes_service_pb2


logger = gdm_logger.get_logger()
_WINDOW_COVERING_CLUSTER = matter_enums.WindowCoveringCluster
# TODO(gdm-authors): switch to percent when TLV is supported.
PERCENT_ATTRIBUTE_TYPE = (
    attributes_service_pb2.AttributeType.ZCL_INT8U_ATTRIBUTE_TYPE
)
ATTRIBUTE_TYPE = (
    attributes_service_pb2.AttributeType.ZCL_INT8U_ATTRIBUTE_TYPE
)


class WindowCoveringClusterPwRpc(window_covering_base.WindowCoveringClusterBase
                                ):
  """Matter Matter Window Covering cluster capability."""

  @decorators.DynamicProperty
  def current_position_lift_percentage(self) -> int:
    """The CurrentPositionLiftPercentage attribute.

    The CurrentPositionLiftPercentage attribute identifies the actual position
    as a percentage from 0% to 100% with 1% default step. This attribute is
    equal to CurrentPositionLiftPercent100ths attribute divided by 100.

    Returns:
      The CurrentPositionLiftPercentage attribute.
    """
    return self._read_percent_attribute(
        attribute_id=_WINDOW_COVERING_CLUSTER
        .ATTRIBUTE_CURRENT_POSITION_LIFT_PERCENTAGE)

  @current_position_lift_percentage.setter
  def current_position_lift_percentage(self, percent: int) -> None:
    """Updates the CurrentPositionLiftPercentage attribute.

    The CurrentPositionLiftPercentage attribute identifies the actual position
    as a percentage from 0% to 100% with 1% default step. This attribute is
    equal to CurrentPositionLiftPercent100ths attribute divided by 100.

    Args:
      percent: The value CurrentPositionLiftPercentage should update to.
    """
    self._write_percent_attribute(attribute_id=_WINDOW_COVERING_CLUSTER
                                  .ATTRIBUTE_CURRENT_POSITION_LIFT_PERCENTAGE,
                                  percent=percent)

    if self.current_position_lift_percentage != percent:  # pylint: disable=comparison-with-callable
      raise errors.DeviceError(
          f"Device {self._device_name} current_position_lift_percentage didn't "
          f"change to {percent}.")

  @decorators.DynamicProperty
  def target_position_lift(self) -> int:
    """The TargetPositionLift attribute.

    The TargetPositionLift attribute identifies the target position
    as a value from 0 to 10000. This attribute is
    equal to TargetPositionLiftPercent100ths attribute divided by 100.

    Returns:
      The TargetPositionLift attribute.
    """
    return self._read_attribute(
        attribute_id=_WINDOW_COVERING_CLUSTER
        .ATTRIBUTE_TARGET_POSITION_LIFT)

  @target_position_lift.setter
  def target_position_lift(self, lift: int) -> None:
    """Updates the TargetPositionLift attribute.

    The TargetPositionLift attribute identifies the target position
    as a value from 0 to 10000. This attribute is
    equal to TargetPositionLiftPercent100ths attribute divided by 100.

    Args:
      lift: The value TargetPositionLift should update to.
    """
    self._write_attribute(
        attribute_id=_WINDOW_COVERING_CLUSTER.ATTRIBUTE_TARGET_POSITION_LIFT,
        attribute_name=lift,
    )

    if self.target_position_lift != lift:  # pylint: disable=comparison-with-callable
      raise errors.DeviceError(
          f"Device {self._device_name} target_position_lift didn't "
          f"change to {lift}.")

  @decorators.DynamicProperty
  def current_position_tilt_percentage(self) -> int:
    """The CurrentPositionTiltPercentage attribute.

    The CurrentPositionTiltPercentage attribute identifies the actual position
    as a percentage from 0% to 100% with 1% default step. This attribute is
    equal to CurrentPositionTiltPercent100ths attribute divided by 100.

    Returns:
      The CurrentPositionTiltPercentage attribute.
    """
    return self._read_percent_attribute(
        attribute_id=_WINDOW_COVERING_CLUSTER
        .ATTRIBUTE_CURRENT_POSITION_TILT_PERCENTAGE)

  @current_position_tilt_percentage.setter
  def current_position_tilt_percentage(self, percent: int) -> None:
    """Updates the CurrentPositionTiltPercentage attribute.

    The CurrentPositionTiltPercentage attribute identifies the actual position
    as a percentage from 0% to 100% with 1% default step. This attribute is
    equal to CurrentPositionTiltPercent100ths attribute divided by 100.

    Args:
      percent: The value CurrentPositionTiltPercentage should update to.
    """
    self._write_percent_attribute(attribute_id=_WINDOW_COVERING_CLUSTER
                                  .ATTRIBUTE_CURRENT_POSITION_TILT_PERCENTAGE,
                                  percent=percent)

    if self.current_position_tilt_percentage != percent:  # pylint: disable=comparison-with-callable
      raise errors.DeviceError(
          f"Device {self._device_name} current_position_tilt_percentage didn't "
          f"change to {percent}.")

  @decorators.DynamicProperty
  def target_position_tilt(self) -> int:
    """The TargetPositionTilt attribute.

    The TargetPositionTilt attribute identifies the target position
    as a value from 0 to 10000. This attribute is
    equal to TargetPositionTiltPercent100ths attribute divided by 100.

    Returns:
      The TargetPositionTilt attribute.
    """
    return self._read_attribute(
        attribute_id=_WINDOW_COVERING_CLUSTER
        .ATTRIBUTE_TARGET_POSITION_TILT)

  @target_position_tilt.setter
  def target_position_tilt(self, tilt: int) -> None:
    """Updates the TargetPositionTilt attribute.

    The TargetPositionTilt attribute identifies the target position
    as a value from 0 to 10000. This attribute is
    equal to TargetPositionTiltPercent100ths attribute divided by 100.

    Args:
      tilt: The value TargetPositionTiltPercentage should update to.
    """
    self._write_attribute(
        attribute_id=_WINDOW_COVERING_CLUSTER.ATTRIBUTE_TARGET_POSITION_TILT,
        attribute_name=tilt,
    )

    if self.target_position_tilt != tilt:  # pylint: disable=comparison-with-callable
      raise errors.DeviceError(
          f"Device {self._device_name} target_position_tilt didn't "
          f"change to {tilt}.")

  def _read_percent_attribute(self, attribute_id: int) -> int:
    """Helper method to read percent attribute type."""
    measured_value_data = self._read(
        endpoint_id=self._endpoint_id,
        cluster_id=_WINDOW_COVERING_CLUSTER.ID,
        attribute_id=attribute_id,
        attribute_type=PERCENT_ATTRIBUTE_TYPE)
    return measured_value_data.data_uint8

  def _write_percent_attribute(self, attribute_id: int, percent: int) -> None:
    """Helper method to write percent attribute type."""
    self._write(
        endpoint_id=self._endpoint_id,
        cluster_id=_WINDOW_COVERING_CLUSTER.ID,
        attribute_id=attribute_id,
        attribute_type=PERCENT_ATTRIBUTE_TYPE,
        data_uint8=percent)

  def _read_attribute(self, attribute_id: int) -> int:
    """Helper method to read attribute type."""
    measured_value_data = self._read(
        endpoint_id=self._endpoint_id,
        cluster_id=_WINDOW_COVERING_CLUSTER.ID,
        attribute_id=attribute_id,
        attribute_type=ATTRIBUTE_TYPE)
    return measured_value_data.data_uint8

  def _write_attribute(self, attribute_id: int, attribute_name: int) -> None:
    """Helper method to write attribute type."""
    self._write(
        endpoint_id=self._endpoint_id,
        cluster_id=_WINDOW_COVERING_CLUSTER.ID,
        attribute_id=attribute_id,
        attribute_type=ATTRIBUTE_TYPE,
        data_uint8=attribute_name)
