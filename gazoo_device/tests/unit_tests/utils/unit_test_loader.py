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

"""Utilities for loading unit tests."""
import os
import re
import typing
from typing import Optional, TypeVar, Union
import unittest

from absl import flags

_FLAG_TEST_CASE_REGEX = flags.DEFINE_string(
    "test_case_regex",
    default=None,
    help=("Regular expression for matching test names. "
          "Can be used to specify modules, test classes, or test case names. "
          "Test name format is 'module_test.ModuleTests.test_something'."),
    short_name="r")

_TestSuiteT = TypeVar("_TestSuiteT", bound=unittest.TestSuite)
_TestCaseT = TypeVar("_TestCaseT", bound=unittest.TestCase)


def _get_matching_test_cases(
    test_case_or_suite: Union[_TestSuiteT, _TestCaseT],
    test_case_regex: str
) -> Optional[Union[_TestSuiteT, _TestCaseT]]:
  """Recursively filters the test suite for test cases matching the regex."""
  if isinstance(test_case_or_suite, unittest.TestCase):
    if re.search(test_case_regex, test_case_or_suite.id()) is not None:
      # .id() example: "manager_test.ManagerTests.test_devices".
      return test_case_or_suite
    return None

  filtered_sub_test_cases_or_suites = [
      _get_matching_test_cases(sub_test_case_or_suite, test_case_regex)
      for sub_test_case_or_suite in test_case_or_suite]
  filtered_sub_test_cases_or_suites = [
      sub_test_case_or_suite
      for sub_test_case_or_suite in filtered_sub_test_cases_or_suites
      if sub_test_case_or_suite is not None]
  if filtered_sub_test_cases_or_suites:
    # Return the same test suite type as provided by the caller.
    return type(test_case_or_suite)(filtered_sub_test_cases_or_suites)
  # If there are no matching test cases in the suite, return None instead of an
  # empty suite to avoid returning a number of empty suites after filtering.
  return None


def _make_suite_with_matching_test_cases(
    test_suite: _TestSuiteT, test_case_regex: str) -> _TestSuiteT:
  """Returns a test suite with test cases matching the regex."""
  suite = _get_matching_test_cases(test_suite, test_case_regex)
  if suite is not None:
    return typing.cast(_TestSuiteT, suite)
  # If there are no matching tests, return an empty test suite of the same type
  # as provided by the caller.
  return type(test_suite)()


def discover_tests(
    loader: unittest.TestLoader,
    start_dir: str,
    top_level_dir: Optional[str] = None,
    raise_if_no_tests_found: bool = True) -> unittest.TestSuite:
  """Helper for finding specific tests cases for unittest 'load_tests' calls."""
  unit_tests = loader.discover(
      start_dir, pattern="*_test.py", top_level_dir=top_level_dir)
  if _FLAG_TEST_CASE_REGEX.value is not None:
    unit_tests = _make_suite_with_matching_test_cases(
        unit_tests, _FLAG_TEST_CASE_REGEX.value)

  if raise_if_no_tests_found and not unit_tests.countTestCases():
    # If any test case selection filters are specified and sharding is enabled,
    # there may be more shards than test cases. Don't raise an error if the
    # current shard has nothing to run and assume other shards have at least one
    # test to run.
    if not(_FLAG_TEST_CASE_REGEX.value is not None and
           int(os.environ.get("TEST_TOTAL_SHARDS", 1)) > 1):
      raise RuntimeError("Did not find any tests to run.")
  return unit_tests
