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

"""Unit tests for subprocess_utils.py."""

import os
import select
import subprocess
from unittest import mock

from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import subprocess_utils


class SubprocessUtilsTest(unit_test_case.UnitTestCase):

  def setUp(self):
    super().setUp()
    self.add_time_mocks()
    self.mock_os_set_blocking = self.enter_context(
        mock.patch.object(os, "set_blocking", autospec=True))
    mock_stdout_fp = mock.MagicMock()
    mock_stdout_fp.read.return_value = "output\n"
    mock_select_result = [mock_stdout_fp], [], []
    self.mock_select = self.enter_context(
        mock.patch.object(select, "select", autospec=True,
                          return_value=mock_select_result))

    self.mock_subprocess = mock.MagicMock()
    self.mock_subprocess_popen = self.enter_context(
        mock.patch.object(subprocess, "Popen"))
    self.mock_subprocess_popen.return_value.__enter__.return_value = (
        self.mock_subprocess)

  def test_run_and_stream_output(self):
    """Ensures run_and_stream_output should run as expected."""
    cmd_args = ["echo", "hello"]
    timeout = 5
    # Let the process run first 3 time unit and return 0 after that.
    self.mock_subprocess.poll.side_effect = [None, None, None, 0]
    self.mock_subprocess.wait.return_value = 0

    return_code, output = subprocess_utils.run_and_stream_output(
        cmd_args, timeout)

    self.mock_os_set_blocking.assert_called_once()
    self.assertEqual(self.mock_select.call_count, 3)
    self.assertEqual(return_code, 0)
    self.assertEqual(output, "output\noutput\noutput\n")

  def test_run_and_stream_output_timeout(self):
    """Ensures run_and_stream_output raise TimeoutExpired if timeout."""
    cmd_args = ["echo", "hello"]
    timeout = 5
    # Let the process be always running.by Popen.poll() return None
    # Popen.wait(time) might throw TimeoutExpired exception in this case
    self.mock_subprocess.poll.return_value = None
    self.mock_subprocess.wait.side_effect = subprocess.TimeoutExpired(
        cmd=mock.ANY, timeout=mock.ANY)

    with self.assertRaises(subprocess.TimeoutExpired):
      subprocess_utils.run_and_stream_output(cmd_args, timeout)
    self.mock_select.assert_called()

  def test_run_and_stream_output_with_shell_enabled(self):
    """Test run_and_stream_output with shell enabled ."""
    cmd_args = ["echo", "hello"]
    timeout = 5
    shell = True
    self.mock_subprocess.poll.return_value = 0
    self.mock_subprocess.wait.return_value = 0
    _, _ = subprocess_utils.run_and_stream_output(
        cmd_args, timeout, shell)

    self.mock_subprocess_popen.assert_called_once_with(cmd_args,
                                                       shell=True,
                                                       encoding="utf-8",
                                                       errors="replace",
                                                       stdout=subprocess.PIPE,
                                                       stderr=subprocess.STDOUT)

if __name__ == "__main__":
  unit_test_case.main()
