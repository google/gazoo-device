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

"""Default implementation of the fastboot capability."""
import time
from typing import Callable, Dict, Optional

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import fastboot_base
from gazoo_device.utility import adb_utils
from gazoo_device.utility import common_utils

logger = gdm_logger.get_logger()

_REQUIRED_TIMEOUTS = ("ONLINE",)


class FastbootDefault(fastboot_base.FastbootBase):
  """Fastboot capability."""

  def __init__(self,
               device_name: str,
               communication_address: str,
               fastboot_serial: str,
               timeouts_dict: Dict[str, float],
               add_log_note_fn: Callable[[str], None],
               verify_reboot_fn: Callable[[], None],
               root_device_fn: Callable[[], None]) -> None:
    """Initializes the FastbootDefault capability.

    Args:
      device_name: Name of the device using the capability.
      communication_address: The device ADB serial.
      fastboot_serial: The device fastboot serial.
      timeouts_dict: Dictionary of timeouts.
      add_log_note_fn: Function to add output to log file.
      verify_reboot_fn: Function to wait for the device to boot up.
      root_device_fn: Function to root the device if not rooted.
    """
    super().__init__(device_name=device_name)
    self._communication_address = communication_address
    self._fastboot_serial = fastboot_serial
    self._timeouts_dict = timeouts_dict
    self._add_log_note_fn = add_log_note_fn
    self._verify_reboot_fn = verify_reboot_fn
    self._root_device_fn = root_device_fn

    self.validate_required_keys(_REQUIRED_TIMEOUTS, self._timeouts_dict,
                                "timeouts_dict")

  @decorators.CapabilityLogDecorator(logger)
  def enter(self) -> None:
    """Enters fastboot (bootloader) mode for updating device firmware.

    Raises:
      DeviceError: If unable to boot device into fastboot mode.
    """
    if self._is_in_fastboot_mode():
      return

    output = adb_utils.enter_fastboot(self._communication_address)
    for line in output.splitlines():
      self._add_log_note_fn(line + "\n")

    if not self._is_in_fastboot_mode(timeout=self._timeouts_dict["ONLINE"]):
      raise errors.DeviceError(
          "{} failed to enter fastboot mode in {}s.".format(
              self._device_name, self._timeouts_dict["ONLINE"]))

  @decorators.CapabilityLogDecorator(logger)
  def exit(self) -> None:
    """Exits fastboot (bootloader) mode after updating device firmware.

    Raises:
      DeviceError: If unable to reboot device out of fastboot mode.
    """
    if not adb_utils.is_fastboot_mode(self._fastboot_serial):
      return

    self._add_log_note_fn("GDM triggered reboot via 'fastboot reboot'")
    start_time = time.time()
    output = adb_utils.exit_fastboot(self._fastboot_serial)
    if output:
      for line in output.splitlines():
        self._add_log_note_fn(line + "\n")
      logger.info("{} fastboot reboot took {}s.", self._device_name,
                  time.time() - start_time)
    self._verify_reboot_fn()
    self._root_device_fn()

  def _is_in_fastboot_mode(self, timeout: Optional[float] = None) -> bool:
    """Returns if device in fastboot mode.

    Waits up to timeout time. We try to verify whether the device is in fastboot
    mode in the {timeout} duration, with retry interval 0.5 sec. If timeout is
    None (not provided), there will be no retry.

    Args:
      timeout: Maximum wait time in seconds. If timeout is None, we will not
        retry.

    Returns:
      Whether device is in fastboot mode.
    """
    # No retry when timeout is None. Setting timeout to 0.1 is equivalent to
    # "no retry" since interval is 0.5 sec.
    timeout = timeout or 0.1

    try:
      common_utils.retry(
          adb_utils.is_fastboot_mode,
          func_args=(self._fastboot_serial,),
          is_successful=bool,
          timeout=timeout,
          interval=0.5)
      logger.info("{} is in fastboot mode.", self._device_name)
      return True
    except errors.CommunicationTimeoutError:
      return False
