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

"""Interface for an PwRPC (Pigweed RPC) lighting capability."""
import abc
from gazoo_device.capabilities.interfaces import capability_base
from gazoo_device.protos import lighting_service_pb2


MAX_BRIGHTNESS_LEVEL = 255


class PwRPCLightBase(capability_base.CapabilityBase):
  """Pigweed RPC lighting capability for devices communicating over PwRPC."""

  @abc.abstractmethod
  def on(self, level: int = MAX_BRIGHTNESS_LEVEL, hue: int = 0,
         saturation: int = 0, verify: bool = True) -> None:
    """Turns on the light state of the device.

    Args:
      level: Brightness level to be set.
      hue: Hue of lighting color to be set.
      saturation: Saturation of lighting color to be set.
      verify: If True, returns after verifying the light configurations.
    """

  @abc.abstractmethod
  def off(self, verify: bool = True) -> None:
    """Turns off the light state of the device.

    Args:
      verify: If true, verifies the light configurations before returning.
    """

  @property
  @abc.abstractmethod
  def state(self) -> bool:
    """The light state of the device.

    Returns:
      True if the device is in on state, false if it's in off state.
    """

  @property
  @abc.abstractmethod
  def brightness(self) -> int:
    """The brightness level of the device: between 0 and 255 inclusive.

    Returns:
      The current brightness level.
    """

  @property
  @abc.abstractmethod
  def color(self) -> lighting_service_pb2.LightingColor:
    """The lighting color of the device.

    Color consists of hue and saturation, which are between 0x00 and 0xFE
    inclusive.

    Returns:
      The current lighting color.
    """
