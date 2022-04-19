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

"""Unit tests for functional test suites and functional test configs."""
import os
from unittest import mock

from absl.testing import absltest
from absl.testing import flagsaver
from absl.testing import parameterized
from gazoo_device.tests.functional_tests import auxiliary_device_common_test_suite
from gazoo_device.tests.functional_tests import file_transfer_test_suite
from gazoo_device.tests.functional_tests import switchboard_test_suite
from gazoo_device.tests.functional_tests.utils import configs_test
from gazoo_device.tests.functional_tests.utils import suite_filter
from mobly import asserts
from mobly import config_parser
from mobly import records

OUTPUT_DIRECTORY = "/tmp"

_TEST_SUITES = (
    switchboard_test_suite.SwitchboardTestSuite,
    auxiliary_device_common_test_suite.AuxiliaryDeviceCommonTestSuite,
    file_transfer_test_suite.FileTransferTestSuite)


def reorder_by_name(
    test_suite_list: suite_filter.SuiteCollectionType
) -> suite_filter.SuiteCollectionType:
  """Reorders test suites to ensure upgrade and factory reset run first."""

  def _get_suite_name(suite: suite_filter.SuiteType) -> str:
    return suite.__name__

  return sorted(test_suite_list, key=_get_suite_name)


class FunctionalTestSuiteAndConfigUnitTests(configs_test.ConfigsBaseTest):
  """Unit tests for functional test suites and configs."""
  MODULE_NAME = "gazoo_device"

  @mock.patch.object(
      suite_filter, "_get_test_config",
      return_value={
          "do_not_run_tests": ["FakeTest.test_do_not_run"],
          "volatile_tests": ["FakeTest.test_rerun"],
          "slow_tests": []
      })
  def test_mobly_test_retries_and_skips(self, _):
    """Uses a fake mobly test to verify filters skip and retry as expected."""

    class FakeTest(suite_filter.SuiteFilterBase):
      """Fake Mobly test to verify functionality."""

      def __init__(self, configs):
        super().__init__(configs)
        self.iteration = 0

      @classmethod
      def is_applicable_to(cls, device_type: str, device_class,
                           device_name: str) -> bool:
        return True

      @classmethod
      def requires_pairing(cls) -> bool:
        return False

      def test_pass(self):
        """This test should pass."""

      def test_rerun(self):
        """This test should pass on the second attempt."""
        self.iteration += 1
        asserts.assert_equal(self.iteration, 2)

      def test_do_not_run(self):
        """This test should not run."""
        asserts.fail("this test should not run")

    fake_config = config_parser.TestRunConfig()
    name = suite_filter._CONTROLLER_MODULE.MOBLY_CONTROLLER_CONFIG_NAME
    fake_config.controller_configs[name] = [{"id": "cambrionix-1234"}]
    fake_config.log_path = OUTPUT_DIRECTORY
    summary_file = os.path.join(OUTPUT_DIRECTORY, "summary.yaml")
    fake_config.summary_writer = records.TestSummaryWriter(summary_file)
    test = FakeTest(fake_config)

    with mock.patch.object(suite_filter.mobly_base, "open"):
      with mock.patch.object(suite_filter.mobly_base.yaml, "safe_load_all"):
        test.run()
    self.assertTrue(test.results.skipped, "test_do_not_run should be skipped")
    self.assertEqual(
        test.results.skipped[0].test_name, "test_do_not_run",
        f"test_do_not_run should be skipped "
        f"instead of {test.results.skipped[0].test_name}")
    self.assertFalse(test.results.error,
                     f"Test results error: {test.results.error}")
    self.assertLen(
        test.results.failed, 1,
        f"Initial test rerun should have failed: {test.results.error}")
    self.assertLen(test.results.passed, 2)

  def test_label_expansion(self):
    """Ensures test config is expanded properly with test suite."""
    test_config = {
        "do_not_run_tests": ["A.test_1", "A.test_2", "B"],
        "slow_tests": ["A.test_3"],
        "volatile_tests": ["A.test_4"],
        "expected": "X"
    }
    final_test_config = {
        "do_not_run_tests": [
            "A.test_1",
            "A.test_2",
            "B.test_1",
            "B.test_2",
            "B.test_3",
            "B.test_4",
        ],
        "slow_tests": ["A.test_3"],
        "volatile_tests": ["A.test_4"],
        "expected": "X"
    }
    b_tests = ["test_1", "test_2", "test_3", "test_4"]
    suite_filter._expand_test_suite_name_if_necessary("B", b_tests, test_config)
    self.assertEqual(test_config, final_test_config)

  @parameterized.named_parameters(
      {
          "testcase_name": "_default",
          "test_name": "A.test_stable",
          "run_flag": suite_filter.RunType.FULL,
          "skip": False
      },
      {
          "testcase_name": "_do_not_run",
          "test_name": "A.test_do_not_run",
          "run_flag": suite_filter.RunType.FULL,
          "skip": True
      },
      {
          "testcase_name": "_presubmit_slow",
          "test_name": "A.test_slow",
          "run_flag": suite_filter.RunType.PRESUBMIT,
          "skip": True
      },
      {
          "testcase_name": "_presubmit_volatile",
          "test_name": "A.test_volatile",
          "run_flag": suite_filter.RunType.PRESUBMIT,
          "skip": False
      },
      {
          "testcase_name": "_stable_volatile",
          "test_name": "B.test_volatile_and_slow",
          "run_flag": suite_filter.RunType.STABLE,
          "skip": True
      },
      {
          "testcase_name": "_volatile_volatile",
          "test_name": "A.test_volatile",
          "run_flag": suite_filter.RunType.VOLATILE,
          "skip": False
      },
      {
          "testcase_name": "_volatile_slow",
          "test_name": "A.test_slow",
          "run_flag": suite_filter.RunType.VOLATILE,
          "skip": True
      },
  )
  def test_skip_tests(self, test_name, run_flag, skip):
    """Verifies all the conditions of _get_skip_reason."""
    test_config = {
        suite_filter.TestLabel.DO_NOT_RUN.value: ["A.test_do_not_run"],
        suite_filter.TestLabel.SLOW.value: [
            "A.test_slow", "B.test_volatile_and_slow"
        ],
        suite_filter.TestLabel.VOLATILE.value: [
            "A.test_volatile", "B.test_volatile_and_slow"
        ]
    }
    with flagsaver.flagsaver((suite_filter._FLAG_RUN_TYPE, run_flag)):
      skip_reason = suite_filter._get_skip_reason(test_name, test_config)
      if skip:
        self.assertTrue(
            skip_reason,
            (f"Flag is {suite_filter._FLAG_RUN_TYPE.value} and skip_reason "
             "should not be empty"))
      else:
        self.assertFalse(skip_reason)

  @parameterized.named_parameters(
      {
          "testcase_name": "_default",
          "tests_to_run": [
              "AuxiliaryDeviceCommonTestSuite.test_close_device",
              "AuxiliaryDeviceCommonTestSuite.test_factory_reset",
              "AuxiliaryDeviceCommonTestSuite.test_firmware_version",
              "AuxiliaryDeviceCommonTestSuite.test_get_prop",
              "AuxiliaryDeviceCommonTestSuite.test_logging",
              "AuxiliaryDeviceCommonTestSuite.test_reboot",
              "AuxiliaryDeviceCommonTestSuite.test_redetect",
              "AuxiliaryDeviceCommonTestSuite.test_serial_number",
              "AuxiliaryDeviceCommonTestSuite.test_shell"
          ],
          "reorder_method": None,
          "flag_files": None,
          "flag_tests": None,
          "device_name": "cambrionix-1234"
      }, {
          "testcase_name": "_files",
          "tests_to_run": [
              "AuxiliaryDeviceCommonTestSuite.test_close_device",
              "AuxiliaryDeviceCommonTestSuite.test_factory_reset",
              "AuxiliaryDeviceCommonTestSuite.test_firmware_version",
              "AuxiliaryDeviceCommonTestSuite.test_get_prop",
              "AuxiliaryDeviceCommonTestSuite.test_logging",
              "AuxiliaryDeviceCommonTestSuite.test_reboot",
              "AuxiliaryDeviceCommonTestSuite.test_redetect",
              "AuxiliaryDeviceCommonTestSuite.test_serial_number",
              "AuxiliaryDeviceCommonTestSuite.test_shell",
              "FileTransferTestSuite.test_file_transfer"
          ],
          "reorder_method": None,
          "flag_files": [
              "auxiliary_device_common_test_suite", "file_transfer_test_suite"
          ],
          "flag_tests": None,
          "device_name": "cambrionix-1234"
      }, {
          "testcase_name": "_tests",
          "tests_to_run": [
              "AuxiliaryDeviceCommonTestSuite.test_close_device",
              "AuxiliaryDeviceCommonTestSuite.test_factory_reset"
          ],
          "reorder_method": None,
          "flag_files": None,
          "flag_tests": [
              "AuxiliaryDeviceCommonTestSuite.test_close_device",
              "AuxiliaryDeviceCommonTestSuite.test_factory_reset"
          ],
          "device_name": "cambrionix-1234"
      }, {
          "testcase_name": "_files_and_tests",
          "tests_to_run": [
              "FileTransferTestSuite.test_file_transfer",
              "AuxiliaryDeviceCommonTestSuite.test_close_device"
          ],
          "reorder_method": None,
          "flag_files": [
              "auxiliary_device_common_test_suite", "file_transfer_test_suite"
          ],
          "flag_tests": [
              "FileTransferTestSuite.test_file_transfer",
              "AuxiliaryDeviceCommonTestSuite.test_close_device"
          ],
          "device_name": "cambrionix-1234"
      }, {
          "testcase_name": "_reorder",
          "tests_to_run": [
              "AuxiliaryDeviceCommonTestSuite.test_close_device",
              "AuxiliaryDeviceCommonTestSuite.test_factory_reset",
              "AuxiliaryDeviceCommonTestSuite.test_firmware_version",
              "AuxiliaryDeviceCommonTestSuite.test_get_prop",
              "AuxiliaryDeviceCommonTestSuite.test_logging",
              "AuxiliaryDeviceCommonTestSuite.test_reboot",
              "AuxiliaryDeviceCommonTestSuite.test_redetect",
              "AuxiliaryDeviceCommonTestSuite.test_serial_number",
              "AuxiliaryDeviceCommonTestSuite.test_shell",
              "SwitchboardTestSuite.test_do_and_expect",
              "SwitchboardTestSuite.test_expect_with_bogus_logline",
              "SwitchboardTestSuite.test_rotate_log",
              "SwitchboardTestSuite.test_send_and_expect"
          ],
          "reorder_method": reorder_by_name,
          "flag_files": None,
          "flag_tests": None,
          "device_name": "unifi_switch-1234"
      })
  def test_loading_suites(self, tests_to_run, flag_files, flag_tests,
                          reorder_method, device_name):
    """Ensures that suites are loaded properly."""
    with flagsaver.flagsaver(files=flag_files):
      with flagsaver.flagsaver(tests=flag_tests):
        test_suite_dict = suite_filter.identify_tests_to_run(
            _TEST_SUITES,
            device_name=device_name,
            reorder_test_suites=reorder_method)
        full_test_names = []
        for test_suite, test_list in test_suite_dict.items():
          full_names = [
              f"{test_suite.__name__}.{test_name}" for test_name in test_list
          ]
          full_test_names += full_names
      self.assertEqual(tests_to_run, full_test_names)


if __name__ == "__main__":
  absltest.main()
