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

"""Common reusable utility functions."""
import multiprocessing
import os
import time
import weakref
from gazoo_device import errors

# Lists of callable functions with no arguments
_run_before_fork_functions = []
_run_after_fork_in_parent_functions = []

# _Sentinel objects used by multiprocessing.util.register_after_fork. This list keeps the objects
# alive by keeping a strong reference to them. multiprocessing.util stores these in a
# weakref.WeakValueDictionary, so if a strong reference is not stored somewhere, the sentinel
# will be destroyed, removing the function registered with it from the list of "after fork"
# functions (b/154659535).
_register_after_fork_sentinels = []


class MethodWeakRef(object):
  """Allows creating weak references to instance methods.

  Note:
      using weakref.ref() on an instance method directly returns a dead
      reference. See https://stackoverflow.com/questions/599430.
  """

  def __init__(self, instance_method):
    """Create a weak reference to an instance (bound) method.

        Args:
            instance_method (method): instance (bound) method.
    """
    self._func = instance_method.__func__
    self._instance_weakref = weakref.ref(instance_method.__self__)

  def __call__(self, *args, **kwargs):
    """Calls the instance method if the instance is still alive."""
    instance = self._instance_weakref()
    if instance is not None:
      self._func(instance, *args, **kwargs)


class _Sentinel(object):
  """Empty object which supports weakrefs."""
  pass


def _default_is_successful(_):
  return True


def not_func(val):
  """Takes an input value and returns bool value after performing a negate operation.

  Args:
      val (object): any python object

  Returns:
      bool: True if bool(val) is False and False if bool(val) is True
  """
  return not bool(val)


def is_true(val):
  """Takes an input value and returns bool value.

  Args:
      val (object): any python object

  Returns:
      bool: bool(val)
  """
  return bool(val)


def retry(func,
          func_args=(),
          func_kwargs=None,
          is_successful=_default_is_successful,
          timeout=10,
          interval=1,
          reraise=True,
          exc_type=errors.CommunicationTimeoutError):
  """Wait until either execution of func() succeeds or timeout is reached.

  Success of execution of func() is determined by is_successful() function,
  which should return True on successful execution of func().

  Args:
      func (function): function to execute
      func_args (tuple): positional arguments to the function
      func_kwargs (dict): keyword arguments to the function
      is_successful (function): function which takes in the result of func()
        and returns whether function execution should be considered
        successful. To indicate success, return True. Defaults to always
        returning True.
      timeout (int): if no run of func() succeeds in this time period, raise
        an error.
      interval (float): how long to wait between retries of func().
      reraise (bool): whether to re-raise exceptions in func() or not. If
        True, will re-raise any exceptions from func(). If False, considers
        execution of func() a failure if an Exception is raised.
        is_successful() will NOT be called if an Exception occurs.
      exc_type (class): type of exception to raise when timeout is reached.
        Note that the class constructor will be called with just 1 argument.

  Returns:
      object: return value of first successful func() call.

  Raises:
      Exception: if timeout is reached. The default exception type is
      errors.TimeoutError. OR if an Exception occurs in func() and reraise is
      False.
  """
  if func_kwargs is None:
    func_kwargs = {}

  tried_times = 0
  start_time = time.time()
  end_time = start_time + timeout

  while time.time() < end_time:
    exception_occurred = False
    tried_times += 1
    try:
      func_result = func(*func_args, **func_kwargs)
    except Exception:
      if reraise:
        raise
      else:
        exception_occurred = True

    if not exception_occurred and is_successful(func_result):
      return func_result

    time.sleep(interval)

  time_elapsed = time.time() - start_time
  raise exc_type("Timeout in {}s. Tried calling {} {} times.".format(
      time_elapsed, func.__name__, tried_times))


def generate_name(_object):
  """Generates a snake_case name (str) for the given object.

  Args:
      _object (object): any python object which has a non-empty __name__
        attribute.

  Raises:
      ValueError: _object does not have __name__ attribute, or __name__ is "".

  Returns:
      str: snake_case name for the object.
  """
  object_name = getattr(_object, "__name__", "")
  if not object_name:
    raise ValueError(
        "Object {} must have a non-empty __name__ attribute.".format(_object))

  if "_" in object_name:  # Presumably already snake_case
    return object_name.lower()
  else:  # Presumably TitleCase
    return title_to_snake_case(object_name)


