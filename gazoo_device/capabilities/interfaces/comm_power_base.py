# Copyright 2020 Google LLC
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

"""Interface for the communication power capability."""
import abc
from gazoo_device.capabilities.interfaces import capability_base


class CommPowerBase(capability_base.CapabilityBase):
    """Abstract Base class for the communication power capability."""

    @abc.abstractmethod
    def off(self):
        """Turn off power to the device communication port."""

    @abc.abstractmethod
    def on(self):
        """Turn on power to the device communication port."""
