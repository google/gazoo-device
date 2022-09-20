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

"""Capability unit test for pwrpc_button_default module."""
from unittest import mock
from gazoo_device import errors
from gazoo_device.capabilities import pwrpc_button_default
from gazoo_device.switchboard import switchboard
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_FAKE_DEVICE_NAME = "button_device"
_FAKE_BUTTON_ID = 0
_FAKE_VALID_BUTTON_IDS = (0, 1)
_FAKE_TIMEOUT = 3


class PwRPCButtonDefaultTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for PwRPCButtonDefault."""

  def setUp(self):
    super().setUp()
    self.switchboard_call_mock = mock.Mock(
        spec=switchboard.SwitchboardDefault.call)
    self.uut = pwrpc_button_default.PwRPCButtonDefault(
        device_name=_FAKE_DEVICE_NAME,
        valid_button_ids=_FAKE_VALID_BUTTON_IDS,
        switchboard_call=self.switchboard_call_mock,
        rpc_timeout_s=_FAKE_TIMEOUT)

  def test_button_push_pass(self):
    """Verifies button push success."""
    self.uut.push(_FAKE_BUTTON_ID)
    self.switchboard_call_mock.assert_called_once()

  def test_button_push_fail_invalid_id(self):
    """Verifies button push fails with invalid button id."""
    invalid_button_id = 2
    error_regex = (f"Invalid button id {invalid_button_id}. Possible valid "
                   f"ids: {_FAKE_VALID_BUTTON_IDS}.")
    with self.assertRaisesWithLiteralMatch(errors.DeviceError, error_regex):
      self.uut.push(invalid_button_id)
    self.switchboard_call_mock.assert_not_called()


if __name__ == "__main__":
  fake_device_test_case.main()
