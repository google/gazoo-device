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

"""Common shell() capability for devices communicating over SSH."""
import re
import time
from typing import Callable, Collection, Optional, Tuple, Union

from gazoo_device import config
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import shell_base
from gazoo_device.switchboard import expect_response

_SSH_CONNECTION_FAILURE_MARKERS = ("Connection to", "Connection reset")

logger = gdm_logger.get_logger()


class ShellSSH(shell_base.ShellBase):
  """Common shell() method implementation for devices communicating over SSH."""

  def __init__(
      self,
      send_and_expect: Callable[..., expect_response.ExpectResponse],
      device_name: str,
      tries: int = shell_base.TRIES,
      timeout: float = shell_base.TIMEOUT,
      failure_markers: Collection[str] = _SSH_CONNECTION_FAILURE_MARKERS
  ) -> None:
    """Initializes an instance of ShellSSH capability.

    Args:
      send_and_expect: send_and_expect method of the device class instance.
      device_name: Name of the device using this capability.
      tries: How many times to try sending the shell command.
      timeout: Shell timeout in seconds.
      failure_markers: Markers indicating SSH connection failure.
    """
    super().__init__(
        send_and_expect=send_and_expect,
        device_name=device_name,
        tries=tries,
        timeout=timeout)
    self._failure_markers = failure_markers

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
    if timeout is None:
      timeout = self._timeout

    command = command.rstrip()  # Remove trailing newlines.
    command_str = ("echo '{}';".format(command.replace("'", r"'\''")) +
                   command + ";" +
                   "echo Return Code: $?\n")
    command_start_regex = re.escape(command)
    command_end_regex = r"Return Code: (-?\d+)"

    logger.debug("%s sending %r to generate %s in %ds on port %d",
                 self._device_name, command, command_name, timeout, port)

    for attempt in range(self._tries):
      response = self._send_and_expect(
          command_str, [command_start_regex, command_end_regex],
          timeout=timeout,
          port=port,
          searchwindowsize=searchwindowsize,
          expect_type="response",
          mode="sequential")
      if not response.timedout:
        break

      if (any(failure_marker in response.before
              for failure_marker in self._failure_markers) and
          attempt < self._tries - 1):
        logger.warning(
            "{}: SSH connection died with output {}. Trying again.".format(
                self._device_name, response.before))
        # SSH connection died. Retry.
        time.sleep(.1)
      else:
        raise errors.DeviceError("Device {} shell failed for command {!r}. "
                                 "Timed out waiting {}s for response. "
                                 "Shell output: {!r}.".format(
                                     self._device_name, command, timeout,
                                     response.before))

    # Compile shell output and filter results for only our command's output.
    result_list = response.before.splitlines() + response.after.splitlines()
    result_str = response.before + response.after
    pattern = (r"\n" +  # Beginning of a new line.
               command_start_regex + r"\n" +  # The echoed command.
               r"(.*)" +  # The response. May not end in a newline.
               command_end_regex + r"\n")  # The return code.
    match_echo = re.search(pattern, result_str, re.M | re.I | re.DOTALL)
    if match_echo:
      result = match_echo.group(1).strip()
    else:
      result = "\n".join(result_list[1:-1]).strip()

    if include_return_code:
      return_code = int(response.match.group(1))
      return result, return_code
    else:
      return result

  def has_command(self, binary_name: str) -> bool:
    """Returns if binary_name is installed on the device.

    Args:
      binary_name: Name of the executable.
    """
    _, result_code = self.shell(
        f"which {binary_name}\n", include_return_code=True)
    return result_code == 0
