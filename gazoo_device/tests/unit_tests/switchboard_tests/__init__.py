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

"""Switchboard unit tests."""
import os.path

from absl import flags
from gazoo_device import config

_CUR_DIR = os.path.join(config.PACKAGE_PATH, "tests", "unit_tests",
                        "switchboard_tests")


def load_tests(loader, standard_tests, unused_pattern):
  """Called by unittest framework to load tests for this module."""
  pattern_match = "*_test.py"

  if flags.FLAGS.file:
    filename = flags.FLAGS.file
    if not filename.endswith(".py"):
      filename += ".py"  # allow filenames without the .py extension
    pattern_match = filename
  elif flags.FLAGS.skip_slow:
    return standard_tests  # skip switchboard tests

  switchboard_tests = loader.discover(_CUR_DIR, pattern=pattern_match)
  standard_tests.addTests(switchboard_tests)
  return standard_tests
