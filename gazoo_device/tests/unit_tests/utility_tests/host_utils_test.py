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
"""Unit tests for gazoo_device.utility.host_utils.py."""

import os
import subprocess
from unittest import mock

from absl.testing import parameterized
from gazoo_device import config
from gazoo_device import data_types
from gazoo_device import extensions
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import host_utils
import immutabledict


_TEST_PACKAGE = "foo_package"
_EXPECTED_KEY_DIR = os.path.join(config.KEYS_DIRECTORY, _TEST_PACKAGE)
_TEST_KEY_SSH_PRIVATE_NAME = "foo_key"
_EXPECTED_KEY_SSH_PRIVATE_PATH = os.path.join(_EXPECTED_KEY_DIR,
                                              _TEST_KEY_SSH_PRIVATE_NAME)
_TEST_KEY_SSH_PUBLIC_NAME = "foo_key.pub"
_EXPECTED_KEY_SSH_PUBLIC_PATH = os.path.join(_EXPECTED_KEY_DIR,
                                             _TEST_KEY_SSH_PUBLIC_NAME)
_TEST_KEY_OTHER_NAME = "bar_key"
_EXPECTED_KEY_OTHER_PATH = os.path.join(_EXPECTED_KEY_DIR, _TEST_KEY_OTHER_NAME)
_TEST_KEY_SSH_PRIVATE = data_types.KeyInfo(
    _TEST_KEY_SSH_PRIVATE_NAME,
    type=data_types.KeyType.SSH,
    package=_TEST_PACKAGE)
_TEST_KEY_SSH_PUBLIC = data_types.KeyInfo(
    _TEST_KEY_SSH_PUBLIC_NAME,
    type=data_types.KeyType.SSH,
    package=_TEST_PACKAGE)
_TEST_KEY_OTHER = data_types.KeyInfo(
    _TEST_KEY_OTHER_NAME, type=data_types.KeyType.OTHER, package=_TEST_PACKAGE)


