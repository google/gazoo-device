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
from absl.testing import parameterized
from gazoo_device import errors
from gazoo_device.capabilities import package_management_android
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.utility import adb_utils
import immutabledict

_ADB_SERIAL = 'ABCDE123456789'
_DEVICE_NAME = 'my-device'
_PACKAGE_NAME = 'android.package'
_PACKAGE_PATH = '/path/to/'

_FAKE_RESPONSE_DICT = immutabledict.immutabledict({
    'pm list packages com.android\n': 'package:com.android.shell\n',
    'pm list packages com.android.shell\n': 'package:com.android.shell\n',
    'pm list packages com.google.android.tv\n':
        'package:com.google.android.tv\n',
    'pm list packages -s com.android.shell\n': 'package:com.android.shell\n',
    'pm list packages -s com.google.android.tv\n': '',
    'pm list packages\n':
        'package:android\n'
        'package:com.google.android.tv\n'
        'package:com.android.shell\n',
    'pm list packages -s\n':
        'package:android\n'
        'package:com.android.shell\n',
    'dumpsys package |grep "Package \[.*\]" -A 15\n':  # pylint:disable=anomalous-backslash-in-string
        'Packages\n'
        '  Package [com.android.shell] (123abc):\n'
        '　  userId=1000\n'
        '    pkg=Package{123abc com.android.shell}\n'
        '    versionCode=123456 minSdk=30 targetSdk=31\n'
        '    versionName=12.34.56 (123456-789)\n'
        '    lastUpdateTime=2022-11-15 10:47:59\n'
        '　　 resourcePath=/product/priv-app/shell\n'
        '  Package [com.google.android.tv] (456def):\n'
        '　  userId=1000\n'
        '    pkg=Package{123abc com.google.android.tv}\n'
        '    versionCode=1 minSdk=30 targetSdk=30\n'
        '    versionName=2.4.6\n'
        '    lastUpdateTime=2022-11-15 10:47:59\n'
        '　　 resourcePath=/product/priv-app/android-tv\n'
        'Hidden system packages:\n'
        '  Package [com.android.shell] (456xyz):\n'
        '    userId=1000\n'
        '    pkg=Package{456xyz com.android.shell}\n'
        '    versionCode=111111 minSdk=30 targetSdk=31\n'
        '    versionName=111111\n'
        '    lastUpdateTime=2022-11-15 10:47:59\n'
        '　　 resourcePath=/product/priv-app/shell\n',
    'dumpsys package com.android.shell\n':
        'Packages\n'
        '  Package [com.android.shell] (123abc):\n'
        '　  userId=1000\n'
        '    pkg=Package{123abc com.android.shell}\n'
        '    versionCode=123456 minSdk=30 targetSdk=31\n'
        '    versionName=12.34.56 (123456-789)\n'
        '    lastUpdateTime=2022-11-15 10:47:59\n'
        '　　 resourcePath=/product/priv-app/shell\n'
        'Hidden system packages:\n'
        '  Package [com.android.shell] (456xyz):\n'
        '    userId=1000\n'
        '    pkg=Package{456xyz com.android.shell}\n'
        '    versionCode=111111 minSdk=30 targetSdk=31\n'
        '    versionName=111111\n'
        '    lastUpdateTime=2022-11-15 10:47:59\n'
        '　　 resourcePath=/product/priv-app/shell\n'
})


