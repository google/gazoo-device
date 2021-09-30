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
from gazoo_device.capabilities import pwrpc_common_default
from gazoo_device.capabilities import pwrpc_lock_default
from gazoo_device.protos import device_service_pb2
from gazoo_device.protos import locking_service_pb2
from gazoo_device.utility import pwrpc_utils
import immutabledict


logger = gdm_logger.get_logger()
_LOCK_SERVICE_REGEXES = immutabledict.immutabledict({
    pwrpc_lock_default.LockedState.LOCKED: "Lock Action has been completed",
    pwrpc_lock_default.LockedState.UNLOCKED:
        "Unlock Action has been completed"})
_REGEXES = {"FACTORY_RESET": r"lock-app: App Task started",}
_RPC_TIMEOUT = 10  # seconds
_BOOTUP_TIMEOUT = 10  # seconds


class ESP32PigweedLocking(espressif_esp32_device.EspressifESP32Device):
  """Device class for ESP32PigweedLocking devices.

  This device class is for the Pigweed locking application running on
  the Espressif ESP32 M5Stack platform:
  https://github.com/project-chip/connectedhomeip/tree/master/examples/lock-app/esp32
  """
  DETECT_MATCH_CRITERIA = {
      detect_criteria.PigweedQuery.product_name:
          "cp2104 usb to uart bridge controller",
      detect_criteria.PigweedQuery.manufacturer_name: r"silicon(_| )labs",
      detect_criteria.PigweedQuery.app_type:
          pwrpc_utils.PigweedAppType.LOCKING.value,
  }
  DEVICE_TYPE = "esp32pigweedlocking"
  _OWNER_EMAIL = "gdm-authors@google.com"
  _COMMUNICATION_KWARGS = {"protobufs": (locking_service_pb2,
                                         device_service_pb2,),
                           "baudrate": espressif_esp32_device.BAUDRATE}

  def __init__(self,
               manager,
               device_config,
               log_file_name=None,
               log_directory=None):
    super().__init__(
        manager,
        device_config,
        log_file_name=log_file_name,
        log_directory=log_directory)
    self._regexes.update(_REGEXES)

  @decorators.DynamicProperty
  def firmware_version(self) -> str:
    """Firmware version of the device."""
    return str(self.pw_rpc_common.software_version)

  @decorators.LogDecorator(logger)
  def reboot(self, no_wait: bool = True) -> None:
    """Reboots the device.

    The no_wait default value is set to True since the reboot method of ESP32
    locking app doesn't have log lines: b/193478488.

    Args:
      no_wait: Return before reboot completes.
    """
    self.pw_rpc_common.reboot(no_wait=no_wait,
                              rpc_timeout_s=_RPC_TIMEOUT)

  @decorators.LogDecorator(logger)
  def factory_reset(self, no_wait: bool = False) -> None:
    """Factory resets the device.

    Args:
      no_wait: Return before factory_reset completes.
    """
    self.pw_rpc_common.factory_reset(
        no_wait=no_wait,
        rpc_timeout_s=_RPC_TIMEOUT,
        bootup_logline_regex=self.regexes["FACTORY_RESET"],
        bootup_timeout=_BOOTUP_TIMEOUT)

  @decorators.CapabilityDecorator(pwrpc_common_default.PwRPCCommonDefault)
  def pw_rpc_common(self):
    """PwRPCCommonDefault capability to send RPC commands."""
    return self.lazy_init(
        pwrpc_common_default.PwRPCCommonDefault,
        device_name=self.name,
        switchboard_call=self.switchboard.call,
        switchboard_call_expect=self.switchboard.call_and_expect)

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
