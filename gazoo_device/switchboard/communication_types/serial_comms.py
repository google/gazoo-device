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
"""Communication type for device communication over basic serial."""
from collections.abc import Sequence
import dataclasses
from typing import Optional, Union

from gazoo_device import data_types
from gazoo_device.switchboard import line_identifier
from gazoo_device.switchboard.communication_types import base_comms
from gazoo_device.switchboard.transports import serial_transport
from gazoo_device.switchboard.transports import ssh_transport
from gazoo_device.utility import host_utils


@dataclasses.dataclass(frozen=True)
class SshLogConfig:
  """Configuration for an SSH logging channel."""

  log_cmd: Sequence[str]
  args: Sequence[str] = host_utils.DEFAULT_SSH_OPTIONS
  key_info: Optional[data_types.KeyInfo] = None
  username: str = "root"


class SerialComms(base_comms.CommunicationType):
  """Communication type for device communication over basic serial."""

  def __init__(
      self,
      comms_address: str,
      log_line_regex: Optional[str] = None,
      baudrate: int = serial_transport.DEFAULT_BAUDRATE,
      ssh_log_configs: Sequence[SshLogConfig] = (),
      ip_address: str = "",
  ):

    super().__init__(comms_address)
    self.log_line_regex = log_line_regex
    self.baudrate = baudrate
    self.ip_address = ip_address
    self.ssh_log_configs = list(ssh_log_configs)

  @classmethod
  def get_comms_addresses(cls) -> list[str]:
    exclude_products = [
        base_comms.JLINK_COMMS_PRODUCT_NAME,
    ]
    exclude_product_ids = [
    ]

    match_criteria = {
        "product_name": {
            "exclude_regex": "|".join(exclude_products)
        },
        "product_id": {
            "exclude_regex": "|".join(exclude_product_ids)
        },
        "ftdi_interface": {
            "include_regex": "0|1"
        }
    }
    return base_comms.get_specific_serial_addresses(match_criteria)

  def get_transport_list(
      self,
  ) -> list[serial_transport.SerialTransport | ssh_transport.SSHTransport]:
    primary_transport = serial_transport.SerialTransport(
        comms_address=self.comms_address, baudrate=self.baudrate
    )
    ssh_transports = [
        ssh_transport.SSHTransport(
            comms_address=self.ip_address,
            args=ssh_config.args,
            username=ssh_config.username,
            key_info=ssh_config.key_info,
            log_cmd=ssh_config.log_cmd,
        )
        for ssh_config in self.ssh_log_configs
    ]
    return [primary_transport] + ssh_transports

  def get_identifier(  # pytype: disable=signature-mismatch  # overriding-return-type-checks
      self,
  ) -> Union[
      line_identifier.AllUnknownIdentifier,
      line_identifier.RegexLogIdentifier,
      line_identifier.PortLogIdentifier,
      line_identifier.MultiportIdentifier,
  ]:
    if self.ssh_log_configs:
      if self.log_line_regex:
        identifiers = [line_identifier.RegexLogIdentifier(self.log_line_regex)]
        identifiers.extend(
            [line_identifier.AllLogIdentifier()] * len(self.ssh_log_configs)
        )
        return line_identifier.MultiportIdentifier(identifiers)
      else:
        log_ports = list(range(1, 1 + len(self.ssh_log_configs)))
        return line_identifier.PortLogIdentifier(log_ports=log_ports)
    if self.log_line_regex:
      return line_identifier.RegexLogIdentifier(self.log_line_regex)
    return super().get_identifier()
