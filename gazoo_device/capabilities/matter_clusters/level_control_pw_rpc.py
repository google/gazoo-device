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

"""Pigweed RPC implementation of the Matter Level Control cluster capability."""
from typing import Any, Callable
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.matter_clusters.interfaces import level_control_base
from gazoo_device.protos import lighting_service_pb2
from gazoo_device.switchboard.transports import pigweed_rpc_transport

logger = gdm_logger.get_logger()


class LevelControlClusterPwRpc(level_control_base.LevelControlClusterBase):
  """Matter Level Control cluster capability."""

  def __init__(self,
               device_name: str,
               switchboard_call: Callable[..., Any],
               rpc_timeout_s: int):
    """Initializes an instance of the Matter Level Control cluster capability.

    Args:
      device_name: Device name used for logging.
      switchboard_call: The switchboard.call method.
      rpc_timeout_s: Timeout (s) for RPC call.
    """
    super().__init__(device_name=device_name)
    self._switchboard_call = switchboard_call
    self._rpc_timeout_s = rpc_timeout_s

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
    # TODO(b/206894490) Use Ember API instead of the Lighting endpoint.
    previous_level = self.current_level
    set_level_kwargs = {"level": level, "pw_rpc_timeout_s": self._rpc_timeout_s}
    ack, _ = self._switchboard_call(
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
        method_args=("Lighting", "Set"),
        method_kwargs=set_level_kwargs)
    if not ack:
      raise errors.DeviceError(
          f"Device {self._device_name} moving current level to {level} failed.")
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
    # TODO(b/206894490) Use Ember API instead of the Lighting endpoint.
    ack, state_in_bytes = self._switchboard_call(
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
        method_args=("Lighting", "Get"),
        method_kwargs={"pw_rpc_timeout_s": self._rpc_timeout_s})
    if not ack:
      raise errors.DeviceError(
          f"Device {self._device_name} getting CurrentLevel attribute failed.")
    state = lighting_service_pb2.LightingState.FromString(state_in_bytes)
    return state.level
