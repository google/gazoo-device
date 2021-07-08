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

"""Base class for GDM functional tests."""
import abc
import enum
import inspect
import json
import os.path
import time
import typing
from typing import Any, Collection, Dict, List, Optional, Sequence, Tuple, Type
import unittest

from absl import flags
from absl.testing import xml_reporter
from gazoo_device import custom_types
from gazoo_device import errors
from gazoo_device import manager
from gazoo_device.utility import host_utils
import immutabledict
from gazoo_device.tests import functional_tests
from gazoo_device.tests.functional_tests.utils import gazootest

DeviceType = custom_types.Device

_DEVICE_CREATION_ATTEMPTS = 2
_TEST_RETRY_INTERVAL = 30
_TEST_CONFIG_TEMPLATE = "{device_type}_test_config.json"
_TIMEOUTS = immutabledict.immutabledict({
    "CREATION_FAILURE": 10,
    "RECONNECT": 60,
})


class TestLabel(enum.Enum):
  """Test labels used in functional test configs."""
  DO_NOT_RUN = "do_not_run_tests"
  SLOW = "slow_tests"
  VOLATILE = "volatile_tests"


class RunType(enum.Enum):
  """Type of test run used to determine applicable tests."""
  FULL = "full"
  PRESUBMIT = "presubmit"
  STABLE = "stable"
  VOLATILE = "volatile"


FLAGS = flags.FLAGS
flags.DEFINE_string(
    name="run_type", default=RunType.FULL.value,
    help="Used to determine subset of tests to run in the suite.")


