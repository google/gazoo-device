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

"""Unit tests for the PackageManagementAndroid capability."""
from unittest import mock
from gazoo_device.capabilities import package_management_android
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.utility import adb_utils
import immutabledict

_ADB_SERIAL = 'ABCDE123456789'
_DEVICE_NAME = 'my-device'
_PACKAGE_NAME = 'android.package'
_PACKAGE_PATH = '/path/to/'

_FAKE_RESPONSE_DICT = immutabledict.immutabledict({
    'pm list packages com.android.shell\n': 'package:com.android.shell\n',
    'pm list packages\n': (
        'package:android\npackage:com.google.android.tv\n'
        'package:com.android.shell\n'),
})


class PackageManagementAndroidCapabilityTests(
    fake_device_test_case.FakeDeviceTestCase):
  """Unit test for PackageManagementAndroid capability implementation."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements()
    self.uut = package_management_android.PackageManagementAndroid(
        device_name=_DEVICE_NAME, adb_serial=_ADB_SERIAL,
        shell_fn=self._shell)
    self.fake_responder.behavior_dict = _FAKE_RESPONSE_DICT.copy()

  def _shell(self, command):
    """Fake shell function which leverages send_and_expect in fake_responder."""
    response = self.mock_switchboard.send_and_expect(command, ['(.*)'])
    return response.match.group(1).strip()

  @mock.patch.object(adb_utils, 'install_package_on_device', return_value=None)
  def test_install_package_success(self, mock_adb_install):
    """Verifies install_package calls adb_util to install package correctly."""
    self.uut.install_package(_PACKAGE_PATH)

    mock_adb_install.assert_called_once()

  @mock.patch.object(adb_utils, 'install_package_on_device', return_value=None)
  def test_install_package_success_with_options(self, mock_adb_install):
    """Verifies install_package with options calls correctly."""
    self.uut.install_package(
        _PACKAGE_PATH, allow_downgrade=True,
        allow_test_apk=True, reinstall=True, all_permissions=True)

    mock_adb_install.assert_called_once_with(
        _PACKAGE_PATH,
        adb_serial=_ADB_SERIAL,
        allow_downgrade=True,
        allow_test_apk=True,
        reinstall=True,
        all_permissions=True)

  @mock.patch.object(
      adb_utils, 'uninstall_package_on_device', return_value=None)
  def test_uninstall_package_success(self, mock_adb_uninstall):
    """Verifies uninstall_package calls adb_util to uninstall package."""
    self.uut.uninstall_package(_PACKAGE_NAME)

    mock_adb_uninstall.assert_called_once_with(
        _PACKAGE_NAME, adb_serial=_ADB_SERIAL)

  def test_list_packages_success(self):
    """Verifies list_packages return all installed packages."""
    results = self.uut.list_packages()

    self.assertEqual(
        results, ['android', 'com.google.android.tv', 'com.android.shell'])

  def test_has_package_true(self):
    """Verifies has_package return True when the package exists."""
    result = self.uut.has_package('com.android.shell')

    self.assertTrue(result)

  def test_has_package_false(self):
    """Verifies has_package return False when the package doesn't exist."""
    result = self.uut.has_package('bad package')

    self.assertFalse(result)
