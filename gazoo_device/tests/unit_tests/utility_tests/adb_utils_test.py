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

"""This test script performs unit tests on functions in the adb_utils module."""
import grp
import json
import os
import subprocess
from unittest import mock

from absl.testing import parameterized
from gazoo_device import config
from gazoo_device import errors
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import adb_utils
from gazoo_device.utility import host_utils
import immutabledict

ADB_CMD_PATH = "/usr/bin/adb"
FAKE_ADB_DEVICES_OUTPUT = (
    "* daemon not running; starting now at tcp:1234\n"
    "* daemon started successfully\n"
    "List of devices attached\n"
    "04576e89\tdevice\n"
    "04576ee5\tsideload\n"
    "04576eaz\toffline\n"
    "04576abc\tbootloader\n"
    "04576bcd\tno permissions (some reason); see [some url]\n"
    "04576cde\trecovery\n"
    "04576def\tunauthorized\n"
    "04576efg\tunknown\n"
    "04576fgh\thost\n"
    "04576ghi\tthis-should-fail-to-parse\n"
    "123.45.67.89:5555\tdevice\n"
    "123.45.67.90:5555\tsideload\n"
    "123.45.67.91:5555\toffline\n"
    "123.45.67.92:5555\tbootloader\n"
    "123.45.67.93:5555\tno permissions (some reason); see [some url]\n"
    "123.45.67.94:5555\trecovery\n"
    "123.45.67.95:5555\tunauthorized\n"
    "123.45.67.96:5555\tunknown\n"
    "123.45.67.97:5555\thost\n"
    "123.45.67.98:5555\tthis-should-fail-to-parse\n"
    "\n")
PARSED_ADB_DEVICES = immutabledict.immutabledict({
    adb_utils.AdbDeviceState.DEVICE: ["04576e89", "123.45.67.89:5555"],
    adb_utils.AdbDeviceState.SIDELOAD: ["04576ee5", "123.45.67.90:5555"],
    adb_utils.AdbDeviceState.OFFLINE: ["04576eaz", "123.45.67.91:5555"],
    adb_utils.AdbDeviceState.BOOTLOADER: ["04576abc", "123.45.67.92:5555"],
    adb_utils.AdbDeviceState.NO_PERMISSIONS: ["04576bcd", "123.45.67.93:5555"],
    adb_utils.AdbDeviceState.RECOVERY: ["04576cde", "123.45.67.94:5555"],
    adb_utils.AdbDeviceState.UNAUTHORIZED: ["04576def", "123.45.67.95:5555"],
    adb_utils.AdbDeviceState.UNKNOWN: ["04576efg", "123.45.67.96:5555"],
    adb_utils.AdbDeviceState.HOST: ["04576fgh", "123.45.67.97:5555"],
    adb_utils.AdbDeviceState.UNRECOGNIZED: ["04576ghi", "123.45.67.98:5555"],
})
ADB_DEVICES = PARSED_ADB_DEVICES[adb_utils.AdbDeviceState.DEVICE]
SIDELOAD_DEVICES = PARSED_ADB_DEVICES[adb_utils.AdbDeviceState.SIDELOAD]
OFFLINE_DEVICES = PARSED_ADB_DEVICES[adb_utils.AdbDeviceState.OFFLINE]
FAKE_ADB_REBOOT = ""
FAKE_ADB_ROOT = ""

FAKE_SHELL = "abc\n123\n"
FASTBOOT_CMD_PATH = "/usr/bin/fastboot"
FASTBOOT_CMD = os.path.basename(FASTBOOT_CMD_PATH)
FASTBOOT_DEVICES = ["04576e89", "06011HFDD0165R", "04576ee5"]
FAKE_FASTBOOT = ("04576e89	fastboot\n"
                 "06011HFDD0165R Android Fastboot\n"
                 "04576ee5	fastboot\n\n")
FAKE_FASTBOOT_REBOOT = ("Rebooting...\n\n"
                        "Finished. Total time: 0.157s\n")

FAKE_PORT_FORWARDING_LIST = (
    "DEVICESERIAL_A tcp:8000 tcp:8000\n"
    "DEVICESERIAL_B tcp:8012 tcp:8034\n"
    "DEVICESERIAL_B tcp:8056 tcp:8078\n"
    "192.168.0.1:5555 tcp:8098 tcp:8099\n"
)

DEVICE_NAME = "somedevice"
DEVICE_ADB_SERIAL = "aabbccdd"
DEVICE_FASTBOOT_SERIAL = "aabbccdd"

TEST_GROUP_ENTRY = ("plugdev", None, 46, None)
TEST_GOOD_GROUP_LIST = [42, 46]
TEST_USER_UID = 1000
TEST_USER_NAME = "test_user"


