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

"""Interface for the file transfer capability."""
import abc
from gazoo_device.capabilities.interfaces import capability_base


class FileTransferBase(capability_base.CapabilityBase):
  """Abstract Base class for the file transfer capability."""

  @abc.abstractmethod
  def send_file_to_device(self, src, dest):
    """Copy a file from the local host to the device.

    Args:
        src (str): Absolute path of the source file on the host.
        dest (str): Absolute path of the destination on the device

    Raises:
        DeviceError: if the file transfer fails for any reason,
          or if the specified mode is invalid.

    Note:
        dest may be either a directory or a file name.
    """

  @abc.abstractmethod
  def recv_file_from_device(self, src, dest):
    """Copy a file from the device to the local host.

    Args:
        src (str): Absolute path of the source file on the device.
        dest (str): Absolute path of the destination on the host

    Raises:
        DeviceError: if the file transfer fails for any reason.

    Note:
        dest can be directory or a file name.
    """
