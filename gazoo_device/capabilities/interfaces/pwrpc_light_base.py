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

"""Interface for an PwRPC (Pigweed RPC) lighting capability."""
import abc
from typing import Tuple

from gazoo_device.capabilities.interfaces import capability_base


class PwRPCLightBase(capability_base.CapabilityBase):
  """Pigweed RPC lighting capability for devices communicating over PwRPC."""

  @abc.abstractmethod
  def on(self, no_wait: bool = False) -> None:
    """Turns on the light state of the device.

    Args:
      no_wait: If True, returns before verifying the light state.

    Raises:
      DeviceError: When the device does not transition to the appropriate
      state or if it remains off.
    """

  @abc.abstractmethod
  def off(self, no_wait: bool = False) -> None:
    """Turns off the light state of the device.

    Args:
      no_wait: If True, returns before verifying the light state.

    Raises:
      DeviceError: When the device does not transition to the appropriate
      state or if it remains on.
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
  def brightness(self) -> Tuple[int, int]:
    """The brightness level of the device.

    Returns:
      Current brightness level and the maximal brightness level.
    """
