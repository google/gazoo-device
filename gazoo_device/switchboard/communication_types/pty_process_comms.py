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
"""Communication type for communication with a process on the host machine."""
from gazoo_device.switchboard import line_identifier
from gazoo_device.switchboard.communication_types import base_comms
from gazoo_device.switchboard.transports import pty_transport


class PtyProcessComms(base_comms.CommunicationType):
  """Communication type for communication with a process on the host machine.

  No detection provided.
  """

  @classmethod
  def get_comms_addresses(cls) -> list[str]:
    return []

  def __init__(self, comms_address: str) -> None:
    full_command_list = comms_address.split()
    comms_address = full_command_list[0]
    super().__init__(comms_address)
    self.args = full_command_list[1:]

  def get_transport_list(self) -> list[pty_transport.PtyTransport]:
    return [pty_transport.PtyTransport(self.comms_address, args=self.args)]

  def get_identifier(self) -> line_identifier.AllUnknownIdentifier:
    return line_identifier.AllUnknownIdentifier()
