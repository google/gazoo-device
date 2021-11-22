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

"""Device class for ESP32 M5Stack locking device."""
from gazoo_device import decorators
from gazoo_device import detect_criteria
from gazoo_device import gdm_logger
from gazoo_device.base_classes import esp32_matter_device
from gazoo_device.capabilities import pwrpc_lock_default
from gazoo_device.protos import device_service_pb2
from gazoo_device.protos import locking_service_pb2
from gazoo_device.utility import pwrpc_utils

logger = gdm_logger.get_logger()
_LOCK_RPC_TIMEOUT = 5  # seconds


class Esp32MatterLocking(esp32_matter_device.Esp32MatterDevice):
  """Device class for Esp32MatterLocking devices.

  Matter locking application running on the Espressif ESP32 M5Stack platform:
  https://github.com/project-chip/connectedhomeip/tree/master/examples/lock-app/esp32
  """
  DETECT_MATCH_CRITERIA = {
      detect_criteria.PigweedQuery.product_name:
          "cp2104 usb to uart bridge controller",
      detect_criteria.PigweedQuery.manufacturer_name: r"silicon(_| )labs",
      detect_criteria.PigweedQuery.app_type:
          pwrpc_utils.PigweedAppType.LOCKING.value,
  }
  DEVICE_TYPE = "esp32matterlocking"
  _OWNER_EMAIL = "gdm-authors@google.com"
  _COMMUNICATION_KWARGS = {"protobufs": (locking_service_pb2,
                                         device_service_pb2,),
                           "baudrate": esp32_matter_device.BAUDRATE}

  @decorators.CapabilityDecorator(pwrpc_lock_default.PwRPCLockDefault)
  def pw_rpc_lock(self):
    """PwRPCLock instance to send RPC commands."""
    return self.lazy_init(
        pwrpc_lock_default.PwRPCLockDefault,
        device_name=self.name,
        switchboard_call=self.switchboard.call,
        rpc_timeout_s=_LOCK_RPC_TIMEOUT)
