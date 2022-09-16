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

"""Unit and integration (multiprocessing) tests for parallel_utils."""
import concurrent.futures
import functools
import importlib
import time
from typing import NoReturn
import unittest
from unittest import mock

from absl import flags
from absl.testing import parameterized

from gazoo_device import errors
from gazoo_device import extensions
from gazoo_device import gdm_logger
from gazoo_device import manager
from gazoo_device import package_registrar
from gazoo_device.base_classes import gazoo_device_base
from gazoo_device.capabilities.interfaces import flash_build_base
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import parallel_utils


_TEST_EXCEPTION = RuntimeError("Something went wrong.")


def _test_function_with_return(
    manager_inst: manager.Manager, some_arg: int) -> int:
  """Returns some_arg."""
  assert isinstance(manager_inst, manager.Manager)
  return some_arg


def _test_function_no_return(manager_inst: manager.Manager) -> None:
  """Function without a return statement."""
  assert isinstance(manager_inst, manager.Manager)


def _test_function_raises_exception(manager_inst: manager.Manager) -> NoReturn:
  """Function which raises an error."""
  raise _TEST_EXCEPTION


def _test_function_times_out(manager_inst: manager.Manager) -> None:
  """Function which is designed to time out."""
  assert isinstance(manager_inst, manager.Manager)
  time.sleep(15)


def load_tests(loader, standard_tests, pattern):
  """Skips ParallelUtilsIntegrationTests if '-s' flag is provided."""
  del standard_tests, pattern  # Unused.
  suite = unittest.TestSuite(
      loader.loadTestsFromTestCase(ParallelUtilsUnitTests))
  if not flags.FLAGS.skip_slow:
    suite.addTests(loader.loadTestsFromTestCase(ParallelUtilsIntegrationTests))
  return suite


class MockFuture:
  """Mocks behavior of a concurrent.futures.Future object."""

  def __init__(self, fn, *args, **kwargs):
    self.fn = fn
    self.args = args
    self.kwargs = kwargs

  def result(self, timeout=None):
    del timeout  # No-op for this mock. Use mock with side effect for timeout.
    return self.fn(*self.args, **self.kwargs)

  def cancel(self):
    pass


def _mock_submit_func(pool_mock, fn, *args, **kwargs):
  pool_mock_call_args = pool_mock.call_args[1]
  if pool_mock_call_args["initializer"]:
    pool_mock_call_args["initializer"](*pool_mock_call_args["initargs"])
  return MockFuture(fn, *args, **kwargs)


