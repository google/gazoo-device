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

"""Matter spec enum module."""
import enum
from gazoo_device.protos import attributes_service_pb2

# The Matter cluster enums definitions: (only enums used in GDM are defined)


class ColorControlCluster(enum.Enum):
  """Color control cluster ID and its attribute IDs.

  The enum values are defined in the Matter spec.
  """
  ID = attributes_service_pb2.ClusterType.ZCL_COLOR_CONTROL_CLUSTER_ID

  # Attribute IDs
  ATTRIBUTE_CURRENT_HUE = 0x0000
  ATTRIBUTE_CURRENT_SATURATION = 0x0001


class DoorLockCluster(enum.Enum):
  """Door lock cluster ID and its attribute IDs.

  The enum values are defined in the Matter spec.
  """
  ID = attributes_service_pb2.ClusterType.ZCL_DOOR_LOCK_CLUSTER_ID

  # Attribute IDs
  ATTRIBUTE_LOCK_STATE = 0x0000


class LevelControlCluster(enum.Enum):
  """Level control cluster ID and its attribute IDs.

  The enum values are defined in the Matter spec.
  """
  ID = attributes_service_pb2.ClusterType.ZCL_LEVEL_CONTROL_CLUSTER_ID

  # Attribute IDs
  ATTRIBUTE_CURRENT_LEVEL = 0x0000


class OnOffCluster(enum.Enum):
  """OnOff cluster ID and its attribute IDs.

  The enum values are defined in the Matter spec.
  """
  ID = attributes_service_pb2.ClusterType.ZCL_ON_OFF_CLUSTER_ID

  # Attribute IDs
  ATTRIBUTE_ON_OFF = 0x0000


# Lock state attribute enums
class LockState(enum.Enum):
  """Lock state attribute values.
  """
  NOT_FULLY_LOCKED = 0
  LOCKED = 1
  UNLOCKED = 2
