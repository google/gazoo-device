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

"""Switchboard unit tests.

Unit testing documentation:
https://github.com/google/gazoo-device/blob/master/gazoo_device/tests/unit_tests/README.md  # pylint: disable=line-too-long
"""
import os.path
import unittest

from absl import flags
from absl.testing import absltest
from gazoo_device import config
from gazoo_device.tests.unit_tests.utils import unit_test_loader

_CUR_DIR = os.path.join(config.PACKAGE_PATH, "tests", "unit_tests",
                        "switchboard_tests")


def load_tests(loader: absltest.TestLoader,
               standard_tests: unittest.TestSuite,
               unused_pattern: str) -> unittest.TestSuite:
  """Called by unittest framework to load tests for this module."""
  if flags.FLAGS.skip_slow:
    return standard_tests  # Skip switchboard tests.
  standard_tests.addTests(
      unit_test_loader.discover_tests(
          loader,
          start_dir=_CUR_DIR,
          # Don't raise if no tests are selected under switchboard_tests/.
          # This check should only be performed by top-level unit test suites.
          raise_if_no_tests_found=False))
  return standard_tests