class PackageManagementAndroidCapabilityTests(
    fake_device_test_case.FakeDeviceTestCase):
  """Unit test for PackageManagementAndroid capability implementation."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements()
    self._mock_reboot = mock.MagicMock()
    self.uut = package_management_android.PackageManagementAndroid(
        device_name=_DEVICE_NAME, adb_serial=_ADB_SERIAL,
        shell_fn=self._shell,
        reboot_fn=self._mock_reboot)
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

  @mock.patch.object(adb_utils, 'push_to_device')
  @mock.patch.object(adb_utils, 'remount_device')
  def test_install_system_package_success(self, mock_remount, mock_push_file):
    """Veririfes install_system_package works as expected."""
    destination = '/system/priv-app/x.apk'

    self.uut.install_system_package(_PACKAGE_PATH, destination)

    mock_remount.assert_called_once_with(
        _ADB_SERIAL, reboot_fn=self._mock_reboot)
    mock_push_file.assert_called_once_with(
        _ADB_SERIAL, _PACKAGE_PATH, destination)

  @mock.patch.object(
      adb_utils, 'uninstall_package_on_device', return_value=None)
  def test_uninstall_package_success(self, mock_adb_uninstall):
    """Verifies uninstall_package calls adb_util to uninstall package."""
    self.uut.uninstall_package(_PACKAGE_NAME)

    mock_adb_uninstall.assert_called_once_with(
        _PACKAGE_NAME, adb_serial=_ADB_SERIAL)

  @parameterized.named_parameters(
      ('all packages', False,
       ['android', 'com.google.android.tv', 'com.android.shell']),
      ('system packages', True,
       ['android', 'com.android.shell']),
  )
  def test_list_packages_success(self, system_package_only, expected_result):
    """Verifies list_packages return all installed packages."""
    self.assertEqual(
        self.uut.list_packages(system_package_only=system_package_only),
        expected_result)

  @parameterized.named_parameters(
      ('true', True, 'com.android.shell', False),
      ('false_not_exists', False, 'bad_package', False),
      ('false_partial_matched', False, 'com.android', False),
      ('system_package_true', True, 'com.android.shell', True),
      ('system_package_false', False, 'com.google.android.tv', True),
  )
  def test_has_package(
      self, expected_result, package_name, system_package_only):
    """Verifies has_package return expected result."""
    result = self.uut.has_package(package_name, system_package_only)

    self.assertEqual(result, expected_result)

  def test_get_package_versions(self):
    """Verifies get_package_versions return all package versions."""
    self.assertEqual(
        self.uut.get_package_versions(),
        {
            'com.android.shell': '12.34.56 (123456-789)',
            'com.google.android.tv': '2.4.6'
        })

  def test_get_package_versions_missing_package_name(self):
    """Verifies get_package_versions raises if package name info not exist."""
    self.fake_responder.behavior_dict = immutabledict.immutabledict({
        'dumpsys package |grep "Package \[.*\]" -A 15\n':  # pylint:disable=anomalous-backslash-in-string
            'Packages\n'
            '  Package [com.android.shell] (123abc):\n'
            '.   userId=1000\n'
            '    versionCode=123456 minSdk=30 targetSdk=31\n'
            '    versionName=12.34.56 (123456-789)\n'
    })
    with self.assertRaisesRegex(
        errors.DeviceError,
        'failed to parse pkg value'):
      self.uut.get_package_versions()

  def test_get_package_version(self):
    """Verifies get_package_version return correct result."""
    self.assertEqual(
        self.uut.get_package_version('com.android.shell'),
        '12.34.56 (123456-789)')

  def test_get_package_version_hidden_system_package_not_exist(self):
    """Verifies get_package_version when getting non existent hidden version."""
    self.assertIsNone(self.uut.get_package_version(
        'com.google.android.tv', hidden_system_package=True))

  def test_get_package_version_hidden_system_package_exist(self):
    """Verifies get_package_version when getting hidden version."""
    self.assertEqual(
        self.uut.get_package_version(
            'com.android.shell', hidden_system_package=True),
        '111111')

  def test_get_package_version_not_installed(self):
    """Verifies get_package_version return None if the package not installed."""
    self.assertIsNone(self.uut.get_package_version('com.android.my_package'))

  def test_get_package_version_missing_version_name(self):
    """Verifies get_package_version raises if version name info not exist."""

    self.fake_responder.behavior_dict = immutabledict.immutabledict({
        'pm list packages com.android.shell\n': 'package:com.android.shell\n',
        'dumpsys package com.android.shell\n':
            'Packages\n'
            '  Package [com.android.shell] (123abc):\n'
            '.   userId=1000\n'
            '    pkg=Package{123abc com.android.shell}\n'
            '    versionCode=123456 minSdk=30 targetSdk=31\n'
    })

    with self.assertRaisesRegex(
        errors.DeviceError,
        'failed to parse versionName'):
      self.uut.get_package_version('com.android.shell')

  def test_get_package_installation_time(self):
    """Verifies get_package_installation_time return correct result."""
    self.assertEqual(
        self.uut.get_package_installation_time('com.android.shell'),
        '2022-11-15 10:47:59')

  def test_get_package_installation_time_not_installed(self):
    """Verifies get_package_installation_time return None if not installed."""
    self.assertIsNone(self.uut.get_package_installation_time(
        'com.android.fake_package'))

  def test_get_package_resource_path(self):
    """Verifies get_package_resource_path return correct result."""
    self.assertEqual(
        self.uut.get_package_resource_path('com.android.shell'),
        '/product/priv-app/shell')

  def test_get_package_resource_path_not_installed(self):
    """Verifies get_package_resource_path return None if not installed."""
    self.assertIsNone(self.uut.get_package_resource_path(
        'com.android.fake_package'))

  def test_package_versions_property(self):
    """Verifies te package_versions property has correct value."""
    self.assertEqual(
        self.uut.package_versions,
        {
            'com.android.shell': '12.34.56 (123456-789)',
            'com.google.android.tv': '2.4.6'
        })

