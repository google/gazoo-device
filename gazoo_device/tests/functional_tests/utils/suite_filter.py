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

"""Functional test suite filter library to interact with GDM's test configs.

Defines helper functions for identifying applicable test suites, ordering them
and skipping them based on the GDM test configs.

If a list of test suites to run is not specified, all applicable test suites for
the given device will be run. This is determined by checking whether each
available test suite is applicable to the device under test.
"""
import abc
import collections
import enum
import inspect
import json
import logging
import os.path
from typing import Any, Callable, Collection, Dict, List, Mapping, Optional, Sequence, Tuple, Type

from absl import flags
from gazoo_device import custom_types
from gazoo_device import manager
from mobly import asserts
from mobly import config_parser
from mobly import records

from mobly import base_test
import gazoo_device

_CONTROLLER_MODULE = gazoo_device


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


_FLAG_RUN_TYPE = flags.DEFINE_enum(
    name="run_type",
    default=RunType.FULL.value,
    enum_values=[member.value for member in RunType],
    help="Used to determine subset of tests to run in the suite.")

_FLAG_FILES = flags.DEFINE_list(
    name="files",
    default=None,
    help="Names of functional test suite files to run. Order is preserved.",
    short_name="f")

_FLAG_TESTS = flags.DEFINE_list(
    name="tests", default=None, help="Names of individual tests to run.")
_TEST_CONFIG_TEMPLATE = "{device_type}_test_config.json"
_TEST_RETRY_INTERVAL = 30
DeviceType = custom_types.Device


class SuiteFilterBase(base_test.BaseTestClass, metaclass=abc.ABCMeta):
  """Base TestCase to use with suite filter functionality."""
  _CONFIG_DIRS = []
  _CONTROLLER_MODULE = _CONTROLLER_MODULE

  def __init__(self, configs: Collection[config_parser.TestRunConfig]) -> None:
    super().__init__(configs)
    self.device_config = {}
    self.device_name = ""
    self.device_type = ""
    self.test_config = {}

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
  def required_test_config_variables(cls) -> Tuple[str, ...]:
    """Returns keys required to be present in the functional test config.

    Returns:
      Functional test config keys which are used by the test suite.
    """
    return ()

  def get_full_test_name(self) -> str:
    """Returns the full test_name."""
    return type(self).__name__ + "." + self.current_test_info.name

  def get_manager(self) -> gazoo_device.Manager:
    """Returns an instance of manager."""
    return gazoo_device.get_manager()
  def setup_class(self) -> None:
    """Loads device-specific configs for testing."""
    super().setup_class()
    self._load_variables()

  def setup_test(self) -> None:
    """Skips if test is not relevant."""
    super().setup_test()
    skip_reason = _get_skip_reason(self.get_full_test_name(), self.test_config)
    if skip_reason:
      asserts.skip(skip_reason)

  def _load_variables(self) -> None:
    controller_name = self._CONTROLLER_MODULE.MOBLY_CONTROLLER_CONFIG_NAME
    self.device_config = self.controller_configs[controller_name][0]
    self.device_name = self.device_config["id"]
    self.device_type = self.device_name.rsplit("-", maxsplit=1)[0]
    required_keys = self.required_test_config_variables()
    self.test_config = _get_test_config(self.device_name, self._CONFIG_DIRS)
    _validate_test_config_keys(self.test_config, required_keys)
    test_suite_name = type(self).__name__
    test_names = self.get_existing_test_names()
    _expand_test_suite_name_if_necessary(test_suite_name, test_names,
                                         self.test_config)
    self.already_tried_tests = []

  def exec_one_test(self,
                    test_name,
                    test_method,
                    record=None) -> Optional[records.TestResultRecord]:
    """Overriding mobly's exec_one_test to enable retry of volatile tests."""
    full_name = f"{type(self).__name__}.{test_name}"
    if full_name not in self.already_tried_tests:
      if full_name in self.test_config[TestLabel.VOLATILE.value]:
        self.already_tried_tests.append(full_name)  # prevent infinite recursion
        return self._exec_one_test_with_retry(
            test_name, test_method, max_count=2)
    return super().exec_one_test(test_name, test_method, record)


