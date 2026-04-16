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
import shutil
import subprocess
from unittest import mock

from absl.testing import parameterized
from gazoo_device import config
from gazoo_device import data_types
from gazoo_device import errors
from gazoo_device import extensions
from gazoo_device.keys import raspberry_pi_key
from gazoo_device.keys import unifi_poe_switch_key
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import host_utils
import immutabledict


_FAKE_IFCONFIG = (
    "enp0s21f0u1u2u3: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500\n"
    "        inet6 abcd::1234:bcde:5678:912  prefixlen 64  scopeid 0x20<link>\n"
    "        ether 12:34:56:78:9a:bc  txqueuelen 1000  (Ethernet)\n"
    "        RX packets 0  bytes 0 (0.0 B)\n"
    "        RX errors 0  dropped 0  overruns 0  frame 0\n"
    "        TX packets 0  bytes 0 (0.0 B)\n"
    "        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0\n\n"
    "enp0s4567: flags=4099<UP,BROADCAST,MULTICAST>  mtu 1500\n"
    "        ether 11:22:33:44:55:66  txqueuelen 1000  (Ethernet)\n"
    "        RX packets 0  bytes 0 (0.0 B)\n"
    "        RX errors 0  dropped 0  overruns 0  frame 0\n"
    "        TX packets 0  bytes 0 (0.0 B)\n"
    "        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0\n"
    "        device interrupt 16  memory 0xf1200000-f1220000  \n\n"
    "lo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536\n"
    "        inet 127.0.0.1  netmask 255.0.0.0\n"
    "        inet6 ::1  prefixlen 128  scopeid 0x10<host>\n"
    "        loop  txqueuelen 1000  (Local Loopback)\n"
    "        RX packets 3772453  bytes 623727145 (594.8 MiB)\n"
    "        RX errors 0  dropped 0  overruns 0  frame 0\n"
    "        TX packets 3772453  bytes 623727145 (594.8 MiB)\n"
    "        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0\n\n"
    "wlp1s2: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500\n"
    "        inet 11.0.12.24  netmask 255.255.255.0  broadcast 11.0.12.255\n"
    "        inet6 1234::def0:9abc:5678:1234  prefixlen 64  "
    "scopeid 0x20<link>\n"
    "        ether cb:a9:87:65:43:21  txqueuelen 1000  (Ethernet)\n"
    "        RX packets 21567332  bytes 13865987347 (12.9 GiB)\n"
    "        RX errors 0  dropped 0  overruns 0  frame 0\n"
    "        TX packets 15424749  bytes 7935060413 (7.3 GiB)\n"
    "        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0\n\n")

_FAKE_ARP_TABLE = (
    "Address                  HWtype  HWaddress           Flags Mask  Iface\n"
    "host1000.somewhere.com   ether   00:00:56:00:78:65   C           eno1\n"
    "111.22.33.210            ether   66:77:88:99:cc:dd   C           "
    "enx00123456789a\n"
    "111.22.33.74             ether   67:89:ab:cd:ef:70   C           "
    "enx00123456789a\n"
    "host2000.somewhere.com   ether   ef:01:23:45:67:0b   C           eno1\n"
    "host3000.somewhere.com   ether   22:33:44:55:66:f0   C           eno1\n"
    "host4000.somewhere.com   ether   34:56:78:9a:bc:f0   C           eno1\n"
    "host5000.somewhere.com   ether   00:88:ff:99:55:21   C           "
    "qd_00095042f\n"
    "host6000.somewhere.com   ether   ab:cd:ef:12:34:56   C           eno1\n"
    "111.22.33.21                     (incomplete)                    "
    "enx00123456789a\n"
).encode()

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
_TEST_CMD_PATH = "/usr/bin/something"
_TEST_BAD_CMD_PATH = _TEST_CMD_PATH + "\n"
_TEST_CMD = os.path.basename(_TEST_CMD_PATH)
_NONEXISTENT_CMD = "nothing"
_GOOD_IP = "111.22.33.74"
_BAD_IP = "111.22.33.21"  # should not be returned as listed as incomplete


