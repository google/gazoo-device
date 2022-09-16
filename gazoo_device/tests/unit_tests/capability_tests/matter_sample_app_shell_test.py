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
"""Capability unit test for matter_sample_app_shell module."""
import os
import time
from unittest import mock

from gazoo_device import errors
from gazoo_device.capabilities import file_transfer_scp
from gazoo_device.capabilities import matter_sample_app_shell
from gazoo_device.capabilities import shell_ssh
from gazoo_device.capabilities.interfaces import matter_endpoints_base
from gazoo_device.primary_devices import raspberry_pi_matter
from gazoo_device.switchboard import switchboard
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.utility import retry

_FAKE_DEVICE_NAME = "fake-device-name"
_FAKE_PORT = 2
_FAKE_PROCESS_ID = "123"


class MatterSampleAppShellTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for MatterSampleAppShell."""

  def setUp(self):
    super().setUp()
    self.fake_shell = mock.Mock(spec=shell_ssh.ShellSSH.shell)
    self.fake_switchboard_close = mock.Mock(
        spec=switchboard.SwitchboardDefault.close_transport)
    self.fake_switchboard_open = mock.Mock(
        spec=switchboard.SwitchboardDefault.open_transport)
    self.fake_send_file_to_device = mock.Mock(
        spec=file_transfer_scp.FileTransferScp.send_file_to_device)
    self.fake_wait_for_bootup_complete = mock.Mock(
        spec=raspberry_pi_matter.RaspberryPiMatter.wait_for_bootup_complete)
    self.fake_reset_endpoints = mock.Mock(
        spec=matter_endpoints_base.MatterEndpointsBase.reset)
    self.uut = matter_sample_app_shell.MatterSampleAppShell(
        device_name=_FAKE_DEVICE_NAME,
        shell_fn=self.fake_shell,
        close_transport_fn=self.fake_switchboard_close,
        open_transport_fn=self.fake_switchboard_open,
        pigweed_port=_FAKE_PORT,
        send_file_to_device_fn=self.fake_send_file_to_device,
        wait_for_bootup_complete_fn=self.fake_wait_for_bootup_complete,
        reset_endpoints_fn=self.fake_reset_endpoints)

  def test_is_present(self):
    """Verifies is_present on success."""
    self.fake_shell.return_value = "", 0
    self.assertTrue(self.uut.is_present)

  def test_has_service(self):
    """Verifies has_service on success."""
    self.fake_shell.return_value = "", 0
    self.assertTrue(self.uut.has_service)

  def test_is_service_enabled(self):
    """Verifies is_service_enabled on success."""
    self.fake_shell.return_value = "enabled"
    self.assertTrue(self.uut.is_service_enabled)

  def test_is_running(self):
    """Verifies is_running on success."""
    self.fake_shell.return_value = _FAKE_PROCESS_ID
    self.assertTrue(self.uut.is_running)

  def test_get_process_ids(self):
    """Verifies get_process_ids on success."""
    self.fake_shell.return_value = _FAKE_PROCESS_ID
    self.assertEqual([_FAKE_PROCESS_ID], self.uut.get_process_ids())

  def test_enable_service(self):
    """Verifies enable_service on success."""
    self.fake_shell.side_effect = ["disabled", ""]
    self.uut.enable_service()

  @mock.patch.object(
      matter_sample_app_shell.MatterSampleAppShell,
      "get_process_ids",
      return_value=[_FAKE_PROCESS_ID])
  @mock.patch.object(retry, "retry")
  def test_restart(self, mock_retry, mock_get_process):
    """Verifies restart on success."""
    self.uut.restart()

    self.fake_switchboard_close.assert_called_once()
    self.fake_shell.assert_called_once()
    mock_retry.assert_called_once()
    self.fake_switchboard_open.assert_called_once()
    self.fake_wait_for_bootup_complete.assert_called_once()

  @mock.patch.object(time, "sleep")
  @mock.patch.object(retry, "retry")
  @mock.patch.object(os, "access", return_value=True)
  @mock.patch.object(os.path, "exists", return_value=True)
  def test_upgrade_on_success(
      self, mock_exists, mock_access, mock_retry, mock_sleep):
    """Verifies upgrade on success."""
    self.uut.upgrade("/path/to/sample-app-binary")

    self.fake_switchboard_close.assert_called_once()
    self.assertEqual(2, self.fake_shell.call_count)
    self.fake_send_file_to_device.assert_called_once()
    mock_retry.assert_called_once()
    self.fake_switchboard_open.assert_called_once()
    self.fake_wait_for_bootup_complete.assert_called_once()
    self.fake_reset_endpoints.assert_called_once()

  @mock.patch.object(os.path, "exists", return_value=False)
  def test_upgrade_on_failure_not_exists(self, mock_exists):
    """Verifies upgrade on failure when the sample app file not exists."""
    with self.assertRaisesRegex(errors.DeviceError, "does not exist"):
      self.uut.upgrade("not-exists")

  @mock.patch.object(os, "access", return_value=False)
  @mock.patch.object(os.path, "exists", return_value=True)
  def test_upgrade_on_failure_not_executable(self, mock_exists, mock_access):
    """Verifies upgrade on failure when the sample app is not executable."""
    with self.assertRaisesRegex(errors.DeviceError, "not executable"):
      self.uut.upgrade("not-executable")

  def test_factory_reset(self):
    """Verifies factory reset on success."""
    self.uut.factory_reset()


if __name__ == "__main__":
  fake_device_test_case.main()
