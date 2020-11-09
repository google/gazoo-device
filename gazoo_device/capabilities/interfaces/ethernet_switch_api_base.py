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

"""Abstract base class for ethernet switch port manipulation."""
from __future__ import absolute_import
import abc
from gazoo_device.capabilities.interfaces import capability_base


class EthernetSwitchApiBase(capability_base.CapabilityBase):
    """Interface for ethernet switch port manipulation for devices with an ethernet connection."""

    @abc.abstractmethod
    def disable(self, no_wait=False):
        """Disables ethernet_switch port for device's ethernet connection.

        Args:
            no_wait (bool): If True, returns before verifying connection status.

        Raises:
          GazooDeviceError: if ethernet connection has not been disabled.
        """

    @abc.abstractmethod
    def enable(self, no_wait=False):
        """Enables ethernet_switch port for devices ethernet connection.

        Args:
            no_wait (bool): If True, returns before verifying connection status.

        Raises:
            GazooDeviceError: if ethernet connection has not been enabled.
        """

    @abc.abstractproperty
    def address(self):
        """Returns the address of the ethernet switch where device is conneced.

        Returns:
            str: ethernet switch ip address
        """

    @abc.abstractproperty
    def port(self):
        """Returns the port number on the ethernet switch where device is conneced.

        Returns:
            str: ethernet switch ip address
        """

    @abc.abstractproperty
    def status(self):
        """Current status of the ethernet switch port.

        Returns:
            bool: True if ethernet ethernet switch port is enabled, otherwise False
        """
