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

"""Unit tests for utility/multiprocessing_utils.py."""
import multiprocessing
import os
import sys
from unittest import mock

from absl.testing import parameterized
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import multiprocessing_utils

_get_multiprocessing_spawn_executable = (
    multiprocessing_utils._get_multiprocessing_spawn_executable)


class MultiprocessingUtilsTests(unit_test_case.UnitTestCase):
  """Multiprocessing utility tests."""

  @parameterized.named_parameters(
      ("no_executable", None, None),
      ("executable_python_3_10", "/usr/bin/python3", "/usr/bin/python3"),
      ("executable_python_3_11", b"/usr/bin/python3", "/usr/bin/python3"),
  )
  @mock.patch.object(multiprocessing.spawn, "get_executable", autospec=True)
  def test_get_multiprocessing_spawn_executable(
      self, get_executable_return_value, expected_executable,
      mock_get_executable):
    """Tests _get_multiprocessing_spawn_executable."""
    mock_get_executable.return_value = get_executable_return_value
    self.assertEqual(
        multiprocessing_utils._get_multiprocessing_spawn_executable(),
        expected_executable)


if __name__ == "__main__":
  unit_test_case.main()