class HostUtilsTests(unit_test_case.UnitTestCase):
  """Unit tests for gazoo_device.utility.host_utils.py."""

  def setUp(self):
    super().setUp()

    self.mock_download_key = mock.Mock()
    extensions_key_to_download_function_patch = mock.patch.object(
        extensions, "key_to_download_function", new={
            _TEST_KEY_SSH_PRIVATE: self.mock_download_key,
            _TEST_KEY_SSH_PUBLIC: self.mock_download_key,
            _TEST_KEY_OTHER: self.mock_download_key,
        })
    extensions_key_to_download_function_patch.start()
    self.addCleanup(extensions_key_to_download_function_patch.stop)
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

  @mock.patch.object(
      subprocess,
      "run",
      autospec=True,
      return_value=mock.Mock(spec=subprocess.CompletedProcess, stderr=""))
  @mock.patch.object(host_utils, "_scp_use_legacy_option", new=None)
  def test_get_scp_command(self, mock_subprocess_run):
    """Tests _get_scp_command."""
    self.assertEqual(
        host_utils._get_scp_command(
            src="path/to/src", dest="path/to/dest", ssh_opt=["opts"]),
        ["scp", "-r", "-O", "opts", "path/to/src", "path/to/dest"])
    self.assertEqual(host_utils._scp_use_legacy_option, ("-O",))
    mock_subprocess_run.assert_called_once_with(["scp", "-O"],
                                                capture_output=True,
                                                text=True,
                                                check=False)

  @parameterized.named_parameters(
      ("linux", "unknown option -- O"),
      ("macos", "scp: illegal option -- O"))
  @mock.patch.object(host_utils, "_scp_use_legacy_option", new=None)
  def test_get_scp_command_legacy(self, mock_subprocess_stderr):
    """Tests _get_scp_command for legacy scp."""

    with mock.patch.object(
        subprocess, "run", autospec=True,
        return_value=mock.Mock(
            spec=subprocess.CompletedProcess,
            stderr=mock_subprocess_stderr)) as mock_subprocess_run:
      self.assertEqual(
          host_utils._get_scp_command(
              src="path/to/src", dest="path/to/dest", ssh_opt=["opts"]),
          ["scp", "-r", "opts", "path/to/src", "path/to/dest"])
    self.assertEqual(host_utils._scp_use_legacy_option, ())
    mock_subprocess_run.assert_called_once_with(["scp", "-O"],
                                                capture_output=True,
                                                text=True,
                                                check=False)

  @mock.patch.object(subprocess,
                     "check_output",
                     autospec=True,
                     return_value=b"command output")
  def test_scp_success(self, mock_check_output):
    """Tests the success of _scp util."""
    host_utils._scp(
        source="path/to/src",
        destination="path/to/dest",
        options=["opt1", "opt2"])
    args = [
        "scp", "-r", *host_utils._scp_use_legacy_option, "opt1", "opt2",
        "path/to/src", "path/to/dest"
    ]
    mock_check_output.assert_called_once_with(args, stderr=subprocess.STDOUT)

  @mock.patch.object(host_utils, "verify_key", return_value=None)
  @mock.patch.object(subprocess,
                     "check_output",
                     autospec=True,
                     return_value=b"command output")
  def test_scp_to_device(self, mock_check_output, unused_mock_verify_key):
    """Tests the success of scp_to_device."""
    key_info = data_types.KeyInfo(
        file_name="key", type=data_types.KeyType.SSH, package="package")
    host_utils.scp_to_device(
        ip_address="192.168.0.1",
        local_file_path="path/to/src",
        remote_file_path="path/to/dest",
        options=["opt1", "opt2"],
        key_info=key_info)
    args = [
        "scp", "-r", *host_utils._scp_use_legacy_option, "opt1", "opt2", "-i",
        host_utils.get_key_path(key_info), "path/to/src",
        "root@192.168.0.1:path/to/dest"
    ]
    mock_check_output.assert_called_once_with(args, stderr=subprocess.STDOUT)

  @mock.patch.object(host_utils, "verify_key", return_value=None)
  @mock.patch.object(subprocess,
                     "check_output",
                     autospec=True,
                     return_value=b"command output")
  def test_scp_from_device(self, mock_check_output, unused_mock_verify_key):
    """Tests the success of scp_from_device."""
    key_info = data_types.KeyInfo(
        file_name="key", type=data_types.KeyType.SSH, package="package")
    host_utils.scp_from_device(
        ip_address="192.168.0.1",
        local_file_path="path/to/dest",
        remote_file_path="path/to/src",
        options=["opt1", "opt2"],
        key_info=key_info)
    args = [
        "scp", "-r", *host_utils._scp_use_legacy_option, "opt1", "opt2", "-i",
        host_utils.get_key_path(key_info), "root@192.168.0.1:path/to/src",
        "path/to/dest"
    ]
    mock_check_output.assert_called_once_with(args, stderr=subprocess.STDOUT)


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

  @mock.patch.object(subprocess, "check_output", autospec=True)
  def test_accepts_snmp__pass(self, mock_check_output):
    ip_address = "0.0.0.0"
    self.assertTrue(host_utils.accepts_snmp(ip_address=ip_address))
    cmd = host_utils._SNMPGET_SYSTEM_DESCRIPTION_COMMAND.format(
        ip_address=ip_address).split()
    mock_check_output.assert_called_once_with(
        cmd, timeout=host_utils._SNMPGET_SYSTEM_DESCRIPTION_TIMEOUT)

  @parameterized.named_parameters(
      ("called_process_error",
       subprocess.CalledProcessError(1, "snmpget something")),
      ("timeout_expired",
       subprocess.TimeoutExpired("snmpget something", 3)),
  )
  @mock.patch.object(subprocess, "check_output", autospec=True)
  def test_accepts_snmp__fail(
      self, check_output_side_effect, mock_check_output):
    mock_check_output.side_effect = check_output_side_effect
    self.assertFalse(host_utils.accepts_snmp(ip_address="0.0.0.0"))

  @parameterized.named_parameters(
      ("gcloud_in_path",
       lambda cmd: "/bin/gcloud",
       lambda path: True,
       "/bin/gcloud"),
      ("macos_gcloud_not_in_path",
       lambda cmd: "",
       lambda path: path == host_utils._GCLOUD_MACOS_PATH,
       host_utils._GCLOUD_MACOS_PATH),
  )
  @mock.patch.object(host_utils, "get_command_path", autospec=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(host_utils, "_gcloud_cli", new=None)
  def test_set_gcloud_cli_success(
      self, get_command_path_side_effect, os_path_exists_side_effect,
      expected_gcloud_cli, mock_os_path_exists,
      mock_get_command_path):
    """Tests that _set_gcloud_cli finds a suitable CLI."""
    mock_os_path_exists.side_effect = os_path_exists_side_effect
    mock_get_command_path.side_effect = get_command_path_side_effect
    host_utils._set_gcloud_cli()
    self.assertEqual(
        host_utils._gcloud_cli, expected_gcloud_cli)

  @mock.patch.object(
      host_utils, "get_command_path", autospec=True, return_value="")
  @mock.patch.object(os.path, "exists", autospec=True, return_value=False)
  @mock.patch.object(host_utils, "_gcloud_cli", new=None)
  def test_set_gcloud_cli_failure(
      self, mock_os_path_exists, mock_get_command_path):
    """Tests that _set_gcloud_cli raises when neither CLI is found."""
    with self.assertRaisesRegex(
        errors.DependencyUnavailableError, "Unable to find a 'gcloud' binary"):
      host_utils._set_gcloud_cli()

  @parameterized.named_parameters(
      ("unauthenticated",
       subprocess.CalledProcessError(
           1,
           "gcloud storage ls gs://some/dir/",
           ("ERROR: (gcloud.storage.ls) Some authentication problem\n"
            "Please run:\n"
            "\n"
            "$ gcloud auth login\n"
            "\n"
            "to obtain new credentials.")),
       errors.GcloudUnauthenticatedError,
       # (?s) sets re.DOTALL to match newlines with '.'.
       (r"(?s)Run.*/usr/bin/gcloud auth login.*"
        r"If.*bazel test.*CLOUDSDK_CONFIG.*"
        r"'/usr/bin/gcloud storage ls gs://some/dir/' failed. Output: "
        r"ERROR: \(gcloud.storage.ls\) Some authentication problem.*"
        r"Please run.*gcloud auth login"),
      ),
      ("oauth_token_expired",
       subprocess.CalledProcessError(
           1,
           "gcloud storage ls gs://some/dir/",
           "ERROR: (gcloud.storage.ls) HTTPError 401: Invalid Credentials"),
       errors.GcloudUnauthenticatedError,
       (r"(?s)The OAuth 2\.0 token may have expired.*"
        r"'/usr/bin/gcloud storage ls gs://some/dir/' failed. Output: "
        r"ERROR: \(gcloud.storage.ls\) HTTPError 401: Invalid Credentials")
      ),
  )
  @mock.patch.object(
      subprocess,
      "check_output",
      side_effect=subprocess.CalledProcessError(
          "some_err", "some_cmd", "some_output"))
  @mock.patch.object(host_utils, "_set_gcloud_cli")
  @mock.patch.object(host_utils, "_gcloud_cli", new="/usr/bin/gcloud")
  def test_gcs_command_failure(
      self,
      check_output_side_effect,
      expected_error,
      expected_error_regex,
      mock_set_gcloud_cli,
      mock_check_output,
  ):
    """Verifies gcs_command fails when expected."""
    mock_check_output.side_effect = check_output_side_effect
    with self.assertRaisesRegex(expected_error, expected_error_regex):
      host_utils.gcs_command("ls", "gs://some/dir/")

  @parameterized.named_parameters(
      ("no_flags", {}, ["ping", "-c", "1", "-W", "2", "12.34.56.78"]),
      ("all_flags", {"timeout": 3, "packet_count": 4, "deadline": 5},
       ["ping", "-c", "4", "-W", "3", "-w", "5", "12.34.56.78"]),
      ("no_deadline", {"timeout": 3, "packet_count": 4},
       ["ping", "-c", "4", "-W", "3", "12.34.56.78"]),
  )
  @mock.patch.object(subprocess,
                     "check_output",
                     autospec=True,
                     return_value=b"some_output")
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
      autospec=True,
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
  @mock.patch.object(subprocess,
                     "check_output",
                     autospec=True,
                     return_value=b"some_output")
  def test_is_pingable_ip_address_format(
      self, ip_address, expected_result, mock_check_output):
    """Verifies is_pingable check if the ip_address format is valid."""
    result = host_utils.is_pingable(ip_address)

    self.assertEqual(result, expected_result)

  @mock.patch.object(
      shutil,
      "which",
      autospec=True,
      return_value=_TEST_CMD_PATH)
  def test_host_utils_get_command_path(self, mock_which):
    """Verify that the get_command_path() expected case works correctly."""

    self.assertEqual(_TEST_CMD_PATH, host_utils.get_command_path(_TEST_CMD))
    mock_which.assert_called_once_with(_TEST_CMD)

  @mock.patch.object(
      shutil,
      "which",
      autospec=True,
      return_value=None)
  def test_host_utils_get_command_path_error(self, mock_which):
    """Verify that the get_command_path() error case works correctly."""

    self.assertEqual(
        "", host_utils.get_command_path(os.path.basename(_TEST_CMD)))
    mock_which.assert_called_once_with(os.path.basename(_TEST_CMD))

  @mock.patch.object(
      shutil,
      "which",
      autospec=True,
      return_value=_TEST_CMD_PATH)
  def test_host_utils_has_command(self, mock_which):
    """Verify that the has_command() True case works correctly."""

    self.assertTrue(host_utils.has_command(os.path.basename(_TEST_CMD)))
    mock_which.assert_called_once_with(os.path.basename(_TEST_CMD))

  @mock.patch.object(
      shutil,
      "which",
      autospec=True,
      return_value=None)
  def test_host_utils_has_command_exception(self, mock_which):
    """Verify that has_command() returns False when an exception is raised."""

    self.assertFalse(
        host_utils.has_command(os.path.basename(_NONEXISTENT_CMD)))
    mock_which.assert_called_once_with(os.path.basename(_NONEXISTENT_CMD))

  @mock.patch.object(shutil, "which", return_value=None)
  def test_host_utils_has_command_false(self, mock_which):
    """Verify that the has_command() False case works correctly."""

    self.assertFalse(host_utils.has_command(os.path.basename(_TEST_CMD)))
    mock_which.assert_called_once_with(os.path.basename(_TEST_CMD))

  @mock.patch.object(
      subprocess,
      "check_output",
      autospec=True,
      return_value=_FAKE_IFCONFIG.encode())
  def test_host_utils_is_in_ifconfig_by_ip(self, mock_check_output):
    """Verify that the is_in_ifconfig() using an IP address."""

    self.assertTrue(host_utils.is_in_ifconfig("11.0.12.24"))
    mock_check_output.assert_called_once()

  @mock.patch.object(
      subprocess,
      "check_output",
      autospec=True,
      return_value=_FAKE_IFCONFIG.encode())
  def test_host_utils_is_in_ifconfig_by_mac(self, mock_check_output):
    """Verify that the is_in_ifconfig() using a MAC address."""

    self.assertTrue(host_utils.is_in_ifconfig("cb:a9:87:65:43:21"))
    mock_check_output.assert_called_once()

  @mock.patch.object(
      subprocess,
      "check_output",
      autospec=True,
      return_value=_FAKE_IFCONFIG.encode())
  def test_host_utils_is_in_ifconfig_missing(self, mock_check_output):
    """Verify that the is_in_ifconfig() missing IP."""

    ip_address = "192.168.201.1"
    self.assertFalse(host_utils.is_in_arp_table(ip_address))
    mock_check_output.assert_called_once()

  @mock.patch.object(host_utils, "has_command", return_value=False)
  def test_host_utils_is_sshable(self, mock_has_command):
    """Verify is_pingable works."""
    with mock.patch.object(
        subprocess,
        "check_output",
        side_effect=[None,
                     subprocess.CalledProcessError(-1, ["unreachable"])]):
      self.assertTrue(host_utils.is_sshable("127.0.0.1"))
      self.assertFalse(host_utils.is_sshable("127.0.0.2"))

  @mock.patch.object(
      subprocess,
      "check_output",
      autospec=True,
      side_effect=subprocess.CalledProcessError(-1, ["unreachable"]))
  def test_scp_from_device_and_to_device_raises_error(
      self, mock_subprocess):
    """Verify scp_from_device works."""
    with self.assertRaisesRegex(RuntimeError, "gobbly"):
      host_utils.scp_to_device("192.168.201.1", "gobbly", "gook")
    with self.assertRaisesRegex(RuntimeError, "gobbly"):
      host_utils.scp_from_device("192.168.201.1", "gobbly", "gook")

  @mock.patch.object(
      subprocess,
      "check_output",
      autospec=True,
      return_value=b"100%   16     7.0KB/s   00:00")
  def test_scp_to_and_from_device_success(self, mock_subprocess):
    """Verify scp_to_device works."""
    output = host_utils.scp_to_device("192.168.201.1", "gobbly", "gook")
    self.assertEqual(
        output, "100%   16     7.0KB/s   00:00",
        "scp_to_device should of returned {} but instead returned {}".format(
            "100%   16     7.0KB/s   00:00", output))
    output = host_utils.scp_from_device("192.168.201.1", "gobbly", "gook")
    self.assertEqual(
        output, "100%   16     7.0KB/s   00:00",
        "scp_from_device should of returned {} but instead returned {}".format(
            "100%   16     7.0KB/s   00:00", output))

  @mock.patch.object(subprocess,
                     "check_output",
                     autospec=True,
                     return_value=b"root")
  def test_ssh_command_success(self, mock_subprocess):
    """Verify ssh command works."""
    output = host_utils.ssh_command("192.168.201.1", ["whoami"])
    self.assertEqual(output, "root")

  @mock.patch.object(
      subprocess,
      "run",
      autospec=True,
      return_value=subprocess.CompletedProcess(
          args=[], returncode=0, stdout="root", stderr=""
      ),
  )
  def test_ssh_command_success_with_include_return_code(self, mock_subprocess):
    """Verify ssh command works with include_return_code."""
    output = host_utils.ssh_command(
        "192.168.201.1", ["whoami"], include_return_code=True
    )

    self.assertEqual(output, ("root", 0))
    mock_subprocess.assert_called_once()

  @mock.patch.object(
      subprocess,
      "check_output",
      autospec=True,
      side_effect=subprocess.CalledProcessError(-1, "whoami", "unreachable"))
  def test_ssh_command_fail(self, mock_subprocess):
    """Verify ssh_command raises error."""
    with self.assertRaisesRegex(RuntimeError, "whoami"):
      host_utils.ssh_command("192.168.201.1", ["whoami"])

  @mock.patch.object(
      shutil,
      "which",
      autospec=True,
      return_value="ykushcmd")
  @mock.patch.object(
      subprocess,
      "check_output",
      autospec=True,
      side_effect=[
          b"Attached YKUSH Boards:\n\nYK21624\n\nYK21624",
      ])
  def test_yepkit_detection(self, mock_subprocess, mock_which):
    """Test fetching yepkit serial numbers."""
    serials = host_utils.get_all_yepkit_serials()
    self.assertEqual(["YK21624", "YK21624"], serials)

  @mock.patch.object(
      subprocess,
      "check_output",
      return_value=b"Attached YKUSH Boards:\n\nNo YKUSH boards found")
  def test_yepkit_detection_no_yepkits(self, mock_subprocess):
    """Test no yepkits detected."""
    serials = host_utils.get_all_yepkit_serials()
    self.assertEqual([], serials)

  @mock.patch.object(
      subprocess,
      "check_output",
      autospec=True,
      side_effect=subprocess.CalledProcessError(-1,
                                                ["ykushcmd: command not found"])
  )
  def test_yepkit_detection_error(self, mock_subprocess):
    """Test an error fetching yepkit serial numbers."""
    serials = host_utils.get_all_yepkit_serials()
    self.assertEqual([], serials)

  @parameterized.named_parameters([("scp_from_device",
                                    host_utils.scp_from_device),
                                   ("scp_to_device", host_utils.scp_to_device)])
  @mock.patch.object(host_utils, "verify_key")
  def test_scp_with_ipv6_address(self, scp_method, _):
    """Verifies scp command when destination is ipv6 address."""
    ip_address = "1234:5678:9ab:cde:f12:345:6789:abc"
    local_file_path = "/tmp/dummy_file.txt"
    remote_file_path = "/home/pi/dummy_file.txt"

    with mock.patch.object(subprocess,
                           "check_output",
                           autospec=True) as mock_check_output:
      scp_method(
          ip_address=ip_address,
          local_file_path=local_file_path,
          remote_file_path=remote_file_path)
      mock_check_output.assert_called_once()
      self.assertIn(
          f"root@[{ip_address}]:{remote_file_path}",
          mock_check_output.call_args[0][0])

  @mock.patch.object(
      subprocess,
      "check_output",
      return_value=_FAKE_ARP_TABLE)
  def test_host_utils_get_all_connected_arp_ips(self, mock_check_output):
    """Verify that the get_all_connected_arp_ips returns a list."""
    return_value = host_utils.get_all_connected_arp_ips()
    self.assertIsInstance(return_value, list)
    self.assertEqual(len(return_value), 8)

  @mock.patch.object(
      subprocess,
      "check_output",
      return_value=_FAKE_ARP_TABLE)
  def test_host_utils_is_in_arp_table_by_ip(self, mock_check_output):
    """Verify that the is_in_arp_table() using an IP address."""

    self.assertTrue(host_utils.is_in_arp_table(_GOOD_IP))
    mock_check_output.assert_called_once()

  @mock.patch.object(
      subprocess,
      "check_output",
      return_value=_FAKE_ARP_TABLE)
  def test_host_utils_is_in_arp_table_by_mac(self, mock_check_output):
    """Verify that the is_in_arp_table() using a MAC address."""

    self.assertFalse(host_utils.is_in_arp_table(_BAD_IP))
    mock_check_output.assert_called_once()

  @mock.patch.object(
      subprocess,
      "check_output",
      return_value=_FAKE_ARP_TABLE)
  def test_host_utils_is_in_arp_table_missing(self, mock_check_output):
    """Verify that the is_in_arp_table() missing IP."""

    self.assertFalse(host_utils.is_in_arp_table(_BAD_IP))
    mock_check_output.assert_called_once()

  @mock.patch.object(
      subprocess,
      "check_output",
      side_effect=subprocess.CalledProcessError(-1, ["arp", "-e"]))
  def test_host_utils_is_in_arp_table_exception(self, mock_check_output):
    """Verify that is_in_arp_table() handles CalledProcessError internally."""
    self.assertFalse(host_utils.is_in_arp_table(_GOOD_IP))
    mock_check_output.assert_called_once()

  @mock.patch.object(host_utils, "verify_key")
  @mock.patch.object(subprocess, "check_output")
  def test_verify_key_info_in_scp(self, mock_check_output, mock_verify_key):
    """Verify ssh key is properly retrieved for scp call given key_info."""
    key_info = raspberry_pi_key.SSH_KEY_PRIVATE
    local_key_path = os.path.join(config.KEYS_DIRECTORY,
                                  key_info.package,
                                  key_info.file_name)
    host_utils.scp_to_device(
        ip_address="111.22.33.122",
        local_file_path="/tmp/dummy_file.txt",
        remote_file_path="/home/pi/dummy_file.txt",
        key_info=key_info)
    mock_check_output.assert_called_once()
    self.assertIn(local_key_path, mock_check_output.call_args[0][0])

  @mock.patch.object(
      subprocess,
      "check_output",
      side_effect=subprocess.CalledProcessError(-1, ["ifconfig"]))
  def test_host_utils_is_in_ifconfig_exception(self, mock_check_output):
    """Verify that is_in_ifconfig() handles CalledProcessError internally."""

    ip_address = "101.119.185.84"
    self.assertFalse(host_utils.is_in_ifconfig(ip_address))
    mock_check_output.assert_called_once()

  @mock.patch.object(host_utils, "verify_key")
  def test_generate_ssh_args_ssh_key(self, mock_verify_key):
    """Verify generate_ssh_args adds an ssh key to args."""
    key_info = raspberry_pi_key.SSH_KEY_PRIVATE
    ssh_args = host_utils.generate_ssh_args(
        "192.168.201.1", "whoami", user="root", key_info=key_info)
    expected_key_local_path = os.path.join(config.KEYS_DIRECTORY,
                                           key_info.package,
                                           key_info.file_name)
    self.assertIn(expected_key_local_path, ssh_args)
    mock_verify_key.assert_called_once_with(key_info)

  def test_check_ssh_key_exists_permissions_correct(self):
    """Test checking SSH key permissions."""
    stat_return_value = mock.Mock()
    stat_return_value.st_mode = 33152  # 0600
    with mock.patch.object(os.path, "exists", return_value=True):
      with mock.patch.object(os, "stat", return_value=stat_return_value):
        with mock.patch.object(os, "chmod") as mock_chmod:
          host_utils.verify_key(raspberry_pi_key.SSH_KEY_PRIVATE)
          mock_chmod.assert_not_called()

  def test_verify_key_key_exists_wrong_permissions_corrected(self):
    """Test verify_key() updating the permissions of an SSH key."""
    stat_return_value = mock.Mock()
    stat_return_value.st_mode = 33206  # 0666
    with mock.patch.object(os.path, "exists", return_value=True):
      with mock.patch.object(os, "stat", return_value=stat_return_value):
        with mock.patch.object(os, "chmod") as mock_chmod:
          host_utils.verify_key(unifi_poe_switch_key.SSH_KEY_PRIVATE)
          mock_chmod.assert_called()

  def test_verify_key_key_exists_wrong_permissions_could_not_be_corrected(
      self):
    """Test verify_key() failing to update the permissions of an SSH key."""
    stat_return_value = mock.Mock()
    stat_return_value.st_mode = 33206  # 0666
    with mock.patch.object(os.path, "exists", return_value=True):
      with mock.patch.object(os, "stat", return_value=stat_return_value):
        with mock.patch.object(
            os, "chmod", side_effect=OSError("Permission denied")):
          with self.assertRaisesRegex(ValueError, "chmod 400"):
            host_utils.verify_key(unifi_poe_switch_key.SSH_KEY_PRIVATE)

  @mock.patch.object(subprocess, "run", autospec=True, return_value=b"root")
  def test_curl_command_success_with_raise_error(self, mock_subprocess):
    """Verify curl command works."""
    output = host_utils.curl_command(
        ["https://www.google.com"], raise_error=True
    )

    self.assertIsNone(output)
    mock_subprocess.assert_called_once_with(
        ["curl", "https://www.google.com", "--fail-with-body"],
        capture_output=True,
        text=True,
        check=True,
    )

  @mock.patch.object(subprocess, "run", autospec=True, return_value=b"root")
  def test_curl_command_success_without_raise_error(self, mock_subprocess):
    """Verify curl command works."""
    output = host_utils.curl_command(
        ["https://www.google.com"], raise_error=False
    )

    self.assertIsNone(output)
    mock_subprocess.assert_called_once_with(
        ["curl", "https://www.google.com"],
        capture_output=True,
        text=True,
        check=True,
    )

  @mock.patch.object(subprocess, "run", autospec=True, return_value=b"root")
  def test_curl_command_raises_error(self, mock_subprocess):
    """Verify curl command raises error."""
    mock_subprocess.side_effect = subprocess.CalledProcessError(
        -1, ["curl", "https://www.google.com", "--fail-with-body"]
    )
    with self.assertRaisesRegex(RuntimeError, "curl"):
      host_utils.curl_command(["https://www.google.com"], raise_error=True)

  @mock.patch.object(subprocess, "check_output", autospec=True)
  def test_run_command_success(self, mock_check_output):
    mock_check_output.return_value = b"some command output"
    command_str = "echo hello"
    expected_output = "some command output"

    actual_output = host_utils.run_command(command_str)

    self.assertEqual(actual_output, expected_output)
    mock_check_output.assert_called_once_with(command_str.split(), timeout=None)

  @mock.patch.object(subprocess, "check_output", autospec=True)
  def test_run_command_success_with_timeout(self, mock_check_output):
    mock_check_output.return_value = b"output within timeout"
    command_str = "sleep 1"
    timeout_val = 2
    expected_output = "output within timeout"

    actual_output = host_utils.run_command(command_str, timeout=timeout_val)

    self.assertEqual(actual_output, expected_output)
    mock_check_output.assert_called_once_with(
        command_str.split(), timeout=timeout_val
    )

  @mock.patch.object(subprocess, "check_output", autospec=True)
  def test_run_command_failure_called_process_error(self, mock_check_output):
    command_str = "failing_command"
    mock_check_output.side_effect = subprocess.CalledProcessError(
        returncode=1, cmd=command_str.split(), output=b"error details"
    )

    with self.assertRaises(subprocess.CalledProcessError):
      host_utils.run_command(command_str)
    mock_check_output.assert_called_once_with(command_str.split(), timeout=None)

  @mock.patch.object(subprocess, "check_output", autospec=True)
  def test_run_command_failure_timeout_expired(self, mock_check_output):
    command_str = "timeout_command"
    timeout_val = 1
    mock_check_output.side_effect = subprocess.TimeoutExpired(
        cmd=command_str.split(), timeout=timeout_val
    )
    with self.assertRaises(subprocess.TimeoutExpired):
      host_utils.run_command(command_str, timeout=timeout_val)
    mock_check_output.assert_called_once_with(
        command_str.split(), timeout=timeout_val
    )


class DeletePathTests(unit_test_case.UnitTestCase):
  """Unit tests for host_utils.delete_path."""

  def setUp(self):
    super().setUp()
    self.test_device_name = "test_device"
    self.test_dir = self.create_tempdir("test_dir").full_path
    self.test_file = self.create_tempfile(
        os.path.join(self.test_dir, "test_file.txt")
    ).full_path

  def test_delete_directory_success(self):
    host_utils.delete_path(self.test_device_name, self.test_dir)
    self.assertFalse(os.path.exists(self.test_dir))

  def test_delete_file_success(self):
    host_utils.delete_path(self.test_device_name, self.test_file)
    self.assertFalse(os.path.exists(self.test_file))

  def test_catch_oserror(self):
    # Make the directory non-writable to trigger an OSError.
    os.chmod(self.test_dir, 0o400)
    with self.assertLogs(level="WARNING") as logger:
      host_utils.delete_path(self.test_device_name, self.test_dir)
    self.assertIn("failed to remove path", logger.output[0])
    # Make the directory writable again for cleanup.
    os.chmod(self.test_dir, 0o700)

  @mock.patch.object(os, "remove", autospec=True, side_effect=PermissionError)
  def test_catch_permission_error(self, mock_remove):
    with self.assertLogs(level="WARNING") as logger:
      host_utils.delete_path(self.test_device_name, self.test_file)
    self.assertIn("failed to remove path", logger.output[0])
    mock_remove.assert_called_once()

  def test_delete_nonexistent_path_raises_file_not_found_error_when_check_path_exists_is_true(
      self,
  ):
    with self.assertLogs(level="WARNING") as logger:
      host_utils.delete_path(
          self.test_device_name, "nonexistent_path_123", check_path_exists=True
      )
    self.assertIn("failed to remove path", logger.output[0])

  def test_delete_nonexistent_path_does_not_raise_error_when_check_path_exists_is_false(
      self,
  ):
    host_utils.delete_path(
        self.test_device_name, "nonexistent_path_123", check_path_exists=False
    )


if __name__ == "__main__":
  unit_test_case.main()
