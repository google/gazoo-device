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

"""Simplicity commander implementation for flashing EFR32 devices."""
import os
from typing import Callable, Optional

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import flash_build_base
from gazoo_device.capabilities.interfaces import switchboard_base
from gazoo_device.utility import host_utils
from gazoo_device.utility import subprocess_utils


_logger = gdm_logger.get_logger()

# Simplicity commander tool
# https://www.silabs.com/documents/public/user-guides/ug162-simplicity-commander-reference-guide.pdf
_COMMANDER = "commander"
_FLASH_TIMEOUT_S = 180


class FlashBuildCommander(flash_build_base.FlashBuildBase):
  """Commander binary implementation for flashing EFR32 devices."""

  def __init__(
      self,
      device_name: str,
      serial_number: str,
      reset_endpoints_fn: Optional[Callable[[], None]] = None,
      switchboard: Optional[switchboard_base.SwitchboardBase] = None,
      wait_for_bootup_complete_fn: Optional[Callable[[int], None]] = None):
    """Initializes an instance of the FlashBuildCommander capability.

    Args:
      device_name: Device name used for logging.
      serial_number: Device serial number.
      reset_endpoints_fn: Method to reset matter_endpoint capability.
        This method will be called after flashing is completed.
      switchboard: A Switchboard capability instance if the device supports it.
      wait_for_bootup_complete_fn: wait_for_bootup_complete method for verifying
        device responsiveness after flashing.
    """
    super().__init__(device_name=device_name)
    self._serial_number = serial_number
    self._reset_endpoints_fn = reset_endpoints_fn
    self._switchboard = switchboard
    self._wait_for_bootup_complete_fn = wait_for_bootup_complete_fn

  @decorators.CapabilityLogDecorator(_logger, level=None)
  def health_check(self) -> None:
    """Checks whether the 'commander' binary is installed.

    Raises:
      DependencyUnavailableError: 'commander' is not installed.
    """
    if self._healthy is None:
      self._healthy = host_utils.has_command(_COMMANDER)
    if not self._healthy:
      instructions = (
         "follow the instructions at "
         "https://github.com/google/gazoo-device/blob/master/docs/device_setup/EFR32_Matter_sample_app.md")
      raise errors.DependencyUnavailableError(
          f"{_COMMANDER} is not installed. "
          f"To install {_COMMANDER} on the host, {instructions}")

  @decorators.CapabilityLogDecorator(_logger)
  def flash_device(self,
                   list_of_files: list[str],
                   expected_version: Optional[str] = None,
                   expected_build_type: Optional[str] = None,
                   verify_flash: bool = True,
                   method: Optional[str] = None,
                   erase_flash: bool = True) -> None:
    """Flashes the firmware image (.s37 file) on the device.

    Args:
      list_of_files: Image files on local host, currently supports flashing
        only one .s37 file at a time.
      expected_version: Not used.
      expected_build_type: Not used.
      verify_flash: Check if we should verify build after flashing.
      method: Not used.
      erase_flash: True if --masserase is applied during flashing.

    Raises:
      ValueError: If invalid arguments are provided.
      DeviceError: If flashing fails.
    """
    del expected_version, expected_build_type, method  # Unused.

    self.health_check()

    # Check if only one valid .s37 file is given.
    if len(list_of_files) != 1:
      raise ValueError(
          f"{self._device_name} Only one .s37 type file can be flashed. "
          f"Provided list_of_files: {list_of_files}")
    image_path = list_of_files[0]
    if not image_path.endswith(".s37"):
      raise ValueError(
          f"{self._device_name} Only .s37 type file can be flashed. "
          f"Provided image_path: {image_path}")
    if not os.path.exists(image_path):
      raise ValueError(f"Firmware image {image_path} does not exist.")

    if self._switchboard is not None:
      self._switchboard.close_all_transports()
    try:
      return_code, output = self._commander_flash(image_path, erase_flash)
    finally:
      if self._switchboard is not None:
        self._switchboard.open_all_transports()
      if self._reset_endpoints_fn is not None:
        self._reset_endpoints_fn()
      if verify_flash and self._wait_for_bootup_complete_fn is not None:
        self._wait_for_bootup_complete_fn()

    if return_code:
      raise errors.DeviceError(
          f"{self._device_name} flash command with commander failed. "
          f"Return code: {return_code}. Output: {output!r}")

  def _commander_flash(
      self, image_path: str, erase_flash: bool) -> tuple[int, str]:
    """Flashes the device via commander binary."""
    flash_command = [_COMMANDER, "flash", image_path, "--serialno",
                     self._serial_number.lstrip("0")]
    if erase_flash:
      flash_command.append("--masserase")
    return subprocess_utils.run_and_stream_output(
        flash_command, timeout=_FLASH_TIMEOUT_S)

  @decorators.CapabilityLogDecorator(_logger)
  def upgrade(self, build_file: str, erase_flash: bool = True) -> None:
    """Upgrade the device based on the provided build arguments.

    Args:
      build_file: Local path to the file.
      erase_flash: True if --masserase is applied during flashing.
    """
    self.flash_device(list_of_files=[build_file], erase_flash=erase_flash)

  @decorators.CapabilityLogDecorator(_logger)
  def extract_build_info(self, build_args=None):
    """Converts the provided build arguments into info about the build."""
    raise NotImplementedError(
        "extract_build_info is not available in flash_build_commander for now.")