def get_value_from_json(json_data, key_sequence, raise_if_absent=True):
  """Extracts a value from a JSON dictionary via provided series of keys.

  This function allows easy extraction of a value stored in a nested
  dictionary structure, with validation of the existence of the necessary
  keys at each level of nesting.

  Args:
      json_data (dict): the response object from which the value will be
        extracted.
      key_sequence (list): an ordered list of string keys representing the
        path through the dictionary necessary to reach the desired value.
                           Ex. to extract foo['baz']['a'] the call would look
                             like: get_value_from_json(foo, ['baz', 'a'])  and
                             would return 'some text' given the example data
                             above.
      raise_if_absent (bool): if False, return None if a key is not present.
        if True, raise KeyError if a key is not present.

  Returns:
      object: the requested JSON field.

  Raises:
      KeyError: If the provided response message doesn't contain the necessary
      keys/values AND if raise_if_absent is True.
  """
  current_dict = json_data
  key_text = ""
  for key in key_sequence:
    if key in current_dict:
      current_dict = current_dict[key]
    else:
      if raise_if_absent:
        raise KeyError(
            "Unable to find key '{}' in json_data{}: json_data = {}".format(
                key, key_text, json_data))
      else:
        return None
    key_text += "['{}']".format(key)
  return current_dict


def register_at_fork(before=None, after_in_parent=None, after_in_child=None):
  """Workaround to simulate os.register_at_fork() behavior in all Python versions.

  Args:
      before (func): function to call prior to os.fork() call.
      after_in_parent (func): function to call after os.fork() returns in the
        parent process.
      after_in_child (func): function to call after os.fork() returns in the
        child process.

  Note: For Python >= 3.7, this delegates to os.register_at_fork(). For Python
    < 3.7, the functions need to be run manually via
    common_utils.run_before_fork() prior to os.fork() and
    common_utils.run_after_fork_in_parent() after os.fork() returns in the
    parent process.
      Note that os.fork() is used internally by the "multiprocessing" library:
        multiprocessing.Process().start() and multiprocessing.Manager() both
        use os.fork().
  """
  if hasattr(os, "register_at_fork"):
    os.register_at_fork(
        before=before,
        after_in_parent=after_in_parent,
        after_in_child=after_in_child)
  else:
    global _run_before_fork_functions
    global _run_after_fork_in_parent_functions
    global _register_after_fork_sentinels

    if callable(before):
      _run_before_fork_functions.append(before)
    if callable(after_in_parent):
      _run_after_fork_in_parent_functions.append(after_in_parent)
    if callable(after_in_child):

      def _consume_sentinel_wrapper(_):
        """Consumes the sentinel argument passed into the function."""
        after_in_child()

      sentinel = _Sentinel()
      _register_after_fork_sentinels.append(sentinel)
      # pytype: disable=module-attr
      multiprocessing.util.register_after_fork(sentinel,
                                               _consume_sentinel_wrapper)
      # pytype: enable=module-attr


def run_after_fork_in_parent():
  """Run functions registered to run in parent after os.fork() calls."""
  for func in _run_after_fork_in_parent_functions:
    func()


def run_before_fork():
  """Run functions registered to run before os.fork() calls."""
  for func in _run_before_fork_functions:
    func()


def title_to_snake_case(s):
  """Convert TitleCase string to snake_case.

  Args:
      s (str): TitleCase string.

  Returns:
      str: snake_case string.

  Raises:
      ValueError: provided string contains underscores.

  Note:
      consecutive capital characters are supported ("ABc"), but underscores
      are not.
  """
  if "_" in s:
    raise ValueError(
        "{} is not a TitleCase string (found underscores).".format(s))

  word_starts = [pos for pos in range(len(s)) if _is_new_word(s, pos)
                ] + [len(s)]
  words = [
      s[word_starts[idx]:word_starts[idx + 1]].lower()
      for idx in range(len(word_starts) - 1)
  ]
  return "_".join(words)


def _is_new_word(s, pos):
  """Returns whether a new words starts at s[pos] in a TitleCase string."""
  return (pos == 0 or (s[pos].isupper() and
                       (not s[pos - 1].isupper() or
                        (pos + 1 < len(s) and not s[pos + 1].isupper()))))
