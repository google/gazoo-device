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

"""Capability unit test for pwrpc_lock_default module."""
from unittest import mock

import gazoo_device
from gazoo_device import errors
from gazoo_device.capabilities import pwrpc_lock_default
from gazoo_device.protos import locking_service_pb2
from gazoo_device.tests.unit_tests.utils import fake_device_test_case


_PWRPC_LOCK_CLASS = (
    gazoo_device.capabilities.pwrpc_lock_default.PwRPCLockDefault)
_FAKE_DEVICE_NAME = "lock_device"
_FAKE_LOCK_REGEXES = {pwrpc_lock_default.LockedState.LOCKED: "locked",
                      pwrpc_lock_default.LockedState.UNLOCKED: "unlocked"}
_FAKE_TIMEOUT = 3


class PwRPCLockDefaultTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for PwRPCLockDefault."""

  def setUp(self):
    super().setUp()
    self.switchboard_call_mock = mock.Mock()
    self.uut = pwrpc_lock_default.PwRPCLockDefault(
        device_name=_FAKE_DEVICE_NAME,
        expect_locking_regexes=_FAKE_LOCK_REGEXES,
        expect_timeout=_FAKE_TIMEOUT,
        switchboard_call=self.switchboard_call_mock,
        switchboard_call_expect=self.switchboard_call_mock)
    fake_locked_state = locking_service_pb2.LockingState(locked=True)
    fake_unlocked_state = locking_service_pb2.LockingState(locked=False)
    self.locked_state_in_bytes = fake_locked_state.SerializeToString()
    self.unlocked_state_in_bytes = fake_unlocked_state.SerializeToString()

  @mock.patch.object(_PWRPC_LOCK_CLASS,
                     "state", new_callable=mock.PropertyMock)
  def test_001_lock_on_success(self, mock_state):
    """Verifies locking device on success."""
    self.switchboard_call_mock.return_value = (None, (True, None))
    mock_state.return_value = True
    self.uut.lock()
    self.switchboard_call_mock.assert_called_once()
    self.assertEqual(1, mock_state.call_count)

  def test_001_lock_on_failure_false_ack(self):
    """Verifies locking device on failure with false ack value."""
    self.switchboard_call_mock.return_value = (None, (False, None))
    error_regex = f"Locking device {_FAKE_DEVICE_NAME} failed."
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.lock()
    self.switchboard_call_mock.assert_called_once()

  @mock.patch.object(_PWRPC_LOCK_CLASS,
                     "state", new_callable=mock.PropertyMock)
  def test_001_lock_on_failure_incorrect_state(self, mock_state):
    """Verifies locking device on failure with incorrect state."""
    self.switchboard_call_mock.return_value = (None, (True, None))
    mock_state.return_value = False
    error_regex = f"Locking device {_FAKE_DEVICE_NAME} failed."
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.lock()
    self.switchboard_call_mock.assert_called_once()
    self.assertEqual(2, mock_state.call_count)

  @mock.patch.object(_PWRPC_LOCK_CLASS,
                     "state", new_callable=mock.PropertyMock)
  def test_002_unlock_on_success(self, mock_state):
    """Verifies unlocking device on success."""
    self.switchboard_call_mock.return_value = (None, (True, None))
    mock_state.return_value = False
    self.uut.unlock()
    self.switchboard_call_mock.assert_called_once()
    self.assertEqual(1, mock_state.call_count)

  def test_002_unlock_on_failure_false_ack(self):
    """Verifies unlocking device on failure with false ack value."""
    self.switchboard_call_mock.return_value = (None, (False, None))
    error_regex = f"Unlocking device {_FAKE_DEVICE_NAME} failed."
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.unlock()
    self.switchboard_call_mock.assert_called_once()

  @mock.patch.object(_PWRPC_LOCK_CLASS,
                     "state", new_callable=mock.PropertyMock)
  def test_002_unlock_on_failure_incorrect_state(self, mock_state):
    """Verifies unlocking device on failure with incorrect state."""
    self.switchboard_call_mock.return_value = (None, (True, None))
    mock_state.return_value = True
    error_regex = f"Unlocking device {_FAKE_DEVICE_NAME} failed."
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.unlock()
    self.switchboard_call_mock.assert_called_once()
    self.assertEqual(2, mock_state.call_count)

  def test_003_locked_state_lock_pass(self):
    """Verifies getting locked state = True successfully."""
    self.switchboard_call_mock.return_value = (True,
                                               self.locked_state_in_bytes)
    self.assertTrue(self.uut.state)
    self.switchboard_call_mock.assert_called_once()

  def test_003_locked_state_unlock_pass(self):
    """Verifies getting locked state = False successfully."""
    self.switchboard_call_mock.return_value = (True,
                                               self.unlocked_state_in_bytes)
    self.assertFalse(self.uut.state)
    self.switchboard_call_mock.assert_called_once()

  def test_003_locked_state_fail_false_ack(self):
    """Verifies getting locked state lock successfully."""
    self.switchboard_call_mock.return_value = (False, None)
    error_regex = f"Getting device {_FAKE_DEVICE_NAME} locked state failed."
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.state  # pylint: disable=pointless-statement


if __name__ == "__main__":
  fake_device_test_case.main()
