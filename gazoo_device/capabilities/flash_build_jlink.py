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
from typing import Callable, Dict, List, Optional

from gazoo_device import config
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import flash_build_base
from gazoo_device.capabilities.interfaces import switchboard_base
from gazoo_device.switchboard.transports import pigweed_rpc_transport
from gazoo_device.utility import retry
from gazoo_device.utility import subprocess_utils
import intelhex
import pylink

logger = gdm_logger.get_logger()
UNKNOWN = flash_build_base.UNKNOWN
_FLASH_TIMEOUT_S = 60
_JLINK_NO_DLL_ERROR = "Expected to be given a valid DLL."
_RPC_DEVICE_SERVICE_NAME = "Device"
_RPC_GET_DEVICE_INFO_NAME = "GetDeviceInfo"
_RPC_TIMEOUT_S = 1


class FlashBuildJLink(flash_build_base.FlashBuildBase):
  """J-Link implementation of flash_build capability."""

  def __init__(self,
               device_name: str,
               serial_number: int,
               platform_name: str,
               reset_endpoints_fn: Optional[Callable[[str], None]] = None,
               switchboard: Optional[switchboard_base.SwitchboardBase] = None):
    """Initializes an instance of the FlashBuildJLink capability.

    Args:
      device_name: Device name used for logging.
      serial_number: Device serial number.
      platform_name: The target device's platform name.
      reset_endpoints_fn: Method to reset matter_endpoint capability.
        This method will be called after flashing is completed.
      switchboard: A Switchboard capability instance if the device supports it.
    """
    super().__init__(device_name=device_name)
    self._serial_number = serial_number
    self._platform_name = platform_name
    self._reset_endpoints_fn = reset_endpoints_fn
    self._switchboard = switchboard

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

    self._jlink_flash(image_path)

    # For Matter device classes, we'll need to reset the Matter endpoint mapping
    # as the supported endpoints might change after flashing a new build.
    if self._reset_endpoints_fn is not None:
      self._reset_endpoints_fn()
    if verify_flash:
      self._poll_until_device_is_ready()

  def _poll_until_device_is_ready(self) -> None:
    """Polls the device until it's responsive to the RPCs."""
    # No need to poll if it's not a Matter device.
    if self._switchboard is None:
      return

    def is_ack_true(rpc_response):
      ack, _ = rpc_response
      return ack

    switchboard_kwargs = {
        "method": pigweed_rpc_transport.PigweedRPCTransport.rpc,
        "method_args": (_RPC_DEVICE_SERVICE_NAME, _RPC_GET_DEVICE_INFO_NAME),
        "method_kwargs": {"pw_rpc_timeout_s": _RPC_TIMEOUT_S}}
    retry.retry(
        func=self._switchboard.call,
        func_kwargs=switchboard_kwargs,
        is_successful=is_ack_true,
        reraise=False)

  def _jlink_flash(self, image_path: str) -> None:
    """Flashes the provided image onto the device via J-Link."""
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

    jlink.open(serial_no=self._serial_number)
    jlink.set_tif(pylink.enums.JLinkInterfaces.SWD)
    jlink.connect(chip_name=self._platform_name, speed="auto")
    jlink.halt()

    image = intelhex.IntelHex(os.path.abspath(image_path))
    for segment_start, segment_end in image.segments():
      segment_size = segment_end - segment_start
      segment = image.tobinarray(start=segment_start, size=segment_size)
      jlink.flash_write8(segment_start, segment)

    jlink.reset()
    jlink.restart()
    jlink.close()

  @decorators.CapabilityLogDecorator(logger)
  def download_build_file(self, remote_build_folder, local_folder):
    """Retrieves the build file(s) from the remote location."""
    raise NotImplementedError(
        "download_build_file is not available in flash_build_jlink for now.")

  @decorators.CapabilityLogDecorator(logger)
  def get_defaults(self):
    """Returns a dictionary of default build arguments."""
    raise NotImplementedError(
        "get_defaults is not available in flash_build_jlink for now.")

  @decorators.CapabilityLogDecorator(logger)
  def get_firmware_type(self, build_args=None):
    """Returns the firmware type based on the build arguments."""
    return UNKNOWN

  @decorators.CapabilityLogDecorator(logger)
  def get_firmware_version(self, build_args=None):
    """Returns the firmware version based on the build arguments."""
    return UNKNOWN

  @decorators.CapabilityLogDecorator(logger)
  def get_remote_build_folder(self, build_args=None):
    """Uses the build arguments to determine the remote build folder."""
    raise NotImplementedError(
        "get_remote_build_folder is not available in "
        "flash_build_jlink for now.")

  @decorators.CapabilityLogDecorator(logger)
  def extract_build_info(self, build_args=None):
    """Converts the provided build arguments into info about the build."""
    raise NotImplementedError(
        "extract_build_info is not available in flash_build_jlink for now.")

  @decorators.CapabilityLogDecorator(logger)
  def latest_verified_build_folder(self):
    """Returns the remote build folder path for the latest verified build."""
    raise NotImplementedError(
        "latest_verified_build_folder is not available in "
        "flash_build_jlink for now.")

  @decorators.CapabilityLogDecorator(logger)
  def upgrade(self,
              build_number: Optional[int] = None,
              build_url: Optional[str] = None,
              build_file: Optional[str] = None,
              forced_upgrade: bool = False,
              latest_verified: bool = False,
              **other_build_args: Dict[str, str]):
    """Upgrade the device based on the provided build arguments.

    Args:
     build_number: Not used.
     build_url: Not used.
     build_file: Local path to the file.
     forced_upgrade: Not used.
     latest_verified: Not used.
     **other_build_args: Not used.
    """
    del build_number, build_url, forced_upgrade, latest_verified  # Unused.
    del other_build_args  # Unused.
    build_args = {"build_file": build_file}
    self.upgrade_over_the_wire(**build_args)

  @decorators.CapabilityLogDecorator(logger)
  def upgrade_over_the_wire(self, **build_args: Dict[str, str]):
    """Using the build arguments, flash the build on the device.

    Args:
      **build_args: Dictionary of build arguments.
    """
    self.flash_device(list_of_files=[build_args["build_file"]])
