# Copyright 2020 Google LLC
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

"""echo flavor of file transfer capability."""
from __future__ import absolute_import
import base64
import os

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import file_transfer_base

logger = gdm_logger.get_gdm_logger()


class FileTransferEcho(file_transfer_base.FileTransferBase):
    """echo file transfer capability."""
    _REQUIRED_COMMANDS = ["ECHO_FILE_IN_BASE64", "IS_DIRECTORY"]

    def __init__(self,
                 device_name,
                 command_dict,
                 shell_fn,
                 echo_file_to_transport_fn,
                 send_tries=1):
        """Initialize echo file transfer capability.

        Args:
            device_name (str): name of the device using the capability.
            command_dict (dict): A dictionary containing the commands used by the capability.
            shell_fn (func): The function that can be called to send a shell command to the device.
            echo_file_to_transport_fn(func): streams file to device in chunks and writes it to
                                             source file on device.
            send_tries (int): number of times to try the file transfer process.
        """
        super(FileTransferEcho, self).__init__(device_name=device_name)
        self._command_dict = command_dict
        self._shell_fn = shell_fn
        self._send_tries = send_tries
        self._echo_file_to_transport_fn = echo_file_to_transport_fn

        self.validate_required_keys(self._REQUIRED_COMMANDS, self._command_dict, "command_dict")

    @decorators.CapabilityLogDecorator(logger)
    def recv_file_from_device(self, src, dest="./"):
        """Copies srcs on device to dest on host.

        Args:
            src (str): file path on device to copy to host.
            dest (str): destination path on host computer.

        Raises:
            GazooDeviceError: if destination directory doesn't exist or copy failed.

        Note:
            If no dest is provided, the file will be copied to the current working directory
            on the host computer.
        """
        destination_dir = os.path.dirname(dest)
        if destination_dir != "." and not os.path.exists(destination_dir):
            raise errors.GazooDeviceError("Device {} receive from device failed. "
                                          "Destination directory {} doesn't appear to exist.".
                                          format(self._device_name, destination_dir))
        if os.path.isdir(dest):
            dest = os.path.join(dest, os.path.basename(src))
        logger.info("{} receiving file from device. Source: {} Destination: {}",
                    self._device_name, src, dest)

        output, ret_code = self._shell_fn(self._command_dict["ECHO_FILE_IN_BASE64"].format(src),
                                          include_return_code=True)
        if ret_code != 0:
            raise errors.GazooDeviceError("Response to base64 encoding: {!r}".format(output))

        output += "===="  # extraneous padding addresses incorrect padding error (Python bug 33770)
        decoded_contents = base64.decodebytes(output.encode('utf-8', errors='replace'))

        with open(dest, 'wb') as open_file:
            open_file.write(decoded_contents)

        if not os.path.exists(dest):
            raise errors.GazooDeviceError("File {} does not exist".format(dest))

    @decorators.CapabilityLogDecorator(logger)
    def send_file_to_device(self, src, dest):
        """Copies src from host to dest on the device.

        Args:
            src (str): local file path on host computer.
            dest (str): file path on device where the file should be copied to.

        Raises:
            GazooDeviceError: if source file doesn't exist or copy failed.
        """
        if not os.path.exists(src):
            raise errors.GazooDeviceError("Device {} send to device failed. "
                                          "Source file {} doesn't appear to exist.".
                                          format(self._device_name, src))

        if self._is_valid_device_directory(dest):
            dest = os.path.join(dest, os.path.basename(src))
        logger.info("{} sending file to device. Source: {} Destination: {}",
                    self._device_name, src, dest)

        for try_num in range(self._send_tries):
            try:
                self._echo_file_to_transport_fn(src, dest)
                return
            except errors.GazooDeviceError as err:
                logger.info("{} failed to send to device {!r} - Retrying.".format(
                    self._device_name, src))
                if try_num == self._num_tries:
                    raise err

    def _is_valid_device_directory(self, directory):
        _, ret_code = self._shell_fn(self._command_dict["IS_DIRECTORY"].format(directory),
                                     include_return_code=True)
        return ret_code == 0
