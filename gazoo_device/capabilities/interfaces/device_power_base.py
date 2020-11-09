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

"""Interface for the device power capability."""
import abc
from gazoo_device.capabilities.interfaces import capability_base


class DevicePowerBase(capability_base.CapabilityBase):
    """Abstract Base class for the device power capability."""

    @abc.abstractproperty
    def hub_name(self):
        """Name of the hub the device is attached to."""

    @abc.abstractproperty
    def hub_type(self):
        """Type of hub the check is attached to."""

    @abc.abstractproperty
    def port_mode(self):
        """port mode."""

    @abc.abstractproperty
    def port_number(self):
        """Port number the device is attached to."""

    @abc.abstractmethod
    def cycle(self, no_wait=False):
        """Power off then power on the device.

        Args:
            no_wait (bool):  Return before verifying boot up.
        """

    @abc.abstractmethod
    def on(self, no_wait=False):
        """Turn on power to the device.

        Args:
            no_wait (bool):  Return before verifying boot up.
        """

    @abc.abstractmethod
    def off(self):
        """Turn off power to the device."""
