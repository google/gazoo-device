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
from typing import Any

from gazoo_device import mobly_controller
from gazoo_device import version
from gazoo_device.base_classes import espressif_esp32_device
from gazoo_device.detect_criteria import pigweed_detect_criteria
import immutabledict


class ESP32(espressif_esp32_device.EspressifESP32Device):
  """Base Class for ESP32 Devices.

  ESP32 which includes Zigbee, WiFi and BLE to serve as a CHIP-compliant device,
  see more details in https://www.espressif.com/en/products/socs/esp32.
  """
  DETECT_MATCH_CRITERIA = immutabledict.immutabledict({
      pigweed_detect_criteria.PigweedQuery.IS_MATTER: False,
      pigweed_detect_criteria.PigweedQuery.MANUFACTURER_NAME:
      # CH9102F model has an empty string for MANUFACTURER_NAME
          r"(silicon(_| )labs|1a86|)",
      pigweed_detect_criteria.PigweedQuery.PRODUCT_NAME:
          r"(cp2104 usb to uart bridge controller|usb single serial)",
  })
  DEVICE_TYPE = "esp32"


_DeviceClass = ESP32
_COMMUNICATION_TYPE = _DeviceClass.COMMUNICATION_TYPE.__name__
# For Mobly controller integration.
MOBLY_CONTROLLER_CONFIG_NAME = (
    mobly_controller.get_mobly_controller_config_name(_DeviceClass.DEVICE_TYPE))
create = mobly_controller.create
destroy = mobly_controller.destroy
get_info = mobly_controller.get_info
get_manager = mobly_controller.get_manager


def export_extensions() -> dict[str, Any]:
  """Exports device class and capabilities to act as a GDM extension package."""
  return {
      "auxiliary_devices": [_DeviceClass],
      "detect_criteria": immutabledict.immutabledict({
          _COMMUNICATION_TYPE: pigweed_detect_criteria.PIGWEED_QUERY_DICT,
      }),
  }

__version__ = version.VERSION
