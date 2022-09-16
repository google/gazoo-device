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
"""chip-tool implementation of the Matter Door Lock cluster capability.
"""
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters.interfaces import door_lock_base
from typing_extensions import Literal

logger = gdm_logger.get_logger()

_CLUSTER_NAME = "doorlock"


class DoorLockClusterChipTool(door_lock_base.DoorLockClusterBase):
  """chip-tool based Matter Door Lock cluster capability."""

  @decorators.CapabilityLogDecorator(logger)
  def lock_door(self, verify: bool = True) -> None:
    """The Lock Door command to lock the Matter device.

    Args:
      verify: If true, verifies the state configurations before returning.
    """
    self._lock_command("lock-door", verify)

  @decorators.CapabilityLogDecorator(logger)
  def unlock_door(self, verify: bool = True) -> None:
    """The Unlock Door command to unlock the Matter device.

    Args:
      verify: If true, verifies the state configurations before returning.
    """
    self._lock_command("unlock-door", verify)

  @decorators.DynamicProperty
  def lock_state(self) -> matter_enums.LockState:
    """The LockState attribute."""
    locked_data = self._read(self._endpoint_id, _CLUSTER_NAME, "lock-state")
    return matter_enums.LockState(int(locked_data))

  def _lock_command(
      self,
      lock_command: Literal["lock-door", "unlock-door"],
      verify: bool = True) -> None:
    """Locks or unlocks the device.

    Args:
      lock_command: "lock-door" or "unlock-door".
      verify: If true, verifies the lock configurations before returning.

    Raises:
      DeviceError: when the device does not transition to the appropriate
      lock state.
    """
    self._send(
        endpoint_id=self._endpoint_id,
        cluster=_CLUSTER_NAME,
        command=lock_command,
        arguments=[],
        flags=["--timedInteractionTimeoutMs", 1000])

    if verify:
      expected_lock_state = (
          matter_enums.LockState.LOCKED if lock_command == "lock-door" else
          matter_enums.LockState.UNLOCKED)
      if expected_lock_state != self.lock_state:  # pylint: disable=comparison-with-callable
        raise errors.DeviceError(
            f"Device {self._device_name} lock state attribute did not change "
            f"from {self.lock_state}.")
