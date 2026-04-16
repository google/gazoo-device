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

"""Nrfjprog binary implementation for flashing NRF devices."""
import os
import tempfile
from typing import Callable, Optional

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import flash_build_base
from gazoo_device.capabilities.interfaces import switchboard_base
from gazoo_device.utility import host_utils
from gazoo_device.utility import subprocess_utils


logger = gdm_logger.get_logger()

# NRF command line tools
# https://www.nordicsemi.com/Products/Development-tools/nrf-command-line-tools
_NRFJPROG = "nrfjprog"
_FLASH_TIMEOUT_S = 180
_JLINK_EXE = "JLinkExe"


class FlashBuildNrfjprog(flash_build_base.FlashBuildBase):
  """Nrfjprog binary implementation for flashing NRF devices."""

  def __init__(
      self,
      device_name: str,
      serial_number: str,
      reset_endpoints_fn: Optional[Callable[[], None]] = None,
      switchboard: Optional[switchboard_base.SwitchboardBase] = None,
      wait_for_bootup_complete_fn: Optional[Callable[[int], None]] = None):
    """Initializes an instance of the FlashBuildNrfjprog capability.

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
    self._msd_disabled = False

  @decorators.CapabilityLogDecorator(logger, level=None)
  def health_check(self) -> None:
    """Checks whether the 'nrfjprog' binary is installed.

    Raises:
      DependencyUnavailableError: 'nrfjprog' is not installed.
    """
    if self._healthy is None:
      self._healthy = host_utils.has_command(_NRFJPROG)
    if not self._healthy:
      raise errors.DependencyUnavailableError(
          f"{_NRFJPROG} is not installed. Install the binary on the host from "
          "https://www.nordicsemi.com/Products/Development-tools/"
          "nrf-command-line-tools/download")
    self._disable_msd()

  def _disable_msd(self) -> None:
    """Disables the Mass Storage Device on host.

    Due to a known issue in Segger J-Link firmware, data corruption or drops
    will occur if using serial ports with packets larger than 64 bytes.
    Multiple RPC failures are also observed with this issue: b/255635727,
    b/261901521 and b/261846864.

    Disabling the MSD setting on host can fix this issue suggested by Segger:
    https://docs.zephyrproject.org/3.0.0/guides/tools/nordic_segger.html#disabling-the-mass-storage-device-functionality
    """
    if self._msd_disabled:
      return

    if not host_utils.has_command(_JLINK_EXE):
      raise errors.DependencyUnavailableError(
          f"{_JLINK_EXE} is not installed. Install the binary on the host from "
          "https://www.nordicsemi.com/Products/Development-tools/"
          "nrf-command-line-tools/download")

    # Create a jlink script for disabling MSD.
    with tempfile.TemporaryDirectory() as temp_directory:
      jlink_script = os.path.join(temp_directory, "msd.jlink")
      with open(jlink_script, "w") as f:
        f.write("MSDDisable\nExit\n")
      serial_number = self._serial_number.lstrip("0")
      return_code, output = subprocess_utils.run_and_stream_output(
          [_JLINK_EXE, "-CommandFile", jlink_script, "-USB", serial_number],
          timeout=5)
      if return_code:
        raise errors.DeviceError(
            f"{self._device_name} failed to disable the MSD setting. "
            f"Script return code: {return_code}, output: {output}")
    self._msd_disabled = True

  @decorators.CapabilityLogDecorator(logger)
  def flash_device(self,
                   list_of_files: list[str],
                   expected_version: Optional[str] = None,
                   expected_build_type: Optional[str] = None,
                   verify_flash: bool = True,
                   method: Optional[str] = None,
                   erase_flash: bool = True) -> None:
    """Flashes the firmware image (.hex file) on the device.

    Args:
      list_of_files: Image files on local host, currently supports flashing
        only one hex file at a time.
      expected_version: Not used.
      expected_build_type: Not used.
      verify_flash: Check if we should verify build after flashing.
      method: Not used.
      erase_flash: True if --chiperase is applied during flashing.

    Raises:
      ValueError: If invalid arguments are provided.
      DeviceError: If flashing fails.
      DependencyUnavailableError: If J-Link SDK is not installed.
    """
    del expected_version, expected_build_type, method  # Unused.

    self.health_check()

    # Check if only one valid hex file is given.
    if len(list_of_files) != 1:
      raise ValueError("Only one hex file can be flashed via JLink.")
    image_path = list_of_files[0]
    if not image_path.endswith(".hex"):
      raise ValueError("Only hex type file can be flashed.")
    if not os.path.exists(image_path):
      raise ValueError(f"Firmware image {image_path} does not exist.")

    return_code = 0
    output = ""
    if self._switchboard is not None:
      self._switchboard.close_all_transports()
    try:
      # Recover the device before flashing to avoid flakiness.
      # This must be skipped if we set erase_flash = False so we don't erase
      # the commissioning state after flashing b/278786037
      if erase_flash:
        self.recover_device()
      return_code, output = self._nrfjprog_flash(image_path, erase_flash)
    finally:
      if self._switchboard is not None:
        self._switchboard.open_all_transports()
      if self._reset_endpoints_fn is not None:
        self._reset_endpoints_fn()
      if return_code:
        raise errors.DeviceError(
            f"{self._device_name} flash command with binary flasher failed. "
            f"Return code: {return_code}. Output: {output!r}")
      if verify_flash and self._wait_for_bootup_complete_fn is not None:
        self._wait_for_bootup_complete_fn()

  def _nrfjprog_flash(
      self, image_path: str, erase_flash: bool) -> tuple[int, str]:
    """Flashes the device via nrfjprog binary if it is present.

    To program a memory area, it must be erased first otherwise programming will
    fail.
    --chiperase: Erases all of the user non-volatile memory, including the UICR.
    --sectorerase: Erases only the targeted non-volatile memory pages,
      excluding the UICR.

    Args:
      image_path: Path for image file (*.hex).
      erase_flash: If True --chiperase is applied during flashing else
        --sectorerase is used.

    Returns:
      Tuple of (return code, string output)
    """
    snr = self._serial_number.lstrip("0")
    flash_command = [
        _NRFJPROG, "-f", "nrf52", "--program", image_path, "-s", snr, "--reset",
        "--verify"]
    if erase_flash:
      flash_command.append("--chiperase")
    else:
      flash_command.append("--sectorerase")
    return subprocess_utils.run_and_stream_output(
        flash_command, timeout=_FLASH_TIMEOUT_S)

  @decorators.CapabilityLogDecorator(logger)
  def recover_device(self) -> None:
    """Recovers the device by erasing all user available non-volatile memory."""
    self.health_check()

    serial_number = self._serial_number.lstrip("0")
    return_code, output = subprocess_utils.run_and_stream_output(
        [_NRFJPROG, "--family", "NRF52", "--recover", "--snr", serial_number],
        timeout=_FLASH_TIMEOUT_S)
    if return_code:
      raise errors.DeviceError(
          f"Failed to recover the device {serial_number}: {output}.")

  @decorators.CapabilityLogDecorator(logger)
  def upgrade(self, build_file: str, erase_flash: bool = True) -> None:
    """Upgrade the device based on the provided build arguments.

    Args:
      build_file: Local path to the file.
      erase_flash: True if --chiperase is applied during flashing.
    """
    self.flash_device(list_of_files=[build_file], erase_flash=erase_flash)

  @decorators.CapabilityLogDecorator(logger)
  def extract_build_info(self, *args, **kwargs):
    """Converts the provided build arguments into info about the build."""
    raise NotImplementedError(
        "extract_build_info is not available in flash_build_nrfjprog for now.")
