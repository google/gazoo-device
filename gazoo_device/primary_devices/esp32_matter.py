# Copyright 2024 Google LLC
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
from typing import Any

from gazoo_device import decorators
from gazoo_device import gdm_logger
from gazoo_device import mobly_controller
from gazoo_device import version
from gazoo_device.base_classes import matter_device_base
from gazoo_device.capabilities import flash_build_esptool
from gazoo_device.capabilities import pwrpc_wifi_default
from gazoo_device.capabilities.interfaces import matter_controller_base
from gazoo_device.capabilities.matter_clusters.interfaces import measurement_base
from gazoo_device.capabilities.matter_clusters.interfaces import switch_base
from gazoo_device.detect_criteria import pigweed_detect_criteria
import immutabledict

logger = gdm_logger.get_logger()

_BAUDRATE = 115200
_CHIP_TYPE = "esp32"
_DEFAULT_BOOTUP_TIMEOUT_SECONDS = 15
_FLASH_MODE = "dio"
_FLASH_FREQ = "40m"


class Esp32Matter(matter_device_base.MatterDeviceBase):
  """ESP32 Matter device controller."""
  DETECT_MATCH_CRITERIA = immutabledict.immutabledict({
      pigweed_detect_criteria.PigweedQuery.IS_MATTER: True,
      pigweed_detect_criteria.PigweedQuery.MANUFACTURER_NAME:
      # CH9102F model has an empty string for MANUFACTURER_NAME
          r"(silicon(_| )labs|1a86|)",
      pigweed_detect_criteria.PigweedQuery.PRODUCT_NAME:
          r"(cp2104 usb to uart bridge controller|usb single serial)",
  })
  # Button definition on ESP32 M5Stack dev board:
  # 0 --> Left button on M5Stack, Button 1
  # 1 --> Middle button on M5Stack, Button 2
  # 2 --> Right button on M5Stack, Button 3
  VALID_BUTTON_IDS = (0, 1, 2)

  DEVICE_TYPE = "esp32matter"

  MATTER_COMMISSION_METHOD = matter_controller_base.CommissionMethod.BLE_WIFI

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


_DeviceClass = Esp32Matter
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
      "primary_devices": [_DeviceClass],
      "detect_criteria": immutabledict.immutabledict({
          _COMMUNICATION_TYPE: pigweed_detect_criteria.PIGWEED_QUERY_DICT,
      }),
      "capability_interfaces": [
          # Overrides for the implicit export logic.
          # MeasurementClusterBase is an interface. It is not abstract and
          # defines public attributes, so the implicit export logic considers
          # it a flavor by default.
          # This is to resolve b/322915885.
          measurement_base.MeasurementClusterBase,
          switch_base.SwitchClusterBase,
      ],
  }

__version__ = version.VERSION
