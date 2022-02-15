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

"""Function call retry utility."""
import time
from typing import Any, Callable, Mapping, Optional, Sequence, Type, TypeVar

from gazoo_device import errors


def _default_is_successful(_: Any) -> bool:
  return True


def not_func(val: Any) -> bool:
  """Returns True if bool(val) evaluates to False."""
  return not bool(val)


def is_true(val: Any) -> bool:
  """Returns True if bool(val) evaluates to True."""
  return bool(val)


_FuncReturnType = TypeVar("_FuncReturnType")


def retry(
    func: Callable[..., _FuncReturnType],
    func_args: Sequence[Any] = (),
    func_kwargs: Optional[Mapping[str, Any]] = None,
    is_successful: Callable[[_FuncReturnType], bool] = _default_is_successful,
    timeout: float = 10,
    interval: float = 1,
    reraise: bool = True,
    exc_type: Type[Exception] = errors.CommunicationTimeoutError
) -> _FuncReturnType:
  """Retries func() until it succeeds or timeout is reached.

  Success of execution of func() is determined by is_successful() function,
  which should return True on successful execution of func().

  Args:
    func: Function to execute.
    func_args: Positional arguments to the function.
    func_kwargs: Keyword arguments to the function.
    is_successful: Function which takes in the result of func() and returns
      whether function execution should be considered successful. To indicate
      success, return True. Defaults to always returning True.
    timeout: If no run of func() succeeds in this time period, raise an error.
    interval: How long to wait between attempts of func().
    reraise: Whether to re-raise exceptions in func() or not. If True, will
      re-raise any exceptions from func(). If False, considers execution of
      func() a failure if an Exception is raised. is_successful() will NOT be
      called if an Exception occurs.
    exc_type: Type of exception to raise when timeout is reached. Note that the
    class constructor will be called with just 1 argument.

  Returns:
    Return value of first successful func() call.

  Raises:
    Exception: if timeout is reached, or if an Exception occurs in func() with
    reraise=True.
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
    except Exception:  # pylint: disable=broad-except
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
