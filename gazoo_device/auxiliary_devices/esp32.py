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

"""ESP32 dev board device class."""
from gazoo_device import detect_criteria
from gazoo_device.base_classes import espressif_esp32_device


class ESP32(espressif_esp32_device.EspressifESP32Device):
  """Base Class for ESP32 Devices.

  ESP32 which includes Zigbee, WiFi and BLE to serve as a CHIP-compliant device,
  see more details in https://www.espressif.com/en/products/socs/esp32.
  """
  DETECT_MATCH_CRITERIA = {
      detect_criteria.PigweedQuery.IS_MATTER: False,
      detect_criteria.PigweedQuery.MANUFACTURER_NAME:
          r"(silicon(_| )labs|1a86)",
      detect_criteria.PigweedQuery.PRODUCT_NAME:
          r"(cp2104 usb to uart bridge controller|usb single serial)",
  }
  DEVICE_TYPE = "esp32"
  _OWNER_EMAIL = "gdm-authors@google.com"
