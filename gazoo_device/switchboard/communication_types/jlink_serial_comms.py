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
"""Communication type for JLINK and UART communication simultaneously."""
from gazoo_device.switchboard import line_identifier
from gazoo_device.switchboard.communication_types import base_comms
from gazoo_device.switchboard.transports import jlink_transport
from gazoo_device.switchboard.transports import serial_transport
from gazoo_device.switchboard.transports import transport_base
from gazoo_device.utility import usb_utils


class JlinkSerialComms(base_comms.CommunicationType):
  """Communication type for JLINK and UART communication simultaneously.

  Serial is used for primary communication while jlink is used for log
  streaming.
  """

  @classmethod
  def get_comms_addresses(cls):
    # To only detect NRF OpenThread boards for this communication type to avoid
    # the overlap with PigweedSerialComms, which uses the same J-Link detection
    # criteria.
    include_product = [base_comms.JLINK_COMMS_PRODUCT_NAME]
    include_address = [
        base_comms.NRF_DK_COMMS_ADDRESS_LINUX,
        base_comms.NRF_DK_EFR32_COMMS_ADDRESS_MAC,
    ]
    match_criteria = {
        "product_name": {
            "include_regex": "|".join(include_product)
        },
        "address": {
            "include_regex": "|".join(include_address)
        },
        "ftdi_interface": {
            "include_regex": "0"
        }
    }
    return base_comms.get_specific_serial_addresses(match_criteria)

  def __init__(
      self,
      comms_address: str,
      baudrate: int = 115200,
      enable_jlink: bool = True) -> None:
    super().__init__(comms_address)
    self.secondary_address = usb_utils.get_serial_number_from_path(
        comms_address)
    self.baudrate = baudrate
    self.enable_jlink = enable_jlink

  def get_transport_list(self) -> list[transport_base.TransportBase]:
    transports = [
        serial_transport.SerialTransport(
            comms_address=self.comms_address, baudrate=self.baudrate)]
    if self.enable_jlink:
      transports.append(
          jlink_transport.JLinkTransport(
              comms_address=self.secondary_address))
    return transports

  def get_identifier(self) -> line_identifier.PortLogIdentifier:  # pytype: disable=signature-mismatch  # overriding-return-type-checks
    return line_identifier.PortLogIdentifier()
