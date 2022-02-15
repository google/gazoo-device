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

"""Pigweed RPC implementation of the Matter On/Off cluster capability."""
from typing import Any, Callable
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.matter_clusters.interfaces import on_off_base
from gazoo_device.protos import lighting_service_pb2
from gazoo_device.switchboard.transports import pigweed_rpc_transport

logger = gdm_logger.get_logger()


class OnOffClusterPwRpc(on_off_base.OnOffClusterBase):
  """Matter On/Off cluster capability."""

  def __init__(self,
               device_name: str,
               switchboard_call: Callable[..., Any],
               rpc_timeout_s: int):
    """Initializes an instance of the Matter On/Off cluster capability.

    Args:
      device_name: Device name used for logging.
      switchboard_call: The switchboard.call method.
      rpc_timeout_s: Timeout (s) for RPC call.
    """
    super().__init__(device_name=device_name)
    self._switchboard_call = switchboard_call
    self._rpc_timeout_s = rpc_timeout_s

  @decorators.CapabilityLogDecorator(logger)
  def on(self, verify: bool = True) -> None:
    """The On command to turn on the Matter device.

    Args:
      verify: If true, verifies the state change before returning.
    """
    self._onoff_command(on=True, verify=verify)

  @decorators.CapabilityLogDecorator(logger)
  def off(self, verify: bool = True) -> None:
    """The Off command to turn off the Matter device.

    Args:
      verify: If true, verifies the state change before returning.
    """
    self._onoff_command(on=False, verify=verify)

  @decorators.CapabilityLogDecorator(logger)
  def toggle(self, verify: bool = True) -> None:
    """The Toggle command to toggle the OnOff state of the Matter device.

    On receipt of this command, if a device is in its "Off" state it should
    enter its "On" state. Otherwise, if it is in its "On" state it should
    enter its "Off" state.

    Args:
      verify: If true, verifies the state change before returning.
    """
    self._onoff_command(on=not self.onoff, verify=verify)

  @decorators.DynamicProperty
  def onoff(self) -> bool:
    """The OnOff attribute.

    The OnOff attribute indicates the state of the device and has the following
    values: FALSE = "Off" state, TRUE = "On" state.

    Returns:
      True if the device is in on state, false if it's in off state.

    Raises:
      DeviceError: when the ack value is false.
    """
    # TODO(b/206894490) Use Ember API for the state attribute.
    ack, state_in_bytes = self._switchboard_call(
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
        method_args=("Lighting", "Get"),
        method_kwargs={"pw_rpc_timeout_s": self._rpc_timeout_s})
    if not ack:
      raise errors.DeviceError(
          f"Device {self._device_name} getting OnOff state failed.")
    state = lighting_service_pb2.LightingState.FromString(state_in_bytes)
    return state.on

  def _onoff_command(self, on: bool, verify: bool = True) -> None:
    """Turn on/off the device.

    Args:
      on: Turns on the device if true, turn off the device otherwise.
      verify: If true, verifies the device configurations before returning.

    Raises:
      DeviceError: when the ack value if false or the device does not transition
      to the appropriate OnOff state.
    """
    # TODO(b/206894490) Use Ember API for the On/Off commands.
    set_onoff_kwargs = {"on": on, "pw_rpc_timeout_s": self._rpc_timeout_s}

    ack, _ = self._switchboard_call(
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
        method_args=("Lighting", "Set"),
        method_kwargs=set_onoff_kwargs)

    action = "on" if on else "off"
    if not ack:
      raise errors.DeviceError(
          f"Device {self._device_name} turning {action} failed.")

    if verify:
      if on != self.onoff:  # pylint: disable=comparison-with-callable
        raise errors.DeviceError(
            f"Device {self._device_name} didn't turn {action}.")
