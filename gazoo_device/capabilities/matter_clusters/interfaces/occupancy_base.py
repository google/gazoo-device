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

"""Interface for the Matter Occupancy Sensing cluster capability."""
import abc
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters.interfaces import cluster_base
from gazoo_device.protos import attributes_service_pb2

BITMAP_ATTRIBUTE_TYPE = attributes_service_pb2.AttributeType.ZCL_BITMAP8_ATTRIBUTE_TYPE


class OccupancyClusterBase(cluster_base.ClusterBase, metaclass=abc.ABCMeta):
  """Matter Occupancy Sensing cluster capability."""

  CLUSTER_ID = matter_enums.OccupancySensingCluster.ID

  @abc.abstractmethod
  def occupancy(self) -> BITMAP_ATTRIBUTE_TYPE:
    """The Occupancy attribute."""

  @abc.abstractmethod
  def occupancy_sensor_type(self) -> int:
    """The OccupancySensorType attribute."""

  @abc.abstractmethod
  def occupancy_sensor_type_bitmap(self) -> BITMAP_ATTRIBUTE_TYPE:
    """The OccupancySensorTypeBitmap attribute."""
