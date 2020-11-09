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

"""ADB transport which communicates to the device over a process running 'adb shell'."""
from __future__ import absolute_import
import time

from gazoo_device.switchboard import process_transport
from gazoo_device.utility import adb_utils


READY_RETRY_DELAY = 2


class AdbTransport(process_transport.ProcessTransport):
    """Perform transport communication using the adb executable to some device.
    """

    def __init__(self,
                 comms_address,
                 command="shell",
                 adb_path=None,
                 fastboot_path=None,
                 auto_reopen=True,
                 open_on_start=True):
        """Initialize the AdbTransport object with the given properties.

        Args:
            comms_address (str): device adb_serial to use when connecting to device
            command (str): additional commands to pass to device
            adb_path (str): optional path to adb executable to use
            fastboot_path (str): optional path to fastboot executable to use
            auto_reopen (bool): flag indicating transport should be reopened if
                                unexpectedly closed.
            open_on_start (bool): flag indicating transport should be open on
                                  TransportProcess start.
        """
        self.comms_address = comms_address
        if adb_path is None:
            adb_path = adb_utils.get_adb_path()
        if fastboot_path is None:
            fastboot_path = adb_utils.get_fastboot_path()
        args = "-s {} {}".format(comms_address, command)
        super(AdbTransport, self).__init__(command=adb_path,
                                           args=args,
                                           auto_reopen=auto_reopen,
                                           open_on_start=open_on_start)
        self._adb_path = adb_path
        self._fastboot_path = fastboot_path

    def _is_ready_to_open(self):
        result = adb_utils.is_device_online(self.comms_address,
                                            adb_path=self._adb_path,
                                            fastboot_path=self._fastboot_path)
        if not result:
            time.sleep(READY_RETRY_DELAY)
        return result
