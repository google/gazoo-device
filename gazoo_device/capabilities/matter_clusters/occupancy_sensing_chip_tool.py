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
"""chip-tool implementation of Matter Occupancy Sensing cluster capability.
"""
from gazoo_device import decorators
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters.interfaces import occupancy_sensing_base

_CLUSTER_NAME = "occupancysensing"


class OccupancySensingClusterChipTool(
    occupancy_sensing_base.OccupancySensingClusterBase):
  """chip-tool based Matter Occupancy Sensing cluster capability."""

  @decorators.DynamicProperty
  def occupancy(self) -> int:
    """The Occupancy attribute.

    This attribute is a bitmap where bit 0 specifies the sensed occupancy as
    follows: 1 = occupied, 0 = unoccupied. All other bits are reserved.

    Returns:
      The Occupancy attribute.
    """
    return self._read(self._endpoint_id, _CLUSTER_NAME, "occupancy")

  @decorators.DynamicProperty
  def occupancy_sensor_type(self) -> matter_enums.OccupancySensorType:
    """The OccupancySensorType attribute.

    This attribute specifies the type of the occupancy sensor:
    0 = PIR; 1 = Ultrasonic; 2 = PIR and ultrasonic; 3 = Physical contact.

    Returns:
      The OccupancySensorType attribute.
    """
    sensor_type_data = self._read(self._endpoint_id, _CLUSTER_NAME,
                                  "occupancy-sensor-type")
    return matter_enums.OccupancySensorType(sensor_type_data)

  @decorators.DynamicProperty
  def occupancy_sensor_type_bitmap(self) -> int:
    """The OccupancySensorTypeBitmap attribute.

    The attribute specifies the types of the occupancy sensor: a "1" in each bit
    position indicates this type is implemented: Bit 0 = PIR; Bit 1 = Ultrasonic
    ; Bit 2 = Physical contact.

    Returns:
      The OccupancySensorTypeBitmap attribute.
    """
    return self._read(self._endpoint_id, _CLUSTER_NAME,
                      "occupancy-sensor-type-bitmap")
