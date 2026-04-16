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
"""Communication type for devices communicating over ADB."""
from typing import Sequence, TypeAlias
from gazoo_device.switchboard import line_identifier
from gazoo_device.switchboard.communication_types import base_comms
from gazoo_device.switchboard.transports import adb_transport
from gazoo_device.switchboard.transports import serial_transport
from gazoo_device.switchboard.transports import transport_base
from gazoo_device.utility import adb_utils

LogCommandType: TypeAlias = Sequence[str]


class AdbComms(base_comms.CommunicationType):
  """Communication type for devices communicating over ADB.

  Commands/responses go over port 0. Logs are streamed over port 1 and
  above if there are any additional ADB or serial log transports.
  """

  def __init__(
      self,
      comms_address: str,
      log_cmd: LogCommandType = ("logcat", "-v", "threadtime"),
      shell_cmd: LogCommandType = ("shell",),
      additional_log_cmds: Sequence[LogCommandType] | None = None,
      additional_serial_log_configs: (
          Sequence[serial_transport.SerialTransportConfig] | None
      ) = None,
  ) -> None:
    super().__init__(comms_address)
    self.log_cmd = log_cmd
    self.shell_cmd = shell_cmd
    self.additional_log_cmds = additional_log_cmds or ()
    self.additional_serial_log_configs = additional_serial_log_configs or ()

  @classmethod
  def get_comms_addresses(cls) -> list[str]:
    """Returns ADB identifiers of available ADB devices."""
    return adb_utils.get_adb_devices()

  def get_transport_list(self) -> list[transport_base.TransportBase]:
    default_transports = [
        adb_transport.AdbTransport(
            comms_address=self.comms_address, command=self.shell_cmd
        ),
        adb_transport.AdbTransport(
            comms_address=self.comms_address, command=self.log_cmd
        ),
    ]

    additional_log_transports = [
        adb_transport.AdbTransport(
            comms_address=self.comms_address, command=command
        )
        for command in self.additional_log_cmds
    ]

    serial_log_transports = [
        serial_transport.SerialTransport(
            comms_address=config.communication_address,
            baudrate=config.baudrate,
        )
        for config in self.additional_serial_log_configs
    ]

    return (
        default_transports + additional_log_transports + serial_log_transports
    )

  def get_identifier(self) -> line_identifier.LineIdentifier:  # pytype: disable=signature-mismatch  # overriding-return-type-checks
    log_ports = list(range(1, len(self.get_transport_list())))
    return line_identifier.PortLogIdentifier(log_ports=log_ports)
