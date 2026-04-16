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
"""Communication type for device communication over Pigweed RPC socket."""
import types
from typing import Collection, Optional, Sequence
from gazoo_device import data_types
from gazoo_device.switchboard import line_identifier
from gazoo_device.switchboard.communication_types import ssh_comms
from gazoo_device.switchboard.transports import pigweed_rpc_transport
from gazoo_device.switchboard.transports import transport_base
from gazoo_device.utility import host_utils
from gazoo_device.utility import pwrpc_utils


class PigweedSocketComms(ssh_comms.SshComms):
  """Communication type for device communication over Pigweed RPC socket."""

  def __init__(self,
               comms_address: str,
               protobufs: Collection[types.ModuleType],
               port: int = pwrpc_utils.MATTER_LINUX_APP_DEFAULT_PORT,
               log_cmd: Sequence[str] = ("tail", "-F", "-n",
                                         "/var/log/messages"),
               args: Sequence[str] = host_utils.DEFAULT_SSH_OPTIONS,
               key_info: Optional[data_types.KeyInfo] = None,
               username: str = "ubuntu") -> None:
    super().__init__(comms_address, log_cmd, args, key_info, username)
    self.protobufs = protobufs
    self.port = port

  def get_transport_list(self) -> list[transport_base.TransportBase]:  # pytype: disable=signature-mismatch  # overriding-return-type-checks
    """Transports for Pigweed Socket communication types.

    Port 0 and port 1 are SSHTransport, port 2 is PigweedRpcSocketTransport.

    Returns:
      The list of supported transports.
    """
    transport_list = super().get_transport_list()
    protobuf_import_paths = [module.__name__ for module in self.protobufs]
    rpc_socket_transport = pigweed_rpc_transport.PigweedRpcSocketTransport(
        comms_address=self.comms_address,
        protobuf_import_paths=protobuf_import_paths,
        port=self.port)
    transport_list.append(rpc_socket_transport)
    return transport_list

  def get_identifier(self) -> line_identifier.PortLogIdentifier:
    return line_identifier.PortLogIdentifier(log_ports=[1, 2])