class HostUtilsTests(unit_test_case.UnitTestCase):
  """Unit tests for gazoo_device.utility.host_utils.py."""

  def setUp(self):
    super().setUp()

    self.mock_download_key = mock.Mock()
    extensions_keys_patch = mock.patch.object(
        extensions, "keys", new=[_TEST_KEY_SSH_PRIVATE, _TEST_KEY_OTHER])
    extensions_keys_patch.start()
    self.addCleanup(extensions_keys_patch.stop)
    package_info_patch = mock.patch.object(
        extensions, "package_info", new={
            _TEST_PACKAGE: immutabledict.immutabledict({
                "version": "0.0.1",
                "key_download_function": self.mock_download_key,
            })
        })
    package_info_patch.start()
    self.addCleanup(package_info_patch.stop)

  def test_get_key_path(self):
    """Test that path returned by get_key_path() is correct."""
    self.assertEqual(host_utils.get_key_path(_TEST_KEY_SSH_PRIVATE),
                     _EXPECTED_KEY_SSH_PRIVATE_PATH)

  @mock.patch.object(os.path, "isdir", side_effect=[False, True])
  @mock.patch.object(os, "makedirs")
  @mock.patch.object(os.path, "exists", return_value=True)
  @mock.patch.object(host_utils, "_set_key_permissions")
  def test_download_key_creates_directory_if_its_absent(
      self, unused_mock_set_key_permissions, unused_mock_exists, mock_makedirs,
      mock_isdir):
    """Test that _download_key() creates package key dir if it's absent."""
    host_utils._download_key(_TEST_KEY_SSH_PRIVATE)
    mock_isdir.assert_called_once_with(_EXPECTED_KEY_DIR)
    mock_makedirs.assert_called_once_with(_EXPECTED_KEY_DIR)
    self.mock_download_key.assert_called_once_with(
        _TEST_KEY_SSH_PRIVATE, _EXPECTED_KEY_SSH_PRIVATE_PATH)

  @mock.patch.object(os.path, "isdir", return_value=True)
  @mock.patch.object(os, "makedirs")
  @mock.patch.object(os.path, "exists", return_value=True)
  @mock.patch.object(host_utils, "_set_key_permissions")
  def test_download_key_does_not_create_directory_if_its_present(
      self, unused_mock_set_key_permissions, unused_mock_exists, mock_makedirs,
      mock_isdir):
    """Test that _download_key() does not create key dir if it's present."""
    host_utils._download_key(_TEST_KEY_SSH_PRIVATE)
    mock_isdir.assert_called_once_with(_EXPECTED_KEY_DIR)
    mock_makedirs.assert_not_called()

  @mock.patch.object(os.path, "isdir", return_value=True)
  @mock.patch.object(os, "makedirs")
  @mock.patch.object(os.path, "exists", return_value=False)
  def test_download_key_raises_if_key_isnt_downloaded(
      self, mock_exists, unused_mock_makedirs, unused_mock_isdir):
    """Test that _download_key() raises an error if key isn't downloaded."""
    error_regex = r"Key .*{}.* was not downloaded to {}".format(
        _TEST_KEY_SSH_PRIVATE_NAME, _EXPECTED_KEY_SSH_PRIVATE_PATH)
    with self.assertRaisesRegex(FileNotFoundError, error_regex):
      host_utils._download_key(_TEST_KEY_SSH_PRIVATE)
    mock_exists.assert_called_with(_EXPECTED_KEY_SSH_PRIVATE_PATH)

  @mock.patch.object(os.path, "isdir", return_value=True)
  @mock.patch.object(os, "makedirs")
  @mock.patch.object(os.path, "exists", return_value=True)
  @mock.patch.object(host_utils, "_set_key_permissions")
  def test_download_key_sets_permissions_for_private_ssh_keys(
      self, mock_set_key_permissions, unused_mock_exists, unused_mock_makedirs,
      unused_mock_isdir):
    """Test that _download_key() changes permissions for SSH keys."""
    host_utils._download_key(_TEST_KEY_SSH_PRIVATE)
    mock_set_key_permissions.assert_called_once_with(
        _EXPECTED_KEY_SSH_PRIVATE_PATH)

  @mock.patch.object(os.path, "isdir", return_value=True)
  @mock.patch.object(os, "makedirs")
  @mock.patch.object(os.path, "exists", return_value=True)
  @mock.patch.object(host_utils, "_set_key_permissions")
  def test_download_key_doesnt_set_permissions_for_non_ssh_keys(
      self, mock_set_key_permissions, unused_mock_exists, unused_mock_makedirs,
      unused_mock_isdir):
    """Test that _download_key() doesn't change permissions for non-SSH keys."""
    host_utils._download_key(_TEST_KEY_OTHER)
    mock_set_key_permissions.assert_not_called()

  @mock.patch.object(os.path, "isdir", return_value=True)
  @mock.patch.object(os, "makedirs")
  @mock.patch.object(os.path, "exists", return_value=True)
  @mock.patch.object(host_utils, "_set_key_permissions")
  def test_download_key_doesnt_set_permissions_for_public_ssh_keys(
      self, mock_set_key_permissions, unused_mock_exists, unused_mock_mkdir,
      unused_mock_isdir):
    """Test that _download_key() doesn't set permissions for public SSH keys."""
    host_utils._download_key(_TEST_KEY_SSH_PUBLIC)
    mock_set_key_permissions.assert_not_called()

  @mock.patch.object(os, "chmod")
  def test_set_key_permissions_already_correct(self, mock_chmod):
    """Test _set_key_permissions for already correct permissions."""
    mock_stat_result = mock.Mock()
    mock_stat_result.st_mode = int("400", 8)
    with mock.patch.object(os, "stat", return_value=mock_stat_result):
      host_utils._set_key_permissions(_EXPECTED_KEY_SSH_PRIVATE_PATH)
    mock_chmod.assert_not_called()

  @mock.patch.object(os, "chmod")
  def test_set_key_permissions_incorrect_permissions(self, mock_chmod):
    """Test _set_key_permissions for incorrect permissions."""
    mock_stat_result = mock.Mock()
    mock_stat_result.st_mode = int("644", 8)
    with mock.patch.object(os, "stat", return_value=mock_stat_result):
      host_utils._set_key_permissions(_EXPECTED_KEY_SSH_PRIVATE_PATH)
    mock_chmod.assert_called_once_with(_EXPECTED_KEY_SSH_PRIVATE_PATH,
                                       int("400", 8))

  @mock.patch.object(os, "chmod", side_effect=OSError("Some failure"))
  def test_set_key_permissions_incorrect_permissions_failure(self, mock_chmod):
    """Test _set_key_permissions failing to correct permissions."""
    mock_stat_result = mock.Mock()
    mock_stat_result.st_mode = int("644", 8)
    with mock.patch.object(os, "stat", return_value=mock_stat_result):
      with self.assertRaisesRegex(ValueError, "Unable to change permissions"):
        host_utils._set_key_permissions(_EXPECTED_KEY_SSH_PRIVATE_PATH)
    mock_chmod.assert_called_once_with(_EXPECTED_KEY_SSH_PRIVATE_PATH,
                                       int("400", 8))


