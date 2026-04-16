# Copyright 2023 Google LLC
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

"""Capability unit test for commander flashing capability."""
import os
from unittest import mock

from gazoo_device import errors
from gazoo_device.base_classes import matter_device_base
from gazoo_device.capabilities import flash_build_commander
from gazoo_device.capabilities import matter_endpoints_accessor_pw_rpc
from gazoo_device.switchboard import switchboard
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.utility import host_utils
from gazoo_device.utility import subprocess_utils


class FlashBuildCommanderTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for FlashBuildCommander."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements("efr32matter-1234")
    self.mock_matter_endpoints_reset = mock.Mock(
        spec=matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc.reset
    )
    self.mock_switchboard = mock.Mock(spec=switchboard.SwitchboardDefault)
    self.mock_wait_for_bootup_complete = mock.Mock(
        spec=matter_device_base.MatterDeviceBase.wait_for_bootup_complete)
    self.uut = flash_build_commander.FlashBuildCommander(
        device_name="MOCK_DEVICE",
        serial_number="123456789",
        reset_endpoints_fn=self.mock_matter_endpoints_reset,
        switchboard=self.mock_switchboard,
        wait_for_bootup_complete_fn=self.mock_wait_for_bootup_complete)

  @mock.patch.object(
      host_utils, "has_command", return_value=False, autospec=True)
  def test_health_check_on_failure(self, mock_has_command):
    """Verifies health check on failure."""
    with self.assertRaisesRegex(
        errors.DependencyUnavailableError, "commander is not installed"):
      self.uut.health_check()

  @mock.patch.object(
      flash_build_commander.FlashBuildCommander, "health_check", autospec=True)
  def test_flash_device_fail_more_than_one_file(self, mock_health_check):
    """Verifies flash_device on failure when more than one build file."""
    with self.assertRaisesRegex(
        errors.DeviceError, "Only one .s37 type file can be flashed"):
      self.uut.flash_device(["a.s37", "b.s37"])

  @mock.patch.object(
      flash_build_commander.FlashBuildCommander, "health_check", autospec=True)
  def test_flash_device_fail_invalid_file_type(self, mock_health_check):
    """Verifies flash_device on failure for invalid file type."""
    with self.assertRaisesRegex(
        errors.DeviceError, "Only .s37 type file can be flashed"):
      self.uut.flash_device(["a.hex"])

  @mock.patch.object(
      flash_build_commander.FlashBuildCommander, "health_check", autospec=True)
  @mock.patch.object(os.path, "exists", return_value=False, autospec=True)
  def test_flash_device_fail_build_file_not_exists(
      self, mock_exists, mock_health_check):
    """Verifies flash_device on failure build file not exists."""
    with self.assertRaisesRegex(
        errors.DeviceError, "a.s37 does not exist"):
      self.uut.flash_device(["a.s37"])

  @mock.patch.object(
      subprocess_utils,
      "run_and_stream_output",
      return_value=(1, ""),
      autospec=True)
  @mock.patch.object(
      flash_build_commander.FlashBuildCommander, "health_check", autospec=True)
  @mock.patch.object(os.path, "exists", return_value=True, autospec=True)
  def test_flash_device_fail_return_code_not_zero(
      self, mock_exists, mock_health_check, mock_run_and_stream_output):
    """Verifies flash_device on failure return code not zero."""
    with self.assertRaisesRegex(
        errors.DeviceError, "flash command with commander failed"):
      self.uut.flash_device(["a.s37"])

  @mock.patch.object(
      subprocess_utils,
      "run_and_stream_output",
      return_value=(0, ""),
      autospec=True)
  @mock.patch.object(
      flash_build_commander.FlashBuildCommander, "health_check", autospec=True)
  @mock.patch.object(os.path, "exists", return_value=True, autospec=True)
  def test_upgrade_on_success(
      self, mock_exists, mock_health_check, mock_run_and_stream_output):
    """Verifies upgrade method on success."""
    self.uut.upgrade("a.s37")
    self.mock_switchboard.close_all_transports.assert_called_once()
    self.mock_switchboard.open_all_transports.assert_called_once()
    self.mock_wait_for_bootup_complete.assert_called_once()
    self.mock_matter_endpoints_reset.assert_called_once()
    mock_run_and_stream_output.assert_called_once()


if __name__ == "__main__":
  fake_device_test_case.main()
