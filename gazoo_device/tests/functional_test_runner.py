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

"""Functional Test Runner main.

Runs the on-device regression test suites for a particular testbed model.
See README.md for more information.
"""
from typing import Optional, Sequence

from absl import app
from absl import flags
import gazoo_device
from gazoo_device.tests.functional_tests import functional_test_runner_lib
from gazoo_device.tests.functional_tests.utils import suite_filter
from mobly import config_parser
from mobly import suite_runner

_CONFIG_FLAG = flags.DEFINE_string(
    name="config",
    default=None,
    help="Path to the Mobly .yml testbed config file",
    required=True,
    short_name="c")

SuiteCollectionType = suite_filter.SuiteCollectionType


def _reorder_test_suites(
    test_suites: SuiteCollectionType) -> SuiteCollectionType:
  """Reorders test suites to ensure factory reset run first."""
  return sorted(test_suites, key=functional_test_runner_lib.get_suite_index)


def _get_device_name(config_path: str) -> str:
  """Extracts the device name from the Mobly config."""
  config = config_parser.load_test_config_file(config_path)[0]
  controller_name = gazoo_device.MOBLY_CONTROLLER_CONFIG_NAME
  return config.controller_configs[controller_name][0]["id"]


def _run_tests(argv: Optional[Sequence[str]] = None) -> None:
  """Identifies tests to run and runs them via the Mobly test runner."""
  del argv  # Unused.
  device_name = _get_device_name(_CONFIG_FLAG.value)
  test_suite_dict = suite_filter.identify_tests_to_run(
      all_test_suites=functional_test_runner_lib.TEST_SUITES,
      reorder_test_suites=_reorder_test_suites,
      device_name=device_name)
  all_test_names = []
  for suite_class, test_names in test_suite_dict.items():
    for test_name in test_names:
      all_test_names.append(f"{suite_class.__name__}.{test_name}")
  suite_runner.run_suite(
      test_classes=test_suite_dict.keys(),
      argv=["--tests"] + all_test_names + ["--config", _CONFIG_FLAG.value])


def main(argv: Optional[Sequence[str]] = None) -> None:
  app.run(main=_run_tests, argv=argv)


if __name__ == "__main__":
  main()
