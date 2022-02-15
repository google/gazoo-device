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

"""The implementation of the package management capability on Android devices.

The Android package management capability is used on the android devices which
can have
Android APKs installed. The Android package systems rely on adb command to
manage packages.
"""
from typing import Any, Callable, List
from gazoo_device import decorators
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import package_management_base
from gazoo_device.utility import adb_utils

logger = gdm_logger.get_logger()

_COMMAND_LIST_PACKAGES = 'pm list packages'
_PACKAGE_PREFIX = 'package:'


class PackageManagementAndroid(package_management_base.PackageManagementBase):
  """Android package management capability implementation."""

  def __init__(self,
               device_name: str,
               adb_serial: str,
               shell_fn: Callable[..., Any]):
    """Creates an instance of the Android package management capability.

    Args:
      device_name: Name of device used for logging.
      adb_serial: The adb device serial.
      shell_fn: The function used to send shell commands to the devic.
    """
    super().__init__(device_name=device_name)
    self._adb_serial = adb_serial
    self._shell_fn = shell_fn

  @decorators.CapabilityLogDecorator(logger)
  def install_package(self,
                      package_path: str,
                      allow_downgrade: bool = False,
                      allow_test_apk: bool = False,
                      reinstall: bool = False,
                      all_permissions: bool = False) -> None:
    """Installs an Android package on the device.

    Args:
      package_path: The path to the package on the host machine.
      allow_downgrade: Allows version code downgrade.
      allow_test_apk: Allows test APKs to be installed.
      reinstall: Reinstalls an existing package and keeps its data.
      all_permissions: Grants all runtime permission to the app.
    """
    adb_utils.install_package_on_device(
        package_path,
        adb_serial=self._adb_serial,
        allow_downgrade=allow_downgrade,
        allow_test_apk=allow_test_apk,
        reinstall=reinstall,
        all_permissions=all_permissions)

  @decorators.CapabilityLogDecorator(logger)
  def uninstall_package(self, package_name: str) -> None:
    """Uninstalls an Android package on the device.

    Args:
      package_name: The name of the package to uninstall.
    """
    adb_utils.uninstall_package_on_device(
        package_name, adb_serial=self._adb_serial)

  @decorators.CapabilityLogDecorator(logger)
  def list_packages(self) -> List[str]:
    """Lists all the installed packages on the device.

    Here we use `pm list package` command to show all the packages on the
    device. Note that the results will have be "package:<package_name>".
    We will remove the prefix here.

    Returns:
      List of package names.
    """
    cmd_result = self._shell_fn(_COMMAND_LIST_PACKAGES)
    packages = [
        pkg.replace(_PACKAGE_PREFIX, '') for pkg in cmd_result.split('\n')
    ]
    return packages

  @decorators.CapabilityLogDecorator(logger)
  def has_package(self, package_name: str) -> bool:
    """Checks if a package is installed on the device.

    Args:
      package_name: The package name.

    Returns:
      True if the package is installed else False.
    """
    cmd_result = self._shell_fn(f'{_COMMAND_LIST_PACKAGES} {package_name}')
    full_package_name = f'{_PACKAGE_PREFIX}{package_name}'
    return full_package_name in cmd_result
