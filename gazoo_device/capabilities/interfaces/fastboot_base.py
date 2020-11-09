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

"""Fastboot capability interface."""
import abc
from gazoo_device.capabilities.interfaces import capability_base


class FastbootBase(capability_base.CapabilityBase):
    """Abstract base class for the Fastboot capability."""

    @abc.abstractmethod
    def enter(self):
        """Enters fastboot (bootloader) mode for updating device firmware.

        Raises:
            GazooDeviceError: if unable to boot device into fastboot mode.
        """

    @abc.abstractmethod
    def exit(self):
        """Exits fastboot (bootloader) mode after updating device firmware.

        Raises:
            GazooDeviceError if unable to reboot device out of fastboot mode
        """
