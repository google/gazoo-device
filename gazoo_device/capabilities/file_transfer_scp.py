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

"""scp flavor of file transfer capability (for devices using SSH transports)."""
import os.path
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import file_transfer_base
from gazoo_device.utility import host_utils

logger = gdm_logger.get_logger()


class FileTransferScp(file_transfer_base.FileTransferBase):
  """scp-based file or folder transfer capability."""

  def __init__(self,
               ip_address_or_fn,
               device_name,
               add_log_note_fn,
               user="root",
               key_info=None):
    """Initialize scp file or folder transfer capability.

    Args:
        ip_address_or_fn (str or callable): IP address of the device, or a
          callable which returns the IP address.
        device_name (str): name of the device using the capability.
        add_log_note_fn (func): add output to log file.
        user (str): username which scp should use.
        key_info (data_types.KeyInfo): SSH key to use.
    """
    super(FileTransferScp, self).__init__(device_name=device_name)

    self._ip_address_or_fn = ip_address_or_fn
    self._user = user
    self._key_info = key_info
    self._add_log_note_fn = add_log_note_fn

  @decorators.CapabilityLogDecorator(logger)
  def recv_file_from_device(self, src, dest="./"):
    """Copies srcs on device to dest on host.

    Args:
        src (str): file or folder path on device to copy to host.
        dest (str): destination path on host computer.

    Raises:
        DeviceError: if destination directory doesn't exist or copy failed.

    Note:
        If no dest is provided, the file will be copied to the current
        working directory on the host computer.
    """
    dest_dir = os.path.dirname(dest)
    if dest_dir != "." and not os.path.exists(dest_dir):
      raise errors.DeviceError(
          "Device {} receive from device failed. "
          "Destination directory {} doesn't appear to exist.".format(
              self._device_name, dest_dir))
    ip_address = self._get_valid_ip_address()
    logger.info("%s receiving from device. Source(s): %s Destination: %s",
                self._device_name, src, dest)
    try:
      output = host_utils.scp_from_device(
          ip_address,
          dest,
          src,
          user=self._user,
          key_info=self._key_info)
      for line in output.splitlines():
        self._add_log_note_fn(line + "\n")

      if not os.path.exists(dest):
        raise RuntimeError("Final file {} does not exist".format(dest))

    except RuntimeError as err:
      raise errors.DeviceError("Device {} receiving from device failed. "
                               "Unable to copy {} on device to {}. "
                               "Error: {!r}".format(self._device_name, src,
                                                    dest, err))

  @decorators.CapabilityLogDecorator(logger)
  def send_file_to_device(self, src, dest):
    """Copies src from host to dest on the device.

    Args:
        src (str): local file or folder path on host computer.
        dest (str): file path on device where the file should be copied to.

    Raises:
        DeviceError: if source file doesn't exist or copy failed.
    """
    if not os.path.exists(src):
      raise errors.DeviceError("Device {} send to device failed. "
                               "Source file {} doesn't appear to exist.".format(
                                   self._device_name, src))
    ip_address = self._get_valid_ip_address()
    logger.info(
        "{} sending file to device. Source: {}, destination: {}.".format(
            self._device_name, src, dest))
    try:
      output = host_utils.scp_to_device(
          ip_address,
          src,
          dest,
          user=self._user,
          key_info=self._key_info)
      for line in output.splitlines():
        self._add_log_note_fn(line + "\n")

    except RuntimeError as err:
      raise errors.DeviceError("Device {} send to device failed. "
                               "Unable to copy {} to {} on device. "
                               "Error: {!r}".format(self._device_name, src,
                                                    dest, err))

  def _check_ip_address_valid(self, ip_address):
    """Checks that the IP address of the device is valid (non-empty and pingable).

    Args:
        ip_address (str): IP address of the device.

    Raises:
        DeviceError: device has no IP address, or the IP address is not
        pingable.
    """
    if not ip_address:
      raise errors.DeviceError(
          f"{self._device_name} does not have an IPv4 address. "
          "An IPv4 address is required for file transfer functionality.")
    if not host_utils.is_pingable(ip_address):
      raise errors.DeviceError("{}'s IP address {} is not pingable.".format(
          self._device_name, ip_address))

  def _get_valid_ip_address(self):
    """Returns a valid IP address (non-empty and pingable)."""
    ip_address = self._ip_address_or_fn
    if callable(self._ip_address_or_fn):
      ip_address = self._ip_address_or_fn()
    self._check_ip_address_valid(ip_address)
    return ip_address
