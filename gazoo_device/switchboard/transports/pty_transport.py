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

"""Pseudoterminal transport class.

Some processes like the simulator shell script can fork/exec other
processes and need job control. A common way of overcoming this problem is
for the shell script to become a process leader. This is usually achieved by
using pseudoterminals.

More details: https://goo.gl/ckgF91

Pseudoterminals have a slightly different interface to reading and writing.

Example:
    os.read(self._process.stdout, size) in PTY
    self._process.stdout.read(size) in a regular process

This class will act as an adapter

"""
import os
import pty
import subprocess
import time

from gazoo_device import gdm_logger
from gazoo_device.switchboard import transport_properties
from gazoo_device.switchboard.transports import process_transport
import six

logger = gdm_logger.get_logger()


class PtyTransport(process_transport.ProcessTransport):
  """Perform process transport over pseudoterminal."""

  def __init__(self,
               comms_address,
               args="",
               auto_reopen=False,
               open_on_start=True):
    """Initialize the pty transport object with the given process properties.

    Args:
        comms_address (str): the process command and args to communicate
        args (str): additional args to pass to the main process to open
          communication.
        auto_reopen (bool): flag indicating transport should be reopened if
          unexpectedly closed.
        open_on_start (bool): flag indicating transport should be open on
          TransportProcess start.
    """
    self.comms_address = comms_address
    working_directory = os.path.dirname(comms_address)
    if working_directory:
      comms_address = comms_address.replace(working_directory, "./")
    else:
      working_directory = None
    super(PtyTransport, self).__init__(
        command=comms_address,
        args=args,
        auto_reopen=auto_reopen,
        open_on_start=open_on_start,
        working_directory=working_directory)
    self.primary = None
    self.secondary = None

  def close(self):
    """Closes the process if open."""
    if self.primary:
      os.close(self.primary)
      self.primary = None
    if self.secondary:
      os.close(self.secondary)
      self.secondary = None
    if hasattr(self, "_process") and self._process:
      if self._process.poll() is None:
        self._process.terminate()
        while self._process.poll() is None:
          time.sleep(0.001)
      self._process = None

  def _open(self):
    """Opens or reopens the process using the current property values.

    Raises:
        Exception: when invalid executable or options are provided.
    """
    if self._is_ready_to_open():
      try:
        # self.primary corresponds to the "master" file descriptor from pty.openpty().
        # self.secondary corresponds to the "slave" file descriptor from pty.openpty().
        self.primary, self.secondary = pty.openpty()
        self._process = subprocess.Popen(  # pylint: disable=subprocess-popen-preexec-fn
            self._args,
            stdin=self.secondary,
            stdout=self.secondary,
            stderr=self.secondary,
            cwd=self._cwd,
            close_fds=self._properties[transport_properties.CLOSE_FDS],
            preexec_fn=os.setsid  # This creates a new "process group"
        )
        # Set the stdin and stdout to self.primary
        self._process.stdout = self.primary
        self._process.stdin = self.primary
        os.close(self.secondary)
        self.secondary = None
      except Exception:
        self.close()
        raise

  def _read_data(self, size):
    try:
      return os.read(self._process.stdout, size)
    except OSError as err:
      logger.debug("Error in pty_process: {!r}".format(err))
      return b""

  def _write_data(self, data):
    if isinstance(data, six.integer_types):
      data = six.int2byte(data)
    os.write(self._process.stdin, data)
    return len(data)
