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

"""Capability unit test for pwrpc_button_default module."""
from unittest import mock
from gazoo_device import errors
from gazoo_device.capabilities import pwrpc_button_default
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_FAKE_DEVICE_NAME = "button_device"
_FAKE_BUTTON_ID = 0
_FAKE_BUTTON_REGEXES = {_FAKE_BUTTON_ID: f"button {_FAKE_BUTTON_ID} is pressed"}
_FAKE_TIMEOUT = 3


class PwRPCButtonDefaultTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for PwRPCButtonDefault."""

  def setUp(self):
    super().setUp()
    self.switchboard_call_mock = mock.Mock()
    self.uut = pwrpc_button_default.PwRPCButtonDefault(
        device_name=_FAKE_DEVICE_NAME,
        expect_button_regexes=_FAKE_BUTTON_REGEXES,
        expect_timeout=_FAKE_TIMEOUT,
        switchboard_call_expect=self.switchboard_call_mock)

  def test_001_button_push_pass(self):
    """Verifies button push success."""
    self.switchboard_call_mock.return_value = (None, (True, None))
    self.uut.push(_FAKE_BUTTON_ID)
    self.switchboard_call_mock.assert_called_once()

  def test_002_button_push_fail_invalid_id(self):
    """Verifies button push fails with invalid button id."""
    invalid_button_id = 1
    error_regex = (f"Invalid button id {invalid_button_id}. Possible valid "
                   f"ids: {set(_FAKE_BUTTON_REGEXES.keys())}.")
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.push(invalid_button_id)
    self.switchboard_call_mock.assert_not_called()

  def test_003_button_push_fail_invalid_ack(self):
    """Verifies button push fails with invalid ack value."""
    self.switchboard_call_mock.return_value = (None, (False, None))
    error_regex = (f"Device {_FAKE_DEVICE_NAME} button {_FAKE_BUTTON_ID} push "
                   f"failed.")
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.push(_FAKE_BUTTON_ID)
    self.switchboard_call_mock.assert_called_once()


if __name__ == "__main__":
  fake_device_test_case.main()
