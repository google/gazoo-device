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
"""Capability unit test for matter_app_controls_shell module."""
from unittest import mock

from gazoo_device.capabilities import matter_app_controls_shell
from gazoo_device.capabilities import shell_ssh
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
    self.uut = matter_app_controls_shell.MatterSampleAppShell(
        device_name=_FAKE_DEVICE_NAME,
        shell_fn=self.fake_shell,
        close_transport_fn=self.fake_switchboard_close,
        open_transport_fn=self.fake_switchboard_open,
        pigweed_port=_FAKE_PORT)

  def test_is_present(self):
    """Verifies is_present on success."""
    self.fake_shell.return_value = "exists"
    self.assertTrue(self.uut.is_present)

  def test_is_running(self):
    """Verifies is_running on success."""
    self.fake_shell.return_value = _FAKE_PROCESS_ID
    self.assertTrue(self.uut.is_running)

  def test_get_process_ids(self):
    """Verifies get_process_ids on success."""
    self.fake_shell.return_value = _FAKE_PROCESS_ID
    self.assertEqual([_FAKE_PROCESS_ID], self.uut.get_process_ids())

  @mock.patch.object(
      matter_app_controls_shell.MatterSampleAppShell,
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


if __name__ == "__main__":
  fake_device_test_case.main()
