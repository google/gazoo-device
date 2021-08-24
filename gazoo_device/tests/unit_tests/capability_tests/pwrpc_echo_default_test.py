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

"""Capability unit test for pwrpc_echo_default module."""
from unittest import mock
from gazoo_device import errors
from gazoo_device.capabilities import pwrpc_echo_default
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_MOCK_DEVICE_NAME = "echo_device"
_MOCK_ECHO_MSG = "pigweed rpc echo message"


class PwRPCEchoDefaultTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for PwRPCEchoDefault."""

  def setUp(self):
    super().setUp()
    self.switchboard_call_mock = mock.Mock()
    self.switchboard_call_mock.return_value = (True, _MOCK_ECHO_MSG)
    self.uut = pwrpc_echo_default.PwRPCEchoDefault(
        device_name=_MOCK_DEVICE_NAME,
        switchboard_call=self.switchboard_call_mock)

  def test_001_echo_pass(self):
    """Verifies echo capability on success."""
    msg = self.uut.echo(_MOCK_ECHO_MSG)
    self.assertEqual(msg, _MOCK_ECHO_MSG)
    self.switchboard_call_mock.assert_called_once()

  def test_002_echo_fail(self):
    """Verifies echo capability on failure."""
    error_regex = f"{_MOCK_DEVICE_NAME} echo failed."
    self.switchboard_call_mock.return_value = (False, "")
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.echo(_MOCK_ECHO_MSG)
    self.switchboard_call_mock.assert_called_once()


if __name__ == "__main__":
  fake_device_test_case.main()
