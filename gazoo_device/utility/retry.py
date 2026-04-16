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
import itertools
import logging
import time
from typing import Any, Callable, Mapping, Optional, Sequence, TypeVar

from gazoo_device import errors


_LOGGER = logging.getLogger(__name__)


def _default_is_successful(_: Any) -> bool:
  return True


def not_func(val: Any) -> bool:
  """Returns True if bool(val) evaluates to False."""
  return not bool(val)


def is_true(val: Any) -> bool:
  """Returns True if bool(val) evaluates to True."""
  return bool(val)


_FuncReturnT = TypeVar("_FuncReturnT")


def retry(
    func: Callable[..., _FuncReturnT],
    func_args: Sequence[Any] = (),
    func_kwargs: Optional[Mapping[str, Any]] = None,
    is_successful: Callable[[_FuncReturnT], bool] = _default_is_successful,
    timeout: float = 10,
    interval: float = 1,
    reraise: bool = True,
    exc_type: type[Exception] = errors.CommunicationTimeoutError,
    logger: logging.Logger = _LOGGER,
    log_prefix: str = "[RETRY]",
) -> _FuncReturnT:
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
    logger: Logger to use for logging attempt failures at DEBUG level.
    log_prefix: String to prefix to the log message (e.g., "[WIFI]").

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
  func_results = []

  while time.time() < end_time:
    exception_occurred = False
    tried_times += 1
    try:
      func_result = func(*func_args, **func_kwargs)
    except Exception as e:  # pylint: disable=broad-except
      func_result = e
      if reraise:
        raise
      else:
        exception_occurred = True

    if not exception_occurred and is_successful(func_result):
      return func_result

    logger.debug(
        "%s Attempt %d (%.1fs elapsed) of %s(%s, %s) failed with %s: %r",
        log_prefix,
        tried_times,
        time.time() - start_time,
        getattr(func, "__name__", repr(func)),
        func_args,
        func_kwargs,
        "exception" if exception_occurred else "result",
        func_result,
    )

    time.sleep(interval)
    func_results.append(repr(func_result))

  time_elapsed = time.time() - start_time
  func_result_lines = []
  seq = 1
  for func_result, func_result_group in itertools.groupby(func_results):
    func_result_group_size = len(list(func_result_group))
    if func_result_group_size == 1:
      result_seq = "{:3}     ".format(seq)
    else:
      result_seq = "{:3}..{:3}".format(seq, seq+func_result_group_size-1)
    func_result_lines.append(f"{result_seq}: {func_result}")
    seq += func_result_group_size
  func_summary = "\n".join(func_result_lines)
  raise exc_type(f"Timeout in {time_elapsed}s. Tried calling {func.__name__} "
                 f"{tried_times} times with a {interval}-second interval. "
                 f"Call results:\n{func_summary}.")