class GDMTestBase(gazootest.TestCase, metaclass=abc.ABCMeta):
  """Base class for GDM functional test suites."""
  device_config = None
  test_config = None
  testing_properties = None

  def __init__(self, *args, **kwargs):
    """Initialize the test suite."""
    super().__init__(*args, **kwargs)
    self.device = None
    self.run_type = RunType(FLAGS.run_type)
    self.is_do_not_run, self.is_slow, self.is_volatile = (False, False, False)

  @classmethod
  @abc.abstractmethod
  def is_applicable_to(cls, device_type: str, device_class: Type[DeviceType],
                       device_name: str) -> bool:
    """Determines if this test suite is applicable to the given device type.

    Allows the test runner to dynamically determine the set of test suites to
    run for a device. device_name is provided in case you need to communicate to
    the device. Most implementations won't need to create a device instance.
    Since device creation is slower, prefer using device_type and/or
    device_class arguments instead unless you have to communicate with the
    device.

    Args:
      device_type: One of the device types supported by GDM.
      device_class: Device controller class object.
      device_name: GDM device name.

    Returns:
      True if this test suite can run on the given device type, False otherwise.
    """

  @classmethod
  @abc.abstractmethod
  def requires_pairing(cls) -> bool:
    """Returns True if the device must be paired to run this test suite."""

  @classmethod
  def check_properties_set(cls, device_name: str,
                           property_list: Collection[str]) -> bool:
    """Returns True if all of the properties are set."""
    mgr = manager.Manager()
    for property_name in property_list:
      value = mgr.get_device_prop(device_name, property_name)
      if value is None or str(value).startswith("Exception"):
        return False
    return True

  @classmethod
  def create_device(
      cls,
      device_name: str,
      log_name_prefix: str,
      attempts: int = _DEVICE_CREATION_ATTEMPTS) -> Optional[DeviceType]:
    """Creates a device instance.

    Args:
      device_name: GDM identifier of the device to create.
      log_name_prefix: String to prepend to log filename.
      attempts: Number of times to attempt device creation.

    Returns:
      GDM device instance.

    Raises:
      DeviceError: Device creation failed.
    """
    for attempt in range(attempts):
      try:
        return cls.get_manager().create_device(
            device_name, log_name_prefix=log_name_prefix)

      # Wait and retry if creation fails, or raise if final creation attempt.
      except errors.DeviceError as err:
        if attempt == attempts - 1:
          raise
        cls.logger.info(
            "Device creation failed attempt %d/%d. "
            "Waiting %d seconds before re-attempting device creation. "
            "Error: %r.",
            attempt + 1, attempts, _TIMEOUTS["CREATION_FAILURE"], err)
        time.sleep(_TIMEOUTS["CREATION_FAILURE"])

  @classmethod
  def get_test_config(cls) -> Dict[str, Any]:
    """Returns the functional test config for the device in the testbed."""
    config_file_name = _TEST_CONFIG_TEMPLATE.format(
        device_type=cls.device_config.device_type)
    config_path = os.path.join(
        os.path.abspath(os.path.dirname(functional_tests.__file__)),
        "configs", config_file_name)
    with open(config_path) as test_config_file:
      return json.load(test_config_file)

  @classmethod
  def required_test_config_variables(cls) -> Tuple[str, ...]:
    """Returns keys required to be present in the functional test config.

    Returns:
      Functional test config keys which are used by the test suite.
    """
    return ()

  @classmethod
  def setUpClass(cls) -> None:
    """Loads device-specific configs for testing."""
    super().setUpClass()
    cls.testing_properties = cls.get_testbed().testing_properties
    cls.device_config = cls.get_testbed().devices[0]
    cls.test_config = cls.get_test_config()

  def setUp(self) -> None:
    """Creates the first device listed in the testbed config.

    Fails the test if unable to create the device in 2 attempts.
    """
    super().setUp()
    self.is_do_not_run, self.is_slow, self.is_volatile = self.get_test_labels()
    self.skip_if_not_applicable(self.is_do_not_run, self.is_slow,
                                self.is_volatile)
    self.validate_test_config_keys()
    self.device = self.create_device(self.device_config.name,
                                     self.get_log_suffix(),
                                     attempts=_DEVICE_CREATION_ATTEMPTS)

    try:
      if hasattr(type(self.device), "firmware_version"):
        self.logger.info(f"DUT: {self.device.name}, "
                         f"firmware version: {self.device.firmware_version}")
    except errors.DeviceError as error:
      if self.device:  # for pytype
        self.device.close()
      raise

  def tearDown(self) -> None:
    """Closes the device."""
    if self.device:
      try:
        self.wait_for_device()
      finally:
        self.device.close()
    super().tearDown()

  def run(
      self, result: Optional[unittest.TestResult] = None
  ) -> Optional[unittest.TestResult]:
    """Retries the test if it's volatile. Otherwise identical to super().run."""
    result = super().run(result)
    test_failed = result and result.failures and result.failures[-1][0] is self
    test_errored = result and result.errors and result.errors[-1][0] is self
    should_retry = result and self.is_volatile and (test_failed or test_errored)

    if should_retry:
      # Erase the test result from the previous attempt in unittest.
      # This reverts test result changes from
      # unittest.result.TestResult.startTest(), .addError(), .addFailure().
      result.testsRun -= 1
      if test_failed:
        result.failures.pop()
      elif test_errored:
        result.errors.pop()
      # Erase the test result from the previous attempt in absltest.
      # This reverts test result changes from
      # absl.testing.xml_reporter._TestSuiteResult.add_test_case_result.
      suite_name = type(self).__name__
      result = typing.cast(xml_reporter._TextAndXMLTestResult, result)
      result.suite.suites[suite_name].pop()
      if test_failed:
        result.suite.failure_counts[suite_name] -= 1
      elif test_errored:
        result.suite.error_counts[suite_name] -= 1
      # Rerun the test.
      self.logger.info(
          f"Test {self._testMethodName} failed the first attempt and is known "
          f"to be flaky on {self.device.device_type}. "
          f"RETRYING in {_TEST_RETRY_INTERVAL}s.")
      time.sleep(_TEST_RETRY_INTERVAL)
      result = super().run(result)
    return result

  def get_log_suffix(self) -> str:
    """Returns the log suffix to be used for test log files."""
    return type(self).__name__ + "." + self._testMethodName

  def get_test_labels(self) -> Tuple[bool, bool, bool]:
    """Returns labels for the current test: "do_not_run", "slow", "volatile"."""
    current_test_name = self._testMethodName
    all_tests = [
        name for name, _ in inspect.getmembers(self, inspect.ismethod)
        if name.startswith("test_")
    ]

    # Check the test config for any tests we might want to skip.
    do_not_run_tests = self._get_matching_tests(
        all_tests, TestLabel.DO_NOT_RUN)
    slow_tests = self._get_matching_tests(
        all_tests, TestLabel.SLOW)
    volatile_tests = self._get_matching_tests(
        all_tests, TestLabel.VOLATILE)

    return (current_test_name in do_not_run_tests,
            current_test_name in slow_tests,
            current_test_name in volatile_tests)

  def skip_if_not_applicable(
      self, is_do_not_run: bool, is_slow: bool, is_volatile: bool) -> None:
    """Skips the current test if it's not applicable to the current test run."""
    if is_do_not_run:
      self.skipTest("Excluding do_not_run_tests from testing")
    if self.run_type == RunType.PRESUBMIT:
      if is_slow:
        self.skipTest("Excluding slow tests from presubmit testing")
    elif self.run_type == RunType.STABLE:
      if is_volatile:
        self.skipTest("Excluding volatile tests from stable testing")
    elif self.run_type == RunType.VOLATILE:
      if not is_volatile:
        self.skipTest("Excluding non-volatile tests from volatile testing")

  def validate_test_config_keys(self) -> None:
    """Checks that all required keys are present in the functional test config.

    Raises:
      KeyError: One or more of the required keys are missing from the functional
        test config.
    """
    missing_keys = [
        key for key in self.required_test_config_variables()
        if key not in self.test_config
    ]
    if missing_keys:
      raise KeyError("The following keys are missing from the functional test "
                     f"config: {missing_keys}.")

  def wait_for_device(self) -> None:
    """Waits for the device if it went offline during the test."""
    deadline = time.time() + _TIMEOUTS["RECONNECT"]
    while time.time() < deadline:
      if self.get_manager().is_device_connected(self.device.name):
        break
      self.logger.info("%s is not connected. Waiting for it to reconnect...",
                       self.device.name)
      time.sleep(1)
    else:
      self.fail("{} failed to reconnect in {}s".format(self.device.name,
                                                       _TIMEOUTS["RECONNECT"]))

  def _get_matching_tests(self, all_tests: Sequence[str],
                          label: TestLabel) -> List[str]:
    """Returns test names in the current test suite matching the label.

    Args:
      all_tests: Names of tests in the current test suite.
      label: Test label corresponding to "do not run" tests, "slow" tests, or
        "volatile" (flaky) tests.
    """
    test_or_suite_names = self.test_config.get(label.value, [])
    filtered_tests = []

    for full_name in test_or_suite_names:
      if "." in full_name:  # name is SuiteName.test_name
        suite_name, test_name = full_name.split(".")
        if suite_name == type(self).__name__ and test_name in all_tests:
          filtered_tests.append(test_name)
      elif full_name == type(self).__name__:  # name is SuiteName
        filtered_tests = list(all_tests)
        break
    return filtered_tests


def main(*args, **kwargs):
  return gazootest.main(*args, **kwargs)
