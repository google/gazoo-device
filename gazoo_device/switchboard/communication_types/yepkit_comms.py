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
"""Communication type for yepkit devices."""
from gazoo_device.switchboard.communication_types import base_comms
from gazoo_device.switchboard.transports import transport_base
from gazoo_device.utility import host_utils


class YepkitComms(base_comms.CommunicationType):
  """Communication type for yepkit devices.

  Currently supports just detection as communication does not yet work as
  expected.
  """

  @classmethod
  def get_comms_addresses(cls) -> list[str]:
    return host_utils.get_all_yepkit_serials()

  def get_transport_list(self) -> list[transport_base.TransportBase]:
    return []
