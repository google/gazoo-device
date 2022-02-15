# Copyright 2022 Google LLC
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
import abc
from typing import Callable, Optional, Tuple, Union

from gazoo_device import config
from gazoo_device.capabilities.interfaces import capability_base
from gazoo_device.switchboard import expect_response

TIMEOUT = 10
TRIES = 2

_DEVICE_CAPABILITY_NAME = "shell_capability"


class ShellBase(capability_base.CapabilityBase):
  """Abstract base class defining the API for the shell() method."""

  def __init__(self,
               send_and_expect: Callable[..., expect_response.ExpectResponse],
               device_name: str,
               tries: int = TRIES,
               timeout: float = TIMEOUT) -> None:
    """Initializes an instance of Shell capability.

    Args:
      send_and_expect: send_and_expect method of the device class instance.
      device_name: Name of the device using this capability.
      tries: How many times to try sending the shell command.
      timeout: Shell timeout in seconds.
    """
    super().__init__(device_name=device_name)

    self._send_and_expect = send_and_expect
    self._tries = tries
    self._timeout = timeout

  @classmethod
  def get_capability_name(cls) -> str:
    """Override the default to avoid a name conflict with the "shell" method."""
    return _DEVICE_CAPABILITY_NAME

  @abc.abstractmethod
  def shell(
      self,
      command: str,
      command_name: str = "shell",
      timeout: Optional[float] = None,
      port: int = 0,
      include_return_code: bool = False,
      searchwindowsize: int = config.SEARCHWINDOWSIZE
  ) -> Union[str, Tuple[str, int]]:
    """Sends command and returns response and optionally return code.

    If the SSH connection fails, the command is retried (up to a total of
    self._tries attempts).

    Args:
      command: Command to send to the device.
      command_name: Identifier for command.
      timeout: Time in seconds to wait for device to respond.
      port: Which port to send on. Port 0 is typically used for commands.
      include_return_code: Whether to also return the command return code.
      searchwindowsize: Number of the last bytes to look at.

    Raises:
      DeviceError: if communication fails.

    Returns:
      If include_return_code is False, returns the device response to the
        command.
      If include_return_code is True, returns the device response and the
        command return code.
    """

  @abc.abstractmethod
  def has_command(self, binary_name: str) -> bool:
    """Returns if binary_name is installed on the device.

    Args:
      binary_name: Name of the executable.
    """
