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

"""Pigweed RPC implementation of the Matter Door Lock cluster capability."""
import enum
from typing import Any, Callable
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.matter_clusters.interfaces import door_lock_base
from gazoo_device.protos import locking_service_pb2
from gazoo_device.switchboard.transports import pigweed_rpc_transport

logger = gdm_logger.get_logger()


class LockState(enum.Enum):
  """Lock state attribute values.
  """
  NOT_FULLY_LOCKED = 0
  LOCKED = 1
  UNLOCKED = 2


class DoorLockClusterPwRpc(door_lock_base.DoorLockClusterBase):
  """Matter Door Lock cluster capability."""

  def __init__(self,
               device_name: str,
               switchboard_call: Callable[..., Any],
               rpc_timeout_s: int):
    """Initializes an instance of the Matter Door Lock cluster capability.

    Args:
      device_name: Device name used for logging.
      switchboard_call: The switchboard.call method.
      rpc_timeout_s: Timeout (s) for RPC call.
    """
    super().__init__(device_name=device_name)
    self._switchboard_call = switchboard_call
    self._rpc_timeout_s = rpc_timeout_s

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
    ack, state_in_bytes = self._switchboard_call(
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
        method_args=("Locking", "Get"),
        method_kwargs={"pw_rpc_timeout_s": self._rpc_timeout_s})
    if not ack:
      raise errors.DeviceError(
          f"Device {self._device_name} getting LockState attribute failed.")
    state = locking_service_pb2.LockingState.FromString(state_in_bytes)
    if state.locked:
      return LockState.LOCKED.value
    else:
      return LockState.UNLOCKED.value

  def _lock_command(self, lock: bool, verify: bool = True) -> None:
    """Locks or unlocks the device.

    Args:
      lock: Locks the device if true, unlocks the device if false.
      verify: If true, verifies the lock configurations before returning.

    Raises:
      DeviceError: Ack value is false or the device does not transition to the
      appropriate state.
    """
    lock_unlock_kwargs = {
        "locked": lock, "pw_rpc_timeout_s": self._rpc_timeout_s}

    ack, _ = self._switchboard_call(
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
        method_args=("Locking", "Set"),
        method_kwargs=lock_unlock_kwargs)

    action = "Locking" if lock else "Unlocking"
    expected_state = (LockState.LOCKED.value if lock else
                      LockState.UNLOCKED.value)

    if not ack:
      raise errors.DeviceError(
          f"{action} device {self._device_name} failed.")

    if verify:
      if expected_state != self.lock_state:  # pylint: disable=comparison-with-callable
        raise errors.DeviceError(
            f"Device {self._device_name} lock state attribute did not change "
            f"from {self.lock_state}.")
