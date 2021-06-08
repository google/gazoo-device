"""Test suite for the package_management capability."""
import os
import shutil
from typing import Tuple, Type
from gazoo_device.tests.functional_tests.utils import gdm_test_base
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
    self.logger.info("Downloading package from %s to %s",
                     remote_package_path, local_file)
    host_utils.gsutil_command("cp", remote_package_path, [local_folder])
    return local_file

  def test_list_packages(self):
    """Tests the ability to list all packages on a device."""
    packages_on_device = self.device.package_management.list_packages()
    # Not sure what packages are on device, but guaranteed to be not empty.
    self.assertTrue(packages_on_device, "Cannot list packages on the device.")

  def test_install_and_uninstalled_package(self):
    """Tests the ability to install and uninstall a package."""
    package_name = self.test_config["sample_package_name"]
    download_folder = _DOWNLOAD_FOLDER_TEMPLATE.format(
        device_name=self.device.name)
    if not os.path.isdir(download_folder):
      os.mkdir(download_folder)

    try:
      package_path = self._download_package(
          self.test_config["sample_package_path"], download_folder)
      # Ensure package is not already present on the device.
      packages_on_device = self.device.package_management.list_packages()
      self.assertNotIn(
          package_name, packages_on_device,
          f"Package {package_name} is already present on the device")

      # Install the package and check if it is in the package list.
      self.logger.info("Installing package %s from %s",
                       package_name, package_path)
      self.device.package_management.install_package(package_path)
      packages_on_device = self.device.package_management.list_packages()
      self.assertIn(
          package_name, packages_on_device,
          f"New installed package {package_name} should be in the package "
          "list.")

      # Uninstall the package and check if it is not in the package list.
      self.logger.info("Uninstalling package %s", package_name)
      self.device.package_management.uninstall_package(package_name)
      packages_on_device = self.device.package_management.list_packages()
      self.assertNotIn(
          package_name, packages_on_device,
          f"Package {package_name} should be uninstalled and not in the "
          "package list.")
    finally:
      shutil.rmtree(download_folder)


if __name__ == "__main__":
  gdm_test_base.main()
