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

"""Defines a process transport by wrapping the subprocess.Popen() constructor."""
import select
import subprocess
import time
import six
from gazoo_device.switchboard import transport_properties
from gazoo_device.switchboard.transports import transport_base


class ProcessTransport(transport_base.TransportBase):
  """Perform communication using a subprocess with the command and args specified."""

  def __init__(self,
               command,
               args="",
               auto_reopen=False,
               open_on_start=True,
               working_directory=None):
    """Initialize the ProcessTransport object with the given process properties.

    Args:
        command (str): command to execute
        args (str): list of additional args to pass to command
        auto_reopen (bool): flag indicating transport should be reopened if
          unexpectedly closed.
        open_on_start (bool): flag indicating transport should be open on
          TransportProcess start.
        working_directory (string): Current working directory.
    """

    super(ProcessTransport, self).__init__(auto_reopen, open_on_start)
    self._args = [command] + args.split()

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

  def close(self):
    """Closes the process."""
    if hasattr(self, "_process") and self._process:
      self._process.stdin.close()
      self._process.stdout.close()
      if self._process.poll() is None:
        self._process.terminate()
        while self._process.poll() is None:
          time.sleep(0.001)
      self._process = None

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
    if isinstance(data, six.text_type):
      data = data.encode("utf-8", errors="replace")

    if timeout:
      return self._write_non_blocking(data, timeout)
    return self._write_data(data)

  def _is_ready_to_open(self):
    return True

  def _read_data(self, size):
    return self._process.stdout.read(size)

  def _read_non_blocking(self, size, timeout):
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
    if isinstance(data, six.integer_types):
      data = six.int2byte(data)
    self._process.stdin.write(data)
    self._process.stdin.flush()
    return len(data)
