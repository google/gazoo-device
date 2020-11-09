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

"""Mobly test suite for PackageManagement capability.

Usage:
    python package_management_test_suite.py -t <test_bed>

Requirements:
    Testbed of a device which supports package management capability.
"""
import os
from mobly import asserts
from gazoo_device.utility import host_utils
from functional_tests import gdm_test_base

_TMP_FOLDER = '/tmp/'


class PackageManagementTestSuite(gdm_test_base.GDMTestBase):
    """Functional test suite for the package_management capability."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._package_path = None
        self._package_name = None

    @classmethod
    def is_applicable_to(cls, device_type, device_class, device_name):
        """Determine if this test suite can run on the given device."""
        return device_class.has_capabilities(["package_management"])

    @classmethod
    def requires_pairing(cls):
        """Returns True if the device in the testbed must be paired to run this test suite."""
        return False

    @classmethod
    def required_test_config_variables(cls):
        """Returns a list of keys required to be present in the functional test config.

        Returns:
            list[str]: functional test config keys which are used by the test suite.
        """
        return ["sample_package_path", "sample_package_name"]

    def setup_class(self):
        super().setup_class()
        self._package_path = self._download_package(self.test_config['sample_package_path'])
        self._package_name = self.test_config['sample_package_name']

    def _download_package(self, gs_path):
        """Downloads a sample package for testing.

        Args:
            gs_path (str): gsutil path starting with prefix.

        Returns:
            str: local package file path.
        """
        local_folder = _TMP_FOLDER
        file_name = gs_path.split('/')[-1]
        local_file = os.path.join(local_folder, file_name)

        self.logger.info('Downloading package from {} to {}'.format(gs_path, local_file))
        host_utils.gsutil_command('cp', gs_path, [local_folder])
        return local_file

    def test_01_list_packages(self):
        """Verify the capability to list all packages on a device."""

        packages_on_device = self.device.package_management.list_packages()
        # Not sure what packages are on device, but guaranteed to be not empty.
        asserts.assert_true(packages_on_device, 'Cannot list packages on the device.')

    def test_02_install_and_uninstalled_package(self):
        """Verify the capability to install and uninstall a package."""

        # Install the package and check if it is in the package list.
        self.logger.info('Installing package {} from {}'.format(self._package_name,
                                                                self._package_path))
        self.device.package_management.install_package(self._package_path)
        packages_on_device = self.device.package_management.list_packages()
        asserts.assert_true(
            self._package_name in packages_on_device,
            'New installed package {} should be in the package list.'.format(
                self._package_name))

        # Uninstall the package and check if it is not in the package list.
        self.logger.info('Uninstalling package {}'.format(self._package_name))
        self.device.package_management.uninstall_package(self._package_name)
        packages_on_device = self.device.package_management.list_packages()
        asserts.assert_false(
            self._package_name in packages_on_device,
            'Package {} should be uninstalled and not  in the package list.'.format(
                self._package_name))


if __name__ == '__main__':
    gdm_test_base.main()
