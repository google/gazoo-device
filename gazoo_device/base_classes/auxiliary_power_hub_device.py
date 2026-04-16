# Copyright 2023 Google LLC
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
"""Base class for auxiliary power hub devices."""
import abc

from gazoo_device.base_classes import auxiliary_device
from gazoo_device.capabilities.interfaces import switch_power_base


class AuxiliaryPowerHubDevice(auxiliary_device.AuxiliaryDevice):
  """Base class for auxiliary power hub devices."""

  @property
  @abc.abstractmethod
  def switch_power(self) -> switch_power_base.SwitchPowerBase:
    """Capability to control switch power."""
