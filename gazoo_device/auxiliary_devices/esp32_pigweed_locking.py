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

"""Device class for ESP32 locking device."""
from gazoo_device import decorators
from gazoo_device import detect_criteria
from gazoo_device import gdm_logger
from gazoo_device.base_classes import espressif_esp32_device
from gazoo_device.capabilities import pwrpc_lock_default
from gazoo_device.protos import locking_service_pb2
from gazoo_device.utility import pwrpc_utils
import immutabledict


logger = gdm_logger.get_logger()
_LOCK_SERVICE_REGEXES = immutabledict.immutabledict({
    pwrpc_lock_default.LockedState.LOCKED: "Lock Action has been completed",
    pwrpc_lock_default.LockedState.UNLOCKED:
        "Unlock Action has been completed"})
_RPC_TIMEOUT = 10  # seconds


class ESP32PigweedLocking(espressif_esp32_device.EspressifESP32Device):
  """Device class for ESP32PigweedLocking devices.

  This device class is for the Pigweed locking application running on
  the Espressif ESP32 M5Stack platform:
  https://github.com/project-chip/connectedhomeip/tree/master/examples/lock-app/esp32
  """
  DETECT_MATCH_CRITERIA = {
      detect_criteria.PigweedQuery.product_name:
          "cp2104 usb to uart bridge controller",
      detect_criteria.PigweedQuery.manufacturer_name: "silicon_labs",
      detect_criteria.PigweedQuery.app_type:
          pwrpc_utils.PigweedAppType.LOCKING.value,
  }
  DEVICE_TYPE = "esp32pigweedlocking"
  _OWNER_EMAIL = "gdm-authors@google.com"
  _COMMUNICATION_KWARGS = {"protobufs": (locking_service_pb2,),
                           "baudrate": espressif_esp32_device.BAUDRATE}

  @decorators.DynamicProperty
  def firmware_version(self):
    """Firmware version of the device."""
    # TODO(b/193478488) Add pwrpc_common capability.
    return "NOT_IMPLEMENTED"

  @decorators.CapabilityDecorator(pwrpc_lock_default.PwRPCLockDefault)
  def pw_rpc_lock(self):
    """PwRPCLock instance to send RPC commands."""
    return self.lazy_init(
        pwrpc_lock_default.PwRPCLockDefault,
        device_name=self.name,
        expect_locking_regexes=_LOCK_SERVICE_REGEXES,
        expect_timeout=_RPC_TIMEOUT,
        switchboard_call=self.switchboard.call,
        switchboard_call_expect=self.switchboard.call_and_expect)
