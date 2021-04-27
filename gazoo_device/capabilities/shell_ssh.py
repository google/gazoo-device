# Copyright 2021 Google LLC
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
import time
from gazoo_device import config
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import shell_base

_SSH_CONNECTION_FAILURE_MARKERS = ["Connection to", "Connection reset"]

logger = gdm_logger.get_logger()


class ShellSSH(shell_base.ShellBase):
  """Common shell() method implementation for devices communicating over SSH."""

  def __init__(self,
               send_and_expect,
               device_name,
               shell_cmd=shell_base._SHELL_CMD,
               shell_regex=shell_base._SHELL_REGEX,
               tries=shell_base._TRIES,
               timeout=shell_base._TIMEOUT,
               failure_markers=None):
    """Initalize the SSH shell capability.

    Args:
        send_and_expect (method): bound send_and_expect method of the device
          class instance.
        device_name (str): name of the device using this capability.
        shell_cmd (str): return code wrapper around the shell command to
          execute.
        shell_regex (str): shell regex to use. Must contain two capturing
          groups: one for the output and one for the return code.
        tries (int): how many times to try sending the shell command.
        timeout (float): shell timeout in seconds.
        failure_markers (list): list of markers (strings) indicating SSH
          connection failure.
    """
    super(ShellSSH, self).__init__(
        send_and_expect=send_and_expect,
        device_name=device_name,
        shell_cmd=shell_cmd,
        shell_regex=shell_regex,
        tries=tries,
        timeout=timeout)

    if failure_markers is None:
      failure_markers = _SSH_CONNECTION_FAILURE_MARKERS

    self._failure_markers = failure_markers

  def shell(self,
            command,
            command_name="shell",
            timeout=None,
            port=0,
            include_return_code=False,
            searchwindowsize=config.SEARCHWINDOWSIZE):
    """Sends command and returns response and optionally return code.

    Args:
        command (str): Command to send to the device.
        command_name (str): Identifier for command.
        timeout (float): Time in seconds to wait for device to respond.
        port (int): Which port to send on, 0 or 1.
        include_return_code (bool): flag indicating return code should be
          returned.
        searchwindowsize (int): Number of the last bytes to look at.

    Raises:
        DeviceError: if communication fails.

    Note:
        Can try multiple times as connection can sometimes fail.
        See the init args for setting the number of retry attempts.

    Returns:
        str: If include_return_code is False return the device response to
        the command.
        tuple: If include_return_code is True return the device response and
        return code.
    """
    if timeout is None:
      timeout = self._timeout

    command = self._shell_cmd.format(cmd=command.rstrip())

    logger.debug("{} sending {!r} to generate {} in {}s on port {}",
                 self._device_name, command, command_name, timeout, port)

    for attempt in range(self._tries):
      response = self._send_and_expect(
          command, [self._shell_regex],
          timeout=timeout,
          port=port,
          searchwindowsize=searchwindowsize,
          expect_type="response")
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

    result = response.match.group(1).strip()
    return_code = int(response.match.group(2))

    if include_return_code:
      return result, return_code
    else:
      return result

  def has_command(self, binary_name):
    """Returns if binary_name is installed on the device.

    Args:
        binary_name (str): name of the executable.

    Returns:
        bool: True if the executable is found on the device, False
        otherwise.
    """
    _, result_code = self.shell(
        f'which {binary_name}\n', include_return_code=True)
    return result_code == 0
