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


class ColorControlCluster(enum.IntEnum):
  """Color control cluster ID and its attribute IDs.

  The enum values are defined in the Matter spec.
  """
  ID = attributes_service_pb2.ClusterType.ZCL_COLOR_CONTROL_CLUSTER_ID

  # Attribute IDs
  ATTRIBUTE_CURRENT_HUE = 0x0000
  ATTRIBUTE_CURRENT_SATURATION = 0x0001


class DoorLockCluster(enum.IntEnum):
  """Door lock cluster ID and its attribute IDs.

  The enum values are defined in the Matter spec.
  """
  ID = attributes_service_pb2.ClusterType.ZCL_DOOR_LOCK_CLUSTER_ID

  # Attribute IDs
  ATTRIBUTE_LOCK_STATE = 0x0000


class LevelControlCluster(enum.IntEnum):
  """Level control cluster ID and its attribute IDs.

  The enum values are defined in the Matter spec.
  """
  ID = attributes_service_pb2.ClusterType.ZCL_LEVEL_CONTROL_CLUSTER_ID

  # Attribute IDs
  ATTRIBUTE_CURRENT_LEVEL = 0x0000


class OccupancySensingCluster(enum.IntEnum):
  """Occupacny sensing cluster ID and its attribute IDs.

  The enum values are defined in the Matter spec.
  """
  ID = attributes_service_pb2.ClusterType.ZCL_OCCUPANCY_SENSING_CLUSTER_ID

  # Attributes ID
  ATTRIBUTE_OCCUPANCY = 0x0000
  ATTRIBUTE_OCCUPANCY_SENSOR_TYPE = 0x0001
  ATTRIBUTE_OCCUPANCY_SENSOR_TYPE_BITMAP = 0x0002


class OnOffCluster(enum.IntEnum):
  """OnOff cluster ID and its attribute IDs.

  The enum values are defined in the Matter spec.
  """
  ID = attributes_service_pb2.ClusterType.ZCL_ON_OFF_CLUSTER_ID

  # Attribute IDs
  ATTRIBUTE_ON_OFF = 0x0000


class TemperatureMeasurementCluster(enum.IntEnum):
  """Temperature Measurement cluster ID and its attribute IDs.

  The enum values are defined in the Matter spec.
  """
  ID = attributes_service_pb2.ClusterType.ZCL_TEMP_MEASUREMENT_CLUSTER_ID

  # Attribute IDs
  ATTRIBUTE_MEASURED_VALUE = 0
  ATTRIBUTE_MIN_MEASURED_VALUE = 1
  ATTRIBUTE_MAX_MEASURED_VALUE = 2


# Lock state attribute enums
class LockState(enum.IntEnum):
  """Lock state attribute values.
  """
  NOT_FULLY_LOCKED = 0
  LOCKED = 1
  UNLOCKED = 2


# Occupancy Sensor type enums.
class OccupancySensorType(enum.IntEnum):
  """Occupancy Sensor type.
  """
  PIR = 0
  ULTRASONIC = 1
  PIR_AND_ULTRASONIC = 2
  PHYSICAL_CONTACT = 3
