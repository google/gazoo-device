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

"""Interface for an PwRPC (Pigweed RPC) locking capability."""
import abc
from gazoo_device.capabilities.interfaces import capability_base


class PwRPCLockBase(capability_base.CapabilityBase):
  """Pigweed RPC locking capability for devices communicating over PwRPC."""

  @abc.abstractmethod
  def lock(self, verify: bool = True) -> None:
    """Locks the device.

    Args:
      verify: If true, verifies the lock configurations before returning.
    """

  @abc.abstractmethod
  def unlock(self, verify: bool = True) -> None:
    """Unlocks the device.

    Args:
      verify: If true, verifies the lock configurations before returning.
    """

  @property
  @abc.abstractmethod
  def state(self) -> bool:
    """The locked state of the device.

    Returns:
      True if the device is locked, false if it's unlocked.
    """
