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
"""Communication type for device communication over Pigweed RPC serial."""
import types
from typing import Collection
from gazoo_device.switchboard import line_identifier
from gazoo_device.switchboard.communication_types import base_comms
from gazoo_device.switchboard.transports import pigweed_rpc_transport
from gazoo_device.switchboard.transports import serial_transport
from gazoo_device.switchboard.transports import transport_base


CP2104_COMMS_PRODUCT_NAME = "CP2104"
USB_COMMS_PRODUCT_NAME = "USB Single Serial"
EFR32_COMMS_ADDRESS_LINUX = "Silicon_Labs_J-Link"
ESP32_M5STACK_CP2104_COMMS_ADDRESS_LINUX = "Silicon_Labs_CP2104"
ESP32_M5STACK_CP2104_COMMS_ADDRESS_MAC = "tty.usbserial"
ESP32_M5STACK_CH9102F_COMMS_ADDRESS_LINUX = "1a86_USB_Single_Serial"


class PigweedSerialComms(base_comms.CommunicationType):
  """Communication type for device communication over Pigweed RPC serial."""

  @classmethod
  def get_comms_addresses(cls) -> list[str]:
    include_product = [
        base_comms.JLINK_COMMS_PRODUCT_NAME, CP2104_COMMS_PRODUCT_NAME,
        USB_COMMS_PRODUCT_NAME]
    include_address = [
        base_comms.NRF_DK_COMMS_ADDRESS_LINUX,
        base_comms.NRF_DK_EFR32_COMMS_ADDRESS_MAC,
        EFR32_COMMS_ADDRESS_LINUX, ESP32_M5STACK_CP2104_COMMS_ADDRESS_LINUX,
        ESP32_M5STACK_CP2104_COMMS_ADDRESS_MAC,
        ESP32_M5STACK_CH9102F_COMMS_ADDRESS_LINUX
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

  def __init__(self,
               comms_address: str,
               protobufs: Collection[types.ModuleType],
               baudrate: int = serial_transport.DEFAULT_BAUDRATE):
    super().__init__(comms_address)
    self.protobufs = protobufs
    self.baudrate = baudrate

  def get_transport_list(self) -> list[transport_base.TransportBase]:
    protobuf_import_paths = [module.__name__ for module in self.protobufs]
    return [
        pigweed_rpc_transport.PigweedRpcSerialTransport(
            comms_address=self.comms_address,
            protobuf_import_paths=protobuf_import_paths,
            baudrate=self.baudrate)
    ]

  def get_identifier(self) -> line_identifier.AllLogIdentifier:  # pytype: disable=signature-mismatch  # overriding-return-type-checks
    return line_identifier.AllLogIdentifier()

