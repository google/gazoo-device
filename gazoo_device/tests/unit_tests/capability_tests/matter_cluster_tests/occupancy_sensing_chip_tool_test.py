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
"""Matter cluster capability unit test for occupancy_sensing_chip_tool module."""

import functools
from unittest import mock

from gazoo_device.capabilities import matter_controller_chip_tool
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters import occupancy_sensing_chip_tool
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_MATTER_NODE_ID = 1234
_ON_OFF_ENDPOINT_ID = 1


class OccupancySensingClusterChipToolTest(
    fake_device_test_case.FakeDeviceTestCase):
  """Unit test for OccupancyChipTool."""

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
    self.uut = occupancy_sensing_chip_tool.OccupancySensingClusterChipTool(
        device_name="rpi_matter_controller-1234",
        endpoint_id=self._endpoint_id,
        read=self.fake_read,
        write=self.fake_write,
        send=self.fake_send)

  def test_occupancy_attribute(self):
    """Tests the occupancy attribute."""
    self.fake_read.return_value = 1
    self.assertEqual(self.uut.occupancy, self.fake_read.return_value)
    self.fake_read.assert_called_once_with(self._endpoint_id,
                                           "occupancysensing", "occupancy")

  def test_occupancy_sensor_type_attribute(self):
    """Tests the occupancy_sensor_type attribute."""
    self.fake_read.return_value = 3
    self.assertEqual(self.uut.occupancy_sensor_type,
                     matter_enums.OccupancySensorType.PHYSICAL_CONTACT)
    self.fake_read.assert_called_once_with(self._endpoint_id,
                                           "occupancysensing",
                                           "occupancy-sensor-type")

  def test_occupancy_sensor_type_bitmap_attribute(self):
    """Tests the occupancy_sensor_type_bitmap attribute."""
    self.fake_read.return_value = 1
    self.assertEqual(self.uut.occupancy_sensor_type_bitmap,
                     self.fake_read.return_value)
    self.fake_read.assert_called_once_with(self._endpoint_id,
                                           "occupancysensing",
                                           "occupancy-sensor-type-bitmap")


if __name__ == "__main__":
  fake_device_test_case.main()
