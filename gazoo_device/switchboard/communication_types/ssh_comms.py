# Copyright 2023 Google LLC
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
"""Communication type for device communication over ssh."""
from typing import Collection, Optional, Sequence, TypeAlias
from gazoo_device import data_types
from gazoo_device.switchboard import line_identifier
from gazoo_device.switchboard.communication_types import base_comms
from gazoo_device.switchboard.transports import ssh_transport
from gazoo_device.utility import host_utils


LogCommandType: TypeAlias = Sequence[str]


class SshComms(base_comms.CommunicationType):
  """Communication type for device communication over ssh.

  Login is handled by ssh-keys on machine (or device does not require
  password).

  Commands/responses are on port 0 while log streaming happens on port 1.
  """

  @classmethod
  def get_comms_addresses(cls, static_ips: Collection[str]) -> list[str]:
    return host_utils.get_all_ssh_ips(static_ips)

  def __init__(
      self,
      comms_address: str,
      log_cmd: LogCommandType = (
          "tail", "-F", "-n", "/var/log/messages",
      ),
      args: Sequence[str] = host_utils.DEFAULT_SSH_OPTIONS,
      key_info: Optional[data_types.KeyInfo] = None,
      username: str = "root",
      additional_log_cmds: Sequence[LogCommandType] | None = None,
  ) -> None:
    super().__init__(comms_address)
    self.log_cmd = log_cmd
    self.args = args
    self.username = username
    self.key_info = key_info
    self.additional_log_cmds = additional_log_cmds or ()

  def get_transport_list(self) -> list[ssh_transport.SSHTransport]:
    default_transports = [
        ssh_transport.SSHTransport(
            comms_address=self.comms_address,
            args=self.args,
            key_info=self.key_info,
            username=self.username),
        ssh_transport.SSHTransport(
            comms_address=self.comms_address,
            args=self.args,
            username=self.username,
            key_info=self.key_info,
            log_cmd=self.log_cmd)
    ]
    additional_log_transports = [
        ssh_transport.SSHTransport(
            comms_address=self.comms_address,
            args=self.args,
            username=self.username,
            key_info=self.key_info,
            log_cmd=log_cmd)
        for log_cmd in self.additional_log_cmds
    ]
    return default_transports + additional_log_transports

  def get_identifier(self) -> line_identifier.PortLogIdentifier:  # pytype: disable=signature-mismatch  # overriding-return-type-checks
    default_log_transport_port = [1]
    additional_log_transport_ports = (
        list(range(2, 2 + len(self.additional_log_cmds)))
    )
    log_ports = default_log_transport_port + additional_log_transport_ports
    return line_identifier.PortLogIdentifier(log_ports=log_ports)
