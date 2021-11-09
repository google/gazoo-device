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

"""Unit tests for common_utils.py."""
import copy
import multiprocessing
import os
from unittest import mock

from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import common_utils

_SAMPLE_RESPONSE = {"a": {"b": {"c": "d"}}}

# Tuples of (Input string, Expected snake_case output string)
_CASE_CONVERSION_TEST_CASES = (
    ("ABc", "a_bc"), ("AB", "ab"), ("A", "a"), ("aB", "a_b"), ("A9x", "a9x"),
    ("A9X", "a9_x"), ("FooBarBAZ", "foo_bar_baz"), ("FooBarBaz", "foo_bar_baz"),
    ("foo", "foo"), ("fooBar", "foo_bar"), ("fooBarBAz", "foo_bar_b_az"))

_GENERATE_NAME_TEST_CASES = _CASE_CONVERSION_TEST_CASES + (
    ("much_wow", "much_wow"), ("__strangename__", "__strangename__"),
    ("_", "_"), ("FooBar_Baz", "foobar_baz"))


class TestClass:
  """TestClass object to track method calls."""

  def __init__(self, method_calls):
    # method_calls is a list of tuples,
    # where each tuple contains (args, kwargs) for each call.
    self.method_calls = method_calls

  def method(self, *args, **kwargs):
    """Keeps track of whether the method has been called or not."""
    self.method_calls.append((args, kwargs))


class _NamedObject:
  """object() with a __name__ attribute."""

  def __init__(self, name):
    super().__init__()
    self.__name__ = name


class CommonUtilsTests(unit_test_case.UnitTestCase):
  """Common utility tests."""

  def test_get_value_from_json_good_response_value_extraction(self):
    """Test for valid extraction of a value nested in a response message."""
    value = common_utils.get_value_from_json(_SAMPLE_RESPONSE, ["a", "b", "c"])
    self.assertEqual("d", value)

  def test_get_value_from_json_bad_response_value_extraction_raises(self):
    """Test for failed extraction with raise option."""
    with self.assertRaisesRegex(KeyError, "Unable to find key"):
      common_utils.get_value_from_json(_SAMPLE_RESPONSE, ["a", "b", "e"])

  def test_get_value_from_json_bad_response_value_extraction_no_raise(self):
    """Test for failed extraction of a value with raise_if_absent=False."""
    value = common_utils.get_value_from_json(_SAMPLE_RESPONSE, ["a", "b", "e"],
                                             False)
    self.assertIsNone(value)

  def test_method_weakref_live_object_no_args(self):
    """Test calling method via weakref on a live object with no method args."""
    method_calls = []
    test_class = TestClass(method_calls)
    method_weakref = common_utils.MethodWeakRef(test_class.method)

    method_weakref()
    expected_calls = [((), {})]
    self.assertEqual(expected_calls, method_calls)

  def test_method_weakref_live_object_with_args(self):
    """Test calling method via a weakref on a live object with method args."""
    method_calls = []
    test_class = TestClass(method_calls)
    method_weakref = common_utils.MethodWeakRef(test_class.method)

    method_weakref("foo", bar=1)
    expected_calls = [(("foo",), {"bar": 1})]
    self.assertEqual(expected_calls, method_calls)

  def test_method_weakref_dead_object(self):
    """Test calling method via a weakref on a dead object."""
    method_calls = []
    test_class = TestClass(method_calls)
    method_weakref = common_utils.MethodWeakRef(test_class.method)

    del test_class
    method_weakref("foo", bar=1)
    self.assertFalse(method_calls)

  def test_title_to_snake_case_error_if_underscore_found(self):
    """Test title_to_snake_case() raises if input contains an underscore."""
    with self.assertRaisesRegex(ValueError, "underscore"):
      common_utils.title_to_snake_case("Foo_Bar")

  def test_title_to_snake_case_success(self):
    """Test title_to_snake_case() on several valid inputs."""
    for title_str, snake_str in _CASE_CONVERSION_TEST_CASES:
      self.assertEqual(snake_str, common_utils.title_to_snake_case(title_str))

  def test_generate_name_error_no_name_attr(self):
    """Test generate_name() raises if object doesn't have __name__ attribute."""
    test_object = object()
    with self.assertRaisesRegex(ValueError,
                                "must have a non-empty __name__ attribute"):
      common_utils.generate_name(test_object)

  def test_generate_name_error_empty_name_attr(self):
    """Test generate_name() raises an error if object's __name__ is ""."""
    test_object = _NamedObject("")
    with self.assertRaisesRegex(ValueError,
                                "must have a non-empty __name__ attribute"):
      common_utils.generate_name(test_object)

  def test_generate_name_success(self):
    """Test generate_name() on several valid inputs."""
    for object_name, expected_name in _GENERATE_NAME_TEST_CASES:
      test_object = _NamedObject(object_name)
      self.assertEqual(expected_name, common_utils.generate_name(test_object))

  def test_register_at_fork(self):
    """Test operation of register_at_fork(), run_before_fork, and run_after_fork_in_parent."""
    func_before = mock.Mock()
    func_parent_after = mock.Mock()
    func_child_after = mock.Mock()

    saved_before_fork_functions = copy.copy(
        common_utils._run_before_fork_functions)
    saved_after_fork_in_parent_functions = copy.copy(
        common_utils._run_after_fork_in_parent_functions)

    try:
      if hasattr(os, "register_at_fork"):
        # common_utils.register_at_fork() should directly call
        # os.register_at_fork().

        with mock.patch.object(os, "register_at_fork") as mock_os_register:
          with mock.patch.object(
              multiprocessing.util,
              "register_after_fork") as mock_mp_util_register:
            common_utils.register_at_fork(
                before=func_before,
                after_in_parent=func_parent_after,
                after_in_child=func_child_after)
        mock_os_register.assert_called_once_with(
            before=func_before,
            after_in_parent=func_parent_after,
            after_in_child=func_child_after)
        mock_mp_util_register.assert_not_called()

        # Values of these lists shouldn't have changed.
        self.assertEqual(common_utils._run_before_fork_functions,
                         saved_before_fork_functions)
        self.assertEqual(common_utils._run_after_fork_in_parent_functions,
                         saved_after_fork_in_parent_functions)

      else:
        # common_utils.register_at_fork() should use the workaround.

        with mock.patch.object(multiprocessing.util,
                               "register_after_fork") as mock_mp_util_register:
          common_utils.register_at_fork(
              before=func_before,
              after_in_parent=func_parent_after,
              after_in_child=func_child_after)
        mock_mp_util_register.assert_called_once()
        self.assertIn(func_before, common_utils._run_before_fork_functions)
        self.assertIn(func_parent_after,
                      common_utils._run_after_fork_in_parent_functions)

        # Check that run_before_fork() and run_after_fork_in_parent()
        # function correctly
        common_utils.run_before_fork()
        func_before.assert_called_once()
        func_parent_after.assert_not_called()

        common_utils.run_after_fork_in_parent()
        func_before.assert_called_once()
        func_parent_after.assert_called_once()

    finally:  # Clean up after the test
      common_utils._run_before_fork_functions = saved_before_fork_functions
      common_utils._run_after_fork_in_parent_functions = saved_after_fork_in_parent_functions


if __name__ == "__main__":
  unit_test_case.main()
