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

"""Functional test runner library.

Defines helper functions to identify applicable test suites, reorder them, and
collect them into a format unittest framework understands.

If a list of test suites to run is not specified, all applicable test suites for
the given device will be run. This is determined by checking whether each
available test suite is applicable to the device under test.
"""
import logging
from typing import Any, Callable, List, Type
import unittest

from absl import flags
from gazoo_device import manager

FLAGS = flags.FLAGS
flags.DEFINE_list(
    name="files", default=None,
    help="Names of functional test suite files to run. Order is preserved.",
    short_name="f")
flags.DEFINE_list(
    name="tests", default=None,
    help="Names of individual tests to run.")

# TODO(gdm-authors): Replace "Any" with "gdm_test_base" once it's open-source.
SuiteCollectionType = List[Type[Any]]


def identify_tests_to_run(
    all_test_suites: SuiteCollectionType,
    reorder_test_suites: Callable[[SuiteCollectionType], SuiteCollectionType],
    device_name: str) -> unittest.TestSuite:
  """Returns selected (via flags) or all applicable tests for the device.

  Order is preserved for test suites and tests.
  If test suites are specified via a flag, that order is used. Otherwise the
  order of all_test_suites is used, unless reordered by reorder_test_suites.
  If tests are specified via a flag, that order is used. Otherwise the default
  test order is used (alphabetic).

  Args:
    all_test_suites: All available test suites.
    reorder_test_suites: Function to reorder test suites in a particular
      fashion. Test suites will run in the order returned by this function.
    device_name: GDM device name (such as "cambrionix-1234").
  """
  if FLAGS.files:
    # Strip .py file extensions if present.
    requested_module_names = [name[:-3] if name.endswith(".py") else name
                              for name in FLAGS.files]
    module_name_to_test_suites = {}
    for suite in all_test_suites:
      module_name = suite.__module__.split(".")[-1]  # Strip off package path.
      if module_name not in module_name_to_test_suites:
        module_name_to_test_suites[module_name] = []
      module_name_to_test_suites[module_name].append(suite)

    unknown_module_names = [name for name in requested_module_names
                            if name not in module_name_to_test_suites]
    if unknown_module_names:
      raise ValueError(f"Test modules {unknown_module_names} do not exist")
    test_suites = []
    for module_name in requested_module_names:
      test_suites.extend(module_name_to_test_suites[module_name])
    logging.info("Running selected test suites in the following order:")
  else:
    test_suites = _get_all_supported_test_suites(all_test_suites, device_name)
    test_suites = reorder_test_suites(test_suites)
    logging.info("Running all applicable test suites in the following order:")
  for suite in test_suites:
    logging.info("\t%s", suite.__name__)

  test_loader = unittest.TestLoader()
  tests_to_run = unittest.TestSuite()
  if FLAGS.tests:
    for requested_test in FLAGS.tests:
      for test_suite in test_suites:
        available_tests = test_loader.getTestCaseNames(test_suite)
        if requested_test in available_tests:
          tests_to_run.addTest(test_suite(requested_test))

    # pytype doesn't recognize that tests_to_run are TestCases, not TestSuites.
    # pytype: disable=attribute-error
    selected_test_names = {test._testMethodName for test in tests_to_run}
    # pytype: enable=attribute-error
    unknown_test_names = [test_name for test_name in FLAGS.tests
                          if test_name not in selected_test_names]
    if unknown_test_names:
      raise ValueError(f"Test methods {unknown_test_names} do not exist in "
                       "the selected test suites")
    logging.info("Running selected tests in the following order:")
    for test in tests_to_run:
      logging.info("\t%s", test)
  else:
    for test_suite in test_suites:
      tests_to_run.addTests(test_loader.loadTestsFromTestCase(test_suite))
    logging.info("Running all tests in alphabetic order (per test suite).")

  return tests_to_run


def _get_all_supported_test_suites(all_test_suites: SuiteCollectionType,
                                   device_name: str) -> SuiteCollectionType:
  """Returns all test suites which are supported by the given device."""
  device_type = device_name.split("-")[0]
  device_class = manager.Manager.get_supported_device_class(device_type)
  applicable_test_suites = []

  for suite in all_test_suites:
    if (suite.is_applicable_to(device_type, device_class, device_name)
        and not suite.requires_pairing()):
      applicable_test_suites.append(suite)

  logging.info("Test suites applicable to device %s:", device_name)
  for suite in applicable_test_suites:
    logging.info("\t%s", suite.__name__)

  inapplicable_test_suites = [suite for suite in all_test_suites
                              if suite not in applicable_test_suites]
  logging.info("Test suites not applicable to device %s:", device_name)
  for suite in inapplicable_test_suites:
    logging.info("\t%s", suite.__name__)

  return applicable_test_suites
