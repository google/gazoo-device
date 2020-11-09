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

"""Shell capability interface."""
from __future__ import absolute_import
import abc
from gazoo_device.capabilities.interfaces import capability_base

_DEVICE_CAPABILITY_NAME = "shell_capability"
_SHELL_CMD = u"{cmd};echo Return Code: $?\n"
_SHELL_REGEX = r"(.*)Return Code: (\d+)\n"
_TIMEOUT = 10
_TRIES = 2


class ShellBase(capability_base.CapabilityBase):
    """Abstract base class defining the API for the shell() method."""

    def __init__(self, send_and_expect, device_name, shell_cmd=_SHELL_CMD,
                 shell_regex=_SHELL_REGEX, tries=_TRIES, timeout=_TIMEOUT):
        """Initalize the SSH shell capability.

        Args:
            send_and_expect (method): bound send_and_expect method of the device class instance.
            device_name (str): name of the device using this capability.
            shell_cmd (str): return code wrapper around the shell command to execute.
            shell_regex (str): shell regex to use. Must contain two capturing groups:
                               one for the output and one for the return code.
            tries (int): how many times to try sending the shell command.
            timeout (float): shell timeout in seconds.
        """
        super(ShellBase, self).__init__(device_name=device_name)

        self._send_and_expect = send_and_expect
        self._shell_regex = shell_regex
        self._shell_cmd = shell_cmd
        self._tries = tries
        self._timeout = timeout

    @classmethod
    def get_capability_name(cls):
        """Override the default to avoid a name conflict with the "shell" method."""
        return _DEVICE_CAPABILITY_NAME

    @abc.abstractmethod
    def shell(self, command, command_name="shell", timeout=10, port=0,
              include_return_code=False):
        """Sends command and returns response and optionally return code.

        Args:
            command (str): Command to send to the device.
            command_name (str): Identifier for command.
            timeout (float): Time in seconds to wait for device to respond.
            port (int): Which port to send on, 0 or 1.
            include_return_code (bool): flag indicating return code should be returned.

        Raises:
            GazooDeviceError: if communication fails.

        Note:
            Can try multiple times as connection can sometimes fail.
            See the init args for setting the number of retry attempts.

        Returns:
            str: If include_return_code is False return the device response to the command.
            tuple: If include_return_code is True return the device response and return code.
        """

    @abc.abstractmethod
    def has_command(self, binary_name):
        """Returns if binary_name is installed on the device.

        Args:
            binary_name (str): name of the executable.

        Returns:
            bool: True if the executable is found on the device, False otherwise.
        """
