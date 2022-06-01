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
"""Matter cluster capability unit test for on_off_chip_tool module."""

import functools
from unittest import mock

from gazoo_device import errors
from gazoo_device.capabilities import matter_controller_chip_tool
from gazoo_device.capabilities.matter_clusters import on_off_chip_tool
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_MATTER_NODE_ID = 1234
_ON_OFF_ENDPOINT_ID = 1


class OnOffClusterChipToolTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for OnOffClusterChipTool."""

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
    self.uut = on_off_chip_tool.OnOffClusterChipTool(
        device_name="rpi_matter_controller-1234",
        endpoint_id=self._endpoint_id,
        read=self.fake_read,
        write=self.fake_write,
        send=self.fake_send)

  def test_onoff_attribute(self):
    """Verifies the onoff attribute."""
    self.uut.onoff()
    self.fake_read.assert_called_once_with(self._endpoint_id, "onoff", "on-off")

  def test_on_command(self):
    """Verifies the on command."""
    self.fake_read.return_value = True
    self.uut.on()
    self.fake_send.assert_called_once_with(self._endpoint_id, "onoff", "on", [])

  def test_off_command(self):
    """Verifies the off command."""
    self.fake_read.return_value = False
    self.uut.off()
    self.fake_send.assert_called_once_with(self._endpoint_id, "onoff", "off",
                                           [])

  def test_toggle_command(self):
    """Verifies the toggle command."""
    self.fake_read.side_effect = [True, False]
    self.uut.toggle()
    self.fake_send.assert_called_once_with(self._endpoint_id, "onoff", "toggle",
                                           [])

  def test_verify_command_failure(self):
    """Verifies the toggle command on failure with incorrect state."""
    self.fake_read.return_value = True
    with self.assertRaises(errors.DeviceError):
      self.uut.toggle()


if __name__ == "__main__":
  fake_device_test_case.main()