SuiteType = Type[SuiteFilterBase]
SuiteCollectionType = Sequence[SuiteType]


def identify_tests_to_run(
    all_test_suites: SuiteCollectionType,
    device_name: str,
    reorder_test_suites: Optional[Callable[[SuiteCollectionType],
                                           SuiteCollectionType]] = None
) -> Mapping[SuiteType, Collection[str]]:
  """Returns selected (via flags) or all applicable tests for the device.

  Order is preserved for test suites and tests.
  If test suites are specified via a flag, that order is used. Otherwise the
  order of all_test_suites is used, unless reordered by reorder_test_suites.
  If tests are specified via a flag, that order is used. Otherwise the default
  test order is used.

  Args:
    all_test_suites: All available test suites.
    device_name: GDM device name (such as "cambrionix-1234").
    reorder_test_suites: Function to reorder test suites in a particular
      fashion. Test suites will run in the order returned by this function.

  Returns:
    dictionary of suites, suite's test_list used as input to mobly_suites.
  """
  if _FLAG_FILES.value:
    test_suites = _get_test_suites_from_files_flag(all_test_suites)
  else:
    test_suites = _get_all_supported_test_suites(all_test_suites, device_name)
    if reorder_test_suites:
      test_suites = reorder_test_suites(test_suites)

  if _FLAG_TESTS.value:
    test_suite_dict = _get_test_suite_dict_from_tests_flag(test_suites)
    logging.info("Running selected tests in the following order:")
    for test_name in _FLAG_TESTS.value:
      logging.info("\t%s", test_name)
  else:
    logging.info("Running all applicable test suites in the following order:")
    for suite in test_suites:
      logging.info("\t%s", suite.__name__)
    test_suite_dict = collections.OrderedDict()
    for test_suite in test_suites:
      test_suite_dict[test_suite] = _get_test_names(test_suite)

  return test_suite_dict


def _get_all_supported_test_suites(all_test_suites: SuiteCollectionType,
                                   device_name: str) -> SuiteCollectionType:
  """Returns all test suites which are supported by the given device."""
  device_type = device_name.split("-")[0]
  device_class = manager.Manager.get_supported_device_class(device_type)
  applicable_test_suites = []
  inapplicable_test_suites = []

  for suite in all_test_suites:
    if (suite.is_applicable_to(device_type, device_class, device_name) and
        not suite.requires_pairing()):
      applicable_test_suites.append(suite)
    else:
      inapplicable_test_suites.append(suite)

  logging.info("Test suites applicable to device %s:", device_name)
  for suite in applicable_test_suites:
    logging.info("\t%s", suite.__name__)

  logging.info("Test suites not applicable to device %s:", device_name)
  for suite in inapplicable_test_suites:
    logging.info("\t%s", suite.__name__)

  return applicable_test_suites


def _get_skip_reason(test_name: str,
                     test_config: Mapping[str, Collection[str]]) -> str:
  """Returns skip reason if test_name is not applicable to current run."""
  if test_name in test_config[TestLabel.DO_NOT_RUN.value]:
    return "Excluding do_not_run_tests from testing"
  elif _FLAG_RUN_TYPE.value == RunType.PRESUBMIT:
    if test_name in test_config[TestLabel.SLOW.value]:
      return "Excluding slow tests from presubmit testing"
  elif _FLAG_RUN_TYPE.value == RunType.STABLE:
    if test_name in test_config[TestLabel.VOLATILE.value]:
      return "Excluding volatile tests from stable testing"
  elif _FLAG_RUN_TYPE.value == RunType.VOLATILE:
    if test_name not in test_config[TestLabel.VOLATILE.value]:
      return "Excluding non-volatile tests from volatile testing"
  return ""


def _expand_test_suite_name_if_necessary(test_suite_name: str,
                                         test_names: Sequence[str],
                                         test_config: Dict[str, Any]):
  """Replaces the test_suite_name in the test config with the suite's test names.

  Args:
    test_suite_name: name of this specific test suite
    test_names: names of all the tests within the test suite.
    test_config: GDM test_config dictionary including test_label tags.
  """
  for label in [TestLabel.DO_NOT_RUN, TestLabel.SLOW, TestLabel.VOLATILE]:
    label_list = list(test_config[label.value])
    if test_suite_name in test_config[label.value]:
      label_list.remove(test_suite_name)
      full_test_names = [
          f"{test_suite_name}.{test_name}" for test_name in test_names
      ]
      test_config[label.value] = label_list + full_test_names


