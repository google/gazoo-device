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

"""Base class module for Espressif ESP32 platform device."""
import os
from typing import Dict, Tuple

from gazoo_device import console_config
from gazoo_device import custom_types
from gazoo_device import decorators
from gazoo_device import gdm_logger
from gazoo_device.base_classes import auxiliary_device
from gazoo_device.capabilities import flash_build_esptool
from gazoo_device.utility import usb_utils

logger = gdm_logger.get_logger()
BAUDRATE = 115200
_DEFAULT_BOOTUP_TIMEOUT_SECONDS = 15
_FLASH_MODE = "dio"
_FLASH_FREQ = "40m"


class EspressifESP32Device(auxiliary_device.AuxiliaryDevice):
  """Base class for Espressif ESP32 platform device.

  ESP32 devices from Espressif which include WiFi and Blutooth LE.
  """
  COMMUNICATION_TYPE = "PigweedSerialComms"
  _COMMUNICATION_KWARGS = {"protobufs": None, "baudrate": BAUDRATE}
  _CHIP_TYPE = "esp32"

  def get_console_configuration(self) -> console_config.ConsoleConfiguration:
    """Returns the interactive console configuration."""
    return console_config.get_log_only_configuration()

  @decorators.LogDecorator(logger)
  def get_detection_info(self) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Gets the persistent and optional attributes of a device during setup.

    Returns:
      Dictionary of persistent attributes and dictionary of
      optional attributes.
    """
    persistent_dict = self.props["persistent_identifiers"]
    address = persistent_dict["console_port_name"]
    persistent_dict["serial_number"] = (
        usb_utils.get_serial_number_from_path(address))
    persistent_dict["model"] = "PROTO"
    return persistent_dict, {}

  @classmethod
  def is_connected(cls,
                   device_config: custom_types.ManagerDeviceConfigDict) -> bool:
    """Returns True if the device is connected to the host."""
    return os.path.exists(device_config["persistent"]["console_port_name"])

  @decorators.PersistentProperty
  def os(self) -> str:
    return "FreeRTOS"

  @decorators.PersistentProperty
  def platform(self) -> str:
    return "ESP32"

  @decorators.CapabilityDecorator(flash_build_esptool.FlashBuildEsptool)
  def flash_build(self):
    """FlashBuildEsptool capability to flash bin image."""
    return self.lazy_init(
        flash_build_esptool.FlashBuildEsptool,
        device_name=self.name,
        chip_type=self._CHIP_TYPE,
        serial_port=self.communication_address,
        boot_up_time=_DEFAULT_BOOTUP_TIMEOUT_SECONDS,
        baud=BAUDRATE,
        flash_mode=_FLASH_MODE,
        flash_freq=_FLASH_FREQ)