class ParallelUtilsUnitTests(unit_test_case.UnitTestCase):
  """Unit tests for parallel_utils. Parallel processes are mocked."""

  def setUp(self):
    super().setUp()
    # Mock ProcessPoolExecutor so tasks execute in sequence.
    self.process_pool_mock = self.enter_context(
        mock.patch.object(
            concurrent.futures, "ProcessPoolExecutor", autospec=True))

    self.executor_mock = mock.create_autospec(spec=concurrent.futures.Executor)
    self.process_pool_mock.return_value.__enter__.return_value = self.executor_mock
    self.executor_mock.submit = functools.partial(
        _mock_submit_func, self.process_pool_mock)

  @parameterized.named_parameters(
      ("factory_reset_success", parallel_utils.factory_reset, (), {}, False),
      ("factory_reset_failure", parallel_utils.factory_reset, (), {}, True),
      ("reboot_success", parallel_utils.reboot, (False,), {"method": "shell"},
       False),
      ("reboot_failure", parallel_utils.reboot, (False,), {"method": "shell"},
       True),
      ("upgrade_success", parallel_utils.upgrade, (),
       {"build_file": "/some/file", "forced_upgrade": False}, False),
      ("upgrade_failure", parallel_utils.upgrade, (),
       {"build_file": "/some/file", "forced_upgrade": False}, True))
  def test_convenience_parallel_function(
      self, function, method_args, method_kwargs, raises):
    """Tests one of the provided convenience parallel functions."""
    mock_manager = mock.MagicMock(spec=manager.Manager)
    mock_device = mock.MagicMock(spec=gazoo_device_base.GazooDeviceBase)
    mock_device.flash_build = mock.MagicMock(flash_build_base.FlashBuildBase)
    mock_device.name = "device-1234"
    mock_manager.create_device.return_value = mock_device

    if function is parallel_utils.factory_reset:
      device_method = mock_device.factory_reset
      device_method.__name__ = "factory_reset"
    elif function is parallel_utils.reboot:
      device_method = mock_device.reboot
      device_method.__name__ = "reboot"
    else:
      device_method = mock_device.flash_build.upgrade
      device_method.__name__ = "upgrade"

    if raises:
      device_method.side_effect = errors.DeviceError("Failed")
      with self.assertRaisesRegex(errors.DeviceError, "Failed"):
        function(mock_manager, mock_device.name, *method_args, **method_kwargs)
    else:
      device_method.return_value = None
      self.assertIsNone(
          function(
              mock_manager, mock_device.name, *method_args, **method_kwargs))

    mock_manager.create_device.assert_called_once_with(
        mock_device.name, log_name_prefix=device_method.__name__)
    device_method.assert_called_once_with(*method_args, **method_kwargs)
    mock_device.close.assert_called_once()

  @mock.patch.object(extensions, "package_info")
  @mock.patch.object(gdm_logger, "initialize_child_process_logging")
  @mock.patch.object(gdm_logger, "get_logger")
  @mock.patch.object(package_registrar, "register")
  @mock.patch.object(importlib, "import_module")
  @mock.patch.object(manager, "Manager")
  def test_process_init_successful_call(
      self, mock_manager_class, mock_import, mock_register, mock_get_logger,
      mock_initialize_logging, mock_package_info):
    """Tests process init sets up process correctly."""
    mock_package_info.items.return_value = [
        ("package_1", {"import_path": "foo.package"}),
        ("package_2", {"import_path": "bar.package"}),
    ]
    mock_manager = mock_manager_class.return_value
    mock_logger = mock_get_logger.return_value
    mock_function = mock.MagicMock()
    mock_function.__name__ = "mock_function"
    args = (1, 2)
    mock_function.return_value = args
    kwargs = {"foo": "bar"}
    proc_results, _ = parallel_utils.execute_concurrently(
        [parallel_utils.CallSpec(mock_function, *args, **kwargs)]
    )
    mock_get_logger.assert_called()
    mock_logger.debug.assert_called()
    mock_import.assert_has_calls(
        [mock.call("foo.package"), mock.call("bar.package")])
    self.assertEqual(mock_register.call_count, 2)
    mock_manager_class.assert_called_once()
    mock_function.assert_called_once_with(mock_manager, *args, **kwargs)
    self.assertEqual(proc_results[0], args)
    mock_manager.close.assert_called_once()

  @mock.patch.object(extensions, "package_info")
  @mock.patch.object(gdm_logger, "initialize_child_process_logging")
  @mock.patch.object(gdm_logger, "get_logger")
  @mock.patch.object(package_registrar, "register")
  @mock.patch.object(importlib, "import_module")
  @mock.patch.object(manager, "Manager")
  def test_process_init_successful_call_with_manager_kwarg(
      self, mock_manager_class, mock_import, mock_register,
      mock_get_logger, mock_initialize_logging, mock_package_info):
    """Tests process init sets up process bcorrectly."""
    mock_package_info.items.return_value = [
        ("package_1", {"import_path": "foo.package"}),
        ("package_2", {"import_path": "bar.package"}),
    ]
    mock_manager = mock_manager_class.return_value
    mock_logger = mock_get_logger.return_value
    mock_function = mock.MagicMock()
    mock_function.__name__ = "mock_function"
    args = (1, 2)
    mock_function.return_value = args

    kwargs = {"foo": "bar"}
    manager_kwargs = {"log_directory": "/fake/log/path"}
    proc_results, _ = parallel_utils.execute_concurrently([
        parallel_utils.CallSpec(
            mock_function, *args, manager_kwargs=manager_kwargs, **kwargs)
    ])

    mock_get_logger.assert_called()
    mock_logger.debug.assert_called()
    mock_import.assert_has_calls(
        [mock.call("foo.package"), mock.call("bar.package")])
    self.assertEqual(mock_register.call_count, 2)
    mock_manager_class.assert_called_once_with(**manager_kwargs)
    mock_function.assert_called_once_with(mock_manager, *(1, 2),
                                          **{"foo": "bar"})
    self.assertEqual(proc_results[0], args)
    mock_manager.close.assert_called_once()

  @mock.patch.object(extensions, "package_info")
  @mock.patch.object(gdm_logger, "initialize_child_process_logging")
  @mock.patch.object(gdm_logger, "get_logger")
  @mock.patch.object(
      package_registrar,
      "register",
      side_effect=errors.PackageRegistrationError(
          "Registration failed", "foo.package"))
  @mock.patch.object(importlib, "import_module", side_effect=[
      None, ImportError("Importing bar.package failed")])
  @mock.patch.object(manager, "Manager")
  def test_process_init_fail(
      self, mock_manager_class, mock_import, mock_register, mock_get_logger,
      mock_initialize_logging, mock_package_info):
    """Tests process_init fails."""
    # This test is for checking that we handle errors in the init process
    # without causing all workers to stop.
    mock_logger = mock_get_logger.return_value
    mock_package_info.items.return_value = [
        ("package_1", {"import_path": "foo.package"}),
        ("package_2", {"import_path": "bar.package"}),
    ]
    mock_function = mock.MagicMock()
    mock_function.__name__ = "mock_function"
    args = (1, 2)
    kwargs = {"foo": "bar"}
    _, proc_errors = parallel_utils.execute_concurrently(
        [parallel_utils.CallSpec(mock_function, *args, **kwargs)],
        raise_on_process_error=True
    )
    mock_logger.debug.assert_called()
    self.assertLen(proc_errors, 1)

  @mock.patch.object(gdm_logger, "initialize_child_process_logging")
  @mock.patch.object(gdm_logger, "get_logger")
  @mock.patch.object(package_registrar, "register")
  @mock.patch.object(importlib, "import_module")
  @mock.patch.object(manager, "Manager")
  def test_execute_concurrently_successful_call(
      self, mock_manager_class, mock_import, mock_register, mock_get_logger,
      mock_initialize_logging):
    """Tests execute_concurrently for a process where there are no errors."""
    mock_function = mock.MagicMock()
    mock_function.__name__ = "mock_function"
    args = (1, 2)
    mock_function.return_value = args
    kwargs = {"foo": "bar"}
    proc_results, proc_errors = parallel_utils.execute_concurrently(
        [parallel_utils.CallSpec(mock_function, *args, **kwargs)]
    )
    self.assertEqual(proc_results[0], args)
    self.assertIsNone(proc_errors[0])

  @mock.patch.object(gdm_logger, "initialize_child_process_logging")
  @mock.patch.object(gdm_logger, "get_logger")
  @mock.patch.object(
      package_registrar,
      "register",
      side_effect=errors.PackageRegistrationError(
          "Registration failed", "foo.package"))
  @mock.patch.object(importlib, "import_module", side_effect=[
      None, ImportError("Importing bar.package failed")])
  @mock.patch.object(manager, "Manager")
  def test_execute_concurrently_exception_call(
      self, mock_manager_class, mock_import, mock_register, mock_get_logger,
      mock_initialize_logging):
    """Tests process error while raise_on_process_error set to False."""
    mock_function = mock.MagicMock()
    mock_function.__name__ = "mock_function"
    mock_function.side_effect = RuntimeError("Something went wrong")
    args = (1, 2)
    kwargs = {"foo": "bar"}
    _, proc_errors = parallel_utils.execute_concurrently(
        [parallel_utils.CallSpec(mock_function, *args, **kwargs)],
        raise_on_process_error=False
    )

    error_type, error_msg, error_tb = proc_errors[0]
    self.assertEqual(error_type, RuntimeError.__name__)
    self.assertEqual(error_msg, "Something went wrong")
    self.assertRegex(
        error_tb, "(?s)Traceback.*RuntimeError: Something went wrong")

  @mock.patch.object(gdm_logger, "initialize_child_process_logging")
  @mock.patch.object(gdm_logger, "get_logger")
  @mock.patch.object(package_registrar, "register")
  @mock.patch.object(importlib, "import_module")
  @mock.patch.object(manager, "Manager")
  def test_execute_concurrently_exception_call_no_wait(
      self, mock_manager_class, mock_import, mock_register, mock_get_logger,
      mock_initialize_logging):
    """Tests process error while raise_on_process_error set to True."""
    mock_function = mock.MagicMock()
    mock_function.__name__ = "mock_function"
    mock_function.side_effect = RuntimeError("Something went wrong.")
    args = (1, 2)
    kwargs = {"foo": "bar"}
    regex = (r"(?s)Encountered errors in parallel processes:\n"
             r".*?Traceback.*RuntimeError: Something went wrong")
    with self.assertRaisesRegex(errors.ParallelUtilsError, regex):
      parallel_utils.execute_concurrently(
          [parallel_utils.CallSpec(mock_function, *args, **kwargs)],
          raise_on_process_error=True
      )

