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

"""Package management capability interface."""
import abc
from gazoo_device.capabilities.interfaces import capability_base


class PackageManagementBase(capability_base.CapabilityBase):
  """Abstract base class defining API for package management."""

  @abc.abstractmethod
  def install_package(self, package_path, *args, **kwargs):
    """Installs a package on the device.

    Args:
        package_path (str): the path to the package on host machine.
        *args (list): positional arguments.
        **kwargs (dict): optional keyword arguments.

    Raises:
        ValueError: when package_path is not valid.
        DeviceError: if failed to install the package.
    """

  @abc.abstractmethod
  def uninstall_package(self, package_name, *args, **kwargs):
    """Uninstalls a package on the device.

    Args:
        package_name (str): the name of the package to uninstall.
        *args (list): positional arguments.
        **kwargs (dict): optional keyword arguments.

    Raises:
        DeviceError: if failed to uninstall the package.
    """
