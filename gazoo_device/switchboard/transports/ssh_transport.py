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

"""Defines an ssh transport interface by extending the process_transport.py."""
from typing import Optional

from gazoo_device import data_types
from gazoo_device.switchboard.transports import process_transport
from gazoo_device.utility import host_utils


class SSHTransport(process_transport.ProcessTransport):
  """Transport for communicating over SSH with a device."""

  def __init__(self,
               comms_address: str,
               args: str = host_utils.DEFAULT_SSH_OPTIONS,
               key_info: Optional[data_types.KeyInfo] = None,
               log_cmd: str = "",
               auto_reopen: bool = True,
               open_on_start: bool = True,
               username: str = "root"):
    """Initializes an SSHTransport object with the given properties.

    Args:
      comms_address: IP address of the device.
      args: Extra command line args for the SSH command.
      key_info: SSH key to use. If None, don't use an SSH key.
      log_cmd: Command to execute over SSH, such as "logcat".
      auto_reopen: Flag indicating whether the transport should be automatically
        reopened if unexpectedly closed.
      open_on_start: Flag indicating whether the transport should be open on
        TransportProcess start.
      username: Username to log in as.
    """
    self.comms_address = comms_address
    args = host_utils.generate_ssh_args(
        comms_address,
        log_cmd,
        username,
        options=args,
        key_info=key_info)
    super().__init__(
        command="ssh",
        args=args,
        auto_reopen=auto_reopen,
        open_on_start=open_on_start)

  def _is_ready_to_open(self):
    return host_utils.is_pingable(self.comms_address)
