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

"""Device controller for ESP32 Matter device.

This device controller populates the supported Matter endpoints on the ESP32
platform by using the descriptor RPC service.
"""
from gazoo_device import decorators
from gazoo_device import detect_criteria
from gazoo_device import gdm_logger
from gazoo_device.base_classes import matter_device_base
from gazoo_device.capabilities import flash_build_esptool
from gazoo_device.capabilities import pwrpc_wifi_default

logger = gdm_logger.get_logger()

_BAUDRATE = 115200
_CHIP_TYPE = "esp32"
_DEFAULT_BOOTUP_TIMEOUT_SECONDS = 15
_FLASH_MODE = "dio"
_FLASH_FREQ = "40m"


class Esp32Matter(matter_device_base.MatterDeviceBase):
  """ESP32 Matter device controller."""
  DETECT_MATCH_CRITERIA = {
      detect_criteria.PigweedQuery.IS_MATTER: True,
      detect_criteria.PigweedQuery.MANUFACTURER_NAME:
          r"(silicon(_| )labs|1a86)",
      detect_criteria.PigweedQuery.PRODUCT_NAME:
          r"(cp2104 usb to uart bridge controller|usb single serial)",
  }
  # Button definition on ESP32 M5Stack dev board:
  # 0 --> Left button on M5Stack, Button 1
  # 1 --> Middle button on M5Stack, Button 2
  # 2 --> Right button on M5Stack, Button 3
  VALID_BUTTON_IDS = (0, 1, 2)

  DEVICE_TYPE = "esp32matter"

  @decorators.PersistentProperty
  def os(self) -> str:
    """OS of ESP32 platform."""
    return "FreeRTOS"

  @decorators.PersistentProperty
  def platform(self) -> str:
    """ESP32 platform."""
    return "ESP32"

  @decorators.CapabilityDecorator(pwrpc_wifi_default.PwRPCWifiDefault)
  def pw_rpc_wifi(self):
    """PwRPCWifi capability to send RPC commands."""
    return self.lazy_init(
        pwrpc_wifi_default.PwRPCWifiDefault,
        device_name=self.name,
        switchboard_call=self.switchboard.call)

  @decorators.CapabilityDecorator(flash_build_esptool.FlashBuildEsptool)
  def flash_build(self):
    """FlashBuildEsptool capability to flash bin image."""
    return self.lazy_init(
        flash_build_esptool.FlashBuildEsptool,
        device_name=self.name,
        chip_type=_CHIP_TYPE,
        serial_port=self.communication_address,
        switchboard=self.switchboard,
        wait_for_bootup_complete_fn=self.wait_for_bootup_complete,
        reset_endpoints_fn=self.matter_endpoints.reset,
        boot_up_time=_DEFAULT_BOOTUP_TIMEOUT_SECONDS,
        baud=_BAUDRATE,
        flash_mode=_FLASH_MODE,
        flash_freq=_FLASH_FREQ)
