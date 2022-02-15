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

"""Unit tests for retry.py."""
from unittest import mock

from gazoo_device import errors
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import retry


def _not(return_val):
  return not return_val


def _waste_time():
  return True


def _func_raises():
  raise RuntimeError("Foo too bar")


class RetryTests(unit_test_case.UnitTestCase):
  """Retry utility tests."""

  def setUp(self):
    super().setUp()
    self.add_time_mocks()

  def test_retry_timeout_default_error(self):
    """Test retry with a timeout; error type left as default."""
    with self.assertRaisesRegex(errors.CommunicationTimeoutError, "Timeout"):
      retry.retry(
          _waste_time, is_successful=_not, timeout=1, interval=0.25)

  def test_retry_timeout_custom_error(self):
    """Test retry with a timeout; error type is provided."""
    with self.assertRaisesRegex(RuntimeError, "Timeout"):
      retry.retry(
          _waste_time,
          is_successful=_not,
          timeout=1,
          interval=0.25,
          exc_type=RuntimeError)

  def test_reraise_true(self):
    """Test calling a function which raises an Exception with reraise=True."""
    with self.assertRaisesRegex(RuntimeError, "Foo too bar"):
      retry.retry(_func_raises, timeout=1, reraise=True)

  def test_reraise_false(self):
    """Test calling a function which raises an Exception with reraise=False."""
    mock_is_successful = mock.Mock()
    with self.assertRaisesRegex(errors.CommunicationTimeoutError,
                                r"Timeout.*{}".format(_func_raises.__name__)):
      retry.retry(
          _func_raises,
          is_successful=mock_is_successful,
          timeout=1,
          interval=0.25,
          reraise=False)
    mock_is_successful.assert_not_called()

  def test_retry_success(self):
    """Test retry with a success on first try."""

    def _func():
      return True

    retry.retry(_func, timeout=1, interval=0.25)

  def test_retry_return_value(self):
    """Test retry returns the function return value."""
    ret_val = "egret"

    def _func():
      return ret_val

    result = retry.retry(_func, timeout=1, interval=0.25)
    self.assertEqual(result, ret_val)

  def test_retry_success_with_retries(self):
    """Test retry with failure on first tries, but success later."""
    ret_val = "egret"

    def _func():
      _func.called_count += 1
      if _func.called_count >= 3:
        return ret_val

    _func.called_count = 0

    def _is_success(val):
      return val == ret_val

    result = retry.retry(
        _func, is_successful=_is_success, interval=0.25, timeout=2)
    self.assertEqual(result, ret_val)


if __name__ == "__main__":
  unit_test_case.main()
