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
import enum
from typing import Any, Callable, Mapping
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import pwrpc_light_base
from gazoo_device.protos import lighting_service_pb2
from gazoo_device.switchboard.transports import pigweed_rpc_transport

logger = gdm_logger.get_logger()


class LightingAction(enum.Enum):
  ON = True
  OFF = False


class PwRPCLightDefault(pwrpc_light_base.PwRPCLightBase):
  """Pigweed RPC lighting capability for devices communicating over PwRPC."""

  def __init__(self,
               device_name: str,
               expect_lighting_regexes: Mapping[bool, str],
               expect_timeout: int,
               switchboard_call: Callable[..., Any],
               switchboard_call_expect: Callable[..., Any]):
    """Creates an instance of the PwRPCLightDefault capability.

    Args:
      device_name: Device name used for logging.
      expect_lighting_regexes: Expected regexes for lighting on off, the
      dict format: {LightingAction.ON: "<light on regex>", LightingAction.OFF:
        "<light off regex>"}.
      expect_timeout: Timeout (s) to wait for the expected regex.
      switchboard_call: The switchboard.call method.
      switchboard_call_expect: The switchboard.call_and_expect method.
    """
    super().__init__(device_name=device_name)
    self._expect_lighting_regexes = expect_lighting_regexes
    self._expect_timeout = expect_timeout
    self._switchboard_call = switchboard_call
    self._switchboard_call_expect = switchboard_call_expect

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
    state = self._get_state()
    return state.on

  @decorators.DynamicProperty
  def brightness(self) -> int:
    """The brightness level of the device.

    The brightness level is between 0 and 255 inclusive,
    see gazoo_device/protos/lighting_service.proto for more details.

    Returns:
      The current brightness level.
    """
    state = self._get_state()
    return state.level

  @decorators.DynamicProperty
  def color(self) -> lighting_service_pb2.LightingColor:
    """The lighting color of the device.

    The lighting color consists of hue and saturation, which are between 0x00
    and 0xFE inclusive. See gazoo_device/protos/lighting_service.proto for more
    details.

    Returns:
      The current lighting color.
    """
    state = self._get_state()
    return state.color

  def _on_off(self, on: bool, no_wait: bool = False) -> None:
    """Turn on/off the light of the device.

    Args:
      on: Turns on the light if true, turn off the light otherwise.
      no_wait: If True, returns before verifying the light state.

    Raises:
      DeviceError: When the device does not transition to the appropriate
      state or if it remains the same state.
    """
    regex_type = LightingAction.ON if on else LightingAction.OFF
    expect_regex = self._expect_lighting_regexes[regex_type]

    _, (ack, _) = self._switchboard_call_expect(
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
        pattern_list=[expect_regex],
        timeout=self._expect_timeout,
        method_args=("Lighting", "Set"),
        method_kwargs={"on": on},
        raise_for_timeout=True)

    action = "on" if on else "off"
    if not ack:
      raise errors.DeviceError(
          f"Device {self._device_name} turning light {action} failed.")
    if not no_wait:
      if on != self.state:  # pylint: disable=comparison-with-callable
        raise errors.DeviceError(
            f"Device {self._device_name} light didn't turn {action}.")

  def _get_state(self) -> lighting_service_pb2.LightingState:
    """Returns the lighting state of the device.

    Returns:
      The lighting state.

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
    state = lighting_service_pb2.LightingState.FromString(state_in_bytes)
    return state
