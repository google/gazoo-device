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


"""Unit tests for errors.py."""

from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

logger = gdm_logger.get_logger()


def _raise_and_catch(what_to_raise):
  try:
    raise what_to_raise
  except Exception as err:  # pylint: disable=broad-except
    return err


class ErrorTests(fake_device_test_case.FakeDeviceTestCase):
  """Unit tests for errors.py."""

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    cls.msg_str = "Foo outbarred kek."
    cls.msg_exc = ValueError(cls.msg_str)

  def setUp(self):
    super().setUp()
    self.uut_from_str = errors.DeviceError(self.msg_str)
    self.uut_from_exc = errors.DeviceError(self.msg_exc)

  def test_device_error_string_msg_visual_comparison(self):
    """Logs representations of DeviceError for comparison."""
    logger.info(
        "===============================================================")
    logger.info("Representations of DeviceError('{}'):".format(self.msg_str))
    logger.info("repr(e): {}".format(repr(self.uut_from_str)))
    logger.info("str(e): {}".format(str(self.uut_from_str)))
    logger.info(
        "===============================================================")

  def test_device_error_string_msg_repr(self):
    """Tests repr(error) for errors raised from a string message."""
    text = repr(self.uut_from_str)
    self.assertIn(self.msg_str, text)
    self.assertIn(type(self.uut_from_str).__name__, text)

  def test_device_error_string_msg_str(self):
    """Tests str(error) for errors raised from a string message."""
    text = str(self.uut_from_str)
    self.assertIn(self.msg_str, text)
    self.assertNotIn(type(self.uut_from_str).__name__, text)

  def test_device_error_exception_msg_visual_comparison(self):
    """Prints all representations for comparison."""
    logger.info(
        "===============================================================")
    logger.info("Representations of DeviceError({}('{}')):".format(
        type(self.msg_exc).__name__, self.msg_str))
    logger.info("repr(e): {}".format(repr(self.uut_from_exc)))
    logger.info("str(e): {}".format(str(self.uut_from_exc)))
    logger.info(
        "===============================================================")

  def test_device_error_exception_msg_repr(self):
    """Tests repr(error) for errors raised from an Exception."""
    text = repr(self.uut_from_exc)
    self.assertIn(self.msg_str, text)
    self.assertIn(type(self.uut_from_exc).__name__, text)
    self.assertIn(type(self.msg_exc).__name__, text)

  def test_device_error_exception_msg_str(self):
    """Tests str(error) for errors raised from an Exception."""
    text = str(self.uut_from_exc)
    self.assertIn(self.msg_str, text)
    self.assertNotIn(type(self.uut_from_exc).__name__, text)
    self.assertNotIn(type(self.msg_exc).__name__, text)

  def test_device_error_except_with_error_code(self):
    """Verifies exception has correct error code for DeviceError."""
    error = _raise_and_catch(errors.DeviceError("test"))
    self.assertEqual(error.err_code, 1)

  def test_timeout_error_except_with_error_code(self):
    """Verifies correct error code for CommunicationTimeoutError."""
    error = _raise_and_catch(errors.CommunicationTimeoutError("test"))
    self.assertEqual(error.err_code, 10)

  def test_check_device_ready_error_except_with_error_code(self):
    """Verifies exception has correct error code for CheckDeviceReadyError."""
    error = _raise_and_catch(
        errors.CheckDeviceReadyError("device-1234", "test"))
    self.assertEqual(error.err_code, 30)

  def test_device_not_connected_error_error_except_with_error_code(self):
    """Verifies correct error code for DeviceNotConnectedError."""
    error = _raise_and_catch(
        errors.DeviceNotConnectedError("device-1234", "test"))
    self.assertEqual(error.err_code, 31)

  def test_device_not_bootup_complete_error_except_with_error_code(self):
    """Verifies correct error code for DeviceNotBootupCompleteError."""
    error = _raise_and_catch(
        errors.DeviceNotBootupCompleteError("device-1234", "test"))
    self.assertEqual(error.err_code, 32)

  def test_device_not_responsive_error_except_with_error_code(self):
    """Verifies correct error code for DeviceNotResponsiveError."""
    error = _raise_and_catch(
        errors.DeviceNotResponsiveError("device-1234", "test"))
    self.assertEqual(error.err_code, 33)

  def test_no_logs_streaming_error_except_with_error_code(self):
    """Verifies exception has correct error code for NoLogsStreamingError."""
    error = _raise_and_catch(
        errors.NoLogsStreamingError("device-1234", "test"))
    self.assertEqual(error.err_code, 34)

  def test_non_root_user_error_except_with_error_code(self):
    """Verifies exception has correct error code for NonRootUserError."""
    error = _raise_and_catch(errors.NonRootUserError("device-1234", "test"))
    self.assertEqual(error.err_code, 35)

  def test_logging_agent_not_enabled_error_except_with_error_code(self):
    """Verifies correct error code for LoggingAgentNotEnabledError."""
    error = _raise_and_catch(
        errors.LoggingAgentNotEnabledError("device-1234", "test"))
    self.assertEqual(error.err_code, 36)

  def test_bootloader_mode_error_except_with_error_code(self):
    """Verifies exception has correct error code for BootloaderModeError."""
    error = _raise_and_catch(errors.BootloaderModeError("device-1234", "test"))
    self.assertEqual(error.err_code, 37)

  def test_dfu_mode_error_except_with_error_code(self):
    """Verifies exception has correct error code for DfuModeError."""
    error = _raise_and_catch(errors.DfuModeError("device-1234", "test"))
    self.assertEqual(error.err_code, 38)

  def test_device_not_logged_in_error_except_with_error_code(self):
    """Verifies exception has correct error code for DeviceNotLoggedInError."""
    error = _raise_and_catch(
        errors.DeviceNotLoggedInError("device-1234", "test"))
    self.assertEqual(error.err_code, 39)

  def test_unterminated_quote_error_except_with_error_code(self):
    """Verifies exception has correct error code for UnterminatedQuoteError."""
    error = _raise_and_catch(
        errors.UnterminatedQuoteError("device-1234", "test"))
    self.assertEqual(error.err_code, 40)

  def test_storage_not_healthy_error_except_with_error_code(self):
    """Verifies exception has correct error code for StorageNotHealthyError."""
    error = _raise_and_catch(
        errors.StorageNotHealthyError("device-1234", "test"))
    self.assertEqual(error.err_code, 41)

  def test_battery_too_low_error_except_with_error_code(self):
    """Verifies exception has correct error code for BatteryTooLowError."""
    error = _raise_and_catch(errors.BatteryTooLowError("device-1234", "test"))
    self.assertEqual(error.err_code, 42)

  def test_password_not_disabled_error_except_with_error_code(self):
    """Verifies correct error code for PasswordNotDisabledError."""
    error = _raise_and_catch(
        errors.PasswordNotDisabledError("device-1234", "test"))
    self.assertEqual(error.err_code, 43)

  def test_fastboot_mode_error_except_with_error_code(self):
    """Verifies exception has correct error code for FastbootModeError."""
    error = _raise_and_catch(errors.FastbootModeError("device-1234", "test"))
    self.assertEqual(error.err_code, 44)

  def test_device_binary_missing_error_except_with_error_code(self):
    """Verify exception has correct error code for DeviceBinaryMissingError."""
    error = _raise_and_catch(
        errors.DeviceBinaryMissingError("device-1234", "test"))
    self.assertEqual(error.err_code, 52)

  def test_device_not_rooted_error_except_with_error_code(self):
    """Verifies exception has correct error code for DeviceNotRootedError."""
    error = _raise_and_catch(
        errors.DeviceNotRootedError("device-1234", "test"))
    self.assertEqual(error.err_code, 45)

  def test_device_not_ADB_connected_error_except_with_error_code(self):
    """Verifies correct error code for DeviceNotADBConnectedError."""
    error = _raise_and_catch(
        errors.DeviceNotADBConnectedError("device-1234", "test"))
    self.assertEqual(error.err_code, 46)

  def test_device_baudrate_mismatch_error_except_with_error_code(self):
    """Verifies correct error code for DeviceBaudrateMismatchError."""
    error = _raise_and_catch(
        errors.DeviceBaudrateMismatchError("device-1234", "test"))
    self.assertEqual(error.err_code, 47)

  def test_hub_failed_to_respond_error_except_with_error_code(self):
    """Verifies correct error code for HubFailedToRespondError."""
    error = _raise_and_catch(
        errors.HubFailedToRespondError("device-1234", "test"))
    self.assertEqual(error.err_code, 48)


if __name__ == "__main__":
  fake_device_test_case.main()
