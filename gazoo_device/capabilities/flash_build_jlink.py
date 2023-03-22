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

"""Default implementation of the JLink flashing capability."""
import os
from typing import Callable, List, NoReturn, Optional, Tuple

from gazoo_device import config
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import flash_build_base
from gazoo_device.capabilities.interfaces import switchboard_base
from gazoo_device.utility import subprocess_utils
import immutabledict
import intelhex
import pylink

logger = gdm_logger.get_logger()
UNKNOWN = flash_build_base.UNKNOWN
_FLASH_TIMEOUT_S = 180
_JLINK_NO_DLL_ERROR = "Expected to be given a valid DLL."


class FlashBuildJLink(flash_build_base.FlashBuildBase):
  """J-Link implementation of flash_build capability."""

  def __init__(
      self,
      device_name: str,
      serial_number: str,
      platform_name: str,
      reset_endpoints_fn: Optional[Callable[[], None]] = None,
      switchboard: Optional[switchboard_base.SwitchboardBase] = None,
      wait_for_bootup_complete_fn: Optional[Callable[[], None]] = None):
    """Initializes an instance of the FlashBuildJLink capability.

    Args:
      device_name: Device name used for logging.
      serial_number: Device serial number.
      platform_name: The target device's platform name.
      reset_endpoints_fn: Method to reset matter_endpoint capability.
        This method will be called after flashing is completed.
      switchboard: A Switchboard capability instance if the device supports it.
      wait_for_bootup_complete_fn: wait_for_bootup_complete method for verifying
        device responsiveness after flashing.
    """
    super().__init__(device_name=device_name)
    self._serial_number = serial_number
    self._platform_name = platform_name
    self._reset_endpoints_fn = reset_endpoints_fn
    self._switchboard = switchboard
    self._wait_for_bootup_complete_fn = wait_for_bootup_complete_fn
    self._flash_method_map = immutabledict.immutabledict({
        False: self._flash_device,
    })

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
    if len(list_of_files) != 1:
      raise ValueError("Only one hex file can be flashed via JLink.")
    image_path = list_of_files[0]
    if not image_path.endswith(".hex"):
      raise ValueError("Only hex type file can be flashed.")
    if not os.path.exists(image_path):
      raise ValueError(f"Firmware image {image_path} does not exist.")

    flash_method_key = False
    flash_method = self._flash_method_map[flash_method_key]
    flash_method(image_path, verify_flash)

  def _flash_device(self, image_path: str, verify_flash: bool) -> None:
    """Flashes device via pylink module."""
    try:
      jlink = pylink.JLink()
    except TypeError as e:
      if _JLINK_NO_DLL_ERROR in str(e):
        raise errors.DependencyUnavailableError(
            "No J-Link DLL found. Install the J-Link SDK from "
            "https://www.segger.com/downloads/jlink/#J-LinkSoftwareAndDocumentationPack. "
            f"Error: {e!r}.")
      else:
        raise

    self._pre_flashing(jlink)
    self._flash_image(jlink, image_path)
    self._post_flashing(jlink)

    # For Matter device classes, we'll need to reset the Matter endpoint mapping
    # as the supported endpoints might change after flashing a new build.
    if self._reset_endpoints_fn is not None:
      self._reset_endpoints_fn()
    if verify_flash and self._wait_for_bootup_complete_fn is not None:
      self._wait_for_bootup_complete_fn()

  def _pre_flashing(self, jlink: pylink.jlink.JLink) -> None:
    """Opens Jlink connection and connects to the board."""
    jlink.open(serial_no=self._serial_number)
    jlink.set_tif(pylink.enums.JLinkInterfaces.SWD)
    jlink.connect(chip_name=self._platform_name, speed="auto")
    jlink.halt()

  def _post_flashing(self, jlink: pylink.jlink.JLink) -> None:
    """Resets and closes the Jlink connection."""
    jlink.reset()
    jlink.restart()
    jlink.close()

  def _flash_image(self, jlink: pylink.jlink.JLink, image_path: str) -> None:
    """Flashes image onto the board."""
    image = intelhex.IntelHex(os.path.abspath(image_path))
    # Find the first segment
    segment_start, _ = image.segments()[0]
    jlink.flash_file(image_path, segment_start)

  @decorators.CapabilityLogDecorator(logger)
  def extract_build_info(self, *args, **kwargs) -> NoReturn:
    """Converts the provided build arguments into info about the build."""
    raise NotImplementedError(
        "extract_build_info is not available in flash_build_jlink for now.")

  @decorators.CapabilityLogDecorator(logger)
  def upgrade(self, build_file: str) -> None:
    """Upgrade the device based on the provided build arguments.

    Args:
      build_file: Local path to the file.
    """
    self.flash_device(list_of_files=[build_file])
