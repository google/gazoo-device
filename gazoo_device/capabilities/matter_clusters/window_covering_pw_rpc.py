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
# TODO(b/241698162): switch to percent when TLV is supported.
PERCENT_ATTRIBUTE_TYPE = attributes_service_pb2.AttributeType.ZCL_INT8U_ATTRIBUTE_TYPE


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
