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

"""Test suite for the package_management capability."""
import logging
import os
import shutil
from typing import Tuple, Type
from gazoo_device.tests.functional_tests.utils import gdm_test_base
from mobly import asserts
from gazoo_device.utility import host_utils

_DOWNLOAD_FOLDER_TEMPLATE = "/tmp/{device_name}-packages"


class PackageManagementTestSuite(gdm_test_base.GDMTestBase):
  """Functional test suite for the package_management capability."""

  @classmethod
  def is_applicable_to(cls, device_type: str,
                       device_class: Type[gdm_test_base.DeviceType],
                       device_name: str) -> bool:
    """Determine if this test suite can run on the given device."""
    return device_class.has_capabilities(["package_management"])

  @classmethod
  def requires_pairing(cls) -> bool:
    """Returns True if the device must be paired to run this test suite."""
    return False

  @classmethod
  def required_test_config_variables(cls) -> Tuple[str, ...]:
    """Returns keys required to be present in the functional test config."""
    return ("sample_package_path", "sample_package_name")

  def _download_package(self, remote_package_path: str,
                        local_folder: str) -> str:
    """Downloads package into local folder and returns the local file path."""
    file_name = os.path.basename(remote_package_path)
    local_file = os.path.join(local_folder, file_name)
    logging.info("Downloading package from %s to %s", remote_package_path,
                 local_file)
    host_utils.gsutil_command("cp", remote_package_path, [local_folder])
    return local_file

  def test_has_package(self):
    """Tests the ability to check whether a package is installed."""
    package_exists = self.device.package_management.has_package(
        "nonexistent_package")
    asserts.assert_is_instance(package_exists, bool)
    asserts.assert_false(package_exists, "Package should not exist")

  def test_list_packages(self):
    """Tests the ability to list all packages on a device."""
    if not hasattr(self.device.package_management, "list_packages"):
      asserts.skip(f"{self.device.name}'s package_management capability "
                   "does not implement 'list_packages'.")
    packages_on_device = self.device.package_management.list_packages()
    asserts.assert_true(
        packages_on_device, "Cannot list packages on the device.")
    asserts.assert_is_instance(packages_on_device, list)

  def test_install_and_uninstall_package(self):
    """Tests the ability to install and uninstall a package."""
    package_name = self.test_config["sample_package_name"]
    download_folder = _DOWNLOAD_FOLDER_TEMPLATE.format(
        device_name=self.device.name)
    if not os.path.isdir(download_folder):
      os.mkdir(download_folder)
    if self.device.package_management.has_package(package_name):
      self.device.package_management.uninstall_package(package_name)

    try:
      package_path = self._download_package(
          self.test_config["sample_package_path"], download_folder)
      # Ensure package is not already present on the device.
      asserts.assert_false(
          self.device.package_management.has_package(package_name),
          f"Package {package_name} is already present on the device")

      # Install the package and check if it is in the package list.
      logging.info("Installing package %s from %s", package_name, package_path)
      self.device.package_management.install_package(package_path)
      asserts.assert_true(
          self.device.package_management.has_package(package_name),
          f"Package {package_name} was not installed after running "
          f"package_management.install_package")

      # Uninstall the package and check if it is not in the package list.
      logging.info("Uninstalling package %s", package_name)
      self.device.package_management.uninstall_package(package_name)
      asserts.assert_false(
          self.device.package_management.has_package(package_name),
          f"Package {package_name} is still on the device after running "
          "package_management.uninstall_package")
    finally:
      shutil.rmtree(download_folder)


if __name__ == "__main__":
  gdm_test_base.main()
