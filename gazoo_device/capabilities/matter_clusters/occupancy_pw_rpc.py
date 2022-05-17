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

"""Pigweed RPC implementation of Matter Occupancy Sensing cluster capability.
"""
from gazoo_device import decorators
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters.interfaces import occupancy_base
from gazoo_device.protos import attributes_service_pb2

_OccupancyCluster = matter_enums.OccupancySensingCluster
BITMAP_ATTRIBUTE_TYPE = attributes_service_pb2.AttributeType.ZCL_BITMAP8_ATTRIBUTE_TYPE


class OccupancyClusterPwRpc(occupancy_base.OccupancyClusterBase):
  """Matter Occupancy Sensing cluster capability."""

  @decorators.DynamicProperty
  def occupancy(self) -> BITMAP_ATTRIBUTE_TYPE:
    """The Occupancy attribute.

    This attribute is a bitmap where bit 0 specifies the sensed occupancy as
    follows: 1 = occupied, 0 = unoccupied. All other bits are reserved.

    Returns:
      The Occupancy attribute.
    """
    occupancy_data = self._read(
        endpoint_id=self._endpoint_id,
        cluster_id=_OccupancyCluster.ID,
        attribute_id=_OccupancyCluster.ATTRIBUTE_OCCUPANCY,
        attribute_type=BITMAP_ATTRIBUTE_TYPE)
    return occupancy_data.data_uint8

  @decorators.DynamicProperty
  def occupancy_sensor_type(self) -> int:
    """The OccupancySensorType attribute.

    This attribute specifies the type of the occupancy sensor:
    0 = PIR; 1 = Ultrasonic; 2 = PIR and ultrasonic; 3 = Physical contact

    Returns:
      The OccupancySensorType attribute.
    """
    sensor_type_data = self._read(
        endpoint_id=self._endpoint_id,
        cluster_id=_OccupancyCluster.ID,
        attribute_id=_OccupancyCluster.ATTRIBUTE_OCCUPANCY_SENSOR_TYPE,
        attribute_type=BITMAP_ATTRIBUTE_TYPE)
    return matter_enums.OccupancySensorType(sensor_type_data.data_uint8)

  @decorators.DynamicProperty
  def occupancy_sensor_type_bitmap(self) -> BITMAP_ATTRIBUTE_TYPE:
    """The OccupancySensorTypeBitmap attribute.

    The attribute specifies the types of the occupancy sensor: a "1" in each bit
    position indicates this type is implemented: Bit 0 = PIR; Bit 1 = Ultrasonic
    ; Bit 2 = Physical contact.

    Returns:
      The OccupancySensorTypeBitmap attribute.
    """
    sensor_type_bitmap = self._read(
        endpoint_id=self._endpoint_id,
        cluster_id=_OccupancyCluster.ID,
        attribute_id=
        _OccupancyCluster.ATTRIBUTE_OCCUPANCY_SENSOR_TYPE_BITMAP,
        attribute_type=BITMAP_ATTRIBUTE_TYPE)
    return sensor_type_bitmap.data_uint8
