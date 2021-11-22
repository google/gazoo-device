# Copyright 2021 Google LLC
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

"""Default implementation of the PwRPC (Pigweed RPC) locking capability."""
from typing import Any, Callable

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import pwrpc_lock_base
from gazoo_device.protos import locking_service_pb2
from gazoo_device.switchboard.transports import pigweed_rpc_transport


logger = gdm_logger.get_logger()


class PwRPCLockDefault(pwrpc_lock_base.PwRPCLockBase):
  """Pigweed RPC locking capability for devices communicating over PwRPC."""

  def __init__(self,
               device_name: str,
               switchboard_call: Callable[..., Any],
               rpc_timeout_s: int):
    """Initializes an instance of the PwRPCLockDefault capability.

    Args:
      device_name: Device name used for logging.
      switchboard_call: The switchboard.call method.
      rpc_timeout_s: Timeout (s) for RPC call.
    """
    super().__init__(device_name=device_name)
    self._switchboard_call = switchboard_call
    self._rpc_timeout_s = rpc_timeout_s

  @decorators.CapabilityLogDecorator(logger)
  def lock(self, verify: bool = True) -> None:
    """Locks the device.

    Args:
      verify: If true, verifies the lock configurations before returning.
    """
    self._lock_unlock(True, verify)

  @decorators.CapabilityLogDecorator(logger)
  def unlock(self, verify: bool = True) -> None:
    """Unlocks the device.

    Args:
      verify: If true, verifies the lock configurations before returning.
    """
    self._lock_unlock(False, verify)

  @decorators.DynamicProperty
  def state(self) -> bool:
    """The lock state of the device.

    Returns:
      True if the device is locked, false if it's unlocked.

    Raises:
      DeviceError: Ack value is false.
    """
    ack, state_in_bytes = self._switchboard_call(
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
        method_args=("Locking", "Get"),
        method_kwargs={"pw_rpc_timeout_s": self._rpc_timeout_s})

    if not ack:
      raise errors.DeviceError(
          f"Getting device {self._device_name} locked state failed: "
          "device did not acknowledge the RPC.")

    state = locking_service_pb2.LockingState.FromString(state_in_bytes)
    return state.locked

  def _lock_unlock(self, locked: bool, verify: bool = True) -> None:
    """Locks or unlocks the device.

    Args:
      locked: Locks the device if true, unlocks the device if false.
      verify: If true, verifies the lock configurations before returning.

    Raises:
      DeviceError: Ack value is false or the device does not transition to the
      appropriate state.
    """
    ack, _ = self._switchboard_call(
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
        method_args=("Locking", "Set"),
        method_kwargs={
            "locked": locked, "pw_rpc_timeout_s": self._rpc_timeout_s})

    action = "Locking" if locked else "Unlocking"
    error_mesg = f"{action} device {self._device_name} failed: "
    if not ack:
      raise errors.DeviceError(
          error_mesg + "device did not acknowledge the RPC.")

    if verify:
      if locked != self.state:  # pylint: disable=comparison-with-callable
        raise errors.DeviceError(
            error_mesg + f"device's locked state remains {self.state}.")
