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

"""Sideload capability interface."""
import abc
from gazoo_device.capabilities.interfaces import capability_base


class SideloadBase(capability_base.CapabilityBase):
    """Abstract base class for the sideload capability."""

    @abc.abstractmethod
    def enter(self):
        """Enters sideload mode for updating device firmware.

        Raises:
            GazooDeviceError: if unable to boot device into sideload mode.
        """

    @abc.abstractmethod
    def exit(self):
        """Exits sideload mode after updating device firmware.

        Raises:
            GazooDeviceError if unable to reboot device out of sideload mode
        """

    @abc.abstractmethod
    def is_in_sideload_mode(self):
        """Whether the device is currently in sideload mode.

        Returns:
            bool: True if device in sideload mode; False otherwise.
        """
