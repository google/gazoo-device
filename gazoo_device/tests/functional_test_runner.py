# Copyright 2021 Google LLC
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

"""Functional Test Runner.

Runs the on-device regression test suites for a particular testbed model.
See README.md for more information.
"""
import unittest

from gazoo_device.tests.functional_tests.utils import gazootest
from gazoo_device.tests.functional_tests.utils import runner_lib

SuiteCollectionType = runner_lib.SuiteCollectionType

# TODO(artorl): Open-source test suites.
TEST_SUITES = (
)


def load_tests(loader: unittest.TestLoader,
               standard_tests: unittest.TestSuite,
               pattern: str) -> unittest.TestSuite:
  """Called by unittest framework to load tests."""
  del loader  # We use our own test loader.
  del pattern  # Not used since we don't use the default discovery mechanism.
  testbed_config = gazootest.get_testbed_config()
  device_name = testbed_config.devices[0].name

  standard_tests.addTests(
      runner_lib.identify_tests_to_run(
          TEST_SUITES, _reorder_test_suites, device_name))
  return standard_tests


def _reorder_test_suites(
    test_suites: SuiteCollectionType) -> SuiteCollectionType:
  """Reorders test suites to ensure factory reset test runs before others."""
  # TODO(artorl): Add logic here once more test suites are open-sourced.
  return test_suites


if __name__ == "__main__":
  gazootest.main()
