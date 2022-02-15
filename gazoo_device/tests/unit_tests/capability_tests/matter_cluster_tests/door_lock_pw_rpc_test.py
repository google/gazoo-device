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

"""Matter cluster capability unit test for door_lock_pw_rpc module."""
from unittest import mock

from absl.testing import parameterized
import gazoo_device
from gazoo_device import errors
from gazoo_device.capabilities.matter_clusters import door_lock_pw_rpc
from gazoo_device.protos import locking_service_pb2
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_DOOR_LOCK_RPC_MODULE = (
    gazoo_device.capabilities.matter_clusters.door_lock_pw_rpc.
    DoorLockClusterPwRpc)
_FAKE_DEVICE_NAME = "fake-device-name"
_FAKE_TIMEOUT_S = 10


class DoorLockClusterPwRpcTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for DoorLockClusterPwRpc."""

  def setUp(self):
    super().setUp()
    self.fake_switchboard_call = mock.Mock()
    self.uut = door_lock_pw_rpc.DoorLockClusterPwRpc(
        device_name=_FAKE_DEVICE_NAME,
        switchboard_call=self.fake_switchboard_call,
        rpc_timeout_s=_FAKE_TIMEOUT_S)

  @mock.patch.object(door_lock_pw_rpc.DoorLockClusterPwRpc, "_lock_command")
  def test_lock_door_command(self, mock_lock):
    """Verifies the lock_door command."""
    self.uut.lock_door()
    mock_lock.assert_called_once_with(lock=True, verify=True)

  @mock.patch.object(door_lock_pw_rpc.DoorLockClusterPwRpc, "_lock_command")
  def test_unlock_door_command(self, mock_lock):
    """Verifies the unlock_door command."""
    self.uut.unlock_door()
    mock_lock.assert_called_once_with(lock=False, verify=True)

  @parameterized.named_parameters(
      ("lock_state_true", True, door_lock_pw_rpc.LockState.LOCKED),
      ("lock_state_false", False, door_lock_pw_rpc.LockState.UNLOCKED))
  def test_lock_state_attribute_on_success(self, lock_action, expected_state):
    """Verifies the lock_state attribute on success."""
    fake_lock_state = locking_service_pb2.LockingState(locked=lock_action)
    fake_lock_state_in_bytes = fake_lock_state.SerializeToString()
    self.fake_switchboard_call.return_value = (True, fake_lock_state_in_bytes)

    self.assertEqual(expected_state.value, self.uut.lock_state)

  def test_lock_state_attribute_failure_false_ack(self):
    """Verifies the lock_state attribute on failure with false ack value."""
    self.fake_switchboard_call.return_value = (False, "")
    error_regex = (
        f"Device {_FAKE_DEVICE_NAME} getting LockState attribute failed.")

    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.lock_state  # pylint: disable=pointless-statement

    self.fake_switchboard_call.assert_called_once()

  @mock.patch.object(
      _DOOR_LOCK_RPC_MODULE,
      "lock_state",
      new_callable=mock.PropertyMock(
          return_value=door_lock_pw_rpc.LockState.LOCKED.value))
  def test_lock_command_success(self, mock_state):
    """Verifies _lock_command on success."""
    self.fake_switchboard_call.return_value = (True, None)

    self.uut._lock_command(lock=True, verify=True)

    self.fake_switchboard_call.assert_called_once()

  def test_lock_command_failure_false_ack(self):
    """Verifies _lock_command on failure with false ack value."""
    self.fake_switchboard_call.return_value = (False, None)
    error_regex = f"Locking device {_FAKE_DEVICE_NAME} failed."

    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut._lock_command(lock=True)

  @mock.patch.object(
      _DOOR_LOCK_RPC_MODULE,
      "lock_state",
      new_callable=mock.PropertyMock(
          return_value=door_lock_pw_rpc.LockState.LOCKED.value))
  def test_lock_command_failure_incorrect_state(self, mock_state):
    """Verifies _lock_command on failure with incorrect state."""
    self.fake_switchboard_call.return_value = (True, None)
    error_regex = (
        f"Device {_FAKE_DEVICE_NAME} lock state attribute did not change from"
        " 1.")

    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut._lock_command(lock=False)


if __name__ == "__main__":
  fake_device_test_case.main()
