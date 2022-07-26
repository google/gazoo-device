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

"""M5stick dev board device class."""

from gazoo_device import decorators
from gazoo_device import detect_criteria
from gazoo_device import gdm_logger
from gazoo_device.base_classes import espressif_esp32_device
from gazoo_device.switchboard import switchboard

logger = gdm_logger.get_logger()


class M5Stick(espressif_esp32_device.EspressifESP32Device):
  """Device class for M5stick dev board.

  M5StickC is a mini M5Stack, powered by ESP32. It is a portable, easy-to-use,
  open source, IoT development board. https://docs.m5stack.com/en/core/m5stickc
  """
  COMMUNICATION_TYPE = "SerialComms"
  _COMMUNICATION_KWARGS = {}
  DETECT_MATCH_CRITERIA = {
      detect_criteria.SerialQuery.ADDRESS: r"/dev/serial/by-id/*",
      detect_criteria.SerialQuery.PRODUCT_NAME: "m5stack",
  }
  DEVICE_TYPE = "m5stick"
  _OWNER_EMAIL = "gdm-authors@google.com"

  @decorators.CapabilityDecorator(switchboard.SwitchboardDefault)
  def switchboard(self):
    """Instance for communicating with the device."""
    switchboard_name = self._get_private_capability_name(
        switchboard.SwitchboardDefault)
    if not hasattr(self, switchboard_name):
      switchboard_kwargs = self._COMMUNICATION_KWARGS.copy()
      switchboard_kwargs.update({
          "communication_address": self.communication_address,
          "communication_type": self.COMMUNICATION_TYPE,
          "log_path": self.log_file_name,
          "device_name": self.name,
          "event_parser": None})
      setattr(self, switchboard_name,
              self.get_manager().create_switchboard(**switchboard_kwargs))

    return getattr(self, switchboard_name)
