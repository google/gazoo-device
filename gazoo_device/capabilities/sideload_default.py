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

"""Definition of SideloadDefault capability."""

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import sideload_base
from gazoo_device.utility import adb_utils
from gazoo_device.utility import common_utils

logger = gdm_logger.get_gdm_logger()


class SideloadDefault(sideload_base.SideloadBase):
    """Default implementation for sideload capability."""

    WAIT_TIME_IN_SECS_FOR_ENTERING_SIDELOAD_MODE = 30.0

    def __init__(self,
                 device_name,
                 device_serial,
                 reboot_fn,
                 check_device_ready_fn,
                 root_device_fn):
        """Initialize the sideload capability.

        Args:
            device_name (str): the device name.
            device_serial (str): the device serial.
            reboot_fn (func): the reboot function to exit sideload.
            check_device_ready_fn (func): verify the device is ready to recieve GDM commands.
            root_device_fn (func): roots device if not rooted.
        """
        super(SideloadDefault, self).__init__(device_name=device_name)
        self._device_serial = device_serial
        self._reboot_fn = reboot_fn
        self._check_device_ready_fn = check_device_ready_fn
        self._root_device_fn = root_device_fn

    @decorators.CapabilityLogDecorator(logger)
    def enter(self, auto_reboot=False):
        """Enters sideload mode for updating device firmware.

        Args:
            auto_reboot (bool): whether to use sideload-auto-reboot or not.

        Raises:
            GazooDeviceError: if unable to boot device into sideload mode.
        """
        if self.is_in_sideload_mode():
            return
        _ = adb_utils.enter_sideload(adb_serial=self._device_serial, auto_reboot=auto_reboot)
        self._verify_in_sideload_mode()

    @decorators.CapabilityLogDecorator(logger)
    def exit(self):
        """Exits sideload mode after updating device firmware.

        Raises:
            GazooDeviceError if unable to reboot device out of sideload mode
        """
        if not self.is_in_sideload_mode():
            return
        self._reboot_fn()
        self._check_device_ready_fn()
        self._root_device_fn()

    @decorators.CapabilityLogDecorator(logger)
    def is_in_sideload_mode(self):
        """Whether the device is currently in sideload mode.

        Returns:
            bool: True if device in sideload mode; False otherwise.
        """
        return adb_utils.is_sideload_mode(adb_serial=self._device_serial)

    def _verify_in_sideload_mode(self, timeout=None):
        """Wait up to timeout for device to enter sideload mode.

        Args:
            timeout (float): timeout in seconds to wait for entering sideload.

        Raises:
            GazooDeviceError: if unable to verify in sideload mode until timeout is reached.
        """
        if timeout is None:
            timeout = self.WAIT_TIME_IN_SECS_FOR_ENTERING_SIDELOAD_MODE
        try:
            common_utils.retry(self.is_in_sideload_mode,
                               is_successful=bool,
                               timeout=timeout,
                               interval=0.5)
        except errors.CommunicationTimeoutError as err:
            raise errors.GazooDeviceError('Failed to verify sideload mode. {}'.format(err))
