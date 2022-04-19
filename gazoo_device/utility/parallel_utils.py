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
"""Utilities for interacting with devices in parallel.

Usage example:

  def my_custom_hello_world_function(manager_inst: manager.Manager,
                                     device_name: str, some_arg: int) -> str:
    '''Example function which executes a custom action on a device.

    Args:
      manager_inst: A Manager instance which can be used for device creation.
        A Manager instance is always provided. You do not need to pass one as an
        argument to the function in the CallSpec.
      device_name: Name of the device to use. Must be specified in the CallSpec.
      some_arg: An example of an argument. Must be specified in the CallSpec.
    '''
    device = manager_inst.create_device(device_name)
    try:
      shell_response = device.shell(f"echo 'Hello world {some_arg}'")
    finally:
      device.close()
    return shell_response

  call_specs = [
      parallel_utils.CallSpec(parallel_utils.reboot, "device-1234"),
      parallel_utils.CallSpec(parallel_utils.reboot, "device-2345",
                              no_wait=True, method="shell"),
      parallel_utils.CallSpec(parallel_utils.factory_reset, "device-3456"),
      parallel_utils.CallSpec(parallel_utils.upgrade, "device-4567",
                              build_number=1234, build_branch="1.0"),
      parallel_utils.CallSpec(parallel_utils.upgrade, "device-5678",
                              build_file="/some/file/path.zip"),
      parallel_utils.CallSpec(my_custom_hello_world_function, "device-6789",
                              1),
      parallel_utils.CallSpec(my_custom_hello_world_function, "device-7890",
                              some_arg=2),
  ]

  results, _ = parallel_utils.execute_concurrently(
      call_specs, timeout=300, raise_on_process_error=True)

Results are returned in the same order as call specs. For the hypothetical
example above, results would be
  [None, None, None, None, None, "Hello world 1", "Hello world 2"].

If you need more granular control over exceptions raised in parallel processes,
set raise_on_process_error to False. For example:

  def custom_function_raises(
      manager_inst: manager.Manager, some_arg: int) -> NoReturn:
    raise RuntimeError(f"Demo of exception handling {some_arg}")

  results, errors = parallel_utils.execute_concurrently(
      call_specs = [
          parallel_utils.CallSpec(custom_function_raises, 1),
          parallel_utils.CallSpec(custom_function_raises, 2),
      ],
      timeout=15,
      raise_on_process_error=False)

In this case results will be ["< No result received >",
                              "< No result received >"].
Errors will be [
    ("RuntimeError", "Demo of exception handling 1", "< Exception traceback >"),
    ("RuntimeError", "Demo of exception handling 2", "< Exception traceback >"),
].

Logging behavior:
  Parallel process GDM logger logs are sent to the main process.
  Device logs (from device instances created in parallel processes) are stored
  in new individual device log files.
"""
import concurrent.futures
import dataclasses
import importlib
import multiprocessing
import os
import time
import traceback
from typing import Any, Callable, List, Optional, Sequence, Tuple

from gazoo_device import errors
from gazoo_device import extensions
from gazoo_device import gdm_logger
from gazoo_device import manager
from gazoo_device import package_registrar
from gazoo_device.utility import multiprocessing_utils
import immutabledict

NO_RESULT = "< No result received >"
NO_TRACEBACK = "< No traceback available >"
TIMEOUT_PROCESS = 600.0
_TIMEOUT_TERMINATE_PROCESS = 3
_QUEUE_READ_TIMEOUT = 1
_AnySerializable = Any


@dataclasses.dataclass(init=False)
class CallSpec:
  """Specifies a call to be executed in a parallel process.

  The function will be called in a parallel process as follows:
    return_value = function(<ManagerInstance>, *args, **kwargs)

  A Manager instance is always provided as the first argument to the function,
  followed by *args and **kwargs. The Manager instance will be closed
  automatically after the function returns.

  If the function is performing a device action, it is expected to create a
  device instance using the provided Manager instance (the device name to create
  should be included in the function's arguments), use the device instance to
  perform some action (possibly parameterized by args and kwargs), and close the
  device instance before returning. The return_value of the function will be
  returned to the main process.

  Attributes:
    function: Function to call in the parallel process. The function and its
      return value must be serializable. Prefer module-level functions. In
      particular, lambdas and inner (nested) functions are not serializable.
      Other limitations:
      - For devices communicating over UART or serial: ensure that access to
        device communication is mutually exclusive. In particular, make sure
        that device communication (`<device>.switchboard`) is closed in the main
        process before issuing a parallel action on it and do not execute
        simultaneous parallel actions on the same device.
        `<device>.reset_capability("switchboard")` can be used to close device
        communication, and it will be automatically reopened on the next access.
        - Do not modify GDM device configs (detection, set-prop) in parallel.
        This can result in a race condition.
    args: Positional arguments to the function. Must be serializable. In
      particular, Manager and device instances as well their instance methods
      are not serializable.
    kwargs: Keyword arguments to the function. Must be serializable.
  """
  function: Callable[..., _AnySerializable]
  args: Tuple[_AnySerializable, ...]
  kwargs: immutabledict.immutabledict[str, _AnySerializable]

  def __init__(self, function: Callable[..., _AnySerializable],
               *args: _AnySerializable, **kwargs: _AnySerializable):
    self.function = function
    self.args = args
    self.kwargs = immutabledict.immutabledict(kwargs)


