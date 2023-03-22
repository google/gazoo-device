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
from typing import Callable, List, Optional, Tuple

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
      wait_for_bootup_complete_fn: Optional[Callable[[int], None]] = None,
      power_cycle_fn: Optional[Callable[[], None]] = None):
    """Initializes an instance of the FlashBuildNrfjprog capability.

    Args:
      device_name: Device name used for logging.
      serial_number: Device serial number.
      reset_endpoints_fn: Method to reset matter_endpoint capability.
        This method will be called after flashing is completed.
      switchboard: A Switchboard capability instance if the device supports it.
      wait_for_bootup_complete_fn: wait_for_bootup_complete method for verifying
        device responsiveness after flashing.
      power_cycle_fn: Method to power cycle the device.
    """
    super().__init__(device_name=device_name)
    self._serial_number = serial_number
    self._reset_endpoints_fn = reset_endpoints_fn
    self._switchboard = switchboard
    self._wait_for_bootup_complete_fn = wait_for_bootup_complete_fn
    self._power_cycle_fn = power_cycle_fn
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

    if self._power_cycle_fn is None:
      raise errors.DeviceError(
          f"{self._device_name} no power cycle method provided. Please unplug "
          "and replug the USB connection of the board manually.")

    # Try power cycling the device if it's connected to cambrionix.
    try:
      self._power_cycle_fn()
    except errors.CapabilityNotReadyError as err:
      raise errors.DeviceError(
          f"{self._device_name} cannot be powered cycle: {err}. Please unplug "
          "and replug the USB connection of the board manually.")

    self._msd_disabled = True

  @decorators.CapabilityLogDecorator(logger)
  def flash_device(self,
                   list_of_files: List[str],
                   expected_version: Optional[str] = None,
                   expected_build_type: Optional[str] = None,
                   verify_flash: bool = True,
                   method: Optional[str] = None) -> None:
    """Flashes the firmware image (.hex file) on the device.

    Args:
      list_of_files: Image files on local host, currently supports flashing
        only one hex file at a time.
      expected_version: Not used.
      expected_build_type: Not used.
      verify_flash: Check if we should verify build after flashing.
      method: Not used.

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

    if self._switchboard is not None:
      self._switchboard.close_all_transports()
    try:
      # Always recover the device before flashing to avoid flakiness
      self.recover_device()
      return_code, output = self._nrfjprog_flash(image_path)
    finally:
      if self._switchboard is not None:
        self._switchboard.open_all_transports()
      if self._reset_endpoints_fn is not None:
        self._reset_endpoints_fn()
      if verify_flash and self._wait_for_bootup_complete_fn is not None:
        self._wait_for_bootup_complete_fn()

    if return_code:
      raise errors.DeviceError(
          f"{self._device_name} flash command with binary flasher failed. "
          f"Return code: {return_code}. Output: {output!r}")

  def _nrfjprog_flash(self, image_path: str) -> Tuple[int, str]:
    """Flashes the device via nrfjprog binary if it is present."""
    snr = self._serial_number.lstrip("0")
    flash_command = (
        f"{_NRFJPROG} -f nrf52 --program {image_path} --chiperase -s {snr} "
        "--reset --verify --log nrfjprog_flashing_log.log")
    return subprocess_utils.run_and_stream_output(
        flash_command.split(), timeout=_FLASH_TIMEOUT_S)

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
  def upgrade(self, build_file: str):
    """Upgrade the device based on the provided build arguments.

    Args:
      build_file: Local path to the file.
    """
    self.flash_device(list_of_files=[build_file])

  @decorators.CapabilityLogDecorator(logger)
  def extract_build_info(self, *args, **kwargs):
    """Converts the provided build arguments into info about the build."""
    raise NotImplementedError(
        "extract_build_info is not available in flash_build_nrfjprog for now.")