_GOOD_CALL_TIMEOUT_S = 30
_GOOD_CALL_SPECS = [
    parallel_utils.CallSpec(_test_function_with_return, 5),
    parallel_utils.CallSpec(_test_function_with_return, some_arg=10),
    parallel_utils.CallSpec(_test_function_no_return),
]
_GOOD_CALL_RESULTS = [5, 10, None]
_GOOD_CALL_ERRORS = [None, None, None]
_ERROR_CALL_SPECS = [parallel_utils.CallSpec(_test_function_raises_exception)]
_ERROR_CALL_RESULTS = [parallel_utils.NO_RESULT]
_TIMEOUT_CALL_SPECS = [parallel_utils.CallSpec(_test_function_times_out)]


class ParallelUtilsIntegrationTests(unit_test_case.UnitTestCase):
  """Integration tests (with multiprocessing) for parallel_utils."""

  def test_execute_concurrently_success(self):
    """Tests execute_concurrently when all parallel processes succeed."""
    results, call_errors = parallel_utils.execute_concurrently(
        _GOOD_CALL_SPECS,
        timeout=_GOOD_CALL_TIMEOUT_S,
        max_processes=3,  # Limit the number of executor processes.
        raise_on_process_error=True)
    self.assertEqual(results, _GOOD_CALL_RESULTS)
    self.assertEqual(call_errors, _GOOD_CALL_ERRORS)

  def test_execute_concurrently_error_with_raise_on_process_error(self):
    """Tests execute_concurrently with errors and raise_on_process_error set."""
    regex = (r"(?s)Encountered errors in parallel processes:\n"
             r".*?Traceback.*RuntimeError: Something went wrong\.")
    with self.assertRaisesRegex(errors.ParallelUtilsError, regex):
      parallel_utils.execute_concurrently(
          _GOOD_CALL_SPECS + _ERROR_CALL_SPECS,
          timeout=_GOOD_CALL_TIMEOUT_S,
          max_processes=3,  # Limit the number of executor processes.
          raise_on_process_error=True)

  def test_execute_concurrently_error_without_raise_on_process_error(self):
    """Tests execute_concurrently with errors and no raise_on_process_error."""
    results, call_errors = parallel_utils.execute_concurrently(
        _GOOD_CALL_SPECS + _ERROR_CALL_SPECS,
        timeout=_GOOD_CALL_TIMEOUT_S,
        max_processes=3,  # Limit the number of executor processes.
        raise_on_process_error=False)
    self.assertEqual(results, _GOOD_CALL_RESULTS + _ERROR_CALL_RESULTS)
    self.assertLen(call_errors, len(_GOOD_CALL_SPECS + _ERROR_CALL_SPECS))
    self.assertEqual(call_errors[:len(_GOOD_CALL_SPECS)], _GOOD_CALL_ERRORS)
    error_call_error = call_errors[len(_GOOD_CALL_SPECS)]
    self.assertIsInstance(error_call_error, tuple)
    error_type, error_msg, error_tb = error_call_error
    self.assertEqual(error_type, type(_TEST_EXCEPTION).__name__)
    self.assertEqual(error_msg, str(_TEST_EXCEPTION))
    self.assertRegex(
        error_tb, r"(?s)Traceback.*RuntimeError: Something went wrong\.")

  def test_execute_concurrently_timeout(self):
    """Tests execute_concurrently with a call that times out."""
    regex = ("Encountered errors in parallel processes:\n"
             "ResultNotReceivedError"
             r"\('Did not receive any results from the process.'\)")
    with self.assertRaisesRegex(errors.ParallelUtilsError, regex):
      parallel_utils.execute_concurrently(
          _TIMEOUT_CALL_SPECS,
          timeout=1,
          max_processes=1,  # Limit the number of executor processes.
          raise_on_process_error=True)


if __name__ == "__main__":
  unit_test_case.main()
