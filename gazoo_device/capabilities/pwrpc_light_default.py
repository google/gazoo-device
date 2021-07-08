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

"""Default implementation of the PwRPC (Pigweed RPC) lighting capability."""
from typing import Any, Callable, Tuple
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import pwrpc_light_base
from gazoo_device.switchboard.transports import pigweed_rpc_transport
try:
  # pylint: disable=g-import-not-at-top
  # pytype: disable=import-error
  from lighting_service import lighting_service_pb2
  # pytype: enable=import-error
except ImportError:
  lighting_service_pb2 = None

logger = gdm_logger.get_logger()


class PwRPCLightDefault(pwrpc_light_base.PwRPCLightBase):
  """Pigweed RPC lighting capability for devices communicating over PwRPC."""

  def __init__(self,
               device_name: str,
               switchboard_call: Callable[..., Any]):
    """Create an instance of the PwRPCLightDefault capability.

    Args:
      device_name: Device name used for logging.
      switchboard_call: The Switchboard.call method which calls to the endpoint.
        See more examples in nrf_pigweed_lighting.py.
    """
    super().__init__(device_name=device_name)
    self._switchboard_call = switchboard_call

  @decorators.CapabilityLogDecorator(logger)
  def on(self, no_wait: bool = False) -> None:
    """Turns on the light state of the device.

    Args:
      no_wait: If True, returns before verifying the light state.

    Raises:
      DeviceError: When the device does not transition to the appropriate
      state or if it remains off.
    """
    self._on_off(True, no_wait)

  @decorators.CapabilityLogDecorator(logger)
  def off(self, no_wait: bool = False) -> None:
    """Turns off the light state of the device.

    Args:
      no_wait: If True, returns before verifying the light state.

    Raises:
      DeviceError: When the device does not transition to the appropriate
      state or if it remains on.
    """
    self._on_off(False, no_wait)

  @decorators.DynamicProperty
  def state(self) -> bool:
    """The light state of the device.

    Returns:
      True if the device is in on state, false if it's in off state.

    Raises:
      DeviceError: When the device does not transition to the appropriate
      state or if it remains off.
    """
    state_in_bytes = self._get_state()
    state = lighting_service_pb2.LightingState.FromString(state_in_bytes)
    return state.on

  @decorators.DynamicProperty
  def brightness(self) -> Tuple[int, int]:
    """The brightness level of the device.

    Returns:
      Current brightness level and the maximal brightness level.
    """
    state_in_bytes = self._get_state()
    brightness = lighting_service_pb2.LightingBrightness.FromString(
        state_in_bytes)
    return brightness.level, brightness.max_level

  def _on_off(self, on: bool, no_wait: bool = False) -> None:
    """Turn on/off the light of the device.

    Args:
      on: Turns on the light if true, turn off the light otherwise.
      no_wait: If True, returns before verifying the light state.

    Raises:
      DeviceError: When the device does not transition to the appropriate
      state or if it remains the same state.
    """
    lighting_ack, _ = self._switchboard_call(
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
        method_args=("Lighting", "Set"),
        method_kwargs={"on": on})
    action = "on" if on else "off"
    if not lighting_ack:
      raise errors.DeviceError(
          f"Device {self._device_name} turning light {action} failed.")
    if not no_wait:
      if on != self.state:  # pylint: disable=comparison-with-callable
        raise errors.DeviceError(
            f"Device {self._device_name} light didn't turn {action}.")

  def _get_state(self) -> bytes:
    """Returns the serialized lighting state of the device.

    Returns:
      The serialized lighting state.

    Raises:
      DeviceError: When the ack value is not true.
    """
    ack, state_in_bytes = self._switchboard_call(
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
        method_args=("Lighting", "Get"),
        method_kwargs={})
    if not ack:
      raise errors.DeviceError(
          f"Device {self._device_name} getting light state failed.")
    return state_in_bytes
