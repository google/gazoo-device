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

"""Unit and integration (multiprocessing) tests for parallel_utils."""
import time
from typing import NoReturn
from unittest import mock

from absl.testing import parameterized
from gazoo_device import errors
from gazoo_device import manager
from gazoo_device.base_classes import gazoo_device_base
from gazoo_device.capabilities.interfaces import flash_build_base
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import parallel_utils


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
  time.sleep(5)


_GOOD_CALL_SPECS = [
    parallel_utils.CallSpec(_test_function_with_return, 5),
    parallel_utils.CallSpec(_test_function_with_return, some_arg=10),
    parallel_utils.CallSpec(_test_function_no_return),
]
_GOOD_CALL_RESULTS = [5, 10, None]
_GOOD_CALL_ERRORS = [None, None, None]
_BAD_CALL_SPECS = [
    parallel_utils.CallSpec(_test_function_raises_exception),
    parallel_utils.CallSpec(_test_function_times_out),
]
_BAD_CALL_RESULTS = [parallel_utils.NO_RESULT] * len(_BAD_CALL_SPECS)
_BAD_CALL_ERRORS = [
    (type(_TEST_EXCEPTION).__name__, str(_TEST_EXCEPTION)),
    (errors.ResultNotReceivedError.__name__,
     "Did not receive any results from the process."),
]


class ParallelUtilsIntegrationTests(unit_test_case.UnitTestCase):
  """Integration tests (with multiprocessing) for parallel_utils."""

  def test_execute_concurrently_success(self):
    """Tests execute_concurrently when all parallel processes succeed."""
    results, call_errors = parallel_utils.execute_concurrently(
        _GOOD_CALL_SPECS, timeout=1, raise_on_process_error=True)
    self.assertEqual(results, _GOOD_CALL_RESULTS)
    self.assertEqual(call_errors, _GOOD_CALL_ERRORS)

  def test_execute_concurrently_error_with_raise_on_process_error(self):
    """Tests execute_concurrently with errors and raise_on_process_error set."""
    regex = (r"Encountered errors in parallel processes: \[None, None, None, "
             r"\('RuntimeError', 'Something went wrong.'\), "
             r"\('ResultNotReceivedError', "
             r"'Did not receive any results from the process.'\)\]")
    with self.assertRaisesRegex(errors.ParallelUtilsError, regex):
      parallel_utils.execute_concurrently(
          _GOOD_CALL_SPECS + _BAD_CALL_SPECS,
          timeout=1,
          raise_on_process_error=True)

  def test_execute_concurrently_error_without_raise_on_process_error(self):
    """Tests execute_concurrently with errors and no raise_on_process_error."""
    results, call_errors = parallel_utils.execute_concurrently(
        _GOOD_CALL_SPECS + _BAD_CALL_SPECS,
        timeout=1,
        raise_on_process_error=False)
    self.assertEqual(results, _GOOD_CALL_RESULTS + _BAD_CALL_RESULTS)
    self.assertEqual(call_errors, _GOOD_CALL_ERRORS + _BAD_CALL_ERRORS)


if __name__ == "__main__":
  unit_test_case.main()
