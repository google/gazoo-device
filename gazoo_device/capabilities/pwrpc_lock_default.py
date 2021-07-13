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
import enum
from typing import Any, Callable, Dict

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import pwrpc_lock_base
from gazoo_device.protos import locking_service_pb2
from gazoo_device.switchboard.transports import pigweed_rpc_transport


logger = gdm_logger.get_logger()


class LockedState(enum.Enum):
  LOCKED = True
  UNLOCKED = False


class PwRPCLockDefault(pwrpc_lock_base.PwRPCLockBase):
  """Pigweed RPC locking capability for devices communicating over PwRPC."""

  def __init__(self,
               device_name: str,
               expect_locking_regexes: Dict[bool, str],
               expect_timeout: int,
               switchboard_call: Callable[..., Any],
               switchboard_call_expect: Callable[..., Any]):
    """Initializes an instance of the PwRPCLockDefault capability.

    Args:
      device_name: Device name used for logging.
      expect_locking_regexes: Expected regexes for locking and unlocking, the
      dict format: {LockedState.LOCKED: "<locked regex>", LockedState.UNLOCKED:
        "<unlocked regex>"}.
      expect_timeout: Timeout (s) to wait for the expected regex.
      switchboard_call: The switchboard.call method.
      switchboard_call_expect: The switchboard.call_and_expect method.
    """
    super().__init__(device_name=device_name)
    self._expect_locking_regexes = expect_locking_regexes
    self._expect_timeout = expect_timeout
    self._switchboard_call = switchboard_call
    self._switchboard_call_expect = switchboard_call_expect

  @decorators.CapabilityLogDecorator(logger)
  def lock(self, no_wait: bool = False) -> None:
    """Locks the device.

    Args:
      no_wait: Returns before verifying the locked state if true.
    """
    self._lock_unlock(True, no_wait)

  @decorators.CapabilityLogDecorator(logger)
  def unlock(self, no_wait: bool = False) -> None:
    """Unlocks the device.

    Args:
      no_wait: Returns before verifying the locked state if true.
    """
    self._lock_unlock(False, no_wait)

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
        method_kwargs={})

    if not ack:
      raise errors.DeviceError(
          f"Getting device {self._device_name} locked state failed: "
          "device did not acknowledge the RPC.")

    state = locking_service_pb2.LockingState.FromString(state_in_bytes)
    return state.locked

  def _lock_unlock(self, locked: bool, no_wait: bool = False) -> None:
    """Locks or unlocks the device.

    Args:
      locked: Locks the device if true, unlocks the device if false.
      no_wait: Returns before verifying the locked state if true.

    Raises:
      DeviceError: Ack value is false or the device does not transition to the
      appropriate state.
    """
    regex_type = LockedState.LOCKED if locked else LockedState.UNLOCKED
    expect_regex = self._expect_locking_regexes[regex_type]

    _, (ack, _) = self._switchboard_call_expect(
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
        pattern_list=[expect_regex],
        timeout=self._expect_timeout,
        method_args=("Locking", "Set"),
        method_kwargs={"locked": locked},
        raise_for_timeout=True)

    action = "Locking" if locked else "Unlocking"
    error_mesg = f"{action} device {self._device_name} failed: "
    if not ack:
      raise errors.DeviceError(
          error_mesg + "device did not acknowledge the RPC.")
    if not no_wait:
      if locked != self.state:  # pylint: disable=comparison-with-callable
        raise errors.DeviceError(
            error_mesg + f"device's locked state remains {self.state}.")
