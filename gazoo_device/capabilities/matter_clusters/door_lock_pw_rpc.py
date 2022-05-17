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

"""Pigweed RPC implementation of the Matter Door Lock cluster capability.
"""
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters.interfaces import door_lock_base
from gazoo_device.protos import attributes_service_pb2

logger = gdm_logger.get_logger()
DoorLockCluster = matter_enums.DoorLockCluster
BOOLEAN_ATTRIBUTE_TYPE = attributes_service_pb2.AttributeType.ZCL_BOOLEAN_ATTRIBUTE_TYPE


class DoorLockClusterPwRpc(door_lock_base.DoorLockClusterBase):
  """Matter Door Lock cluster capability."""

  @decorators.CapabilityLogDecorator(logger)
  def lock_door(self, verify: bool = True) -> None:
    """The Lock Door command to lock the Matter device.

    Args:
      verify: If true, verifies the state configurations before returning.
    """
    self._lock_command(lock=True, verify=verify)

  @decorators.CapabilityLogDecorator(logger)
  def unlock_door(self, verify: bool = True) -> None:
    """The Unlock Door command to unlock the Matter device.

    Args:
      verify: If true, verifies the state configurations before returning.
    """
    self._lock_command(lock=False, verify=verify)

  @decorators.DynamicProperty
  def lock_state(self) -> int:
    """The LockState attribute.

    Returns:
      The attribute value of the current locked state.
    """
    locked_data = self._read(
        endpoint_id=self._endpoint_id,
        cluster_id=DoorLockCluster.ID,
        attribute_id=DoorLockCluster.ATTRIBUTE_LOCK_STATE,
        attribute_type=BOOLEAN_ATTRIBUTE_TYPE)
    return (matter_enums.LockState.LOCKED if locked_data.data_bool
            else matter_enums.LockState.UNLOCKED)

  def _lock_command(self, lock: bool, verify: bool = True) -> None:
    """Locks or unlocks the device.

    Args:
      lock: Locks the device if true, unlocks the device if false.
      verify: If true, verifies the lock configurations before returning.

    Raises:
      DeviceError: Ack value is false or the device does not transition to the
      appropriate state.
    """
    self._write(
        endpoint_id=self._endpoint_id,
        cluster_id=DoorLockCluster.ID,
        attribute_id=DoorLockCluster.ATTRIBUTE_LOCK_STATE,
        attribute_type=BOOLEAN_ATTRIBUTE_TYPE,
        data_bool=lock)

    if verify:
      expected_state = (matter_enums.LockState.LOCKED if lock else
                        matter_enums.LockState.UNLOCKED)
      if expected_state != self.lock_state:  # pylint: disable=comparison-with-callable
        raise errors.DeviceError(
            f"Device {self._device_name} lock state attribute did not change "
            f"from {self.lock_state}.")
