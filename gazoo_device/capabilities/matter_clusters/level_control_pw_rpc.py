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

"""Pigweed RPC implementation of the Matter Level Control cluster capability.
"""
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters.interfaces import level_control_base
from gazoo_device.protos import attributes_service_pb2

logger = gdm_logger.get_logger()
LevelControlCluster = matter_enums.LevelControlCluster
INT8U_ATTRIBUTE_TYPE = attributes_service_pb2.AttributeType.ZCL_INT8U_ATTRIBUTE_TYPE


class LevelControlClusterPwRpc(level_control_base.LevelControlClusterBase):
  """Matter Level Control cluster capability."""

  @decorators.CapabilityLogDecorator(logger)
  def move_to_level(self, level: int, verify: bool = True) -> None:
    """The MoveToLevel command.

    On receipt of this command, a device should move from its current level
    to the value given in the Level field.
    The meaning of "level" is device dependent. (For a light it may mean
    brightness level)

    Args:
      level: The level that the device should move to.
      verify: If true, verifies the level changes before returning.
    """
    previous_level = self.current_level

    self._write(
        endpoint_id=self._endpoint_id,
        cluster_id=LevelControlCluster.ID,
        attribute_id=LevelControlCluster.ATTRIBUTE_CURRENT_LEVEL,
        attribute_type=INT8U_ATTRIBUTE_TYPE,
        data_uint8=level)

    if verify:
      if self.current_level != level:  # pylint: disable=comparison-with-callable
        raise errors.DeviceError(
            f"Device {self._device_name} current level didn't change to "
            f"{level} from {previous_level}.")

  @decorators.DynamicProperty
  def current_level(self) -> int:
    """The CurrentLevel attribute.

    The CurrentLevel attribute represents the current level of this device.
    The meaning of "level" is device dependent.

    Returns:
      The current level.
    """
    level_data = self._read(
        endpoint_id=self._endpoint_id,
        cluster_id=LevelControlCluster.ID,
        attribute_id=LevelControlCluster.ATTRIBUTE_CURRENT_LEVEL,
        attribute_type=INT8U_ATTRIBUTE_TYPE)
    return level_data.data_uint8
