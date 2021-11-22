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
from typing import Any, Callable, Optional
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import pwrpc_light_base
from gazoo_device.protos import lighting_service_pb2
from gazoo_device.switchboard.transports import pigweed_rpc_transport
from gazoo_device.utility import pwrpc_utils

_LIGHTING_COLOR_PROTO_CLASS = "gazoo_device.protos.lighting_service_pb2.LightingColor"
logger = gdm_logger.get_logger()


class PwRPCLightDefault(pwrpc_light_base.PwRPCLightBase):
  """Pigweed RPC lighting capability for devices communicating over PwRPC."""

  def __init__(self,
               device_name: str,
               switchboard_call: Callable[..., Any],
               rpc_timeout_s: int):
    """Creates an instance of the PwRPCLightDefault capability.

    Args:
      device_name: Device name used for logging.
      switchboard_call: The switchboard.call method.
      rpc_timeout_s: Timeout (s) for RPC call.
    """
    super().__init__(device_name=device_name)
    self._switchboard_call = switchboard_call
    self._rpc_timeout_s = rpc_timeout_s

  @decorators.CapabilityLogDecorator(logger)
  def on(self, level: int = pwrpc_light_base.MAX_BRIGHTNESS_LEVEL,
         hue: int = 0, saturation: int = 0, verify: bool = True) -> None:
    """Turns on the light and sets the brigthtness level, color of the device.

    Args:
      level: Brightness level to be set.
      hue: Hue of lighting color to be set.
      saturation: Saturation of lighting color to be set.
      verify: If true, verifies the light configurations before returning.
    """
    color = lighting_service_pb2.LightingColor(hue=hue, saturation=saturation)
    self._on_off(on=True, level=level, color=color, verify=verify)

  @decorators.CapabilityLogDecorator(logger)
  def off(self, verify: bool = True) -> None:
    """Turns off the light of the device.

    Args:
      verify: If true, verifies the light configurations before returning.

    Raises:
      DeviceError: When the device does not transition to the appropriate
      state or if it remains on.
    """
    self._on_off(on=False, verify=verify)

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

  def _on_off(
      self,
      on: bool,
      level: Optional[int] = None,
      color: Optional[lighting_service_pb2.LightingColor] = None,
      verify: bool = True) -> None:
    """Turn on/off the light of the device.

    Args:
      on: Turns on the light if true, turn off the light otherwise.
      level: Brightness level to be set, unused if on = False.
      color: Lighting color to be set, unused if on = False.
      verify: If true, verifies the light configurations before returning.

    Raises:
      DeviceError: When the device does not transition to the appropriate
      lighting configuration.
    """
    set_onoff_kwargs = {"on": on, "pw_rpc_timeout_s": self._rpc_timeout_s}
    if on:
      color_proto_state = pwrpc_utils.PigweedProtoState(
          color, _LIGHTING_COLOR_PROTO_CLASS)
      set_onoff_kwargs.update({"level": level, "color": color_proto_state})

    ack, _ = self._switchboard_call(
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
        method_args=("Lighting", "Set"),
        method_kwargs=set_onoff_kwargs)

    action = "on" if on else "off"
    if not ack:
      raise errors.DeviceError(
          f"Device {self._device_name} turning light {action} failed.")

    if verify:
      if on != self.state:  # pylint: disable=comparison-with-callable
        raise errors.DeviceError(
            f"Device {self._device_name} light didn't turn {action}.")
      if on:
        if level != self.brightness:  # pylint: disable=comparison-with-callable
          raise errors.DeviceError(
              f"Device {self._device_name} brightness level didn't change "
              f"to {level}.")
        if color != self.color:  # pylint: disable=comparison-with-callable
          raise errors.DeviceError(
              f"Device {self._device_name} lighting color didn't change "
              f"to {color}.")

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
        method_kwargs={"pw_rpc_timeout_s": self._rpc_timeout_s})
    if not ack:
      raise errors.DeviceError(
          f"Device {self._device_name} getting light state failed.")
    state = lighting_service_pb2.LightingState.FromString(state_in_bytes)
    return state
