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

"""The implementation of the package management capability on Android devices.

The Android package management capability is used on the android devices which
can have
Android APKs installed. The Android package systems rely on adb command to
manage packages.
"""
from gazoo_device import decorators
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import package_management_base
from gazoo_device.utility import adb_utils

logger = gdm_logger.get_logger()

COMMAND_LIST_PACKAGES = 'pm list packages'


class PackageManagementAndroid(package_management_base.PackageManagementBase):
  """Android package management capability implementation."""

  def __init__(self, device_name, adb_serial):
    """Create a instance of the Android package management capability.

    Args:
        device_name (str): Name of device used for logging
        adb_serial (str): the device serial.
    """
    super(PackageManagementAndroid, self).__init__(device_name=device_name)
    self._adb_serial = adb_serial

  @decorators.CapabilityLogDecorator(logger)
  def install_package(self,
                      package_path,
                      allow_downgrade=False,
                      allow_test_apk=False,
                      reinstall=False):
    """Installs an Android package on the device.

    Args:
        package_path (str): the path to the package on the host machine.
        allow_downgrade (bool): allows version code downgrade.
        allow_test_apk (bool): allows test APKs to be installed.
        reinstall (bool): reinstalls an existing package and keeps its data.

    Raises:
        ValueError: when package_path is not valid.
        DeviceError: if failed to install the package.
    """
    adb_utils.install_package_on_device(
        package_path,
        adb_serial=self._adb_serial,
        allow_downgrade=allow_downgrade,
        allow_test_apk=allow_test_apk,
        reinstall=reinstall)

  @decorators.CapabilityLogDecorator(logger)
  def uninstall_package(self, package_name):
    """Uninstalls an Android package on the device.

    Args:
        package_name (str): the name of the package to uninstall.

    Raises:
        DeviceError: if failed to uninstall the package.
    """
    adb_utils.uninstall_package_on_device(
        package_name, adb_serial=self._adb_serial)

  @decorators.CapabilityLogDecorator(logger)
  def list_packages(self):
    """List all the installed packages on the device.

    Here we use `pm list package` command to show all the packages on the
    device. Note that the results will have be "package:<package_name>".
    We will remove the prefix here.

    Returns:
        list: package name strings.

    Raises:
        DeviceError: if failed to list the packages.
    """
    _PACKAGE_PREFIX = 'package:'

    cmd_result = adb_utils.shell(self._adb_serial, COMMAND_LIST_PACKAGES)
    packages = [
        pkg.replace(_PACKAGE_PREFIX, '') for pkg in cmd_result.split('\n')
    ]
    return packages
