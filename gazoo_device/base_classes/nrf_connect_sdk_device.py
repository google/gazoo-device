# Copyright 2021 Google LLC
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

"""Base class module for nRF Connect SDK platform device."""
import os
from typing import Dict, Tuple

from gazoo_device import custom_types
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.base_classes import auxiliary_device
from gazoo_device.capabilities import flash_build_jlink
from gazoo_device.switchboard import switchboard
from gazoo_device.utility import usb_utils

logger = gdm_logger.get_logger()
BAUDRATE = 115200
_NRF_JLINK_NAME = "NRF52840_XXAA"


class NRFConnectSDKDevice(auxiliary_device.AuxiliaryDevice):
  """Base class for nRF Connect SDK devices.

  nRF Connect SDK devices from Nordic which runs Zephyr RTOS.
  """
  COMMUNICATION_TYPE = "PigweedSerialComms"
  _COMMUNICATION_KWARGS = {"protobufs": None, "baudrate": BAUDRATE}

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
    return "Zephyr RTOS"

  @decorators.PersistentProperty
  def platform(self) -> str:
    return "nRF Connect"

  @decorators.CapabilityDecorator(switchboard.SwitchboardDefault)
  def switchboard(self):
    """Instance for communicating with the device."""
    if self._COMMUNICATION_KWARGS.get("protobufs") is None:
      raise errors.DeviceError(
          "Calling switchboard from a non Pigweed device {}".format(self.name))
    name = self._get_private_capability_name(switchboard.SwitchboardDefault)
    if not hasattr(self, name):
      kwargs = self._COMMUNICATION_KWARGS.copy()
      kwargs.update({
          "communication_address": self.communication_address,
          "communication_type": self.COMMUNICATION_TYPE,
          "log_path": self.log_file_name,
          "device_name": self.name,
          "event_parser": None})
      setattr(self, name, self.manager_weakref().create_switchboard(**kwargs))
    return getattr(self, name)

  @decorators.CapabilityDecorator(flash_build_jlink.FlashBuildJLink)
  def flash_build(self):
    return self.lazy_init(flash_build_jlink.FlashBuildJLink,
                          device_name=self.name,
                          serial_number=self.serial_number,
                          platform_name=_NRF_JLINK_NAME)
