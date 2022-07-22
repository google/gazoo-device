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
"""chip-tool implementation of the Matter Level Control cluster capability.
"""
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.matter_clusters.interfaces import level_control_base

logger = gdm_logger.get_logger()

_CLUSTER_NAME = "levelcontrol"

# Default data fields for MoveToLevel command based on the spec.
_DEFAULT_TRANSITION_TIME = 0
_DEFAULT_OPTION_MASK = 0
_DEFAULT_OPTION_OVERRIDE = 0


class LevelControlClusterChipTool(level_control_base.LevelControlClusterBase):
  """chip-tool based Matter Level Control cluster capability."""

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

    self._send(self._endpoint_id, _CLUSTER_NAME, "move-to-level", [
        level, _DEFAULT_TRANSITION_TIME, _DEFAULT_OPTION_MASK,
        _DEFAULT_OPTION_OVERRIDE
    ])

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
    return self._read(self._endpoint_id, _CLUSTER_NAME, "current-level")

  @decorators.DynamicProperty
  def min_level(self) -> int:
    """The MinLevel attribute.

    The MinLevel attribute indicates the minimum value of CurrentLevel that is
    capable of being assigned.

    Returns:
      The min level.
    """
    return self._read(self._endpoint_id, _CLUSTER_NAME, "min-level")

  @decorators.DynamicProperty
  def max_level(self) -> int:
    """The MaxLevel attribute.

    The MaxLevel attribute indicates the maximum value of CurrentLevel that is
    capable of being assigned.

    Returns:
      The max level.
    """
    return self._read(self._endpoint_id, _CLUSTER_NAME, "max-level")
