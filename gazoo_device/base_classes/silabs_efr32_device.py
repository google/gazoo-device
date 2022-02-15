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

"""Base class module for Silabs EFR32 platform device."""
import os
from typing import Dict, Tuple

from gazoo_device import console_config
from gazoo_device import custom_types
from gazoo_device import decorators
from gazoo_device import gdm_logger
from gazoo_device.base_classes import auxiliary_device
from gazoo_device.capabilities import flash_build_jlink
from gazoo_device.utility import usb_utils

logger = gdm_logger.get_logger()
BAUDRATE = 115200
_EFR32_JLINK_NAME = "EFR32MG12PXXXF1024"


class SilabsEFR32Device(auxiliary_device.AuxiliaryDevice):
  """Base class for Silabs EFR32MG platform device.

  EFR32MG devices from Silabs which include Zigbee and Thread software stacks.
  """
  COMMUNICATION_TYPE = "PigweedSerialComms"
  _COMMUNICATION_KWARGS = {"protobufs": None, "baudrate": BAUDRATE}

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
    return "EFR32MG"

  @decorators.CapabilityDecorator(flash_build_jlink.FlashBuildJLink)
  def flash_build(self):
    return self.lazy_init(flash_build_jlink.FlashBuildJLink,
                          device_name=self.name,
                          serial_number=self.serial_number,
                          platform_name=_EFR32_JLINK_NAME)
