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

"""Mixin for Matter Occupancy Sensing cluster test suite."""
from gazoo_device.capabilities import matter_enums
from mobly import asserts

_CLUSTER_NAME = "occupancy_sensing"
_OCCUPIED = 1
_UNOCCUPIED = 0


class OccupancySensingClusterTestSuite:
  """Mixin for Matter Occupancy Sensing cluster test suite.

  The mixin assumes self.endpoint is set.
  """

  def test_occupancy_attribute(self):
    """Tests the Occupancy attribute."""
    if self.endpoint.has_clusters([_CLUSTER_NAME]):
      asserts.assert_is_instance(
          self.endpoint.occupancy_sensing.occupancy, int,
          "Occupancy attribute must be the int type.")
    else:
      asserts.skip(
          f"Endpoint {self.endpoint} does not implement the Occupancy cluster.")

  def test_occupancy_attribute_setter(self):
    """Tests updating Occupancy attribute."""
    if self.endpoint.has_clusters([_CLUSTER_NAME]):
      self.endpoint.occupancy_sensing.occupancy = _OCCUPIED
      self.endpoint.occupancy_sensing.occupancy = _UNOCCUPIED
    else:
      asserts.skip(
          f"Endpoint {self.endpoint} does not implement the Occupancy cluster.")

  def test_occupancy_sensor_type_attribute(self):
    """Tests the OccupancySensorType attribute."""
    if self.endpoint.has_clusters([_CLUSTER_NAME]):
      valid_sensor_types = set(matter_enums.OccupancySensorType)
      asserts.assert_in(
          self.endpoint.occupancy_sensing.occupancy_sensor_type,
          valid_sensor_types,
          "OccupancySensorType attribute must be one of the "
          f"{valid_sensor_types}.")
    else:
      asserts.skip(
          f"Endpoint {self.endpoint} does not implement the Occupancy cluster.")

  def test_occupancy_sensor_type_bitmap(self):
    """Tests the OccupancySensorTypeBitmap attribute."""
    if self.endpoint.has_clusters([_CLUSTER_NAME]):
      asserts.assert_is_instance(
          self.endpoint.occupancy_sensing.occupancy_sensor_type_bitmap, int,
          "OccupancySensorTypeBitmap attribute must be the int type.")
    else:
      asserts.skip(
          f"Endpoint {self.endpoint} does not implement the Occupancy cluster.")
