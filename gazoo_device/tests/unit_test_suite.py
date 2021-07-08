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
from absl import flags
from absl.testing import absltest
from gazoo_device import config

_UNIT_TEST_DIR = os.path.join(config.PACKAGE_PATH, "tests", "unit_tests")

flags.DEFINE_string(
    "file",
    default=None,
    help="Name of unit test file to run.",
    short_name="f")
flags.DEFINE_boolean(  # Consumed by switchboard_tests/__init__.py.
    "skip_slow",
    default=False,
    help="Skip switchboard tests.",
    short_name="s")


def load_tests(loader, standard_tests, unused_pattern):
  """Called by unittest framework to load tests for this module."""
  pattern_match = "*_test.py"

  if flags.FLAGS.file:
    filename = flags.FLAGS.file
    if not filename.endswith(".py"):
      filename += ".py"  # allow filenames without the .py extension
    pattern_match = filename

  unit_tests = loader.discover(
      _UNIT_TEST_DIR, top_level_dir=_UNIT_TEST_DIR, pattern=pattern_match)
  standard_tests.addTests(unit_tests)
  return standard_tests


if __name__ == "__main__":
  absltest.main()
