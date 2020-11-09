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

"""Docker flavor of file transfer capability (for devices using PTY transports)."""
from __future__ import absolute_import
import os

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import file_transfer_base
from gazoo_device.utility import host_utils

logger = gdm_logger.get_gdm_logger()


class FileTransferDocker(file_transfer_base.FileTransferBase):
    """Docker-based file transfer capability."""

    def __init__(self, docker_container, device_name):
        """Initialize docker file transfer capability.

        Args:
            docker_container (str): name or id of the device docker container using the capability.
            device_name (str): name of the device using the capability
        """

        super().__init__(device_name=device_name)
        self._docker_container = docker_container

    @decorators.CapabilityLogDecorator(logger)
    def send_file_to_device(self, src, dest):
        """Copy a file from the local host to the device.

        Args:
            src (str): Absolute path of the source file on the host.
            dest (str): Absolute path of the destination on the device

        Raises:
            GazooDeviceError: if the file transfer fails for any reason,
               or if the specified mode is invalid.

        Note:
           dest may be either a directory or a file name.
        """
        if not os.path.exists(src):
            raise errors.GazooDeviceError("Device {} send to device failed. "
                                          "Source file {} doesn't appear to exist.".
                                          format(self._device_name, src))

        logger.info("{} sending file to device. Source: {} Destination: {}",
                    self._device_name, src, dest)
        host_utils.docker_cp_to_device(docker_container=self._docker_container,
                                       local_file_path=src,
                                       container_file_path=dest)

    @decorators.CapabilityLogDecorator(logger)
    def recv_file_from_device(self, src, dest="./"):
        """Copy a file from the device to the local host.

        Args:
            src (str): Absolute path of the source file on the device.
            dest (str): Absolute path of the destination on the host

        Raises:
          GazooDeviceError: if the file transfer fails for any reason.
          RuntimeError: if the final file does not exist

        Note:
         dest can be directory or a file name.
        """
        dest_dir = os.path.dirname(dest)
        if dest_dir != "." and not os.path.exists(dest_dir):
            raise errors.GazooDeviceError("Device {} receive from device failed. "
                                          "Destination directory {} doesn't appear to exist.".
                                          format(self._device_name,
                                                 dest_dir))

        logger.info("{} receiving file from device. Source: {} Destination: {}",
                    self._device_name, src, dest)
        host_utils.docker_cp_from_device(docker_container=self._docker_container,
                                         local_file_path=dest,
                                         container_file_path=src)
        if not os.path.exists(dest):
            raise RuntimeError(
                "Final file {} does not exist".format(dest))
