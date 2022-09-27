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
"""Matter cluster capability unit test for level_control_chip_tool module."""

import functools
from unittest import mock

from gazoo_device import errors
from gazoo_device.capabilities import matter_controller_chip_tool
from gazoo_device.capabilities.matter_clusters import level_control_chip_tool
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_MATTER_NODE_ID = 1234
_ON_OFF_ENDPOINT_ID = 1


class LevelControlClusterChipToolTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for LevelControlClusterChipTool."""

  def setUp(self):
    super().setUp()
    self._node_id = _MATTER_NODE_ID
    self._endpoint_id = _ON_OFF_ENDPOINT_ID

    self.fake_read = mock.Mock(
        spec=functools.partial(
            matter_controller_chip_tool.MatterControllerChipTool.read,
            self._node_id))
    self.fake_write = mock.Mock(
        spec=functools.partial(
            matter_controller_chip_tool.MatterControllerChipTool.write,
            self._node_id))
    self.fake_send = mock.Mock(
        spec=functools.partial(
            matter_controller_chip_tool.MatterControllerChipTool.send,
            self._node_id))
    self.uut = level_control_chip_tool.LevelControlClusterChipTool(
        device_name="rpi_matter_controller-1234",
        endpoint_id=self._endpoint_id,
        read=self.fake_read,
        write=self.fake_write,
        send=self.fake_send)

  def test_current_level_attribute(self):
    """Tests the current_level attribute."""
    self.fake_read.return_value = 1
    self.assertEqual(self.uut.current_level, self.fake_read.return_value)
    self.fake_read.assert_called_once_with(self._endpoint_id,
                                           "levelcontrol", "current-level")

  def test_move_to_level_command(self):
    """Tests the move_to_level command."""
    self.fake_read.return_value = 10
    self.uut.move_to_level(10)
    self.fake_send.assert_called_once_with(self._endpoint_id, "levelcontrol",
                                           "move-to-level", [10, 0, 1, 1])

  def test_move_to_level_command_failure(self):
    """Tests the move_to_level command failure."""
    with self.assertRaises(errors.DeviceError):
      self.uut.move_to_level(10)
    self.fake_send.assert_called_once_with(self._endpoint_id, "levelcontrol",
                                           "move-to-level", [10, 0, 1, 1])

  def test_min_level_attribute(self):
    """Tests the min_level attribute."""
    self.fake_read.return_value = 0
    self.assertEqual(self.uut.min_level, self.fake_read.return_value)
    self.fake_read.assert_called_once_with(self._endpoint_id,
                                           "levelcontrol", "min-level")

  def test_max_level_attribute(self):
    """Tests the max_level attribute."""
    self.fake_read.return_value = 2
    self.assertEqual(self.uut.max_level, self.fake_read.return_value)
    self.fake_read.assert_called_once_with(self._endpoint_id,
                                           "levelcontrol", "max-level")


if __name__ == "__main__":
  fake_device_test_case.main()
