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

"""Device class for ESP32 Pigweed Echo device."""
from gazoo_device import decorators
from gazoo_device import detect_criteria
from gazoo_device import gdm_logger
from gazoo_device.base_classes import espressif_esp32_device
from gazoo_device.capabilities import pwrpc_echo_default
from gazoo_device.protos import echo_service_pb2
from gazoo_device.switchboard import switchboard
from gazoo_device.utility import pwrpc_utils


logger = gdm_logger.get_logger()


class ESP32PigweedEcho(espressif_esp32_device.EspressifESP32Device):
  """Device class for ESP32PigweedEcho devices.

  This device class is for the Pigweed echo application running on
  the Espressif ESP32 M5Stack platform:
  https://github.com/project-chip/connectedhomeip/tree/master/examples/pigweed-app/esp32
  """
  DETECT_MATCH_CRITERIA = {
      detect_criteria.PigweedQuery.product_name:
          "cp2104 usb to uart bridge controller",
      detect_criteria.PigweedQuery.manufacturer_name: r"silicon(_| )labs",
      detect_criteria.PigweedQuery.app_type:
          pwrpc_utils.PigweedAppType.ECHO.value,
  }
  DEVICE_TYPE = "esp32pigweedecho"
  _OWNER_EMAIL = "gdm-authors@google.com"
  _COMMUNICATION_KWARGS = {"protobufs": (echo_service_pb2,),
                           "baudrate": espressif_esp32_device.BAUDRATE}

  @decorators.DynamicProperty
  def firmware_version(self):
    """Firmware version of the device."""
    return "NOT_IMPLEMENTED"

  @decorators.CapabilityDecorator(pwrpc_echo_default.PwRPCEchoDefault)
  def pw_rpc_echo(self):
    """PwRPCEcho instance to send RPC commands."""
    return self.lazy_init(pwrpc_echo_default.PwRPCEchoDefault,
                          device_name=self.name,
                          switchboard_call=self.switchboard.call)

  @decorators.CapabilityDecorator(switchboard.SwitchboardDefault)
  def switchboard(self):
    """Instance for communicating with the device."""
    name = self._get_private_capability_name(switchboard.SwitchboardDefault)
    if not hasattr(self, name):
      kwargs = self._COMMUNICATION_KWARGS.copy()
      kwargs.update({
          "communication_address": self.communication_address,
          "communication_type": self.COMMUNICATION_TYPE,
          "log_path": self.log_file_name,
          "device_name": self.name,
          "event_parser": None})
      setattr(self, name, self.get_manager().create_switchboard(**kwargs))
    return getattr(self, name)
