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

"""Yepkit unit tests."""
import subprocess
from unittest import mock

from gazoo_device import errors
from gazoo_device.auxiliary_devices import yepkit
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.utility import host_utils
import immutabledict


_PERSISTENT_PROPERTIES = immutabledict.immutabledict({
    "total_ports": 3,
    "serial_number": "YK12345",
    "communication_address": "YK12345",
    "model": "yepkit",
})


class TestYepkit(fake_device_test_case.FakeDeviceTestCase):
  """Unit tests for Yepkit."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements("yepkit-2345")
    self.device_config["persistent"]["console_port_name"] = "YK12345"

    with mock.patch.object(host_utils, "has_command", return_value=True):
      self.uut = yepkit.Yepkit(
          self.mock_manager,
          self.device_config,
          log_directory=self.artifacts_directory)

  @mock.patch.object(
      host_utils, "get_all_yepkit_serials", return_value="fake serial number")
  def test_01_test_is_connected(self, mock_get_all_yepkit_serials):
    """Verify that is_connected works if serial number matches."""
    config = {"persistent": {"console_port_name": "fake serial number"}}
    self.assertTrue(
        yepkit.Yepkit.is_connected(config),
        "Expected is_config to return true.")

  def test_20_recover_raises_error(self):
    """Verify recover raises error."""
    err_msg = "some error"
    with self.assertRaisesRegex(errors.CheckDeviceReadyError, err_msg):
      self.uut.recover(errors.CheckDeviceReadyError(self.uut.name, err_msg))

  @mock.patch.object(host_utils, "has_command", return_value=True)
  def test_21_get_detection_with_bad_serial_number(self, mock_has_command):
    """Verify runtime error is thrown when serial number is too short."""
    self.device_config["persistent"]["console_port_name"] = "YK2"
    self.device_config["persistent"]["serial_number"] = "YK2"
    with self.assertRaisesRegex(errors.DeviceError,
                                "serial number YK2 is too short"):
      self.uut = yepkit.Yepkit(
          self.mock_manager,
          self.device_config,
          log_directory=self.artifacts_directory)
      self.uut.get_detection_info()

  @mock.patch.object(host_utils, "has_command", return_value=False)
  def test_22_yepkit_not_enabled(self, mock_has_command):
    """Verify runtime error is thrown when yepkit is not enabled."""
    del self.uut
    with self.assertRaisesRegex(errors.DependencyUnavailableError,
                                "'ykushcmd' is not installed"):
      self.uut = yepkit.Yepkit(
          self.mock_manager,
          self.device_config,
          log_directory=self.artifacts_directory)

  @mock.patch.object(host_utils, "has_command", return_value=True)
  def test_23_get_detection_info(self, mock_has_command):
    """Verify get_detection_info is successful using valid input."""
    self._test_get_detection_info(
        self.device_config["persistent"]["console_port_name"],
        device_class=yepkit.Yepkit,
        persistent_properties=_PERSISTENT_PROPERTIES)

  @mock.patch.object(subprocess, "check_output", return_value=b"OFF")
  def test_26_is_port_off(self, mock_check_output):
    """Verify is_port_off is successful if return value is byte string."""
    self.assertEqual(self.uut.switch_power.get_mode(port=1), "off")

  def test_28_shell_command_not_ykushcmd(self):
    """Verify a command not containing "ykushcmd" is detected."""
    command = "enterprise -serial"
    with self.assertRaisesRegex(errors.DeviceError,
                                "shell expected 'ykushcmd'"):
      self.uut.shell(command)

  @mock.patch.object(
      subprocess,
      "check_output",
      side_effect=[(b"Attached YKUSH Boards:\n"
                    b"\n"
                    b"YK21624\n")])
  def test_29_shell_command_no_return_code(self, mock_subprocess):
    """Verify a valid ykushcmd is successful and no return code is given."""
    command = "ykushcmd -l"
    result = self.uut.shell(command)
    self.assertIn("YK21624", result)

  @mock.patch.object(
      subprocess,
      "check_output",
      side_effect=[(b"Attached YKUSH Boards:\n"
                    b"\n"
                    b"YK21624\n")])
  def test_30_shell_command_include_return_code(self, mock_subprocess):
    """Verify a valid ykushcmd is successful and gives return code."""
    command = "ykushcmd -l"
    result, return_code = self.uut.shell(command, include_return_code=True)
    self.assertIn("YK21624", result)
    self.assertEqual(return_code, 0)

  @mock.patch.object(
      subprocess,
      "check_output",
      side_effect=[(b"-----:\n"
                    b"\n"
                    b"YKUSH Boards Command Application Help\n"
                    b"\n"
                    b"-----\n")])
  def test_31_shell_command_include_return_code_with_error(
      self, mock_subprocess):
    """Verify a BAD ykushcmd returns help text and includes return code -1."""
    command = "ykushcmd -z"
    result, return_code = self.uut.shell(command, include_return_code=True)
    self.assertIn("Application Help", result)
    self.assertEqual(return_code, -1)

  def test_200_yepkit_has_switch_power_capability(self):
    """Verify that has_capabilities returns true for switch_power capability."""
    self.assertTrue(self.uut.has_capabilities(["switch_power"]))


if __name__ == "__main__":
  fake_device_test_case.main()
