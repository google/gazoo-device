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

"""nRF52840 platform device class."""
from gazoo_device import detect_criteria
from gazoo_device.base_classes import nrf_connect_sdk_device


class NRF52840(nrf_connect_sdk_device.NRFConnectSDKDevice):
  """Base Class for NRF52840 Devices.

  Nordic nRF Connect SDK allows to build a range of applications
  for different CHIP stacks, see more details in
  https://github.com/project-chip/connectedhomeip/blob/master/docs/guides/nrfconnect_platform_overview.md
  """
  DETECT_MATCH_CRITERIA = {
      detect_criteria.PigweedQuery.IS_MATTER: False,
      detect_criteria.PigweedQuery.MANUFACTURER_NAME: "segger",
      detect_criteria.PigweedQuery.PRODUCT_NAME: "j-link",
  }
  DEVICE_TYPE = "nrf52840"
  _OWNER_EMAIL = "gdm-authors@google.com"