def _get_test_names(test_suite: SuiteType) -> List[str]:
  """Returns a list of all test names in a test suite."""
  return [name
          for name, _ in inspect.getmembers(test_suite, callable)
          if name.startswith("test_")]


def _get_test_suites_from_files_flag(
    all_test_suites: SuiteCollectionType) -> SuiteCollectionType:
  """Returns a list of all test suites present in those files."""
  # Strip .py file extensions if present.
  requested_module_names = [
      name[:-3] if name.endswith(".py") else name for name in _FLAG_FILES.value
  ]
  module_name_to_test_suites = collections.OrderedDict()
  for suite in all_test_suites:
    module_name = suite.__module__.split(".")[-1]  # Strip off package path.
    if module_name not in module_name_to_test_suites:
      module_name_to_test_suites[module_name] = []
    module_name_to_test_suites[module_name].append(suite)

  unknown_module_names = [
      name for name in requested_module_names
      if name not in module_name_to_test_suites
  ]
  if unknown_module_names:
    raise ValueError(f"Test modules {unknown_module_names} do not exist")
  test_suites = []
  for module_name in requested_module_names:
    test_suites.extend(module_name_to_test_suites[module_name])
  return test_suites


def _get_test_suite_dict_from_tests_flag(
    test_suites: SuiteCollectionType) -> Dict[SuiteType, Sequence[str]]:
  """Creates a dict of the suites and tests specified in the flag."""
  test_cases_suite_dict = collections.OrderedDict()
  suites_by_name = {
      test_suite.__name__: test_suite for test_suite in test_suites
  }
  for requested_test in _FLAG_TESTS.value:
    suite_name, _, test_name = requested_test.partition(".")

    if suite_name not in suites_by_name:
      raise ValueError(f"Test suite for {requested_test} does not exist in "
                       f"these test_suites {test_suites}. "
                       "Is this formatted <TestSuiteName>.<test_name>?")
    tests = _get_test_names(suites_by_name[suite_name])
    if test_name not in tests:
      raise ValueError(f"Test method {requested_test} does not exist in "
                       f"the tests {tests} "
                       f"from test_suite {suite_name}")
    suite = suites_by_name[suite_name]
    if suite not in test_cases_suite_dict:
      test_cases_suite_dict[suite] = []
    test_cases_suite_dict[suite].append(test_name)
  return test_cases_suite_dict


def _get_test_config(device_name: str,
                     config_dirs: Collection[str]) -> Dict[str, Any]:
  """Loads valid test config and verifies its keys before returning it."""
  device_type = device_name.rsplit("-", maxsplit=1)[0]
  config_file_name = _TEST_CONFIG_TEMPLATE.format(device_type=device_type)
  return _load_test_config(config_file_name, config_dirs)


def _load_test_config(config_file_name: str,
                      config_dirs: Collection[str]) -> Dict[str, Any]:
  """Loads and returns the test config as a dictionary."""
  config_path = os.path.join(config_dirs[0], config_file_name)
  if not os.path.exists(config_path):
    raise FileNotFoundError(
      f"Functional test config does not exist at {config_dirs[0]}")
  with open(config_path) as test_config_file:
    return json.load(test_config_file)


def _validate_test_config_keys(test_config: Mapping[str, Any],
                               required_keys: Collection[str]) -> None:
  """Checks that all required keys are present in the functional test config.

  Args:
     test_config: Contains device type specific keys and values to run tests.
     required_keys: Keys expected for this test suite.

  Raises:
    KeyError: One or more of the required keys are missing from the functional
      test config.
  """
  all_keys = tuple(required_keys) + tuple(member.value for member in TestLabel)
  missing_keys = [key for key in all_keys if key not in test_config]
  if missing_keys:
    raise KeyError("The following keys are missing from the functional test "
                   f"config: {missing_keys}.")
