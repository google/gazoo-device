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

"""Unit test mixin for testing common device functionality."""
from unittest import mock

from absl.testing import parameterized
from gazoo_device import errors
from gazoo_device import manager
from gazoo_device.capabilities import usb_hub_default

_CDR_ERROR_1 = errors.DeviceNotResponsiveError("device-1234", "Not responsive")
_CDR_ERROR_2 = errors.DeviceNotBootupCompleteError("device-1234", "Offline")
_RECOVERY_ERROR = errors.DeviceError("Something went wrong")


class CommonTestMixin(parameterized.TestCase):
  """Unit test mixin for testing common device functionality."""

  @parameterized.named_parameters(
      ("manager_is_alive", mock.Mock(spec=manager.Manager), False),
      ("manager_is_dead", None, True))
  def test_get_manager(self, manager_weakref_return, error_expected):
    """Tests make_device_ready with setting 'check_only'."""
    with mock.patch.object(self.uut, "_manager_weakref",
                           return_value=manager_weakref_return):
      if error_expected:
        with self.assertRaisesRegex(RuntimeError, "Manager is no longer alive"):
          self.uut.get_manager()
      else:
        self.assertEqual(self.uut.get_manager(), manager_weakref_return)

  def test_make_device_ready_off(self):
    """Tests make_device_ready with setting 'off'."""
    with mock.patch.object(self.uut, "check_device_ready"):
      with mock.patch.object(self.uut, "recover"):
        self.uut.make_device_ready(setting="off")

        self.uut.recover.assert_not_called()
        self.uut.check_device_ready.assert_not_called()

  @parameterized.named_parameters(
      ("one_attempt_success", 1, None, None),
      ("two_attempts_success", 2, None, None),
      ("one_attempt_fail", 1, _CDR_ERROR_1, _CDR_ERROR_1),
      ("two_attempts_fail", 2, _CDR_ERROR_1, _CDR_ERROR_1))
  def test_make_device_ready_check_only(
      self, attempts, check_side_effect, expected_error):
    """Tests make_device_ready with setting 'check_only'."""
    with mock.patch.object(type(self.uut), "_RECOVERY_ATTEMPTS", new=attempts):
      with mock.patch.object(self.uut, "check_device_ready",
                             side_effect=check_side_effect):
        with mock.patch.object(self.uut, "recover"):
          if expected_error is None:
            self.uut.make_device_ready(setting="check_only")
          else:
            with self.assertRaises(type(expected_error)):
              self.uut.make_device_ready(setting="check_only")

          self.uut.recover.assert_not_called()
          self.uut.check_device_ready.assert_called_once()

  @parameterized.named_parameters(
      ("one_attempt_success_no_recover",
       1, None, 1, 0, None),
      ("one_attempt_success_with_recover",
       1, [_CDR_ERROR_1, None], 2, 1, None),
      ("one_attempt_fail_same_error_after_recover",
       1, _CDR_ERROR_1, 2, 1, _CDR_ERROR_1),
      ("one_attempt_fail_different_error_after_recover",
       1, [_CDR_ERROR_1, _CDR_ERROR_2], 2, 1, _CDR_ERROR_2),
      ("two_attempts_success_no_recover",
       2, None, 1, 0, None),
      ("two_attempts_success_recover_from_two_different_errors",
       2, [_CDR_ERROR_1, _CDR_ERROR_2, None], 3, 2, None),
      ("two_attempts_fail_same_error_after_recover",
       2, _CDR_ERROR_1, 2, 1, _CDR_ERROR_1))
  @mock.patch.object(
      usb_hub_default.UsbHubDefault,
      "supported_modes",
      new_callable=mock.PropertyMock,
      return_value=["off", "sync", "charge"])
  def test_make_device_ready_on(
      self, attempts, check_side_effect, expected_check_calls,
      expected_recover_calls, expected_error, unused_mock_supported_modes):
    """Tests make_device_ready with setting 'on'."""
    with mock.patch.object(type(self.uut), "_RECOVERY_ATTEMPTS", new=attempts):
      with mock.patch.object(self.uut, "check_device_ready",
                             side_effect=check_side_effect):
        with mock.patch.object(self.uut, "recover"):
          if expected_error is None:
            self.uut.make_device_ready(setting="on")
          else:
            with self.assertRaises(type(expected_error)):
              self.uut.make_device_ready(setting="on")

          self.assertEqual(self.uut.check_device_ready.call_count,
                           expected_check_calls)
          self.assertEqual(self.uut.recover.call_count, expected_recover_calls)

  @mock.patch.object(
      usb_hub_default.UsbHubDefault,
      "supported_modes",
      new_callable=mock.PropertyMock,
      return_value=["off", "sync", "charge"])
  def test_make_device_ready_on_recover_throws_error(
      self, unused_mock_supported_modes):
    """Tests make_device_ready with setting 'on' when recover fails."""
    with mock.patch.object(self.uut, "check_device_ready",
                           side_effect=_CDR_ERROR_1):
      with mock.patch.object(self.uut, "recover", side_effect=_RECOVERY_ERROR):
        with self.assertRaisesRegex(errors.DeviceError, "Something went wrong"):
          self.uut.make_device_ready(setting="on")

        self.uut.check_device_ready.assert_called_once()
        self.uut.recover.assert_called_once_with(_CDR_ERROR_1)

  @parameterized.named_parameters(
      ("one_attempt_fail_no_flash_build",
       False, 1, _CDR_ERROR_1, _CDR_ERROR_1, _CDR_ERROR_1, False),
      ("one_attempt_fail_error_after_flash",
       True, 1, None, _CDR_ERROR_1, _CDR_ERROR_1, True),
      ("two_attempts_fail_error_after_flash",
       True, 2, _RECOVERY_ERROR, _CDR_ERROR_1, _CDR_ERROR_1, True),
      ("one_attempt_success_no_error_after_flash",
       True, 1, None, [_CDR_ERROR_1, _CDR_ERROR_1, None], None, True))
  @mock.patch.object(
      usb_hub_default.UsbHubDefault,
      "supported_modes",
      new_callable=mock.PropertyMock,
      return_value=["off", "sync", "charge"])
  def test_make_device_ready_flash_build(
      self, has_flash_build, attempts, before_flash_error, check_side_effect,
      expected_error, expected_upgrade_call, unused_mock_supported_modes):
    """Tests make_device_ready with setting 'flash_build'."""
    flash_build_before = getattr(type(self.uut), "flash_build", None)
    type(self.uut).flash_build = mock.Mock()
    try:
      with mock.patch.object(self.uut, "has_capabilities",
                             return_value=has_flash_build):
        with mock.patch.object(type(self.uut), "_RECOVERY_ATTEMPTS",
                               new=attempts):
          with mock.patch.object(self.uut, "check_device_ready",
                                 side_effect=check_side_effect):
            with mock.patch.object(self.uut, "recover",
                                   side_effect=before_flash_error):
              if expected_error is None:
                self.uut.make_device_ready(setting="flash_build")
              else:
                with self.assertRaises(type(expected_error)):
                  self.uut.make_device_ready(setting="flash_build")

              if expected_upgrade_call:
                self.uut.flash_build.upgrade.assert_called_once_with(
                    forced_upgrade=True)
              else:
                self.uut.flash_build.upgrade.assert_not_called()
    finally:
      if flash_build_before:
        type(self.uut).flash_build = flash_build_before
      else:
        del type(self.uut).flash_build

  def test_execute_health_check_methods_device_error(self):
    """Test _execute_health_check_methods when a health check fails."""
    with mock.patch.object(self.uut.logger, "info") as mock_info:
      health_checks = [self.uut.check3]
      with self.assertRaises(errors.DeviceError):
        self.uut._execute_health_check_methods(health_checks)
      mock_info.assert_called()

  def test_make_device_ready_methods_device_error(self):
    """Test make_device_ready when a health check fails."""
    with mock.patch.object(
        self.uut, "check_device_ready",
        side_effect=errors.DeviceError("Some error")):
      with mock.patch.object(self.uut.logger, "info") as mock_info:
        with self.assertRaises(errors.DeviceError):
          self.uut.make_device_ready()
        mock_info.assert_called()
