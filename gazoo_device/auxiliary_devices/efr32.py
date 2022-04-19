# Copyright 2022 Google LLC
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

"""EFR32 dev board device class."""
from gazoo_device import detect_criteria
from gazoo_device.base_classes import silabs_efr32_device


class EFR32(silabs_efr32_device.SilabsEFR32Device):
  """Base Class for EFR32 Devices.

  EFR32MG which includes Zigbee and Thread software stacks to serve as a
  CHIP-compliant device, see more details in
  https://www.silabs.com/documents/public/user-guides/ug342-brd4170a-user-guide.pdf
  """
  DETECT_MATCH_CRITERIA = {
      detect_criteria.PigweedQuery.IS_MATTER: False,
      detect_criteria.PigweedQuery.MANUFACTURER_NAME: r"silicon(_| )labs",
      detect_criteria.PigweedQuery.PRODUCT_NAME: "j-link",
  }
  DEVICE_TYPE = "efr32"
  _OWNER_EMAIL = "gdm-authors@google.com"

