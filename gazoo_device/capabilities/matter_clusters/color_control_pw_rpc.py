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

"""Pigweed RPC implementation of the Matter Color Control cluster capability.
"""

from typing import Any, Callable
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.matter_clusters.interfaces import color_control_base
from gazoo_device.protos import lighting_service_pb2
from gazoo_device.switchboard.transports import pigweed_rpc_transport
from gazoo_device.utility import pwrpc_utils

_LIGHTING_COLOR_PROTO_CLASS = "gazoo_device.protos.lighting_service_pb2.LightingColor"
logger = gdm_logger.get_logger()


class ColorControlClusterPwRpc(color_control_base.ColorControlClusterBase):
  """Matter Color Control cluster capability."""

  def __init__(self,
               device_name: str,
               switchboard_call: Callable[..., Any],
               rpc_timeout_s: int):
    """Initializes an instance of the Matter Color Control cluster capability.

    Args:
      device_name: Device name used for logging.
      switchboard_call: The switchboard.call method.
      rpc_timeout_s: Timeout (s) for RPC call.
    """
    super().__init__(device_name=device_name)
    self._switchboard_call = switchboard_call
    self._rpc_timeout_s = rpc_timeout_s

  @decorators.CapabilityLogDecorator(logger)
  def move_to_hue(self, hue: int, verify: bool = True) -> None:
    """The MoveToHue command.

    On receipt of this command, a device should move from its current hue
    to the given hue value.

    Args:
      hue: The hue that the device should move to.
      verify: If true, verifies the hue changes before returning.
    """
    previous_hue = self.current_hue
    self._set_light_color(hue=hue, saturation=self.current_saturation)
    if verify:
      if self.current_hue != hue:  # pylint: disable=comparison-with-callable
        raise errors.DeviceError(
            f"Device {self._device_name} current hue didn't change to {hue} "
            f"from {previous_hue}.")

  @decorators.CapabilityLogDecorator(logger)
  def move_to_saturation(self, saturation: int, verify: bool = True) -> None:
    """The MoveToSaturation command.

    On receipt of this command, a device should move from its current saturation
    to the given saturation value.

    Args:
      saturation: The saturation that the device should move to.
      verify: If true, verifies the hue changes before returning.
    """
    previous_saturation = self.current_saturation
    self._set_light_color(hue=self.current_hue, saturation=saturation)
    if verify:
      if self.current_saturation != saturation:  # pylint: disable=comparison-with-callable
        raise errors.DeviceError(
            f"Device {self._device_name} current saturation didn't change to "
            f"{saturation} from {previous_saturation}.")

  @decorators.DynamicProperty
  def current_hue(self) -> int:
    """The CurrentHue attribute.

    The CurrentHue attribute contains the current hue value of the light.

    Returns:
      The current hue.
    """
    color = self._get_light_color()
    return color.hue

  @decorators.DynamicProperty
  def current_saturation(self) -> int:
    """The CurrentSaturation attribute.

    The CurrentSaturation attribute contains the current saturation value of
    the light.

    Returns:
      The current saturation.
    """
    color = self._get_light_color()
    return color.saturation

  def _get_light_color(self) -> lighting_service_pb2.LightingColor:
    """Returns the current lighting color.

    Returns:
      The current lighting color.
    """
    ack, state_in_bytes = self._switchboard_call(
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
        method_args=("Lighting", "Get"),
        method_kwargs={"pw_rpc_timeout_s": self._rpc_timeout_s})
    if not ack:
      raise errors.DeviceError(
          f"Device {self._device_name} getting lighting state failed.")
    state = lighting_service_pb2.LightingState.FromString(state_in_bytes)
    return state.color

  def _set_light_color(self, hue: int, saturation: int) -> None:
    """Updates the current lighting color.

    Args:
      hue: Color hue to update.
      saturation: Color saturation to update.
    """
    color = lighting_service_pb2.LightingColor(hue=hue, saturation=saturation)
    color_proto_state = pwrpc_utils.PigweedProtoState(
        color, _LIGHTING_COLOR_PROTO_CLASS)
    set_color_kwargs = {
        "color": color_proto_state, "pw_rpc_timeout_s": self._rpc_timeout_s}
    ack, _ = self._switchboard_call(
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
        method_args=("Lighting", "Set"),
        method_kwargs=set_color_kwargs)
    if not ack:
      raise errors.DeviceError(
          f"Device {self._device_name} setting lighting color failed.")