class SnmpHostUtilsTests(unit_test_case.UnitTestCase):
  """Unit tests for SNMP methods in gazoo_device.utility.host_utils.py."""

  @mock.patch.object(host_utils, "is_pingable", return_value=True)
  @mock.patch.object(host_utils, "accepts_snmp", return_value=True)
  def test_get_all_snmp_ips__finds_snmp_enabled_ip(
      self, mock_accepts_snmp, mock_is_pingable,
  ):
    """Test get_all_snmp_ips when it finds SNMP enabled IP."""
    static_ips = ["0.0.0.0"]
    self.assertEqual(
        host_utils.get_all_snmp_ips(static_ips=static_ips), static_ips)
    mock_is_pingable.assert_called_once_with(static_ips[0])
    mock_accepts_snmp.assert_called_once_with(static_ips[0])

  @mock.patch.object(host_utils, "is_pingable", return_value=True)
  @mock.patch.object(host_utils, "accepts_snmp", return_value=True)
  def test_get_all_snmp_ips__finds_multiple_snmp_enabled_ips(
      self, mock_accepts_snmp, mock_is_pingable,
  ):
    """Test get_all_snmp_ips when it finds multiple SNMP enabled IPs."""
    static_ips = ["0.0.0.0", "1.1.1.1", "2.2.2.2"]
    self.assertCountEqual(
        host_utils.get_all_snmp_ips(static_ips=static_ips), static_ips)
    mock_is_pingable.assert_called()
    mock_accepts_snmp.assert_called()

  @mock.patch.object(host_utils, "is_pingable", return_value=False)
  @mock.patch.object(host_utils, "accepts_snmp", return_value=True)
  def test_get_all_snmp_ips__all_ips_unpingable(
      self, mock_accepts_snmp, mock_is_pingable,
  ):
    """Test get_all_snmp_ips when it finds no pingable IPs."""
    static_ips = ["0.0.0.0", "1.1.1.1", "2.2.2.2"]
    self.assertEqual(host_utils.get_all_snmp_ips(static_ips=static_ips), [])

  @mock.patch.object(host_utils, "is_pingable", return_value=True)
  @mock.patch.object(host_utils, "accepts_snmp", return_value=False)
  def test_get_all_snmp_ips__none_snmp_enabled(
      self, mock_accepts_snmp, mock_is_pingable,
  ):
    """Test get_all_snmp_ips when it finds no snmp enabled IPs."""
    static_ips = ["0.0.0.0", "1.1.1.1", "2.2.2.2"]
    self.assertEqual(host_utils.get_all_snmp_ips(static_ips=static_ips), [])

  @mock.patch.object(host_utils, "is_pingable", return_value=True)
  @mock.patch.object(
      host_utils, "accepts_snmp", side_effect=[True, False, True])
  def test_get_all_snmp_ips__finds_two_snmp_enabled_ip(
      self, mock_accepts_snmp, mock_is_pingable,
  ):
    """Test get_all_snmp_ips when it finds only one SNMP enabled IP."""
    static_ips = ["0.0.0.0", "1.1.1.1", "2.2.2.2"]
    snmp_ips = host_utils.get_all_snmp_ips(static_ips=static_ips)
    self.assertLen(snmp_ips, 2)
    self.assertContainsSubset(snmp_ips, static_ips)

  @mock.patch.object(host_utils, "is_pingable", side_effect=[False, True, True])
  @mock.patch.object(
      host_utils, "accepts_snmp", side_effect=[True, False])
  def test_get_all_snmp_ips__few_pingable_and_one_snmp_enabled(
      self, mock_accepts_snmp, mock_is_pingable,
  ):
    """Test get_all_snmp_ips when it finds no SNMP enabled IPs."""
    static_ips = ["0.0.0.0", "1.1.1.1", "2.2.2.2"]
    snmp_ips = host_utils.get_all_snmp_ips(static_ips=static_ips)
    self.assertLen(snmp_ips, 1)
    self.assertContainsSubset(snmp_ips, static_ips)

  @mock.patch.object(subprocess, "check_output")
  def test_accepts_snmp__pass(self, mock_check_output):
    ip_address = "0.0.0.0"
    self.assertTrue(host_utils.accepts_snmp(ip_address=ip_address))
    cmd = host_utils._SNMPWALK_COMMAND.format(ip_address=ip_address).split()
    mock_check_output.assert_called_once_with(
        cmd, timeout=host_utils._SNMPWALK_TIMEOUT)

  @mock.patch.object(
      subprocess,
      "check_output",
      side_effect=subprocess.CalledProcessError("some_err", "some_cmd"))
  def test_accepts_snmp__fail(self, mock_check_output):
    ip_address = "0.0.0.0"
    self.assertFalse(host_utils.accepts_snmp(ip_address=ip_address))

  @parameterized.named_parameters(
      ("default_boto", None, "default_boto"),
      ("custom_boto", "some_boto", "some_boto"),
  )
  @mock.patch.object(subprocess, "check_output", return_value=b"some_output")
  @mock.patch.object(os.path, "exists", return_value=True)
  @mock.patch.object(
      host_utils, "_get_default_boto", return_value="default_boto")
  @mock.patch.object(host_utils, "_set_gsutil_cli")
  def test_gsutil_command_success(
      self,
      boto_path,
      expected_boto_path,
      mock_set_gsutil_cli,
      mock_get_default_boto,
      mock_exists,
      mock_check_output,
  ):
    """Verifies gsutil_command succeeds when expected."""
    output = host_utils.gsutil_command(
        "ls", "gs://some/dir/", boto_path=boto_path)
    mock_check_output.assert_called_once()
    self.assertEqual(output, "some_output")
    check_output_env = mock_check_output.call_args[1]["env"]
    self.assertIn("BOTO_CONFIG", check_output_env)
    self.assertEqual(check_output_env["BOTO_CONFIG"], expected_boto_path)

  @parameterized.named_parameters(
      ("bad_boto", RuntimeError),
      ("bad_gsutil_call", "good_boto"),
  )
  @mock.patch.object(
      subprocess,
      "check_output",
      side_effect=subprocess.CalledProcessError("some_err", "some_cmd"))
  @mock.patch.object(host_utils, "_get_default_boto")
  @mock.patch.object(host_utils, "_set_gsutil_cli")
  def test_gsutil_command_failure(
      self,
      get_default_boto_effect,
      mock_set_gsutil_cli,
      mock_get_default_boto,
      mock_check_output,
  ):
    """Verifies gsutil_command fails when expected."""
    mock_get_default_boto.side_effect = get_default_boto_effect
    with mock.patch.object(host_utils, "_gsutil_cli", new="some_gsutil_cli"):
      with self.assertRaises(RuntimeError):
        host_utils.gsutil_command("ls", "gs://some/dir/")

  @parameterized.named_parameters(
      ("no_flags", {}, ["ping", "-c", "1", "-W", "2", "12.34.56.78"]),
      ("all_flags", {"timeout": 3, "packet_count": 4, "deadline": 5},
       ["ping", "-c", "4", "-W", "3", "-w", "5", "12.34.56.78"]),
      ("no_deadline", {"timeout": 3, "packet_count": 4},
       ["ping", "-c", "4", "-W", "3", "12.34.56.78"]),
  )
  @mock.patch.object(subprocess, "check_output", return_value=b"some_output")
  def test_is_pingable_success(
      self,
      params,
      expected_cmd_list,
      mock_check_output,
  ):
    """Verifies is_pingable succeeds with correct flag parsing."""
    result = host_utils.is_pingable("12.34.56.78", **params)

    self.assertTrue(result)
    mock_check_output.assert_called_once_with(
        expected_cmd_list, stderr=subprocess.STDOUT)

  @mock.patch.object(
      subprocess,
      "check_output",
      side_effect=subprocess.CalledProcessError("some_err", "some_cmd"))
  def test_is_pingable_failure(self, mock_check_output):
    """Verifies is_pingable fails when expected."""
    self.assertFalse(host_utils.is_pingable("12.34.56.78"))

  @parameterized.named_parameters(
      ("Normal IPv4", "12.34.56.78", True),
      ("Normal IPv6", "2001:db8::ff00:42:8329", True),
      ("None", None, False),
      ("Random string", "hello_world", False),
      ("Invalid length", "12.34.56", False),
  )
  @mock.patch.object(subprocess, "check_output", return_value=b"some_output")
  def test_is_pingable_ip_address_format(
      self, ip_address, expected_result, mock_check_output):
    """Verifies is_pingable check if the ip_address format is valid."""
    result = host_utils.is_pingable(ip_address)

    self.assertEqual(result, expected_result)

if __name__ == "__main__":
  unit_test_case.main()
