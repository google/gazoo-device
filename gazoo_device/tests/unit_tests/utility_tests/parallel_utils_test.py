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
import importlib
import time
from typing import NoReturn
import unittest
from unittest import mock

from absl import flags
from absl.testing import parameterized
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device import manager
from gazoo_device import package_registrar
from gazoo_device.base_classes import gazoo_device_base
from gazoo_device.capabilities.interfaces import flash_build_base
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import multiprocessing_utils
from gazoo_device.utility import parallel_utils


def load_tests(loader, standard_tests, pattern):
  """Skips ParallelUtilsIntegrationTests if '-s' flag is provided."""
  del standard_tests, pattern  # Unused.
  suite = unittest.TestSuite(
      loader.loadTestsFromTestCase(ParallelUtilsUnitTests))
  if not flags.FLAGS.skip_slow:
    suite.addTests(loader.loadTestsFromTestCase(ParallelUtilsIntegrationTests))
  return suite


class ParallelUtilsUnitTests(unit_test_case.UnitTestCase):
  """Unit tests for parallel_utils. Parallel processes are mocked."""

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
    elif function is parallel_utils.reboot:
      device_method = mock_device.reboot
    else:
      device_method = mock_device.flash_build.upgrade

    if raises:
      device_method.side_effect = errors.DeviceError("Failed")
      with self.assertRaisesRegex(errors.DeviceError, "Failed"):
        function(mock_manager, mock_device.name, *method_args, **method_kwargs)
    else:
      device_method.return_value = None
      self.assertIsNone(
          function(
              mock_manager, mock_device.name, *method_args, **method_kwargs))

    mock_manager.create_device.assert_called_once_with(mock_device.name)
    device_method.assert_called_once_with(*method_args, **method_kwargs)
    mock_device.close.assert_called_once()

  @mock.patch.object(gdm_logger, "initialize_child_process_logging")
  @mock.patch.object(gdm_logger, "get_logger")
  @mock.patch.object(package_registrar, "register")
  @mock.patch.object(importlib, "import_module")
  @mock.patch.object(manager, "Manager")
  def test_process_wrapper_successful_call(
      self, mock_manager_class, mock_import, mock_register, mock_get_logger,
      mock_initialize_logging):
    """Tests _process_wrapper for a process where there are no errors."""
    mock_manager = mock_manager_class.return_value
    mock_logger = mock_get_logger.return_value
    multiprocessing_queue = multiprocessing_utils.get_context().Queue()
    return_queue = mock.MagicMock(spec=multiprocessing_queue)
    error_queue = mock.MagicMock(spec=multiprocessing_queue)
    logging_queue = mock.MagicMock(spec=multiprocessing_queue)
    process_id = "1"
    mock_function = mock.MagicMock()
    mock_function.__name__ = "mock_function"
    args = (1, 2)
    kwargs = {"foo": "bar"}
    parallel_utils._process_wrapper(
        return_queue=return_queue,
        error_queue=error_queue,
        logging_queue=logging_queue,
        process_id=process_id,
        extension_package_import_paths=["foo.package", "bar.package"],
        call_spec=parallel_utils.CallSpec(mock_function, *args, **kwargs))

    mock_initialize_logging.assert_called_once_with(logging_queue)
    mock_get_logger.assert_called_once()
    mock_logger.debug.assert_called()
    mock_import.assert_has_calls(
        [mock.call("foo.package"), mock.call("bar.package")])
    self.assertEqual(mock_register.call_count, 2)
    mock_manager_class.assert_called_once()
    mock_function.assert_called_once_with(mock_manager, *args, **kwargs)
    return_queue.put.assert_called_once_with(
        (process_id, mock_function.return_value))
    error_queue.put.assert_not_called()
    mock_manager.close.assert_called_once()

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
  def test_process_wrapper_exception_call(
      self, mock_manager_class, mock_import, mock_register, mock_get_logger,
      mock_initialize_logging):
    """Tests _process_wrapper for a process where function raises an error."""
    mock_manager = mock_manager_class.return_value
    mock_logger = mock_get_logger.return_value
    multiprocessing_queue = multiprocessing_utils.get_context().Queue()
    return_queue = mock.MagicMock(spec=multiprocessing_queue)
    error_queue = mock.MagicMock(spec=multiprocessing_queue)
    process_id = "1"
    mock_function = mock.MagicMock()
    mock_function.__name__ = "mock_function"
    mock_function.side_effect = RuntimeError("Something went wrong")
    args = (1, 2)
    kwargs = {"foo": "bar"}
    parallel_utils._process_wrapper(
        return_queue=return_queue,
        error_queue=error_queue,
        logging_queue=mock.MagicMock(spec=multiprocessing_queue),
        process_id=process_id,
        # "foo.package" imports but fails registration.
        # "bar.package" fails to import.
        extension_package_import_paths=["foo.package", "bar.package"],
        call_spec=parallel_utils.CallSpec(mock_function, *args, **kwargs))

    mock_import.assert_has_calls(
        [mock.call("foo.package"), mock.call("bar.package")])
    mock_register.assert_called_once()
    mock_manager_class.assert_called_once()
    mock_function.assert_called_once_with(mock_manager, *args, **kwargs)
    mock_logger.warning.assert_called()
    return_queue.put.assert_not_called()
    error_queue.put.assert_called_once()
    pid, (error_type, error_msg, error_tb) = error_queue.put.call_args[0][0]
    self.assertEqual(pid, process_id)
    self.assertEqual(error_type, RuntimeError.__name__)
    self.assertEqual(error_msg, "Something went wrong")
    self.assertRegex(
        error_tb, "(?s)Traceback.*RuntimeError: Something went wrong")
    mock_manager.close.assert_called_once()


def _test_function_with_return(
    manager_inst: manager.Manager, some_arg: int) -> int:
  """Returns some_arg."""
  assert isinstance(manager_inst, manager.Manager)
  return some_arg


def _test_function_no_return(manager_inst: manager.Manager) -> None:
  """Function without a return statement."""
  assert isinstance(manager_inst, manager.Manager)


_TEST_EXCEPTION = RuntimeError("Something went wrong.")


def _test_function_raises_exception(manager_inst: manager.Manager) -> NoReturn:
  """Function which raises an error."""
  raise _TEST_EXCEPTION


def _test_function_times_out(manager_inst: manager.Manager) -> None:
  """Function which is designed to time out."""
  assert isinstance(manager_inst, manager.Manager)
  time.sleep(15)


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
        raise_on_process_error=True)
    self.assertEqual(results, _GOOD_CALL_RESULTS)
    self.assertEqual(call_errors, _GOOD_CALL_ERRORS)

  def test_execute_concurrently_error_with_raise_on_process_error(self):
    """Tests execute_concurrently with errors and raise_on_process_error set."""
    regex = (r"(?s)Encountered errors in parallel processes:\n"
             r"Traceback.*RuntimeError: Something went wrong\.")
    with self.assertRaisesRegex(errors.ParallelUtilsError, regex):
      parallel_utils.execute_concurrently(
          _GOOD_CALL_SPECS + _ERROR_CALL_SPECS,
          timeout=_GOOD_CALL_TIMEOUT_S,
          raise_on_process_error=True)

  def test_execute_concurrently_error_without_raise_on_process_error(self):
    """Tests execute_concurrently with errors and no raise_on_process_error."""
    results, call_errors = parallel_utils.execute_concurrently(
        _GOOD_CALL_SPECS + _ERROR_CALL_SPECS,
        timeout=_GOOD_CALL_TIMEOUT_S,
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
          raise_on_process_error=True)


if __name__ == "__main__":
  unit_test_case.main()
