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
"""Communication type for device communication over host shell commands."""
from typing import Sequence
from gazoo_device.switchboard import line_identifier
from gazoo_device.switchboard.communication_types import base_comms
from gazoo_device.switchboard.transports import process_transport

HOST_COMMUNICATION_ADDRESS = "/bin/sh"


class HostShellComms(base_comms.CommunicationType):
  """Communication type for device communication over host shell commands.

  Commands/responses are on port 0 while log streaming happens on port 1.
  """

  @classmethod
  def get_comms_addresses(cls) -> list[str]:
    return [HOST_COMMUNICATION_ADDRESS]

  def __init__(
      self,
      comms_address: str = HOST_COMMUNICATION_ADDRESS,
      command: str = "bash",
      args: Sequence[str] = (),
      log_cmd: Sequence[str] = ("tail", "-F", "/var/log/messages"),
  ) -> None:
    super().__init__(comms_address=comms_address)
    self.command = command
    self.args = args
    self.log_cmd = log_cmd

  def get_transport_list(self) -> list[process_transport.ProcessTransport]:
    return [
        process_transport.ProcessTransport(
            comms_address=self.comms_address,
            command=self.command,
            args=self.args,
        ),
        process_transport.ProcessTransport(
            comms_address=self.comms_address,
            command=self.command,
            args=self.log_cmd,
        ),
    ]

  def get_identifier(self) -> line_identifier.PortLogIdentifier:  # pytype: disable=signature-mismatch  # overriding-return-type-checks
    return line_identifier.PortLogIdentifier(log_ports=[1])
