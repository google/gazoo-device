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

"""Interface for an PwRPC (Pigweed RPC) device common capability."""
import abc
from gazoo_device.capabilities.interfaces import capability_base


class PwRPCCommonBase(capability_base.CapabilityBase):
  """Pigweed RPC common capability for devices communicating over PwRPC."""

  @property
  @abc.abstractmethod
  def vendor_id(self) -> str:
    """The vendor id of the device."""

  @property
  @abc.abstractmethod
  def product_id(self) -> str:
    """The product id of the device."""

  @property
  @abc.abstractmethod
  def software_version(self) -> str:
    """The software version of the device."""

  @abc.abstractmethod
  def reboot(self) -> None:
    """Reboots the device."""

  @abc.abstractmethod
  def factory_reset(self) -> None:
    """Factory resets the device."""

  @abc.abstractmethod
  def ota(self) -> None:
    """Triggers OTA to the device."""
