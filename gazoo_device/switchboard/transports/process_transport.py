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

"""Defines a process transport by wrapping the subprocess.Popen() constructor."""
import select
import subprocess
import time
from typing import Optional, Sequence

from gazoo_device import config
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.switchboard import transport_properties
from gazoo_device.switchboard.transports import transport_base
from gazoo_device.utility import retry

logger = gdm_logger.get_logger()


class ProcessTransport(transport_base.TransportBase):
  """Perform communication using a subprocess with the command and args specified."""

  def __init__(self,
               comms_address: str,
               command: str,
               args: Sequence[str] = (),
               auto_reopen: bool = False,
               open_on_start: bool = True,
               working_directory: Optional[str] = None):
    """Initialize the ProcessTransport object with the given process properties.

    Args:
        comms_address: Transport's communication address (e. g. IP address,
            ADB identifier).
        command: Command to execute.
        args: List of additional args to pass to command.
        auto_reopen: Flag indicating transport should be reopened if
            unexpectedly closed.
        open_on_start: Flag indicating transport should be open on
            TransportProcess start.
        working_directory: Current working directory.
    """

    super().__init__(comms_address, auto_reopen, open_on_start)
    self._args = [command] + list(args)
    self._properties.update({
        transport_properties.CLOSE_FDS: True,
    })
    self._process = None
    self._cwd = working_directory

  def is_open(self):
    """Returns True if transport is currently open.

    Returns:
        bool: True if transport is currently open, False otherwise.

    Note:
        If the process unexpected exits this method will return False.
    """
    return (hasattr(self, "_process") and self._process is not None and
            self._process.poll() is None)

  def _open(self):
    """Opens or reopens the process using the current property values."""
    if self._is_ready_to_open():
      self._process = subprocess.Popen(
          self._args,
          bufsize=0,
          close_fds=self._properties[transport_properties.CLOSE_FDS],
          stdin=subprocess.PIPE,
          stdout=subprocess.PIPE,
          stderr=subprocess.STDOUT,
          cwd=self._cwd)

  def _close(self):
    """The close() implementation checks if process is open differently than is_open().

    Hence this method is unused, but has to be overridden.
    """
    pass

  def _close_process(self):
    """Closes the process."""
    if not self.is_open():
      return
    if self._process.poll() is None:
      self._process.terminate()
      try:
        retry.retry(
            func=self._process.poll,
            is_successful=lambda poll_result: poll_result is not None,
            timeout=config.SWITCHBOARD_PROCESS_COMMAND_CONSUMPTION_TIMEOUT_S,
            interval=config.SWITCHBOARD_PROCESS_POLLING_INTERVAL_S)
      except errors.CommunicationTimeoutError as e:
        # process did not terminate.
        self._process.kill()
        raise errors.ProcessCommunicationError(
            "",
            "Process transport did not terminate after {} seconds. "
            "Killed the process.".format(
                config.SWITCHBOARD_PROCESS_COMMAND_CONSUMPTION_TIMEOUT_S)
            ) from e
    self._process = None

  def close(self):
    """Closes the process."""
    if hasattr(self, "_process") and self._process:
      if self._process.stdin is not None:
        self._process.stdin.close()
      if self._process.stdout is not None:
        self._process.stdout.close()
      self._close_process()

  def _read(self, size=1, timeout=None):
    """Returns bytes read up to max_bytes within timeout in seconds specified.

    Args:
        size (int): maximum number of bytes to read within timeout seconds
        timeout (float): maximum seconds to wait to read bytes or
          indefinitely
                         if timeout=None. Default: None

    Returns:
        str: bytes read from transport or None if no bytes were read
    """
    if timeout:
      return self._read_non_blocking(size, timeout)
    return self._read_data(size)

  def _write(self, data, timeout=None):
    """Writes data provided within timeout in seconds specified.

    Args:
        data (str): bytes to be written out within timeout seconds
        timeout (float): maximum seconds to wait to write bytes or
          indefinitely
                         if timeout=None. Default: None

    Returns:
        int: number of bytes written or None if no bytes were written
    """
    if isinstance(data, str):
      data = data.encode("utf-8", errors="replace")

    if timeout:
      return self._write_non_blocking(data, timeout)
    return self._write_data(data)

  def _is_ready_to_open(self):
    return True

  def _read_data(self, size):
    if self._process is None:
      raise ValueError("process is not initialized")
    if self._process.stdout is None:
      raise ValueError("stdout is not initialized")
    return self._process.stdout.read(size)

  def _read_non_blocking(self, size, timeout):
    if self._process is None:
      raise ValueError("process is not initialized")
    count = 0
    result = b""
    end_time = time.time() + timeout
    while count < size and time.time() < end_time:
      time_left = end_time - time.time()
      readable, _, _ = select.select([self._process.stdout], [], [],
                                     0 if time_left < 0 else time_left)
      for stream in readable:
        if stream is self._process.stdout:
          count += 1
          result += self._read_data(1)
    return result

  def _write_non_blocking(self, data, timeout):
    if self._process is None:
      raise ValueError("process is not initialized")
    count = 0
    size = len(data)
    end_time = time.time() + timeout
    while count < size and time.time() < end_time:
      time_left = end_time - time.time()
      _, writable, _ = select.select([], [self._process.stdin], [],
                                     0 if time_left < 0 else time_left)
      for stream in writable:
        if stream is self._process.stdin:
          count += self._write_data(data[count])
    return count

  def _write_data(self, data):
    if self._process is None:
      raise ValueError("process is not initialized")
    if self._process.stdin is None:
      raise ValueError("stdin is not initialized")
    if isinstance(data, int):
      data = bytes((data,))
    self._process.stdin.write(data)
    self._process.stdin.flush()
    return len(data)
