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
from gazoo_device import errors
from gazoo_device.capabilities import matter_endpoints_accessor_pw_rpc
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters import door_lock_pw_rpc
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_FAKE_DEVICE_NAME = "fake-device-name"
_FAKE_ENDPOINT_ID = 1


class DoorLockClusterPwRpcTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for DoorLockClusterPwRpc."""

  def setUp(self):
    super().setUp()
    self.fake_read = mock.Mock(spec=matter_endpoints_accessor_pw_rpc
                               .MatterEndpointsAccessorPwRpc.read)
    self.fake_write = mock.Mock(spec=matter_endpoints_accessor_pw_rpc
                                .MatterEndpointsAccessorPwRpc.write)
    self.uut = door_lock_pw_rpc.DoorLockClusterPwRpc(
        device_name=_FAKE_DEVICE_NAME,
        endpoint_id=_FAKE_ENDPOINT_ID,
        read=self.fake_read,
        write=self.fake_write)

  @mock.patch.object(door_lock_pw_rpc.DoorLockClusterPwRpc, "_lock_command")
  def test_lock_door_command(self, mock_lock):
    """Verifies the lock_door command."""
    self.uut.lock_door()
    mock_lock.assert_called_once_with(
        command=matter_enums.LockState.LOCKED, verify=True)

  @mock.patch.object(door_lock_pw_rpc.DoorLockClusterPwRpc, "_lock_command")
  def test_unlock_door_command(self, mock_lock):
    """Verifies the unlock_door command."""
    self.uut.unlock_door()
    mock_lock.assert_called_once_with(
        command=matter_enums.LockState.UNLOCKED, verify=True)

  @parameterized.named_parameters(
      ("lock_state_jammed", 0, matter_enums.LockState.NOT_FULLY_LOCKED),
      ("lock_state_true", 1, matter_enums.LockState.LOCKED),
      ("lock_state_false", 2, matter_enums.LockState.UNLOCKED))
  def test_lock_state_attribute_on_success(self, lock_action, expected_state):
    """Verifies the lock_state attribute on success."""
    self.fake_read.return_value = mock.Mock(data_uint16=lock_action)

    self.assertEqual(expected_state, self.uut.lock_state)

  @mock.patch.object(door_lock_pw_rpc.DoorLockClusterPwRpc, "_lock_command")
  def test_lock_state_setter_on_success(self, mock_lock):
    """Verifies lock_state setter on success."""
    self.uut.lock_state = matter_enums.LockState.LOCKED

    mock_lock.assert_called_once_with(
        command=matter_enums.LockState.LOCKED)

  def test_lock_command_success(self):
    """Verifies _lock_command on success."""
    mock_data = mock.Mock(data_uint16=matter_enums.LockState.LOCKED)
    self.fake_read.return_value = mock_data
    self.uut._lock_command(command=matter_enums.LockState.LOCKED, verify=True)

    self.fake_write.assert_called_once()

  def test_lock_command_failure_incorrect_state(self,):
    """Verifies _lock_command on failure with incorrect state."""
    mock_data = mock.Mock(data_uint16=matter_enums.LockState.LOCKED)
    self.fake_read.return_value = mock_data
    error_regex = (
        f"Device {_FAKE_DEVICE_NAME} lock state attribute did not change from"
        " 1.")

    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut._lock_command(command=matter_enums.LockState.UNLOCKED)


if __name__ == "__main__":
  fake_device_test_case.main()
