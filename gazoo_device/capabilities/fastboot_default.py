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

"""Definition of the FastbootDefault capability."""
import time

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import fastboot_base
from gazoo_device.utility import adb_utils
from gazoo_device.utility import common_utils

logger = gdm_logger.get_gdm_logger()


class FastbootDefault(fastboot_base.FastbootBase):
    """Fastboot capability."""
    _REQUIRED_TIMEOUTS = ["ONLINE"]

    def __init__(self,
                 device_name,
                 communication_address,
                 fastboot_serial,
                 timeouts_dict,
                 add_log_note_fn,
                 check_device_ready_fn,
                 root_device_fn):
        """Initialize the fastboot capability.

        Args:
            device_name (str): name of the device using the capability.
            communication_address (str): the device serial.
            fastboot_serial (str): the device fastboot serial.
            timeouts_dict (dict): dictionary of timeouts.
            add_log_note_fn (func): add output to log file.
            check_device_ready_fn (func): verify the device is ready to recieve GDM commands.
            root_device_fn (func): roots device if not rooted.
        """
        super(FastbootDefault, self).__init__(device_name=device_name)
        self._communication_address = communication_address
        self._fastboot_serial = fastboot_serial
        self._timeouts_dict = timeouts_dict
        self._add_log_note_fn = add_log_note_fn
        self._check_device_ready_fn = check_device_ready_fn
        self._root_device_fn = root_device_fn

        self.validate_required_keys(self._REQUIRED_TIMEOUTS, self._timeouts_dict, "timeouts_dict")

    @decorators.CapabilityLogDecorator(logger)
    def enter(self):
        """Enters fastboot (bootloader) mode for updating device firmware.

        Raises:
            GazooDeviceError: if unable to boot device into fastboot mode.
        """
        if self._is_in_fastboot_mode():
            return

        output = adb_utils.enter_fastboot(self._communication_address)
        for line in output.splitlines():
            self._add_log_note_fn(line + "\n")
        if not self._is_in_fastboot_mode(timeout=self._timeouts_dict["ONLINE"]):
            raise errors.GazooDeviceError("{} failed to enter fastboot mode in {}s."
                                          .format(self._device_name,
                                                  self._timeouts_dict["ONLINE"]))

    @decorators.CapabilityLogDecorator(logger)
    def exit(self):
        """Exits fastboot (bootloader) mode after updating device firmware.

        Raises:
            GazooDeviceError if unable to reboot device out of fastboot mode
        """
        if not adb_utils.is_fastboot_mode(self._fastboot_serial):
            return

        self._add_log_note_fn("GDM triggered reboot via 'fastboot reboot'")
        start_time = time.time()
        output = adb_utils.exit_fastboot(self._fastboot_serial)
        for line in output.splitlines():
            self._add_log_note_fn(line + "\n")
        logger.info("{} fastboot reboot took {}s.",
                    self._device_name, time.time() - start_time)
        self._check_device_ready_fn()
        self._root_device_fn()

    def _is_in_fastboot_mode(self, timeout=None):
        """Returns if device in fastboot mode. Waits up to timeout time.

        We try verify whether the device is in fastboot mode in the {timeout} duration, with retry
        interval 0.5 sec.
        If timeout is None (not provided), there will be no retry.

        Args:
            timeout (float): optional, maximum wait time in seconds. If timeout is None, we will
                             not retry.

        Returns:
            bool: whether device is in fastboot mode.
        """
        # No retry when timeout is None.
        # (Setting timeout to 0.1 is equivalent to "no retry" since interval is 0.5 sec.)
        timeout = timeout or 0.1

        try:
            common_utils.retry(adb_utils.is_fastboot_mode,
                               func_args=(self._fastboot_serial,),
                               is_successful=bool,
                               timeout=timeout,
                               interval=0.5)
            logger.info("{} is in fastboot mode.", self._device_name)
            return True
        except errors.CommunicationTimeoutError:
            return False
