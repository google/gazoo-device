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

"""M5stick dev board device class."""
from typing import Any

from gazoo_device import decorators
from gazoo_device import gdm_logger
from gazoo_device import mobly_controller
from gazoo_device import version
from gazoo_device.base_classes import espressif_esp32_device
from gazoo_device.detect_criteria import serial_detect_criteria
from gazoo_device.switchboard import switchboard
from gazoo_device.switchboard.communication_types import serial_comms
import immutabledict

logger = gdm_logger.get_logger()


class M5Stick(espressif_esp32_device.EspressifESP32Device):
  """Device class for M5stick dev board.

  M5StickC is a mini M5Stack, powered by ESP32. It is a portable, easy-to-use,
  open source, IoT development board. https://docs.m5stack.com/en/core/m5stickc
  """
  COMMUNICATION_TYPE = serial_comms.SerialComms
  _COMMUNICATION_KWARGS = immutabledict.immutabledict()
  DETECT_MATCH_CRITERIA = immutabledict.immutabledict({
      serial_detect_criteria.SerialQuery.ADDRESS: r"/dev/serial/by-id/*",
      serial_detect_criteria.SerialQuery.PRODUCT_NAME: "m5stack",
  })
  DEVICE_TYPE = "m5stick"

  @decorators.CapabilityDecorator(switchboard.SwitchboardDefault)
  def switchboard(self):
    """Instance for communicating with the device."""
    switchboard_name = self._get_private_capability_name(
        switchboard.SwitchboardDefault)
    if not hasattr(self, switchboard_name):
      switchboard_kwargs = {
          **self._COMMUNICATION_KWARGS,
          "communication_address": self.communication_address,
          "communication_type": self.COMMUNICATION_TYPE.__name__,
          "log_path": self.log_file_name,
          "device_name": self.name,
          "event_parser": None}
      setattr(self, switchboard_name,
              self.get_manager().create_switchboard(**switchboard_kwargs))

    return getattr(self, switchboard_name)


_DeviceClass = M5Stick
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
          _COMMUNICATION_TYPE: serial_detect_criteria.SERIAL_QUERY_DICT,
      }),
  }

__version__ = version.VERSION