def _process_init(
    logging_queue: multiprocessing.Queue,
    extension_package_import_paths: Sequence[str],
) -> None:
  """Initializes worker process."""
  gdm_logger.initialize_child_process_logging(logging_queue)
  logger = gdm_logger.get_logger()
  short_description = f"_process_init in process {os.getpid()}"
  # The state of the main process (such as registered extension packages) is not
  # copied over when using "forkserver" or "spawn" as the process start method.
  for import_path in extension_package_import_paths:
    try:
      package_registrar.register(importlib.import_module(import_path))
    except (ImportError, errors.PackageRegistrationError) as e:
      logger.debug(f"{short_description}: failed to import and register GDM "
                   f"extension package with import path {import_path}. "
                   f"Error: {e!r}. Proceeding despite the failure.")


def _process_wrapper(call_spec: CallSpec) -> Any:
  """Executes the provided function in a parallel process."""
  logger = gdm_logger.get_logger()
  short_description = f"{call_spec.function.__name__} in process {os.getpid()}"
  logger.debug(f"{short_description}: starting execution of {call_spec}...")

  manager_inst = manager.Manager()
  try:
    return_value = call_spec.function(manager_inst, *call_spec.args,
                                      **call_spec.kwargs)
    logger.debug(f"{short_description}: execution succeeded. "
                 f"Return value: {return_value}.")
    return return_value
  finally:
    manager_inst.close()


def _format_process_errors(
    proc_errors: Sequence[Optional[Tuple[str, str, str]]]) -> str:
  """Returns a formatted string with all process errors."""
  formatted_errors = []
  for proc_error in proc_errors:
    if proc_error is not None:
      error_type, error_message, error_tb = proc_error
      if error_tb != NO_TRACEBACK:
        formatted_error = error_tb
      else:
        formatted_error = f"{error_type}({error_message!r})"
      formatted_errors.append(formatted_error)
  return "\n".join(formatted_errors)


def execute_concurrently(
    call_specs: Sequence[CallSpec],
    timeout: float = TIMEOUT_PROCESS,
    raise_on_process_error: bool = True,
    max_processes: Optional[int] = None,
) -> Tuple[List[Any], List[Optional[Tuple[str, str, str]]]]:
  """Concurrently executes function calls in parallel processes.

  Args:
    call_specs: Specifications for each of the parallel executions.
    timeout: Time to wait before terminating all of the parallel processes.
    raise_on_process_error: If True, raise an error if any of the parallel
      processes encounters an error. If False, return a list of errors which
      occurred in the parallel processes along with the received results.
    max_processes: Maximum number of processes to use for the tasks. If set to
      None then os.cpu_count() is used. See docs for futures.ProcessPoolExecutor
      https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.ProcessPoolExecutor

  Returns:
    A tuple of (parallel_process_return_values, parallel_process_errors).
    The order of return values and errors corresponds to the order of provided
    call_specs. parallel_process_return_values will contain return values of the
    functions executed in parallel. If a parallel process fails, the
    corresponding entry in the return value list will be NO_RESULT.
    Errors are only returned if raise_on_process_error is False.
    Each error is specified as a tuple of
    (error_type, error_message, error_traceback). If a parallel process succeeds
    (there's no error), the corresponding entry in the error list will be None.

  Raises:
    ParallelUtilsError: If raise_on_process_error is True and any of the
      parallel processes encounters an error.
  """
  gdm_logger.switch_to_multiprocess_logging()
  logging_queue = gdm_logger.get_logging_queue()
  extension_package_import_paths = [
      package_info["import_path"]
      for package_name, package_info in extensions.package_info.items()
      if package_name != "gazoo_device_controllers"  # Built-in controllers.
  ]

  proc_results = []
  proc_errors = []
  futures = []
  with concurrent.futures.ProcessPoolExecutor(
      max_workers=max_processes,
      mp_context=multiprocessing_utils.get_context(),
      initializer=_process_init,
      initargs=(logging_queue, extension_package_import_paths)) as executor:
    for call_spec in call_specs:
      futures.append(executor.submit(_process_wrapper, call_spec=call_spec))

    deadline = time.time() + timeout
    # Get results and errors.
    for future in futures:
      try:
        remaining_timeout = max(0, deadline - time.time())
        proc_results.append(future.result(timeout=remaining_timeout))
        proc_errors.append(None)
      except concurrent.futures.TimeoutError as e:
        future.cancel()
        proc_results.append(NO_RESULT)
        proc_errors.append((
            errors.ResultNotReceivedError.__name__,
            "Did not receive any results from the process.",
            NO_TRACEBACK))
      except Exception as e:  # pylint: disable=broad-except
        proc_results.append(NO_RESULT)
        proc_errors.append((type(e).__name__, str(e), traceback.format_exc()))

  if raise_on_process_error and any(proc_errors):
    raise errors.ParallelUtilsError(
        "Encountered errors in parallel processes:\n"
        f"{_format_process_errors(proc_errors)}")

  return proc_results, proc_errors


def factory_reset(manager_inst: manager.Manager, device_name: str) -> None:
  """Convenience function for factory resetting devices in parallel."""
  device = manager_inst.create_device(device_name)
  try:
    device.factory_reset()
  finally:
    device.close()


def reboot(manager_inst: manager.Manager, device_name: str, *reboot_args: Any,
           **reboot_kwargs: Any) -> None:
  """Convenience function for rebooting devices in parallel."""
  device = manager_inst.create_device(device_name)
  try:
    device.reboot(*reboot_args, **reboot_kwargs)
  finally:
    device.close()


def upgrade(manager_inst: manager.Manager, device_name: str, *upgrade_args: Any,
            **upgrade_kwargs: Any) -> None:
  """Convenience function for upgrading devices in parallel."""
  device = manager_inst.create_device(device_name)
  try:
    device.flash_build.upgrade(*upgrade_args, **upgrade_kwargs)
  finally:
    device.close()
