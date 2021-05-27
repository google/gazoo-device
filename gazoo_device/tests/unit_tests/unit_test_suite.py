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

"""Runs all unit tests for gazoo_device."""
import os
import unittest
from gazoo_device import config

UNIT_TEST_DIR = os.path.join(config.PACKAGE_PATH, "tests", "unit_tests")


def load_tests(loader, standard_tests, unused_pattern):
  """Called by unittest framework to load tests for this module."""
  folder = UNIT_TEST_DIR
  pattern_match = "test_*.py"
  unit_tests = loader.discover(
      folder, top_level_dir=UNIT_TEST_DIR, pattern=pattern_match)
  standard_tests.addTests(unit_tests)
  return standard_tests


if __name__ == "__main__":
  unittest.main()
