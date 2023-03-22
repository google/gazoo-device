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
import re
from typing import Any, Callable, Dict, List, Optional
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import package_management_base
from gazoo_device.utility import adb_utils

logger = gdm_logger.get_logger()

# Dumpsys package command.
# Grep only the packages part otherwise the output size will be too large.
_COMMAND_DUMPSYS_PACKAGES = r'dumpsys package |grep "Package \[.*\]" -A 15'
_COMMAND_DUMPSYS_PACKAGE = 'dumpsys package {package_name}'
_COMMAND_LIST_PACKAGES = 'pm list packages'
_PACKAGE_PREFIX = 'package:'

# Package system info
_PACKAGE_SYSINFO_SEPARATOR_REGEX = r'\s*Package \[\S+\] \(\S+\):'
_PACKAGE_SYSINFO_HIDDEN_SYSTEM_PACKAGES_SEPARATOR = 'Hidden system packages:'
_PACKAGE_SYSINFO_VERSION_NAME_KEY = 'versionName'
_PACKAGE_SYSINFO_LAST_UPDATE_TIME_KEY = 'lastUpdateTime'
_PACKAGE_SYSINFO_RESOURCE_PATH_KEY = 'resourcePath'
_PACKAGE_SYSINFO_PACKAGE_NAME_KEY = 'pkg'
_PACKAGE_SYSINFO_PACKAGE_NAME_REGEX = r'pkg=Package{\S+ (\S+)}'
_PACKAGE_SYSINFO_VALUE_REGEX = r'{key}=(.+)'


