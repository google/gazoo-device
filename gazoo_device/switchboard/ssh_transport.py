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

"""Defines an ssh transport interface by extending the process_transport.py.

Assumes logcat is available on the device.
"""
from __future__ import absolute_import
from gazoo_device.switchboard import process_transport
from gazoo_device.utility import host_utils


class SSHTransport(process_transport.ProcessTransport):
    """Perform transport communication using the ssh to some device."""

    def __init__(self,
                 comms_address,
                 args=host_utils.DEFAULT_SSH_OPTIONS,
                 ssh_key_type=None,
                 log_cmd="",
                 auto_reopen=True,
                 open_on_start=True,
                 username="root"):
        """Initialize the Ssh Transport object with the given properties.

        Args:
            comms_address (str): ip address to use when connecting to device
            args (str): extra args for ssh command.
            ssh_key_type (str): type of ssh key (types found in config)
            log_cmd (str): additional commands to pass to ssh such as logcat.
            auto_reopen (bool): flag indicating transport should be reopened if
                                unexpectedly closed.
            open_on_start (bool): flag indicating transport should be open on
                                  TransportProcess start.
            username (str): username to log into device.

        """
        self.comms_address = comms_address
        args = host_utils.generate_ssh_args(
            comms_address,
            log_cmd,
            username,
            options=args,
            ssh_key_type=ssh_key_type)
        super(SSHTransport, self).__init__(command="ssh",
                                           args=args,
                                           auto_reopen=auto_reopen,
                                           open_on_start=open_on_start)

    def _is_ready_to_open(self):
        return host_utils.is_pingable(self.comms_address)
