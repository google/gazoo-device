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
"""Unit tests for gazoo_device.utility.faulthandler_utils.py."""

import os
import unittest
from unittest import mock
from absl.testing import parameterized

from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import faulthandler_utils
from gazoo_device.utility import signal_utils


class FaulthandlerUtilsTest(unit_test_case.UnitTestCase):
  """Unit tests for gazoo_device.utility.faulthandler_utils.py."""

  @parameterized.named_parameters(
      ("empty_file_deleted_on_sigterm", "", True, False),
      ("empty_file_deleted_without_sigterm", "", False, False),
      ("nonempty_file_not_deleted_on_sigterm", "some-test-logs", True, True),
      ("nonempty_file_deleted_without_sigterm", "some-test-logs", False, False),
    )
  @mock.patch.object(signal_utils, "has_sigterm_occurred", autospec=True)
  @unittest.skip("Disable faulthandler to investigate b/268778945")
  def test_atexit_handler(
      self, mock_file_contents,
      mock_has_sigterm_occurred_return_value,
      expected_file_to_exist,
      mock_has_sigterm_occurred):
    """Tests atexit faulthandler for graceful and SIGTERM termination."""
    mock_has_sigterm_occurred.return_value = (
        mock_has_sigterm_occurred_return_value
    )
    temp_file = self.create_tempfile()
    with open(temp_file, "w") as f:
      f.write(mock_file_contents)
      faulthandler_utils._stop_traceback_dumps(f)
      self.assertEqual(os.path.exists(f.name), expected_file_to_exist)
