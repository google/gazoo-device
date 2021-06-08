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

"""adb flavor of file transfer capability."""
import os

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import file_transfer_base
from gazoo_device.utility import adb_utils

logger = gdm_logger.get_logger()


class FileTransferAdb(file_transfer_base.FileTransferBase):
  """adb file transfer capability."""

  def __init__(self, device_name, add_log_note_fn, communication_address):
    """Initialize adb file transfer capability.

    Args:
        device_name (str): name of the device using the capability.
        add_log_note_fn (func): add output to log file.
        communication_address (str): device serial number
    """
    super(FileTransferAdb, self).__init__(device_name=device_name)
    self._add_log_note_fn = add_log_note_fn
    self._communication_address = communication_address

  @decorators.CapabilityLogDecorator(logger)
  def recv_file_from_device(self, src, dest="./"):
    """Copies srcs on device to dest on host.

    Args:
        src (str): file path on device to copy to host.
        dest (str): destination path on host computer.

    Raises:
        DeviceError: if destination directory doesn't exist or copy failed.

    Note:
        If no dest is provided, the file will be copied to the current
        working directory on the host computer.
    """
    destination_dir = os.path.dirname(dest)
    if destination_dir != "." and not os.path.exists(destination_dir):
      raise errors.DeviceError(
          "Device {} receive from device failed. "
          "Destination directory {} doesn't appear to exist.".format(
              self._device_name, destination_dir))

    logger.info("{} receiving from device. Source: {} Destination: {}",
                self._device_name, src, dest)
    self._check_adb_mode(self._communication_address)
    output = adb_utils.pull_from_device(
        self._communication_address, src, destination_path=dest)
    for line in output.splitlines():
      self._add_log_note_fn(line + "\n")
    if not os.path.exists(dest):
      raise errors.DeviceError("Final file {} does not exist".format(dest))

  @decorators.CapabilityLogDecorator(logger)
  def send_file_to_device(self, src, dest):
    """Copies src from host to dest on the device.

    Args:
        src (str): local file path on host computer.
        dest (str): file path on device where the file should be copied to.

    Raises:
        DeviceError: if source file doesn't exist or copy failed.
    """
    if not os.path.exists(src):
      raise errors.DeviceError("Device {} send to device failed. "
                               "Source file {} doesn't appear to exist.".format(
                                   self._device_name, src))

    logger.info("{} sending file(s) to device. Source: {} Destination: {}",
                self._device_name, src, dest)
    self._check_adb_mode(self._communication_address)
    try:
      output = adb_utils.push_to_device(self._communication_address, src, dest)
      for line in output.splitlines():
        self._add_log_note_fn(line + "\n")
    except RuntimeError as err:
      raise errors.DeviceError("Unable to copy {} to {} on device. "
                               "Error: {!r}".format(src, dest, err))

  def _check_adb_mode(self, adb_serial):
    """Checks that the adb serial of the device is available for use.

    Args:
        adb_serial (str): adb serial of the device.

    Raises:
        DeviceError: device is not available in adb device list.
    """
    if not adb_utils.is_adb_mode(adb_serial):
      raise errors.DeviceError(
          "{}'s adb serial {} is not in adb device list.".format(
              self._device_name, adb_serial))
