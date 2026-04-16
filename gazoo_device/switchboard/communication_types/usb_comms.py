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
"""Communication type for USB devices which don't leverage switchboard."""
from gazoo_device.switchboard.communication_types import base_comms
from gazoo_device.switchboard.transports import transport_base
from gazoo_device.utility import usb_utils


class UsbComms(base_comms.CommunicationType):
  """Communication type for USB devices which don't leverage switchboard."""

  @classmethod
  def get_comms_addresses(cls) -> list[str]:
    devices = usb_utils.get_usb_devices_having_a_serial_number()
    return [d.serial_number for d in devices]

  def get_transport_list(self) -> list[transport_base.TransportBase]:
    return []

