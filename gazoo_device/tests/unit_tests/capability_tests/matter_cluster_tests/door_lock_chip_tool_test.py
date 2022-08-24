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
"""Matter cluster capability unit test for door_lock_chip_tool module."""

import functools
from unittest import mock

from gazoo_device import errors
from gazoo_device.capabilities import matter_controller_chip_tool
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters import door_lock_chip_tool
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_MATTER_NODE_ID = 1234
_DOOR_LOCK_ENDPOINT_ID = 1


class DoorLockClusterChipToolTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for DoorLockClusterChipTool."""

  def setUp(self):
    super().setUp()
    self.fake_read = mock.Mock(
        spec=functools.partial(
            matter_controller_chip_tool.MatterControllerChipTool.read,
            _MATTER_NODE_ID))
    self.fake_send = mock.Mock(
        spec=functools.partial(
            matter_controller_chip_tool.MatterControllerChipTool.send,
            _MATTER_NODE_ID))
    self.uut = door_lock_chip_tool.DoorLockClusterChipTool(
        device_name="rpi_matter_controller-1234",
        endpoint_id=_DOOR_LOCK_ENDPOINT_ID,
        read=self.fake_read,
        write=None,
        send=self.fake_send)

  @mock.patch.object(
      door_lock_chip_tool.DoorLockClusterChipTool, "_lock_command")
  def test_lock_command(self, fake_lock_command):
    """Verifies Lock Door command."""
    self.uut.lock_door()
    fake_lock_command.assert_called_once_with("lock-door", True)

  @mock.patch.object(
      door_lock_chip_tool.DoorLockClusterChipTool, "_lock_command")
  def test_unlock_command(self, fake_lock_command):
    """Verifies Unlock Door command."""
    self.uut.unlock_door()
    fake_lock_command.assert_called_once_with("unlock-door", True)

  def test_lock_state_attribute(self):
    """Verifies LockState attribute."""
    self.fake_read.return_value = 1
    self.assertEqual(matter_enums.LockState.LOCKED, self.uut.lock_state)

  def test_lock_command_helper_on_success(self):
    """Verifies _lock_command on success."""
    self.fake_read.return_value = 1
    self.uut._lock_command("lock-door")
    self.fake_send.assert_called_once()

  def test_lock_command_helper_on_failure(self):
    """Verifies _lock_command on failure."""
    self.fake_read.return_value = 0
    with self.assertRaisesRegex(errors.DeviceError, "attribute did not change"):
      self.uut._lock_command("lock-door")


if __name__ == "__main__":
  fake_device_test_case.main()