class PackageManagementAndroid(package_management_base.PackageManagementBase):
  """Android package management capability implementation."""

  def __init__(self,
               device_name: str,
               adb_serial: str,
               shell_fn: Callable[..., Any],
               reboot_fn: Callable[..., Any]):
    """Creates an instance of the Android package management capability.

    Args:
      device_name: Name of device used for logging.
      adb_serial: The adb device serial.
      shell_fn: The function used to send shell commands to the devic.
      reboot_fn: The function to reboot the device.
    """
    super().__init__(device_name=device_name)
    self._adb_serial = adb_serial
    self._shell_fn = shell_fn
    self._reboot_fn = reboot_fn

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
  def install_system_package(self, package_path: str, destination: str):
    """Installs an Android package as the system package on the device.

    To install a package as privileged system package, we need to remount the
    device in order to push the package to the system package folder and
    overwrite a system package. The newly added system package will take effect
    after rebooting.

    Args:
      package_path: The path to the package on the host machine.
      destination: The package destination on device.
    """
    adb_utils.remount_device(self._adb_serial, reboot_fn=self._reboot_fn)
    adb_utils.push_to_device(self._adb_serial, package_path, destination)
    self._reboot_fn()

  @decorators.CapabilityLogDecorator(logger)
  def uninstall_package(self, package_name: str) -> None:
    """Uninstalls an Android package on the device.

    Args:
      package_name: The name of the package to uninstall.
    """
    adb_utils.uninstall_package_on_device(
        package_name, adb_serial=self._adb_serial)

  @decorators.CapabilityLogDecorator(logger)
  def list_packages(self, system_package_only: bool = False) -> List[str]:
    """Lists all the installed packages on the device.

    Here we use `pm list package` command to show all the packages on the
    device. Note that the results will have be "package:<package_name>".
    We will remove the prefix here.

    Args:
      system_package_only: List only the system packages.

    Returns:
      List of package names.
    """
    cmd = _COMMAND_LIST_PACKAGES
    if system_package_only:
      cmd = f'{cmd} -s'
    cmd_result = self._shell_fn(cmd)
    packages = [
        pkg.replace(_PACKAGE_PREFIX, '') for pkg in cmd_result.split('\n')
    ]
    return packages

  @decorators.CapabilityLogDecorator(logger)
  def has_package(self, package_name: str,
                  system_package_only: bool = False) -> bool:
    """Checks if a package is installed on the device.

    Args:
      package_name: The package name.
      system_package_only: Checks if it's a system package.

    Returns:
      True if the package is installed else False.
    """
    if system_package_only:
      cmd = f'{_COMMAND_LIST_PACKAGES} -s {package_name}'
    else:
      cmd = f'{_COMMAND_LIST_PACKAGES} {package_name}'
    cmd_result = self._shell_fn(cmd)
    full_package_name = f'{_PACKAGE_PREFIX}{package_name}'
    return full_package_name in cmd_result.splitlines()

  def _get_value_from_package_sys_info(
      self,
      package_sys_info: str,
      key: str,
      regex: Optional[str] = None,
  ) -> str:
    """Gets the value from device's package system info.

    Sample package system info for a package:
    --
    Package [com.my.package] (abcd1234):
       userId=1000
       pkg=Package{abcd1234 com.my.package}
       resourcePath=/path/to/apk
       versionCode=1234 minSdk=30 targetSdk=31
       versionName=12.34.56

    Args:
      package_sys_info: The package system info from dumpsys.
      key: The value key name.
      regex: The regex for getting the value. If empty, use the general regex
        "<key>=<value>".

    Returns:
      The value.

    Raises:
      DeviceError: If failed to parse the value from the package system info.
    """
    if not regex:
      regex = _PACKAGE_SYSINFO_VALUE_REGEX.format(key=key)

    value_match = re.search(regex, package_sys_info)

    if not value_match:
      raise errors.DeviceError(
          f'{self._device_name} failed to parse {key} value from the '
          f'package system info "{package_sys_info}".')
    return value_match.group(1)

  def _get_package_system_info(
      self,
      package_name: str,
      hidden_system_package: bool = False) -> Optional[str]:
    """Gets the system info for the target package.

    Uses 'dumpsys package <package_name>' command to get package system info.
    If a package is a system package and there's another version installed, the
    pre-built package will become the hidden system package.

    Args:
      package_name: The package name.
      hidden_system_package: Return the hidden system package info.

    Returns:
      The package system info or None if the package is not installed.
        If hidden_system_package is True then returns the hidden system package
        info, or None if there is no matching hidden system package.
    """
    if not self.has_package(package_name):
      return None

    command = _COMMAND_DUMPSYS_PACKAGE.format(package_name=package_name)
    package_sys_info_group = self._shell_fn(command).split(
        _PACKAGE_SYSINFO_HIDDEN_SYSTEM_PACKAGES_SEPARATOR)

    package_sys_info = package_sys_info_group[0]
    if hidden_system_package:
      if len(package_sys_info_group) == 1:
        return None
      package_sys_info = package_sys_info_group[1]
    return package_sys_info

  @decorators.CapabilityLogDecorator(logger)
  def get_package_versions(self) -> Dict[str, str]:
    """Gets all installed package versions.

    The package version info is fetched by 'dumpsys package' command.
    The command output contains all the package related system information and
    we parse the versionName field under each package info section.

    Returns:
      A dict that contains {package_name: package_version} info.
    """
    package_sys_info = self._shell_fn(_COMMAND_DUMPSYS_PACKAGES)
    package_sys_info_by_package = re.split(
        _PACKAGE_SYSINFO_SEPARATOR_REGEX, package_sys_info)
    # Removes the first section which is before the package info list.
    package_sys_info_by_package.pop(0)
    result = {}

    for package_sys_info in package_sys_info_by_package:
      package_name = self._get_value_from_package_sys_info(
          package_sys_info=package_sys_info,
          key=_PACKAGE_SYSINFO_PACKAGE_NAME_KEY,
          regex=_PACKAGE_SYSINFO_PACKAGE_NAME_REGEX)
      version_name = self._get_value_from_package_sys_info(
          package_sys_info=package_sys_info,
          key=_PACKAGE_SYSINFO_VERSION_NAME_KEY)

      # Don't let the hidden system package version overwrite the value.
      if package_name not in result:
        result[package_name] = version_name
    return result

  @decorators.CapabilityLogDecorator(logger)
  def get_package_version(
      self,
      package_name: str,
      hidden_system_package: bool = False) -> Optional[str]:
    """Gets the version of the target package.

    Uses 'dumpsys package <package_name>' command to get the target package
    version from the package system info.
    If a package is a system package and there's another version installed, the
    pre-built package will become the hidden system package.

    Args:
      package_name: The package name.
      hidden_system_package: Return the hidden system package version.

    Returns:
      The package version or None if the package is not installed.
        If hidden_system_package=True then returns the version in the
        hidden system package info (could be None).
    """
    package_sys_info = self._get_package_system_info(
        package_name=package_name, hidden_system_package=hidden_system_package)

    if package_sys_info is None:
      return None
    return self._get_value_from_package_sys_info(
        package_sys_info=package_sys_info,
        key=_PACKAGE_SYSINFO_VERSION_NAME_KEY)

  @decorators.CapabilityLogDecorator(logger)
  def get_package_installation_time(self, package_name: str) -> Optional[str]:
    """Gets the installation time of the package.

    Args:
      package_name: The package name.

    Returns:
      The package installation time or None if the package is not installed.
        The time format is "YYYY-MM-DD HH:mm:ss" without locale info.
    """
    package_sys_info = self._get_package_system_info(package_name=package_name)

    if package_sys_info is None:
      return None
    return self._get_value_from_package_sys_info(
        package_sys_info=package_sys_info,
        key=_PACKAGE_SYSINFO_LAST_UPDATE_TIME_KEY)

  @decorators.CapabilityLogDecorator(logger)
  def get_package_resource_path(self, package_name: str) -> Optional[str]:
    """Gets the resource path of the package."""
    package_sys_info = self._get_package_system_info(package_name=package_name)

    if package_sys_info is None:
      return None
    return self._get_value_from_package_sys_info(
        package_sys_info=package_sys_info,
        key=_PACKAGE_SYSINFO_RESOURCE_PATH_KEY)

  @decorators.DynamicProperty
  def package_versions(self) -> Dict[str, str]:
    """All installed package versions."""
    return self.get_package_versions()
