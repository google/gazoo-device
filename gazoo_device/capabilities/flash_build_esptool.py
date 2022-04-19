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
"""Flashing capability implementation based on Esptool."""

import os
import re
import time
from typing import Callable, Dict, List, NoReturn, Optional

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import flash_build_base
from gazoo_device.capabilities.interfaces import switchboard_base

logger = gdm_logger.get_logger()

# Import path differs for esptool internally and externally.
try:
  # pylint: disable=g-import-not-at-top
  from esptool import esptool
  _ESPTOOL_AVAILABLE = True
except ImportError:
  try:
    # pylint: disable=g-import-not-at-top
    import esptool
    _ESPTOOL_AVAILABLE = True
  except ImportError:
    _ESPTOOL_AVAILABLE = False

_DEFAULT_BOOT_UP_TIMEOUT_SECONDS = 30
_SWITCHBOARD_CAPABILITY = 'switchboard'

# Default flash argumnets used with esptool. For details refer to
# https://docs.espressif.com/projects/esptool/en/latest/esp32/esptool/index.html#esptool-py
_BAUDRATE = 460800
_BEFORE_FLASH = 'default_reset'
_AFTER_FLASH = 'hard_reset'
_FLASH_MODE = 'keep'
_FLASH_FREQ = 'keep'
_FLASH_SIZE = 'detect'
_APPLICATION_OFFSET = 0x20000
_PARTITION_OFFSET = 0x8000
_BOOTLOADER_OFFSET = 0x1000