class AdbUtilsTests(unit_test_case.UnitTestCase):
  """ADB utility tests."""

  def setUp(self):
    super().setUp()
    self.add_time_mocks()

  @mock.patch.object(host_utils, "has_command", return_value=False)
  def test_010_adb_utils_get_fastboot_path_raises_error(self,
                                                        mock_get_command_path):
    """Verify get_fastboot_path raises error if get_command_path fails."""
    with self.assertRaises(RuntimeError):
      adb_utils.get_fastboot_path()
    mock_get_command_path.assert_called()

  @mock.patch.object(
      host_utils, "get_command_path", return_value=FASTBOOT_CMD_PATH)
  def test_011_adb_utils_get_fastboot_path_calls_get_command_path(
      self, mock_get_command_path):
    """Verify get_fastboot_path calls get_command_path."""
    self.assertEqual(FASTBOOT_CMD_PATH, adb_utils.get_fastboot_path())
    mock_get_command_path.assert_called()

  @mock.patch.object(
      subprocess,
      "check_output",
      return_value=FAKE_FASTBOOT.encode("utf-8", errors="replace"))
  @mock.patch.object(
      adb_utils, "get_fastboot_path", return_value=FASTBOOT_CMD_PATH)
  def test_020_adb_utils_get_fastboot_devices_calls_get_fastboot_path(
      self, mock_get_fastboot_path, mock_subprocess):
    """Verify get_fastboot_devices calls get_fastboot_path."""
    self.assertEqual(FASTBOOT_DEVICES, adb_utils.get_fastboot_devices())
    mock_get_fastboot_path.assert_called()
    mock_subprocess.assert_called()

  @mock.patch.object(host_utils, "has_command", return_value=False)
  def test_021_adb_utils_get_fastboot_devices_bad_fastboot_path(
      self, mock_has_command):
    """Verify get_fastboot_devices skips get_fastboot_path."""
    devices = adb_utils.get_fastboot_devices(fastboot_path="bogus/path")
    self.assertEqual(devices, [])
    mock_has_command.assert_called()

  @mock.patch.object(
      subprocess,
      "check_output",
      side_effect=subprocess.CalledProcessError(-1, ["fastboot", "devices"]))
  @mock.patch.object(
      adb_utils, "get_fastboot_path", return_value=FASTBOOT_CMD_PATH)
  def test_022_adb_utils_get_fastboot_devices_subprocess_errors(
      self, mock_get_fastboot_path, mock_subprocess):
    """Verify get_fastboot_devices handles subprocess errors internally."""
    self.assertEqual([], adb_utils.get_fastboot_devices())
    mock_get_fastboot_path.assert_called()
    mock_subprocess.assert_called()

  @mock.patch.object(os.path, "exists", return_value=True)
  def test_023_adb_utils_get_fastboot_path_uses_correct_path(self, mock_exists):
    """Verify get_fastboot_devices skips get_fastboot_path."""
    path = adb_utils.get_fastboot_path(fastboot_path="genuine/path")
    self.assertEqual(path, "genuine/path")

  @mock.patch.object(
      adb_utils, "get_fastboot_devices", return_value=FASTBOOT_DEVICES)
  def test_030_adb_utils_is_fastboot_mode_true(self, mock_get_fastboot_devices):
    """Verify is_fastboot_mode returns True."""
    adb_serial = "04576e89"
    self.assertTrue(adb_utils.is_fastboot_mode(adb_serial))
    mock_get_fastboot_devices.assert_called()

  @mock.patch.object(
      adb_utils, "get_fastboot_devices", return_value=FASTBOOT_DEVICES)
  def test_031_adb_utils_is_fastboot_mode_false(self,
                                                mock_get_fastboot_devices):
    """Verify is_fastboot_mode returns False."""
    adb_serial = "bogus"
    self.assertFalse(adb_utils.is_fastboot_mode(adb_serial))
    mock_get_fastboot_devices.assert_called()

  @mock.patch.object(
      adb_utils, "get_sideload_devices", return_value=SIDELOAD_DEVICES)
  def test_032_adb_utils_is_sideload_mode_true(self, mock_get_sideload_devices):
    """Verify is_sideload_mode on True."""
    adb_serial = SIDELOAD_DEVICES[0]
    self.assertTrue(adb_utils.is_sideload_mode(adb_serial))
    mock_get_sideload_devices.assert_called_once()

  @mock.patch.object(
      adb_utils, "get_sideload_devices", return_value=SIDELOAD_DEVICES)
  def test_033_adb_utils_is_sideload_mode_false(self,
                                                mock_get_sideload_devices):
    """Verify is_sideload_mode on False."""
    adb_serial = "bogus"
    self.assertFalse(adb_utils.is_sideload_mode(adb_serial))
    mock_get_sideload_devices.assert_called_once()

  @mock.patch.object(
      subprocess,
      "check_output",
      return_value=FASTBOOT_CMD_PATH.encode("utf-8", errors="replace"))
  @mock.patch.object(grp, "getgrnam", return_value=TEST_GROUP_ENTRY)
  @mock.patch.object(os, "getgroups", return_value=TEST_GOOD_GROUP_LIST)
  @mock.patch.object(os, "getuid", return_value=TEST_USER_UID)
  @mock.patch.object(os, "getlogin", return_value=TEST_USER_NAME)
  def test_040_adb_utils_verify_user_has_fastboot(self, mock_getlogin,
                                                  mock_getuid, mock_getgroups,
                                                  mock_getgrnam,
                                                  mock_check_output):
    """Verify that verify_usr_has_fastboot works correctly."""
    try:
      adb_utils.verify_user_has_fastboot(DEVICE_NAME)
      mock_check_output.assert_called()
    except subprocess.CalledProcessError as err:
      self.fail("verify_user_has_fastboot() raised error: {!r}".format(err))

  @mock.patch.object(
      subprocess,
      "check_output",
      side_effect=subprocess.CalledProcessError(1, ["which", FASTBOOT_CMD]))
  def test_041_adb_utils_verify_user_has_fastboot_no_fastboot(
      self, mock_check_output):
    """Verify that verify_user_has_fastboot raises if fastboot not present."""
    with self.assertRaises(errors.DeviceError):
      adb_utils.verify_user_has_fastboot(DEVICE_NAME)
    mock_check_output.assert_called()

  @mock.patch.object(host_utils, "get_command_path", return_value=ADB_CMD_PATH)
  def test_050_adb_utils_get_adb_path_no_config_file(self,
                                                     mock_get_command_path):
    """Verify get_adb_path handles open errors internally."""
    config_file = os.path.join(self.artifacts_directory,
                               self._testMethodName + ".json")
    with mock.patch.dict(config.__dict__,
                         {"DEFAULT_GDM_CONFIG_FILE": config_file}):
      self.assertEqual(ADB_CMD_PATH, adb_utils.get_adb_path())
      mock_get_command_path.assert_called()

  @mock.patch.object(host_utils, "get_command_path", return_value=ADB_CMD_PATH)
  @mock.patch.object(json, "load", side_effect=ValueError)
  def test_051_adb_utils_get_adb_path_bad_config_data(self, mock_json_load,
                                                      mock_get_command_path):
    """Verify get_adb_path handles json.load errors internally."""
    config_file = os.path.join(self.artifacts_directory,
                               self._testMethodName + ".json")
    with open(config_file, "w") as gdm_config:
      gdm_config.write("{}")
    with mock.patch.dict(config.__dict__,
                         {"DEFAULT_GDM_CONFIG_FILE": config_file}):
      self.assertEqual(ADB_CMD_PATH, adb_utils.get_adb_path())
      mock_json_load.assert_called()
      mock_get_command_path.assert_called()

  @mock.patch.object(host_utils, "get_command_path", return_value=ADB_CMD_PATH)
  def test_052_adb_utils_get_adb_path_no_adb_path_in_config(
      self, mock_get_command_path):
    """Verify get_adb_path handles missing adb_path key errors internally."""
    config_file = os.path.join(self.artifacts_directory,
                               self._testMethodName + ".json")
    with open(config_file, "w") as gdm_config:
      gdm_config.write("{}")
    with mock.patch.dict(config.__dict__,
                         {"DEFAULT_GDM_CONFIG_FILE": config_file}):
      self.assertEqual(ADB_CMD_PATH, adb_utils.get_adb_path())
      mock_get_command_path.assert_called()

  @mock.patch.object(host_utils, "has_command", return_value=False)
  def test_053_adb_utils_get_adb_path_bad_adb_path_raises_error(
      self, mock_has_command):
    """Verify get_adb_path bad adb_path raises error."""
    config_file = os.path.join(self.artifacts_directory,
                               self._testMethodName + ".json")
    with open(config_file, "w") as gdm_config:
      gdm_config.write("{\"")
      gdm_config.write(config.ADB_BIN_PATH_CONFIG)
      gdm_config.write("\":")
      gdm_config.write("\"/some/bad/path\"}")
    with mock.patch.dict(config.__dict__,
                         {"DEFAULT_GDM_CONFIG_FILE": config_file}):
      with self.assertRaises(RuntimeError):
        adb_utils.get_adb_path()

  @mock.patch.object(os.path, "exists", return_value=True)
  def test_054_adb_utils_get_fadb_path_uses_correct_path(self, mock_exists):
    """Verify get_adb_path defaults to path passed in."""
    path = adb_utils.get_adb_path(adb_path="genuine/path")
    self.assertEqual(path, "genuine/path")

  @mock.patch.object(
      adb_utils, "_adb_command", return_value=FAKE_ADB_DEVICES_OUTPUT)
  def test_adb_devices(self, mock_adb_command):
    """Tests adb_devices()."""
    expected_output = []
    for state, identifiers in PARSED_ADB_DEVICES.items():
      for identifier in identifiers:
        expected_output.append((identifier, state))
    self.assertCountEqual(expected_output, adb_utils.adb_devices())

  @mock.patch.object(
      adb_utils, "_adb_command", return_value=(
          "* daemon not running; starting now at tcp:1234\n"
          "* daemon started successfully\n"))
  def test_adb_devices_no_output(self, mock_adb_command):
    """Tests adb_devices() when there's no device output."""
    self.assertFalse(adb_utils.adb_devices())

  @mock.patch.object(
      adb_utils, "_adb_command", return_value=FAKE_ADB_DEVICES_OUTPUT)
  def test_adb_utils_get_adb_devices(self, mock_adb_command):
    """Tests get_adb_devices()."""
    self.assertEqual(ADB_DEVICES, adb_utils.get_adb_devices())
    mock_adb_command.assert_called()

  @mock.patch.object(host_utils, "has_command", return_value=False)
  @mock.patch.object(os.path, "exists", return_value=False)
  def test_061_adb_utils_get_adb_devices_returns_list_when_no_adb(
      self, mock_exists, mock_has_command):
    """Verify get_adb_devices calls _adb_command."""
    self.assertEqual([], adb_utils.get_adb_devices())

  @mock.patch.object(
      adb_utils, "_adb_command", return_value=FAKE_ADB_DEVICES_OUTPUT)
  def test_062_adb_utils_get_sideload_devices_on_success(
      self, mock_adb_command):
    """Verify get_sideload_devices returns devices on success."""
    self.assertEqual(SIDELOAD_DEVICES, adb_utils.get_sideload_devices())
    mock_adb_command.assert_called_once_with("devices", adb_path=None)

  @mock.patch.object(adb_utils, "_adb_command", side_effect=RuntimeError())
  def test_063_adb_utils_get_sideload_devices_on_failure(
      self, mock_adb_command):
    """Verify get_sideload_devices returns empty list on failure."""
    self.assertEqual([], adb_utils.get_sideload_devices())
    mock_adb_command.assert_called_once_with("devices", adb_path=None)

  @parameterized.named_parameters(
      ("available", "04576e89", True),
      ("sideload", "04576ee5", False),
      ("offline", "04576eaz", False),
      ("not_present", "bogus", False))
  @mock.patch.object(
      adb_utils, "get_adb_devices", autospec=True, return_value=ADB_DEVICES)
  def test_is_adb_mode_serial_number(
      self, serial_number, expected_is_adb_mode, mock_get_adb_devices):
    """Tests is_adb_mode() for an ADB serial number identifier."""
    self.assertEqual(adb_utils.is_adb_mode(serial_number), expected_is_adb_mode)
    mock_get_adb_devices.assert_called_once()

  @parameterized.named_parameters(
      ("available_pingable", "123.45.67.89:5555", True, True),
      ("available_not_pingable", "123.45.67.89:5555", False, False),
      ("offline_not_pingable", "123.45.67.91:5555", False, False),
      ("offline_pingable", "123.45.67.91:5555", True, False),
      ("not_present_not_pingable", "123.45.67.123:5555", False, False),
      ("not_present_pingable", "123.45.67.123:5555", True, False))
  @mock.patch.object(
      adb_utils, "get_adb_devices", autospec=True, return_value=ADB_DEVICES)
  def test_is_adb_mode_ip_address_and_port(
      self, ip_address_and_port, is_pingable, expected_is_adb_mode,
      mock_get_adb_devices):
    """Tests is_adb_mode() for an IP address + port identifier."""
    with mock.patch.object(host_utils, "is_pingable", return_value=is_pingable):
      self.assertEqual(
          adb_utils.is_adb_mode(ip_address_and_port), expected_is_adb_mode)
    mock_get_adb_devices.assert_called_once()

  @mock.patch.object(adb_utils, "is_fastboot_mode", return_value=False)
  @mock.patch.object(adb_utils, "is_adb_mode", return_value=True)
  def test_080_adb_utils_is_device_online_yes_no(self, mock_is_adb_mode,
                                                 mock_is_fastboot_mode):
    """Verify is_device_online calls is_adb_mode and not is_fastboot_mode."""
    self.assertTrue(adb_utils.is_device_online(DEVICE_ADB_SERIAL))
    mock_is_adb_mode.assert_called()
    mock_is_fastboot_mode.assert_not_called()

  @mock.patch.object(adb_utils, "is_fastboot_mode", return_value=True)
  @mock.patch.object(adb_utils, "is_adb_mode", return_value=False)
  def test_081_adb_utils_is_device_online_no_yes(self, mock_is_adb_mode,
                                                 mock_is_fastboot_mode):
    """Verify is_device_online calls is_adb_mode and is_fastboot_mode."""
    self.assertTrue(adb_utils.is_device_online(DEVICE_ADB_SERIAL))
    mock_is_adb_mode.assert_called()
    mock_is_fastboot_mode.assert_called()

  @mock.patch.object(adb_utils, "is_fastboot_mode", return_value=False)
  @mock.patch.object(adb_utils, "is_adb_mode", return_value=False)
  def test_082_adb_utils_is_device_online_no_no(self, mock_is_adb_mode,
                                                mock_is_fastboot_mode):
    """Verify is_device_online calls is_adb_mode and is_fastboot_mode."""
    self.assertFalse(adb_utils.is_device_online(DEVICE_ADB_SERIAL))
    mock_is_adb_mode.assert_called()
    mock_is_fastboot_mode.assert_called()

  @mock.patch.object(adb_utils, "is_fastboot_mode", return_value=True)
  @mock.patch.object(adb_utils, "is_adb_mode", return_value=True)
  def test_083_adb_utils_is_device_online_yes_yes(self, mock_is_adb_mode,
                                                  mock_is_fastboot_mode):
    """Verify is_device_online calls is_adb_mode and not is_fastboot_mode."""
    self.assertTrue(adb_utils.is_device_online(DEVICE_ADB_SERIAL))
    mock_is_adb_mode.assert_called()
    mock_is_fastboot_mode.assert_not_called()

  @mock.patch.object(adb_utils, "get_adb_path", return_value=ADB_CMD_PATH)
  def test_100_adb_utils_adb_command_without_adb_serial(self,
                                                        mock_get_adb_path):
    """Verify _adb_command without adb_serial."""
    command = "fake_command"
    command_output = "fake output\n"
    mock_popen = mock.MagicMock(spec=subprocess.Popen, returncode=0)
    mock_popen.communicate.return_value = (command_output.encode(
        "utf-8", errors="replace"), None)
    with mock.patch.object(subprocess, "Popen", return_value=mock_popen):
      output = adb_utils._adb_command(command)
    self.assertEqual(command_output, output)
    mock_get_adb_path.assert_called()

  @mock.patch.object(adb_utils, "get_adb_path", return_value=ADB_CMD_PATH)
  def test_101_adb_utils_adb_command_with_string_command(
      self, mock_get_adb_path):
    """Verify _adb_command with string command."""
    command = "fake_command"
    command_output = "fake output\n"
    mock_popen = mock.MagicMock(spec=subprocess.Popen, returncode=0)
    mock_popen.communicate.return_value = (command_output.encode(
        "utf-8", errors="replace"), None)
    with mock.patch.object(subprocess, "Popen", return_value=mock_popen):
      output = adb_utils._adb_command(command, DEVICE_ADB_SERIAL)
    self.assertEqual(command_output, output)
    mock_get_adb_path.assert_called()

  @mock.patch.object(adb_utils, "get_adb_path", return_value=ADB_CMD_PATH)
  def test_102_adb_utils_adb_command_with_string_command(
      self, mock_get_adb_path):
    """Verify _adb_command with unicode command."""
    command = u"fake_command"
    command_output = "fake output\n"
    mock_popen = mock.MagicMock(spec=subprocess.Popen, returncode=0)
    mock_popen.communicate.return_value = (command_output.encode(
        "utf-8", errors="replace"), None)
    with mock.patch.object(subprocess, "Popen", return_value=mock_popen):
      output = adb_utils._adb_command(command, DEVICE_ADB_SERIAL)
    self.assertEqual(command_output, output)
    mock_get_adb_path.assert_called()

  @mock.patch.object(adb_utils, "get_adb_path", return_value=ADB_CMD_PATH)
  def test_103_adb_utils_adb_command_with_list_command(self, mock_get_adb_path):
    """Verify _adb_command with command list."""
    command = ["fake_command", "arg1"]
    command_output = "fake output\n"
    mock_popen = mock.MagicMock(spec=subprocess.Popen, returncode=0)
    mock_popen.communicate.return_value = (command_output.encode(
        "utf-8", errors="replace"), None)
    with mock.patch.object(subprocess, "Popen", return_value=mock_popen):
      output = adb_utils._adb_command(command, DEVICE_ADB_SERIAL)
    self.assertEqual(command_output, output)
    mock_get_adb_path.assert_called()

  @mock.patch.object(adb_utils, "get_adb_path", return_value=ADB_CMD_PATH)
  def test_104_adb_utils_adb_command_with_tuple_command(self,
                                                        mock_get_adb_path):
    """Verify _adb_command with tuple list."""
    command = ("fake_command", "arg1")
    command_output = "fake output\n"
    mock_popen = mock.MagicMock(spec=subprocess.Popen, returncode=0)
    mock_popen.communicate.return_value = (command_output.encode(
        "utf-8", errors="replace"), None)
    with mock.patch.object(subprocess, "Popen", return_value=mock_popen):
      output = adb_utils._adb_command(command, DEVICE_ADB_SERIAL)
    self.assertEqual(command_output, output)
    mock_get_adb_path.assert_called()

  @mock.patch.object(os.path, "exists", return_value=False)
  @mock.patch.object(host_utils, "has_command", return_value=False)
  def test_105_adb_utils_adb_command_bad_adb_path(self, mock_has_command,
                                                  mock_os_path_exists):
    """Verify _adb_command skips get_adb_path raises error on bad path."""
    with self.assertRaises(RuntimeError):
      adb_utils._adb_command(
          "fake_command", DEVICE_ADB_SERIAL, adb_path="bogus/path")

    mock_os_path_exists.assert_called()
    mock_has_command.assert_called()

  @mock.patch.object(adb_utils, "get_adb_path", return_value=ADB_CMD_PATH)
  def test_106_adb_utils_adb_command_include_return_code(
      self, mock_get_adb_path):
    """Verify _adb_command include_return_code returns tuple."""
    command = "fake_command"
    command_output = "fake output\n"
    command_return_code = 1
    mock_popen = mock.MagicMock(
        spec=subprocess.Popen, returncode=command_return_code)
    mock_popen.communicate.return_value = (command_output.encode(
        "utf-8", errors="replace"), None)
    with mock.patch.object(subprocess, "Popen", return_value=mock_popen):
      output, return_code = adb_utils._adb_command(
          command, DEVICE_ADB_SERIAL, include_return_code=True)
    self.assertEqual(command_output, output)
    self.assertEqual(command_return_code, return_code)
    mock_get_adb_path.assert_called()

  @mock.patch.object(adb_utils, "get_adb_path", return_value=ADB_CMD_PATH)
  def test_107_adb_utils_adb_command_with_offline(self, mock_get_adb_path):
    """Verify _adb_command succeeds if output includes "offline"."""
    command = "fake_command"
    mock_popen = mock.MagicMock(spec=subprocess.Popen, returncode=0)
    mock_popen.communicate.return_value = (
        FAKE_ADB_DEVICES_OUTPUT.encode("utf-8"), None)
    with mock.patch.object(subprocess, "Popen", return_value=mock_popen):
      output = adb_utils._adb_command(command)
    self.assertEqual(FAKE_ADB_DEVICES_OUTPUT, output)
    mock_get_adb_path.assert_called()

  @mock.patch.object(adb_utils, "_adb_command", return_value="Success\n")
  @mock.patch.object(os.path, "exists", return_value=True)
  def test_119_adb_utils_install_package_on_device_success(
      self, mock_path_exists, mock_adb_command):
    """Verify install_package_on_device on success."""
    fake_package_path = "/tmp/xxx.apk"
    adb_utils.install_package_on_device(
        fake_package_path, adb_serial=DEVICE_ADB_SERIAL, adb_path=ADB_CMD_PATH)
    mock_path_exists.assert_called_once_with(fake_package_path)
    mock_adb_command.assert_called_once_with(("install", fake_package_path),
                                             adb_serial=DEVICE_ADB_SERIAL,
                                             adb_path=ADB_CMD_PATH)

  @mock.patch.object(adb_utils, "_adb_command", return_value="Success\n")
  @mock.patch.object(os.path, "exists", return_value=True)
  def test_120_adb_utils_install_package_on_device_with_flags_success(
      self, mock_path_exists, mock_adb_command):
    """Verify install_package_on_device with flags on success."""
    fake_package_path = "/tmp/xxx.apk"
    adb_utils.install_package_on_device(
        fake_package_path,
        adb_serial=DEVICE_ADB_SERIAL,
        adb_path=ADB_CMD_PATH,
        allow_downgrade=True,
        allow_test_apk=True,
        reinstall=True,
        all_permissions=True)
    mock_path_exists.assert_called_once_with(fake_package_path)
    mock_adb_command.assert_called_once_with(
        ("install", "-d", "-g", "-r", "-t", fake_package_path),
        adb_serial=DEVICE_ADB_SERIAL,
        adb_path=ADB_CMD_PATH)

  @mock.patch.object(adb_utils, "_adb_command")
  @mock.patch.object(os.path, "exists")
  def test_121_adb_utils_install_package_on_device_exception(
      self, mock_path_exists, mock_adb_command):
    """Verify install_package_on_device raise exception."""
    # Note:
    #     install_package_on_device() raises exception when:
    #         1) package_path is not a file.
    #         2) 'Success\n' is not found in command response.
    fake_package_path = "/tmp/xxx.apk"
    # 1) package path not a file
    mock_path_exists.return_value = False
    with self.assertRaises(ValueError):
      adb_utils.install_package_on_device(
          fake_package_path,
          adb_serial=DEVICE_ADB_SERIAL,
          adb_path=ADB_CMD_PATH)
    mock_path_exists.assert_called_with(fake_package_path)
    # 2) 'Success\n' is not in command response
    mock_path_exists.return_value = True
    mock_adb_command.return_value = ""
    with self.assertRaises(errors.DeviceError):
      adb_utils.install_package_on_device(
          fake_package_path,
          adb_serial=DEVICE_ADB_SERIAL,
          adb_path=ADB_CMD_PATH)
    mock_adb_command.assert_called_with(("install", fake_package_path),
                                        adb_serial=DEVICE_ADB_SERIAL,
                                        adb_path=ADB_CMD_PATH)

  @mock.patch.object(adb_utils, "_adb_command", return_value="Success\n")
  def test_122_adb_utils_uninstall_package_on_device_success(
      self, mock_adb_command):
    """Verify uninstall_package_on_device on success."""
    fake_package_name = "com.google.fakepackage"
    adb_utils.uninstall_package_on_device(
        fake_package_name, adb_serial=DEVICE_ADB_SERIAL, adb_path=ADB_CMD_PATH)
    mock_adb_command.assert_called_once_with(("uninstall", fake_package_name),
                                             adb_serial=DEVICE_ADB_SERIAL,
                                             adb_path=ADB_CMD_PATH)

  @mock.patch.object(adb_utils, "_adb_command", return_value="")
  def test_123_adb_utils_uninstall_package_on_device_exception(
      self, mock_adb_command):
    """Verify uninstall_package_on_device raise exception."""
    fake_package_name = "com.google.fakepackage"
    with self.assertRaises(errors.DeviceError):
      adb_utils.uninstall_package_on_device(
          fake_package_name,
          adb_serial=DEVICE_ADB_SERIAL,
          adb_path=ADB_CMD_PATH)
    mock_adb_command.assert_called_once_with(("uninstall", fake_package_name),
                                             adb_serial=DEVICE_ADB_SERIAL,
                                             adb_path=ADB_CMD_PATH)

  @mock.patch.object(adb_utils, "_adb_command", return_value=FAKE_SHELL)
  @mock.patch.object(os.path, "isfile", return_value=True)
  def test_124_adb_utils_sideload_package_on_success(self, mock_os_path_isfile,
                                                     mock_adb_command):
    """Verify sideload_pacakge calls _adb_command."""
    package_path = "/tmp/abc"
    self.assertEqual(
        adb_utils.sideload_package(package_path, DEVICE_ADB_SERIAL), FAKE_SHELL)
    mock_os_path_isfile.assert_called_once_with(package_path)
    mock_adb_command.assert_called_once_with(("sideload", package_path),
                                             adb_serial=DEVICE_ADB_SERIAL,
                                             adb_path=None)

  @mock.patch.object(adb_utils, "_adb_command", return_value=FAKE_SHELL)
  @mock.patch.object(os.path, "isfile", return_value=False)
  def test_125_adb_utils_sideload_package_on_exception(self,
                                                       mock_os_path_isfile,
                                                       mock_adb_command):
    """Verify sideload_pacakge raises exception when package_path invalid."""
    package_path = "/tmp/abc"
    with self.assertRaises(RuntimeError):
      adb_utils.sideload_package(package_path, DEVICE_ADB_SERIAL)
    mock_os_path_isfile.assert_called_once_with(package_path)
    mock_adb_command.assert_not_called()

  @mock.patch.object(adb_utils, "_adb_command", return_value=FAKE_ADB_REBOOT)
  def test_140_adb_utils_enter_fastboot_calls_get_adb_path(
      self, mock_adb_command):
    """Verify enter_fastboot calls get_adb_path."""

    self.assertEqual(FAKE_ADB_REBOOT,
                     adb_utils.enter_fastboot(DEVICE_ADB_SERIAL))
    mock_adb_command.assert_called()

  @mock.patch.object(adb_utils, "_adb_command", return_value=FAKE_ADB_REBOOT)
  def test_141_adb_utils_enter_sideload(self, mock_adb_command):
    """Verify enter_sideload calls _adb_command."""
    # Note:
    #     Verify both 1) sideload auto reboot and 2) no auto reboot.

    # With auto_reboot: False
    self.assertEqual(
        FAKE_ADB_REBOOT,
        adb_utils.enter_sideload(DEVICE_ADB_SERIAL, auto_reboot=False))
    mock_adb_command.assert_called_with(("reboot", "sideload"),
                                        adb_serial=DEVICE_ADB_SERIAL,
                                        adb_path=None)
    # With auto_reboot: True
    self.assertEqual(
        FAKE_ADB_REBOOT,
        adb_utils.enter_sideload(DEVICE_ADB_SERIAL, auto_reboot=True))
    mock_adb_command.assert_called_with(("reboot", "sideload-auto-reboot"),
                                        adb_serial=DEVICE_ADB_SERIAL,
                                        adb_path=None)

  @mock.patch.object(
      subprocess,
      "check_output",
      return_value=FAKE_FASTBOOT_REBOOT.encode("utf-8", errors="replace"))
  @mock.patch.object(os.path, "exists", return_value=True)
  @mock.patch.object(
      adb_utils, "get_fastboot_path", return_value=FASTBOOT_CMD_PATH)
  def test_150_adb_utils_exit_fastboot_calls_get_fastboot_path(
      self, mock_get_fastboot_path, mock_os_path_exists, mock_subprocess):
    """Verify exit_fastboot calls get_fastboot_path."""
    self.assertEqual(FAKE_FASTBOOT_REBOOT,
                     adb_utils.exit_fastboot(DEVICE_ADB_SERIAL))
    mock_get_fastboot_path.assert_called()
    mock_os_path_exists.assert_called()
    mock_subprocess.assert_called()

  @mock.patch.object(os.path, "exists", return_value=False)
  @mock.patch.object(adb_utils, "get_fastboot_path")
  def test_151_adb_utils_exit_fastboot_bad_fastboot_path(
      self, mock_get_fastboot_path, mock_os_path_exists):
    """Verify exit_fastboot skips get_fastboot_path."""
    with self.assertRaises(RuntimeError):
      adb_utils.exit_fastboot(DEVICE_ADB_SERIAL, fastboot_path="bogus/path")
    mock_get_fastboot_path.assert_not_called()
    mock_os_path_exists.assert_called()

  @mock.patch.object(
      subprocess,
      "check_output",
      side_effect=subprocess.CalledProcessError(
          -1, ["timeout", "10.0", "fastboot", "reboot"]))
  @mock.patch.object(
      adb_utils, "get_fastboot_path", return_value=FASTBOOT_CMD_PATH)
  @mock.patch.object(os.path, "exists", return_value=True)
  def test_152_adb_utils_exit_fastboot_bad_request(self, mock_get_fastboot_path,
                                                   mock_os_path_exists,
                                                   mock_check_output):
    """Verify exit_fastboot returns None."""
    result = adb_utils.exit_fastboot(DEVICE_ADB_SERIAL)
    self.assertIsNone(result)
    mock_get_fastboot_path.assert_called()
    mock_os_path_exists.assert_called()
    mock_check_output.assert_called()

  @mock.patch.object(adb_utils, "_adb_command", return_value=FAKE_ADB_REBOOT)
  def test_160_adb_utils_reboot_device_calls_get_adb_path(
      self, mock_adb_command):
    """Verify reboot_device calls get_adb_path."""
    self.assertEqual(FAKE_ADB_REBOOT,
                     adb_utils.reboot_device(DEVICE_ADB_SERIAL))
    mock_adb_command.assert_called()

  @mock.patch.object(adb_utils, "_adb_command", return_value=FAKE_ADB_ROOT)
  def test_170_adb_utils_root_device_calls_get_adb_path(self, mock_adb_command):
    """Verify root_device calls get_adb_path."""
    self.assertEqual(FAKE_ADB_ROOT, adb_utils.root_device(DEVICE_ADB_SERIAL))
    mock_adb_command.assert_called()

  @mock.patch.object(
      adb_utils, "_adb_command", return_value=("pull output\n", 0))
  def test_180_adb_utils_pull_from_device_with_single_file(
      self, mock_adb_command):
    """Verify pull_file for a single source file."""
    sources = "/some/device/path/to/file"
    adb_utils.pull_from_device(DEVICE_ADB_SERIAL, sources)
    mock_adb_command.assert_called()

  @mock.patch.object(
      adb_utils, "_adb_command", return_value=("pull output\n", 0))
  def test_181_adb_utils_pull_from_device_with_multiple_files(
      self, mock_adb_command):
    """Verify pull_from_device calls get_adb_path."""
    sources = ["/some/device/path/to/file", "/some/device/path/to/other_file"]
    adb_utils.pull_from_device(DEVICE_ADB_SERIAL, sources)
    mock_adb_command.assert_called()

  @mock.patch.object(
      adb_utils, "_adb_command", return_value=("pull output\n", 1))
  def test_182_adb_utils_pull_from_device_bad_returncode(
      self, mock_adb_command):
    """Verify pull_from_device raises if ADB command fails."""
    sources = "/some/device/path/to/file"
    with self.assertRaises(RuntimeError):
      adb_utils.pull_from_device(DEVICE_ADB_SERIAL, sources)
    mock_adb_command.assert_called()

  @mock.patch.object(adb_utils, "_adb_command")
  @mock.patch.object(os.path, "exists", return_value=False)
  def test_183_adb_utils_pull_from_device_bad_destination_path(
      self, mock_os_path_exists, mock_adb_command):
    """Verify pull_from_device provided bad destination path."""
    sources = "/some/device/path/to/file"
    destination_path = "/bogus/path"
    with self.assertRaises(ValueError):
      adb_utils.pull_from_device(
          DEVICE_ADB_SERIAL, sources, destination_path=destination_path)
    mock_os_path_exists.assert_called()
    mock_adb_command.assert_not_called()

  @mock.patch.object(
      adb_utils, "_adb_command", return_value=("push output\n", 0))
  @mock.patch.object(os.path, "exists", return_value=True)
  def test_190_adb_utils_push_to_device_with_single_file(
      self, mock_os_path_exists, mock_adb_command):
    """Verify push_to_device sends a single file."""
    sources = "/fake/local/path"
    destination_path = "/fake/device/path"
    adb_utils.push_to_device(DEVICE_ADB_SERIAL, sources, destination_path)
    mock_os_path_exists.assert_called()
    mock_adb_command.assert_called()

  @mock.patch.object(
      adb_utils, "_adb_command", return_value=("push output\n", 0))
  @mock.patch.object(os.path, "exists", return_value=True)
  def test_191_adb_utils_push_to_device_with_multiple_files(
      self, mock_os_path_exists, mock_adb_command):
    """Verify push_to_device sends multiple files."""
    sources = ["/fake/local/path/to/file1", "/fake/local/path/to/file2"]
    destination_path = "/fake/device/path"
    adb_utils.push_to_device(DEVICE_ADB_SERIAL, sources, destination_path)
    mock_os_path_exists.assert_called()
    mock_adb_command.assert_called()

  @mock.patch.object(os.path, "exists", return_value=False)
  def test_192_adb_utils_push_to_device_fails_single_file(
      self, mock_os_path_exists):
    """Verify push_to_device fails single file path check."""
    sources = "/bogus/local/file"
    destination_path = "/fake/device/path"
    with self.assertRaises(ValueError):
      adb_utils.push_to_device(DEVICE_ADB_SERIAL, sources, destination_path)
    mock_os_path_exists.assert_called()

  @mock.patch.object(os.path, "exists", side_effect=[True, False])
  def test_193_adb_utils_push_to_device_fails_multiple_files(
      self, mock_os_path_exists):
    """Verify push_to_device fails multiple files path check."""
    sources = ["/fake/local/path/to/file1", "/fake/local/path/to/file2"]
    destination_path = "/fake/device/path"
    with self.assertRaises(ValueError):
      adb_utils.push_to_device(DEVICE_ADB_SERIAL, sources, destination_path)
    mock_os_path_exists.assert_called()

  @mock.patch.object(
      adb_utils, "_adb_command", return_value=("push output\n", 1))
  @mock.patch.object(os.path, "exists", return_value=True)
  def test_194_adb_utils_push_to_device_bad_returncode(self,
                                                       mock_os_path_exists,
                                                       mock_adb_command):
    """Verify push_file subprocess.communicate returns non-zero returncode."""
    sources = "/fake/local/path"
    destination_path = "/fake/device/path"
    with self.assertRaises(RuntimeError):
      adb_utils.push_to_device(DEVICE_ADB_SERIAL, sources, destination_path)
    mock_os_path_exists.assert_called()
    mock_adb_command.assert_called()

  @mock.patch.object(adb_utils, "_adb_command", return_value="fake\n")
  def test_200_adb_shell(self, mock_adb_command):
    """Verifies shell works as expected."""
    self.assertEqual("fake\n", adb_utils.shell("12345", 'echo "fake"'))
    mock_adb_command.assert_called_once_with(
        ["shell", 'echo "fake"'], "12345",
        adb_path=None, retries=mock.ANY, timeout=None,
        include_return_code=False)

  @mock.patch.object(adb_utils, "_adb_command", return_value=("fake\n", 0))
  def test_201_adb_shell_include_return_code(self, mock_adb_command):
    """Verifies shell include return code will return output and code tuple."""
    output, return_code = adb_utils.shell(
        "12345", 'echo "fake"', include_return_code=True)
    self.assertEqual("fake\n", output)
    self.assertEqual(0, return_code)
    mock_adb_command.assert_called_once_with(
        ["shell", 'echo "fake"'], "12345",
        adb_path=None, retries=mock.ANY, timeout=None, include_return_code=True)

  @mock.patch.object(
      adb_utils, "get_fastboot_path", return_value="/fake/path/to/fastboot")
  @mock.patch.object(os.path, "exists", return_value=False)
  def test_300_adb_utils_fastboot_command_without_fastboot_path(
      self, mock_exists, mock_get_fastboot_path):
    """Verify get_fastboot_path called when fastboot_path is not given."""
    with self.assertRaises(RuntimeError):
      adb_utils._fastboot_command("fake command")
    mock_get_fastboot_path.assert_called_once()
    mock_exists.assert_called()

  @mock.patch.object(
      adb_utils, "get_fastboot_path", return_value="/fake/path/to/fastboot")
  @mock.patch.object(os.path, "exists", return_value=False)
  def test_301_adb_utils_fastboot_command_with_bad_fastboot_path(
      self, mock_exists, mock_get_fastboot_path):
    """Verify _fastboot_command raise error when given a bad fastboot_path."""
    with self.assertRaises(RuntimeError):
      adb_utils._fastboot_command(
          "fake_command", fastboot_path="/fake/path/to/fastboot")
    mock_get_fastboot_path.assert_not_called()
    mock_exists.assert_called()

  @mock.patch.object(os.path, "exists", return_value=True)
  def test_302_adb_utils_fastboot_command_without_fastboot_serial(
      self, mock_exists):
    """Verify _fastboot_command without fastboot_serial."""
    fastboot_executable = "fastboot"
    command = "fake_command"
    command_output = "fake_command_output"
    mock_proc = mock.MagicMock(spec=subprocess.Popen)
    mock_proc.communicate.return_value = (command_output.encode(
        "utf-8", errors="replace"), None)
    with mock.patch.object(subprocess, "Popen", return_value=mock_proc):
      output = adb_utils._fastboot_command(
          command, fastboot_path=fastboot_executable)
    self.assertEqual(output, command_output)
    mock_exists.assert_called()

  @mock.patch.object(os.path, "exists", return_value=True)
  @mock.patch.object(
      adb_utils, "get_fastboot_path", return_value=FASTBOOT_CMD_PATH)
  def test_303_adb_utils_fastboot_command_with_string_command(
      self, mock_get_fastboot_path, mock_exists):
    """Verify _fastboot_command with string command."""
    command = "fake_command"
    command_output = "fake command output"
    mock_proc = mock.MagicMock(spec=subprocess.Popen)
    mock_proc.communicate.return_value = (command_output.encode(
        "utf-8", errors="replace"), None)
    with mock.patch.object(subprocess, "Popen", return_value=mock_proc):
      output = adb_utils._fastboot_command(command, DEVICE_FASTBOOT_SERIAL)
    self.assertEqual(command_output, output)
    mock_get_fastboot_path.assert_called()
    mock_exists.assert_called()

  @mock.patch.object(os.path, "exists", return_value=True)
  @mock.patch.object(
      adb_utils, "get_fastboot_path", return_value=FASTBOOT_CMD_PATH)
  def test_304_adb_utils_fastboot_command_with_string_command_unicode(
      self, mock_get_fastboot_path, mock_exists):
    """Verify _fastboot_command with unicode string command."""
    command = u"fake_command"
    command_output = "fake command output"
    mock_proc = mock.MagicMock(spec=subprocess.Popen)
    mock_proc.communicate.return_value = (command_output.encode(
        "utf-8", errors="replace"), None)
    with mock.patch.object(subprocess, "Popen", return_value=mock_proc):
      output = adb_utils._fastboot_command(command, DEVICE_FASTBOOT_SERIAL)
    self.assertEqual(command_output, output)
    mock_get_fastboot_path.assert_called()
    mock_exists.assert_called()

  @mock.patch.object(os.path, "exists", return_value=True)
  @mock.patch.object(
      adb_utils, "get_fastboot_path", return_value=FASTBOOT_CMD_PATH)
  def test_305_adb_utils_fastboot_command_with_list_command(
      self, mock_get_fastboot_path, mock_exists):
    """Verify _fastboot_command with command list."""
    command = ["fake_command", "arg1"]
    command_output = "fake output"
    mock_proc = mock.MagicMock(spec=subprocess.Popen, returncode=0)
    mock_proc.communicate.return_value = (command_output.encode(
        "utf-8", errors="replace"), None)
    with mock.patch.object(subprocess, "Popen", return_value=mock_proc):
      output = adb_utils._fastboot_command(command, DEVICE_FASTBOOT_SERIAL)
    self.assertEqual(command_output, output)
    mock_get_fastboot_path.assert_called()
    mock_exists.assert_called()

  @mock.patch.object(os.path, "exists", return_value=True)
  @mock.patch.object(
      adb_utils, "get_fastboot_path", return_value=FASTBOOT_CMD_PATH)
  def test_306_adb_utils_fastboot_command_with_tuple_command(
      self, mock_get_fastboot_path, mock_exists):
    """Verify _fastboot_command with command tuple."""
    command = ("fake_command", "arg1")
    command_output = "fake output"
    mock_proc = mock.MagicMock(spec=subprocess.Popen, returncode=0)
    mock_proc.communicate.return_value = (command_output.encode(
        "utf-8", errors="replace"), None)
    with mock.patch.object(subprocess, "Popen", return_value=mock_proc):
      output = adb_utils._fastboot_command(command, DEVICE_FASTBOOT_SERIAL)
    self.assertEqual(command_output, output)
    mock_get_fastboot_path.assert_called()
    mock_exists.assert_called()

  @mock.patch.object(os.path, "exists", return_value=True)
  @mock.patch.object(
      adb_utils, "get_fastboot_path", return_value=FASTBOOT_CMD_PATH)
  def test_307_adb_utils_fastboot_command_include_return_code(
      self, mock_get_fastboot_path, mock_exists):
    """Verify _fastboot_command include_return_code works."""
    command = "fake_command"
    command_output = "fake output"
    command_return_code = 1
    mock_proc = mock.MagicMock(
        spec=subprocess.Popen, returncode=command_return_code)
    mock_proc.communicate.return_value = (command_output.encode(
        "utf-8", errors="replace"), None)
    with mock.patch.object(subprocess, "Popen", return_value=mock_proc):
      output, return_code = adb_utils._fastboot_command(
          command, DEVICE_FASTBOOT_SERIAL, include_return_code=True)
    self.assertEqual(command_output, output)
    self.assertEqual(command_return_code, return_code)
    mock_get_fastboot_path.assert_called()
    mock_exists.assert_called()

  @mock.patch.object(adb_utils, "_fastboot_command")
  def test_308_adb_utils_fastboot_unlock_device(self, mock_fastboot_command):
    """Verify fastbook_unlock_device calls _fastboot_command correctly."""
    fastboot_serial = "fake_fastboot_serial"
    fastboot_path = FASTBOOT_CMD_PATH
    fastboot_timeout = 30.0
    adb_utils.fastboot_unlock_device(
        fastboot_serial, fastboot_path=fastboot_path, timeout=fastboot_timeout)
    mock_fastboot_command.assert_called()
    mock_fastboot_command.assert_called_with(("flashing", "unlock"),
                                             fastboot_serial=fastboot_serial,
                                             fastboot_path=fastboot_path,
                                             timeout=fastboot_timeout)

  @mock.patch.object(adb_utils, "_fastboot_command")
  def test_309_adb_utils_fastboot_lock_device(self, mock_fastboot_command):
    """Verify fastbook_lock_device calls _fastboot_command correctly."""
    fastboot_serial = "fake_fastboot_serial"
    fastboot_path = FASTBOOT_CMD_PATH
    fastboot_timeout = 30.0
    adb_utils.fastboot_lock_device(
        fastboot_serial, fastboot_path=fastboot_path, timeout=fastboot_timeout)
    mock_fastboot_command.assert_called()
    mock_fastboot_command.assert_called_with(("flashing", "lock"),
                                             fastboot_serial=fastboot_serial,
                                             fastboot_path=fastboot_path,
                                             timeout=fastboot_timeout)

  @mock.patch.object(adb_utils, "_fastboot_command")
  def test_310_adb_utils_fastboot_wipe_userdata(self, mock_fastboot_command):
    """Verify fastboot_wipe_userdata calls _fastboot_command correctly."""
    fastboot_serial = "fake_fastboot_serial"
    fastboot_path = FASTBOOT_CMD_PATH
    fastboot_timeout = 30.0
    adb_utils.fastboot_wipe_userdata(
        fastboot_serial, fastboot_path=fastboot_path, timeout=fastboot_timeout)
    mock_fastboot_command.assert_called()
    mock_fastboot_command.assert_called_with(
        "-w",
        fastboot_serial=fastboot_serial,
        fastboot_path=fastboot_path,
        timeout=fastboot_timeout)

  @mock.patch.object(adb_utils, "_adb_command", autospec=True, return_value=(
      "connected to 12.34.56.78:5555", 0))
  @mock.patch.object(
      adb_utils, "is_adb_mode", autospec=True, side_effect=[False, True])
  def test_connect_success(self, mock_is_adb_mode, mock_adb_command):
    """Tests connect() when the ADB command succeeds."""
    adb_utils.connect("12.34.56.78:5555")
    mock_adb_command.assert_called_once()
    self.assertEqual(mock_is_adb_mode.call_count, 2)
    mock_is_adb_mode.assert_called_with("12.34.56.78:5555")

  @mock.patch.object(adb_utils, "_adb_command", autospec=True, return_value=(
      "failed to connect to '12.34.56.78:5555': Connection refused", 0))
  @mock.patch.object(adb_utils, "is_adb_mode", autospec=True)
  def test_connect_failure_adb_command_error(
      self, mock_is_adb_mode, mock_adb_command):
    """Tests connect() when the ADB command fails."""
    with self.assertRaisesRegex(
        errors.DeviceError, "Unable to connect to device '12.34.56.78:5555'"):
      adb_utils.connect("12.34.56.78:5555")
    self.assertGreater(mock_adb_command.call_count, 1)
    mock_is_adb_mode.assert_not_called()

  @mock.patch.object(adb_utils, "_adb_command", autospec=True, return_value=(
      "connected to 12.34.56.78:5555", 0))
  @mock.patch.object(
      adb_utils, "is_adb_mode", autospec=True, return_value=False)
  def test_connect_failure_not_in_adb_devices(
      self, mock_is_adb_mode, mock_adb_command):
    """Tests connect() when device is not seen in 'adb devices'."""
    with self.assertRaisesRegex(
        errors.DeviceError,
        "'12.34.56.78:5555' was not found in 'adb devices'"):
      adb_utils.connect("12.34.56.78:5555")
    mock_adb_command.assert_called_once()
    mock_is_adb_mode.assert_called_with("12.34.56.78:5555")
    self.assertGreater(mock_is_adb_mode.call_count, 1)

  @mock.patch.object(adb_utils, "_adb_command", autospec=True, return_value=(
      "disconnected 12.34.56.78:5555", 0))
  @mock.patch.object(adb_utils, "adb_devices", autospec=True, side_effect=[
      [("12.34.56.78:5555", adb_utils.AdbDeviceState.DEVICE)], []])
  def test_disconnect_success(self, mock_adb_devices, mock_adb_command):
    """Tests disconnect() when the ADB command succeeds."""
    adb_utils.disconnect("12.34.56.78:5555")
    mock_adb_command.assert_called_once()
    self.assertEqual(mock_adb_devices.call_count, 2)

  @mock.patch.object(adb_utils, "_adb_command", autospec=True, return_value=(
      "error: no such device '12.34.56.78:5555'", 1))
  @mock.patch.object(adb_utils, "adb_devices", autospec=True)
  def test_disconnect_failure_adb_command_error(
      self, mock_adb_devices, mock_adb_command):
    """Tests disconnect() when the ADB command fails."""
    with self.assertRaisesRegex(
        errors.DeviceError,
        "Unable to disconnect ADB from device '12.34.56.78:5555'"):
      adb_utils.disconnect("12.34.56.78:5555")
    self.assertGreater(mock_adb_command.call_count, 1)
    mock_adb_devices.assert_not_called()

  @mock.patch.object(adb_utils, "_adb_command", autospec=True, return_value=(
      "disconnected 12.34.56.78:5555", 0))
  @mock.patch.object(
      adb_utils, "adb_devices", autospec=True,
      return_value=[("12.34.56.78:5555", adb_utils.AdbDeviceState.DEVICE)])
  def test_disconnect_failure_not_in_adb_devices(
      self, mock_adb_devices, mock_adb_command):
    """Tests disconnect() when device is seen in 'adb devices'."""
    with self.assertRaisesRegex(
        errors.DeviceError,
        "'12.34.56.78:5555' was still found in 'adb devices'"):
      adb_utils.disconnect("12.34.56.78:5555")
    mock_adb_command.assert_called_once()
    self.assertGreater(mock_adb_devices.call_count, 1)

  @mock.patch.object(adb_utils, "get_adb_path", return_value=ADB_CMD_PATH)
  def test_313_adb_command_terminate(self, mock_get_adb_path):
    """Verify adb connect method."""
    command = "fake_command"
    command_output = "fake output\n"
    mock_proc = mock.MagicMock(spec=subprocess.Popen, returncode=0)
    mock_proc.communicate.side_effect = subprocess.TimeoutExpired(
        cmd=command, timeout=1)
    mock_proc.communicate.return_value = (command_output.encode(
        "utf-8", errors="replace"), None)
    with mock.patch.object(subprocess, "Popen", return_value=mock_proc):
      with mock.patch.object(mock_proc, "terminate") as mock_terminate:
        with self.assertRaises(subprocess.TimeoutExpired):
          adb_utils.shell(DEVICE_ADB_SERIAL, command, timeout=1)
        mock_terminate.assert_called_once()

  @mock.patch.object(adb_utils, "get_adb_path", return_value=ADB_CMD_PATH)
  def test_314_adb_shell_retry_failed(self, mock_adb_command):
    """Verify shell works as expected."""
    command_output = "error: closed"
    mock_proc = mock.MagicMock(spec=subprocess.Popen, returncode=0)
    mock_proc.communicate.return_value = (command_output.encode(
        "utf-8", errors="replace"), None)
    with mock.patch.object(subprocess, "Popen", return_value=mock_proc):
      with self.assertRaises(errors.DeviceError):
        adb_utils.shell('echo "fake"', "12345")

  @mock.patch.object(adb_utils, "_adb_command", return_value=("Output", 0))
  def test_320_adb_utils_add_port_forwarding_success(self, mock_adb_command):
    """Verifies add_port_forwarding on success."""
    output = adb_utils.add_port_forwarding(host_port=123,
                                           device_port=456,
                                           adb_serial=DEVICE_ADB_SERIAL,
                                           adb_path=ADB_CMD_PATH)

    mock_adb_command.assert_called_once_with(
        ("forward", "tcp:123", "tcp:456"),
        adb_serial=DEVICE_ADB_SERIAL,
        adb_path=ADB_CMD_PATH,
        include_return_code=True)
    self.assertEqual(output, "Output")

  @mock.patch.object(adb_utils, "_adb_command", return_value=("Error", 1))
  def test_321_adb_utils_add_port_forwarding_exception(self, mock_adb_command):
    """Verifies add_port_forwarding raises exception."""
    with self.assertRaises(RuntimeError):
      adb_utils.add_port_forwarding(host_port=123,
                                    device_port=456,
                                    adb_serial=DEVICE_ADB_SERIAL,
                                    adb_path=ADB_CMD_PATH)

    mock_adb_command.assert_called_once_with(
        ("forward", "tcp:123", "tcp:456"),
        adb_serial=DEVICE_ADB_SERIAL,
        adb_path=ADB_CMD_PATH,
        include_return_code=True)

  @mock.patch.object(adb_utils, "_adb_command", return_value=("Output", 0))
  def test_325_adb_utils_remove_port_forwarding_success(self, mock_adb_command):
    """Verifies remove_port_forwarding on success."""
    output = adb_utils.remove_port_forwarding(host_port=123,
                                              adb_serial=DEVICE_ADB_SERIAL,
                                              adb_path=ADB_CMD_PATH)

    mock_adb_command.assert_called_once_with(
        ("forward", "--remove", "tcp:123"),
        adb_serial=DEVICE_ADB_SERIAL,
        adb_path=ADB_CMD_PATH,
        include_return_code=True)
    self.assertEqual(output, "Output")

  @mock.patch.object(adb_utils, "_adb_command", return_value=("Error", 1))
  def test_326_adb_utils_remove_port_forwarding_exception(self,
                                                          mock_adb_command):
    """Verifies remove_port_forwarding on raise exception."""
    with self.assertRaises(RuntimeError):
      adb_utils.remove_port_forwarding(host_port=123,
                                       adb_serial=DEVICE_ADB_SERIAL,
                                       adb_path=ADB_CMD_PATH)

    mock_adb_command.assert_called_once_with(
        ("forward", "--remove", "tcp:123"),
        adb_serial=DEVICE_ADB_SERIAL,
        adb_path=ADB_CMD_PATH,
        include_return_code=True)

  @parameterized.named_parameters(
      ("Empty result", "", None, []),
      ("All rules", FAKE_PORT_FORWARDING_LIST, None,
       [(8000, 8000), (8012, 8034), (8056, 8078), (8098, 8099)]),
      ("Rules for DeviceB", FAKE_PORT_FORWARDING_LIST, "DEVICESERIAL_B",
       [(8012, 8034), (8056, 8078)]),
      ("Rules for adb-over-ip device", FAKE_PORT_FORWARDING_LIST,
       "192.168.0.1:5555", [(8098, 8099)]),
  )
  @mock.patch.object(adb_utils, "_adb_command")
  def test_list_port_forwarding_success(
      self, cmd_output, adb_serial, expected_result, mock_adb_command):
    """Verifies list_port_forwarding on success."""
    mock_adb_command.return_value = (cmd_output, 0)

    result = adb_utils.list_port_forwarding(adb_serial=adb_serial,
                                            adb_path=ADB_CMD_PATH)

    mock_adb_command.assert_called_once_with(("forward", "--list"),
                                             adb_serial=None,
                                             adb_path=ADB_CMD_PATH,
                                             include_return_code=True)
    self.assertEqual(result, expected_result)

  @mock.patch.object(adb_utils, "_adb_command", return_value=("Error", 1))
  def test_list_port_forwarding_failed(self, mock_adb_command):
    """Verifies list_port_forwarding on raise exception."""
    with self.assertRaises(RuntimeError):
      adb_utils.list_port_forwarding(
          adb_serial=DEVICE_ADB_SERIAL, adb_path=ADB_CMD_PATH)

    mock_adb_command.assert_called_once_with(("forward", "--list"),
                                             adb_serial=None,
                                             adb_path=ADB_CMD_PATH,
                                             include_return_code=True)

  @mock.patch.object(adb_utils, "_fastboot_command")
  def test_330_adb_utils_fastboot_check_is_unlocked(self,
                                                    mock_fastboot_command):
    """Verifies fastboot_check_is_unlocked function return correct result."""
    fastboot_serial = "fake_fastboot_serial"
    unlocked_output = "unlocked: yes"
    locked_output = "unlocked: no"

    mock_fastboot_command.return_value = unlocked_output
    unlocked_expected = adb_utils.fastboot_check_is_unlocked(
        fastboot_serial=fastboot_serial)
    mock_fastboot_command.return_value = locked_output
    locked_expected = adb_utils.fastboot_check_is_unlocked(
        fastboot_serial=fastboot_serial)

    self.assertTrue(unlocked_expected)
    self.assertFalse(locked_expected)

  @mock.patch.object(adb_utils, "_fastboot_command")
  def test_331_adb_utils_fastboot_check_is_unlocked_exception(
      self, mock_fastboot_command):
    """Verifies fastboot_check_is_unlocked function raises with bad output."""
    fastboot_serial = "fake_fastboot_serial"
    unknown_output = "something went wrong"
    mock_fastboot_command.return_value = unknown_output

    with self.assertRaises(RuntimeError):
      adb_utils.fastboot_check_is_unlocked(fastboot_serial=fastboot_serial)

  @mock.patch.object(
      adb_utils, "_adb_command", return_value=("bugreport output\n", 0))
  def test_340_adb_utils_bugreport(self, mock_adb_command):
    """Verifies bugreport."""
    adb_utils.bugreport(DEVICE_ADB_SERIAL)
    mock_adb_command.assert_called()

  @mock.patch.object(
      adb_utils, "_adb_command", return_value=("bugreport output\n", 1))
  def test_341_adb_utils_bugreport_bad_returncode(
      self, mock_adb_command):
    """Verifies bugreport raises if ADB command fails."""
    with self.assertRaises(RuntimeError):
      adb_utils.bugreport(DEVICE_ADB_SERIAL)
    mock_adb_command.assert_called()

  @mock.patch.object(adb_utils, "_adb_command")
  @mock.patch.object(os.path, "exists", return_value=False)
  def test_342_adb_utils_pull_from_device_bad_destination_path(
      self, mock_os_path_exists, mock_adb_command):
    """Verifies bugreport provided bad destination path."""
    destination_path = "/bogus/path"
    with self.assertRaises(ValueError):
      adb_utils.bugreport(DEVICE_ADB_SERIAL, destination_path=destination_path)
    mock_os_path_exists.assert_called()
    mock_adb_command.assert_not_called()

  @mock.patch.object(
      adb_utils, "_adb_command", autospec=True,
      return_value=("restarting in TCP mode port: 5555", 0))
  def test_tcpip_success(self, mock_adb_command):
    """Tests tcpip() when the ADB command succeeds."""
    adb_utils.tcpip("123abcde", 5555)
    mock_adb_command.assert_called_once()

  @mock.patch.object(
      adb_utils, "_adb_command", autospec=True,
      return_value=("adb: tcpip: invalid port: 120321", 1))
  def test_tcpip_failure(self, mock_adb_command):
    """Tests tcpip() when the ADB command fails."""
    with self.assertRaisesRegex(
        RuntimeError, "ADB failed to start listening on port 120321"):
      adb_utils.tcpip("123abcde", 120321)
    mock_adb_command.assert_called_once()

  @parameterized.named_parameters(
      ("ip_address_no_port_arg", "12.34.56.78", None, "12.34.56.78:5555"),
      ("ip_address_with_port_no_port_arg",
       "12.34.56.78:1234", None, "12.34.56.78:1234"),
      ("ip_address_no_port_with_port_arg",
       "12.34.56.78", 1234, "12.34.56.78:1234"))
  def test_get_adb_over_ip_identifier(
      self, identifier, port, expected_identifier):
    """Tests get_adb_over_ip_identifier() with an ADB over IP identifier."""
    if port is None:
      actual_identifier = adb_utils.get_adb_over_ip_identifier(identifier)
    else:
      actual_identifier = adb_utils.get_adb_over_ip_identifier(
          identifier, port=port)
    self.assertEqual(actual_identifier, expected_identifier)

  def test_get_adb_over_ip_identifier_adb_serial(self):
    """Tests get_adb_over_ip_identifier() with an ADB serial."""
    with self.assertRaisesRegex(ValueError, "'abcde123' is not an IP address"):
      adb_utils.get_adb_over_ip_identifier("abcde123")

  @mock.patch.object(adb_utils, "_adb_command", return_value=("", 0))
  def test_wait_for_device_adb(self, mock_adb_command):
    """Tests wait_for_device_adb."""
    adb_utils.wait_for_device("abcde123", 1)  # Should not raise timeout.

  @mock.patch.object(adb_utils, "_adb_command", return_value=("", 124))
  def test_wait_for_device_adb_timeout(self, mock_adb_command):
    """Tests wait_for_device_adb when it times out."""
    with self.assertRaises(errors.CommunicationTimeoutError):
      adb_utils.wait_for_device("abcde123", 1)

  @mock.patch.object(adb_utils, "is_adb_mode", side_effect=[True, False])
  def test_wait_for_device_offline(self, mock_is_adb_mode):
    """Tests wait_for_device_offline returns once device is offline."""
    adb_utils.wait_for_device_offline("abcde123", 1, 0.005)

  @mock.patch.object(adb_utils, "is_adb_mode", return_value=True)
  def test_wait_for_device_offline_timeout(self, mock_is_adb_mode):
    """Tests wait_for_device_raises error when times out waiting."""
    with self.assertRaises(errors.CommunicationTimeoutError):
      adb_utils.wait_for_device_offline("abcde123", 0.005, 0.001)


if __name__ == "__main__":
  unit_test_case.main()
