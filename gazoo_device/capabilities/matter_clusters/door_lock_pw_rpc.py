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
UNSIGNED_ATTRIBUTE_TYPE = attributes_service_pb2.AttributeType.ZCL_INT16U_ATTRIBUTE_TYPE
BOOLEAN_ATTRIBUTE_TYPE = (
    attributes_service_pb2.AttributeType.ZCL_BOOLEAN_ATTRIBUTE_TYPE
)


class DoorLockClusterPwRpc(door_lock_base.DoorLockClusterBase):
  """Matter Door Lock cluster capability."""

  @decorators.CapabilityLogDecorator(logger)
  def set_require_pin_for_remote_operation_attribute(
      self,
      require_pin_for_remote_operation: bool,
      verify: bool = True,
  ) -> None:
    """Sets the Require PIN for Remote Operation attribute."""
    self._write(
        endpoint_id=self._endpoint_id,
        cluster_id=DoorLockCluster.ID,
        attribute_id=DoorLockCluster.ATTRIBUTE_REQUIRE_PIN_FOR_REMOTE_OPERATION,
        attribute_type=BOOLEAN_ATTRIBUTE_TYPE,
        data_bool=require_pin_for_remote_operation,
    )
    if verify:
      require_pin_attribute = self._read(
          endpoint_id=self._endpoint_id,
          cluster_id=DoorLockCluster.ID,
          attribute_id=DoorLockCluster.ATTRIBUTE_REQUIRE_PIN_FOR_REMOTE_OPERATION,
          attribute_type=BOOLEAN_ATTRIBUTE_TYPE,
      )
      if (
          bool(require_pin_attribute.data_bool)
          != require_pin_for_remote_operation
      ):
        raise errors.DeviceError(
            f"Device {self._device_name} require PIN for remote operation "
            "attribute did not change from "
            f"{require_pin_attribute.data_bool}."
        )

  @decorators.CapabilityLogDecorator(logger)
  def set_auto_relock_time_attribute(
      self,
      auto_relock_time: int,
      verify: bool = True,
  ) -> None:
    """Sets the Auto Relock Time attribute."""
    self._write(
        endpoint_id=self._endpoint_id,
        cluster_id=DoorLockCluster.ID,
        attribute_id=DoorLockCluster.ATTRIBUTE_AUTO_RELOCK_TIME,
        attribute_type=UNSIGNED_ATTRIBUTE_TYPE,
        data_uint16=auto_relock_time,
    )
    if verify:
      auto_relock_time_attribute = self._read(
          endpoint_id=self._endpoint_id,
          cluster_id=DoorLockCluster.ID,
          attribute_id=DoorLockCluster.ATTRIBUTE_AUTO_RELOCK_TIME,
          attribute_type=UNSIGNED_ATTRIBUTE_TYPE,
      )
      if auto_relock_time_attribute.data_uint16 != auto_relock_time:
        raise errors.DeviceError(
            f"Device {self._device_name} auto relock time attribute did not "
            f"change from {auto_relock_time_attribute.data_uint16}."
        )

  @decorators.CapabilityLogDecorator(logger)
  def lock_door(self, verify: bool = True) -> None:
    """The Lock Door command to lock the Matter device.

    Args:
      verify: If true, verifies the state configurations before returning.
    """
    self._lock_command(command=matter_enums.LockState.LOCKED, verify=verify)

  @decorators.CapabilityLogDecorator(logger)
  def unlock_door(self, verify: bool = True) -> None:
    """The Unlock Door command to unlock the Matter device.

    Args:
      verify: If true, verifies the state configurations before returning.
    """
    self._lock_command(command=matter_enums.LockState.UNLOCKED, verify=verify)

  @decorators.DynamicProperty
  def lock_state(self) -> matter_enums.LockState:
    """The LockState attribute.

    Returns:
      The attribute value of the current locked state.
    """
    locked_data = self._read(
        endpoint_id=self._endpoint_id,
        cluster_id=DoorLockCluster.ID,
        attribute_id=DoorLockCluster.ATTRIBUTE_LOCK_STATE,
        attribute_type=UNSIGNED_ATTRIBUTE_TYPE)
    return matter_enums.LockState(locked_data.data_uint16)

  @lock_state.setter
  def lock_state(self, value: int) -> None:
    """Updates the LockState attribute with new value."""
    self._lock_command(command=value)

  def _lock_command(
      self, command: matter_enums.LockState, verify: bool = True) -> None:
    """Locks or unlocks the device.

    Args:
      command: Locks or unlocks the device.
      verify: If true, verifies the lock configurations before returning.

    Raises:
      DeviceError: Ack value is false or the device does not transition to the
      appropriate state.
    """
    self._write(
        endpoint_id=self._endpoint_id,
        cluster_id=DoorLockCluster.ID,
        attribute_id=DoorLockCluster.ATTRIBUTE_LOCK_STATE,
        attribute_type=UNSIGNED_ATTRIBUTE_TYPE,
        data_uint16=command)

    if verify:
      if command != self.lock_state:  # pylint: disable=comparison-with-callable
        raise errors.DeviceError(
            f"Device {self._device_name} lock state attribute did not change "
            f"from {self.lock_state}.")