class FlashBuildEsptool(flash_build_base.FlashBuildBase):
  """Esptool implementation of flash_build capability."""

  def __init__(
      self,
      device_name: str,
      chip_type: str,
      serial_port: str,
      switchboard: Optional[switchboard_base.SwitchboardBase] = None,
      wait_for_bootup_complete_fn: Optional[Callable[[int], None]] = None,
      reset_endpoints_fn: Optional[Callable[[str], None]] = None,
      boot_up_time: int = _DEFAULT_BOOT_UP_TIMEOUT_SECONDS,
      baud: int = _BAUDRATE,
      before: str = _BEFORE_FLASH,
      after: str = _AFTER_FLASH,
      flash_mode: str = _FLASH_MODE,
      flash_freq: str = _FLASH_FREQ,
      flash_size: str = _FLASH_SIZE,
      application_offset: int = _APPLICATION_OFFSET,
      partition_offset: int = _PARTITION_OFFSET,
      bootloader_offset: int = _BOOTLOADER_OFFSET):
    """Initializes an instance of the FlashBuildEsptool capability.

    For details related to before/after flash arguments refer to
      https://docs.espressif.com/projects/esptool/en/latest/esp32/esptool/advanced-options.html#reset-modes
    For details related to flash mode, ferq, size arguments refer to
      https://docs.espressif.com/projects/esptool/en/latest/esp32/esptool/flash-modes.html

    Args:
      device_name: Device name used for logging.
      chip_type: The target device's chip type.
      serial_port: Device serial port.
      switchboard: A Switchboard capability instance if the device supports it.
      wait_for_bootup_complete_fn: The wait_for_bootup_complete method. This
        method will be called after flashing is complete. If not specified,
        time.sleep(boot_up_time) will be used to wait for boot up.
      reset_endpoints_fn: Method to reset matter_endpoint capability.
        This method will be called after flashing is completed.
      boot_up_time: The time to wait for boot up sequence to complete.
      baud: Baudrate for device serial communication.
      before: Action to perform before flashing.
      after: Action to perform after flashing is complete.
      flash_mode: Mode for flashing.
      flash_freq: Clock frequency for SPI flash interactions.
      flash_size: Size of the SPI flash to use.
      application_offset: Memory offset in hex format to flash application
        binary.
      partition_offset: Memory offset in hex format to flash partition-table
        binary.
      bootloader_offset: Memory offset in hex format to flash bootloader binary.

    Raises:
      DependencyUnavailableError: If esptool is not installed.
      ValueError: If chip_type is not supported.
    """
    if not _ESPTOOL_AVAILABLE:
      raise errors.DependencyUnavailableError(
          '"esptool" is not installed. "esptool" is not included due to '
          'licensing restrictions. To enable flashing for this device type, '
          'install "esptool": "pip install esptool>=3.2".')

    if chip_type not in esptool.SUPPORTED_CHIPS:  # pytype: disable=module-attr
      raise ValueError(f'Chip {chip_type} not supported by esptool.')

    super().__init__(device_name=device_name)
    self._serial_port = serial_port
    self._chip_type = chip_type
    self._flash_args = {
        'baud': baud,
        'before': before,
        'after': after,
        'flash_mode': flash_mode,
        'flash_freq': flash_freq,
        'flash_size': flash_size,
        'application_offset': application_offset,
        'partition_offset': partition_offset,
        'bootloader_offset': bootloader_offset,
    }
    self._switchboard = switchboard
    self._wait_for_bootup_complete_fn = wait_for_bootup_complete_fn
    self._reset_endpoints_fn = reset_endpoints_fn
    self._boot_up_time = boot_up_time

  @decorators.CapabilityLogDecorator(logger)
  def _get_write_command_arguments(self, erase: bool = False) -> List[str]:
    """Helper function to get write command arguments.

    For details please refer to
    https://docs.espressif.com/projects/esptool/en/latest/esp32/esptool/scripting.html#embedding-into-custom-scripts

    Args:
      erase: True to use erase-all option when flashing, else False.

    Returns:
      Arguments required for flashing.
    """
    basic_command_args = [
        '--port', self._serial_port, '--baud', self._flash_args['baud'],
        '--chip', self._chip_type, '--before', self._flash_args['before'],
        '--after', self._flash_args['after']
    ]
    write_command_args = [
        'write_flash', '--flash_freq', self._flash_args['flash_freq'],
        '--flash_mode', self._flash_args['flash_mode'], '--flash_size',
        self._flash_args['flash_size'], '--compress'
    ]
    if erase:
      write_command_args.append('--erase-all')
    return basic_command_args + write_command_args

  @decorators.CapabilityLogDecorator(logger)
  def _verify_file(self, image_path: str, ends_with: str = '.bin') -> None:
    """Helper function to validate image file.

    Args:
      image_path: Path to the image file.
      ends_with: Expected image suffix. E.g bootloader files are expected to
        have suffix 'bootloader.bin'.

    Raises:
      ValueError: If the image file suffix does not end with 'ends_with' arg.
      FileNotFoundError: If image file does not exist.
    """
    if not image_path.endswith(ends_with):
      raise ValueError(f'Only {ends_with} type file can be flashed.')
    if not os.path.exists(image_path):
      raise FileNotFoundError(f'Firmware image {image_path} does not exist.')

  @decorators.CapabilityLogDecorator(logger)
  def flash_device(self,
                   list_of_files: List[str],
                   expected_version: Optional[str] = None,
                   expected_build_type: Optional[str] = None,
                   verify_flash: bool = True,
                   method: Optional[str] = None,
                   erase_flash: bool = False) -> None:
    """Flashes the firmware image (.bin file) on the device.

    Args:
      list_of_files: List of image files on local host in following order
        [build_file_name, bootloader_file_name, partition_table_file_name].
      expected_version: Not used.
      expected_build_type: Not used.
      verify_flash: Not used. 'esptool' always verifies flashed image.
      method: Not used.
      erase_flash: True if everything needs to be erased before flashing.

    Raises:
      ValueError: If list of files is empty, all values are None or list length
        is more than 3.
    """
    del expected_version, expected_build_type, verify_flash, method  # Unused.
    if len(list_of_files) != 3:
      raise ValueError('Only application, bootloader, partition table files can'
                       ' be flashed via esptool. If only flashing one type'
                       ' please set others to None.')
    if not any(list_of_files):
      raise ValueError('No firmware files provided to flash the device.')

    command = self._get_write_command_arguments(erase=erase_flash)

    offset_types = [
        'application_offset', 'bootloader_offset', 'partition_offset'
    ]
    ends_with = ['.bin', 'bootloader.bin', 'partition-table.bin']
    for image, offset_type, ends_with in zip(list_of_files, offset_types,
                                             ends_with):
      if image is not None:
        self._verify_file(image, ends_with)
        command += [self._flash_args[offset_type], image]

    command = list(map(str, command))

    # Close serial connection from GDM to avoid conflict with esptool flashing.
    if self._switchboard is not None:
      self._switchboard.close_all_transports()

    logger.info(f'Executing esptool command: {command}')
    esptool.main(command)  # pytype: disable=module-attr

    if self._switchboard is not None:
      self._switchboard.open_all_transports()

    if self._flash_args['after'] == _AFTER_FLASH:
      if self._wait_for_bootup_complete_fn:
        self._wait_for_bootup_complete_fn(self._boot_up_time)
      else:
        time.sleep(self._boot_up_time)

    # For Matter device classes, we'll need to reset the Matter endpoint mapping
    # as the supported endpoints might change after flashing a new build.
    if self._reset_endpoints_fn is not None:
      self._reset_endpoints_fn()

  @decorators.CapabilityLogDecorator(logger)
  def download_build_file(self,
                          remote_build_folder: str,
                          local_folder: str) -> NoReturn:
    """Retrieves the build file(s) from the remote location."""
    del remote_build_folder, local_folder
    raise NotImplementedError(
        'download_build_file is not available in flash_build_esptool for now.')

  @decorators.CapabilityLogDecorator(logger)
  def get_defaults(self) -> NoReturn:
    """Returns a dictionary of default build arguments."""
    raise NotImplementedError(
        'get_defaults is not available in flash_build_esptool for now.')

  @decorators.CapabilityLogDecorator(logger)
  def get_firmware_type(self, build_args: Optional[str] = None) -> str:
    """Returns the firmware type based on the build arguments."""
    del build_args
    return flash_build_base.UNKNOWN

  @decorators.CapabilityLogDecorator(logger)
  def get_firmware_version(self, build_args: Optional[str] = None) -> str:
    """Returns the firmware version based on the build arguments."""
    del build_args
    return flash_build_base.UNKNOWN

  @decorators.CapabilityLogDecorator(logger)
  def get_remote_build_folder(self,
                              build_args: Optional[str] = None) -> NoReturn:
    """Uses the build arguments to determine the remote build folder."""
    raise NotImplementedError('get_remote_build_folder is not available in '
                              'flash_build_esptool for now.')

  @decorators.CapabilityLogDecorator(logger)
  def extract_build_info(self, build_args: Optional[str] = None) -> NoReturn:
    """Converts the provided build arguments into info about the build."""
    raise NotImplementedError(
        'extract_build_info is not available in flash_build_esptool for now.')

  @decorators.CapabilityLogDecorator(logger)
  def latest_verified_build_folder(self) -> NoReturn:
    """Returns the remote build folder path for the latest verified build."""
    raise NotImplementedError(
        'latest_verified_build_folder is not available in '
        'flash_build_esptool for now.')

  @decorators.CapabilityLogDecorator(logger)
  def upgrade(
      self,
      build_number: Optional[int] = None,
      build_url: Optional[str] = None,
      build_file: Optional[str] = None,
      forced_upgrade: bool = False,
      latest_verified: bool = False,
      partition_file: Optional[str] = None,
      bootloader_file: Optional[str] = None,
      erase_flash: bool = False,
      baud: Optional[int] = None,
      before: Optional[str] = None,
      after: Optional[str] = None,
      flash_mode: Optional[str] = None,
      flash_freq: Optional[str] = None,
      flash_size: Optional[str] = None,
      application_offset: Optional[int] = None,
      partition_offset: Optional[int] = None,
      bootloader_offset: Optional[int] = None,
      flash_settings_file: Optional[str] = None,
      **other_build_args: str,
  ) -> None:
    """Upgrade the device based on the provided build arguments.

    For details related to before/after flash arguments refer to
      https://docs.espressif.com/projects/esptool/en/latest/esp32/esptool/advanced-options.html#reset-modes

    For details related to flash mode, ferq, size arguments refer to
      https://docs.espressif.com/projects/esptool/en/latest/esp32/esptool/flash-modes.html#

    Each entry in the partition table file has a name (label), type
    (app, data, or something else), subtype and the offset in flash where the
    partition is loaded. For details refer to
    https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guides/partition-tables.html#partition-tables

    A Bootloader selects and loads application image into RAM. To update the
    device bootloder image please specify a bootloader.bin generated when
    compiling a esp32 project. For details refer to
    https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guides/bootloader.html#bootloader

    Args:
     build_number: Not used.
     build_url: Not used.
     build_file: Local path to the application file.
     forced_upgrade: Not used.
     latest_verified: Not used.
     partition_file: Local path to the partition table file.
     bootloader_file: Local path to the bootloader file.
     erase_flash: True if everything needs to be erased before flashing.
     baud: Baudrate for device serial communication.
     before: Action to perform before flashing.
     after: Action to perform after flashing is complete.
     flash_mode: Mode for flashing.
     flash_freq: Clock frequency for SPI flash interactions.
     flash_size: Size of the SPI flash to use.
     application_offset: Memory offset in hex format to flash application
       binary.
     partition_offset: Memory offset in hex format to flash partition-table
       binary.
     bootloader_offset: Memory offset in hex format to flash bootloader binary.
     flash_settings_file: *.flash.py present when using a matter sample app
       from matter-automation-project. This file will be used to read default
       flash settings. These can be overridden if user explicitly passes them as
       an argument.
     **other_build_args: Not used.
    """
    del build_number, build_url, forced_upgrade, latest_verified  # Unused.
    del other_build_args  # Unused.
    build_args = {
        name: value for name, value in locals().items() if name not in ['self']
    }
    self.upgrade_over_the_wire(**build_args)

  @decorators.CapabilityLogDecorator(logger)
  def upgrade_over_the_wire(self, **build_args: str) -> None:
    """Using the build arguments, flash the build on the device.

    Args:
      **build_args: Dictionary of build arguments.
    """
    list_of_files = [
        build_args['build_file'], build_args['bootloader_file'],
        build_args['partition_file']
    ]

    flash_args_keys = self._flash_args.keys()

    # Update flash arguments from *.flash.py
    if build_args['flash_settings_file']:
      with open(build_args['flash_settings_file']) as settings_file:
        settings = settings_file.read()
        # Regex for flash arguments such as `'flash_freq': '30m',`.
        pattern = re.compile(r"'(\w+)': '(\w+)',", re.MULTILINE | re.ASCII)
        self._flash_args.update({
            match.group(1): match.group(2)
            for match in re.finditer(pattern, settings)
            if match.group(1) in flash_args_keys and match.group(2) is not None
        })

    # Override flash settings with user provided arguments.
    self._flash_args.update({
        build_args_key: build_args_value
        for build_args_key, build_args_value in build_args.items()
        if build_args_key in flash_args_keys and build_args_value is not None
    })

    self.flash_device(
        list_of_files=list_of_files, erase_flash=build_args['erase_flash'])
