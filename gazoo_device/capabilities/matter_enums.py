# Copyright 2023 Google LLC
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


class AirQualityCluster(enum.IntEnum):
  """Air Quality cluster ID and its attribute IDs.

  The enum values are defined in the Matter spec.
  """
  ID = attributes_service_pb2.ClusterType.ZCL_AIR_QUALITY_CLUSTER_ID

  # Attribute IDs
  ATTRIBUTE_AIR_QUALITY = 0x0000


class BasicInformationCluster(enum.IntEnum):
  """Basic information cluster ID and its attribute IDs.

  The enum values are defined in the Matter spec.
  """
  ID = attributes_service_pb2.ClusterType.ZCL_BASIC_CLUSTER_ID

  # Attribute IDs
  ATTRIBUTE_DATA_MODEL_REVISION = 0x0000
  ATTRIBUTE_VENDOR_NAME = 0x0001
  ATTRIBUTE_VENDOR_ID = 0x0002
  ATTRIBUTE_PRODUCT_NAME = 0x0003
  ATTRIBUTE_PRODUCT_ID = 0x0004
  ATTRIBUTE_NODE_LABEL = 0x0005
  ATTRIBUTE_LOCATION = 0x0006
  ATTRIBUTE_HARDWARE_VERSION = 0x0007
  ATTRIBUTE_HARDWARE_VERSION_STRING = 0x008
  ATTRIBUTE_SOFTWARE_VERSION = 0x009
  ATTRIBUTE_SOFTWARE_VERSION_STRING = 0x00A
  ATTRIBUTE_MANUFACTURING_DATE = 0x000B
  ATTRIBUTE_PART_NUMBER = 0x000C
  ATTRIBUTE_PRODUCT_URL = 0x000D
  ATTRIBUTE_PRODUCT_LABEL = 0x000D
  ATTRIBUTE_SERIAL_NUMBER = 0x000F
  ATTRIBUTE_UNIQUE_ID = 0x0012


class ColorControlCluster(enum.IntEnum):
  """Color control cluster ID and its attribute IDs.

  The enum values are defined in the Matter spec.
  """
  ID = attributes_service_pb2.ClusterType.ZCL_COLOR_CONTROL_CLUSTER_ID

  # Attribute IDs
  ATTRIBUTE_CURRENT_HUE = 0x0000
  ATTRIBUTE_CURRENT_SATURATION = 0x0001
  ATTRIBUTE_COLOR_TEMPERATURE_MIREDS = 0x0007
  ATTRIBUTE_COLOR_MODE = 0x0008


class ColorMode(enum.IntEnum):
  """ColorMode attribute enum.
  """
  HUE_AND_SATURATION = 0
  XY = 1
  TEMPERATURE = 2


class DoorLockCluster(enum.IntEnum):
  """Door lock cluster ID and its attribute IDs.

  The enum values are defined in the Matter spec.
  """
  ID = attributes_service_pb2.ClusterType.ZCL_DOOR_LOCK_CLUSTER_ID

  # Attribute IDs
  ATTRIBUTE_LOCK_STATE = 0x0000
  ATTRIBUTE_REQUIRE_PIN_FOR_REMOTE_OPERATION = 0x0033
  ATTRIBUTE_AUTO_RELOCK_TIME = 0x0023


class FlowMeasurementCluster(enum.IntEnum):
  """Flow Measurement cluster ID and its attribute IDs.

  The enum values are defined in the Matter spec.
  """
  ID = attributes_service_pb2.ClusterType.ZCL_FLOW_MEASUREMENT_CLUSTER_ID

  # Attribute IDs
  ATTRIBUTE_MEASURED_VALUE = 0x0000
  ATTRIBUTE_MIN_MEASURED_VALUE = 0x0001
  ATTRIBUTE_MAX_MEASURED_VALUE = 0x0002


class FanControlCluster(enum.IntEnum):
  """Fan Control cluster ID and its attribute IDs.

  The enum values are defined in the Matter spec.
  """
  ID = attributes_service_pb2.ClusterType.ZCL_FAN_CONTROL_CLUSTER_ID

  # Attribute IDs
  ATTRIBUTE_FAN_MODE = 0x0000
  ATTRIBUTE_FAN_MODE_SEQUENCE = 0x0001
  ATTRIBUTE_PERCENT_SETTING = 0x0002
  ATTRIBUTE_PERCENT_CURRENT = 0x0003
  ATTRIBUTE_SPEED_MAX = 0x0004
  ATTRIBUTE_SPEED_SETTING = 0x0005
  ATTRIBUTE_SPEED_CURRENT = 0x0006


class FanMode(enum.IntEnum):
  """Fan Mode attribute enum.
  """
  OFF = 0
  LOW = 1
  MEDIUM = 2
  HIGH = 3
  ON = 4
  AUTO = 5
  SMART = 6


class FanModeSequence(enum.IntEnum):
  """Fan Mode Sequence attribute enum.
  """
  OFF_LOW_MED_HIGH = 0
  OFF_LOW_HIGH = 1
  OFF_LOW_MED_HIGH_AUTO = 2
  OFF_LOW_HIGH_AUTO = 3
  OFF_ON_AUTO = 4
  OFF_ON = 5


class IlluminanceMeasurementCluster(enum.IntEnum):
  """Illuminance Measurement cluster ID and its attribute IDs.

  The enum values are defined in the Matter spec.
  """
  ID = attributes_service_pb2.ClusterType.ZCL_ILLUMINANCE_MEASUREMENT_CLUSTER_ID

  # Attribute IDs
  ATTRIBUTE_MEASURED_VALUE = 0x0000
  ATTRIBUTE_MIN_MEASURED_VALUE = 0x0001
  ATTRIBUTE_MAX_MEASURED_VALUE = 0x0002
  ATTRIBUTE_LIGHT_SENSOR_TYPE = 0x0004


class LightSensorType(enum.IntEnum):
  """LightSensorType attribute.
  """
  PHOTODIODE = 0
  CMOS = 1


class LevelControlCluster(enum.IntEnum):
  """Level control cluster ID and its attribute IDs.

  The enum values are defined in the Matter spec.
  """
  ID = attributes_service_pb2.ClusterType.ZCL_LEVEL_CONTROL_CLUSTER_ID

  # Attribute IDs
  ATTRIBUTE_CURRENT_LEVEL = 0x0000
  ATTRIBUTE_MIN_LEVEL = 0x0002
  ATTRIBUTE_MAX_LEVEL = 0x0003


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


class PressureMeasurementCluster(enum.IntEnum):
  """Pressure Measurement cluster ID and its attribute IDs.

  The enum values are defined in the Matter spec.
  """
  ID = attributes_service_pb2.ClusterType.ZCL_PRESSURE_MEASUREMENT_CLUSTER_ID

  # Attribute IDs
  ATTRIBUTE_MEASURED_VALUE = 0
  ATTRIBUTE_MIN_MEASURED_VALUE = 1
  ATTRIBUTE_MAX_MEASURED_VALUE = 2


class RelativeHumidityMeasurementCluster(enum.IntEnum):
  """Relative Humidity Measurement cluster ID and its attribute IDs.

  The enum values are defined in the Matter spec.
  """
  ID = attributes_service_pb2.ClusterType.ZCL_RELATIVE_HUMIDITY_MEASUREMENT_CLUSTER_ID

  # Attribute IDs
  ATTRIBUTE_MEASURED_VALUE = 0
  ATTRIBUTE_MIN_MEASURED_VALUE = 1
  ATTRIBUTE_MAX_MEASURED_VALUE = 2


class SwitchCluster(enum.IntEnum):
  """Switch cluster ID and its attribute IDs.

  The enum values are defined in the Matter spec.
  """
  ID = attributes_service_pb2.ClusterType.ZCL_SWITCH_CLUSTER_ID

  # Attribute IDs
  ATTRIBUTE_NUMBER_OF_POSITIONS = 0
  ATTRIBUTE_CURRENT_POSITION = 1
  ATTRIBUTE_MULTI_PRESS_MAX = 2

  # Spec:
  # https://project-chip.github.io/connectedhomeip-spec/appclusters.html#_events_3
  SWITCH_LATCHED_EVENT_ACTION_ID = 0
  INITIAL_PRESS_EVENT_ACTION_ID = 1
  LONG_PRESS_EVENT_ACTION_ID = 2
  SHORT_RELEASE_EVENT_ACTION_ID = 3
  LONG_RELEASE_EVENT_ACTION_ID = 4
  MULTI_PRESS_ONGOING_EVENT_ACTION_ID = 5
  MULTI_PRESS_COMPLETE_EVENT_ACTION_ID = 6


class TemperatureMeasurementCluster(enum.IntEnum):
  """Temperature Measurement cluster ID and its attribute IDs.

  The enum values are defined in the Matter spec.
  """
  ID = attributes_service_pb2.ClusterType.ZCL_TEMPERATURE_MEASUREMENT_CLUSTER_ID

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


# Door state attribute enums
class DoorState(enum.IntEnum):
  """Door state attribute values.
  """
  DOOR_OPEN = 0
  DOOR_CLOSED = 1
  DOOR_JAMMED = 2


# DegradationDirection attribute enums
class DegradationDirection(enum.IntEnum):
  """DegradationDirection attribute values.
  """
  UP = 0
  DOWN = 1


# ChangeIndication attribute enums
class ChangeIndication(enum.IntEnum):
  """ChangeIndication attribute values.
  """
  OK = 0
  WARNING = 1
  CRITICAL = 2


# Occupancy Sensor type enums.
class OccupancySensorType(enum.IntEnum):
  """Occupancy Sensor type.
  """
  PIR = 0
  ULTRASONIC = 1
  PIR_AND_ULTRASONIC = 2
  PHYSICAL_CONTACT = 3


class BooleanStateCluster(enum.IntEnum):
  """Boolean State cluster ID and its attribute IDs.

  The enum values are defined in the Matter spec.
  """
  ID = attributes_service_pb2.ClusterType.ZCL_BOOLEAN_STATE_CLUSTER_ID

  # Attribute IDs
  ATTRIBUTE_STATE_VALUE = 0


class ThermostatCluster(enum.IntEnum):
  """Thermostat cluster ID and its attribute IDs.

  The enum values are defined in the Matter spec.
  """
  ID = attributes_service_pb2.ClusterType.ZCL_THERMOSTAT_CLUSTER_ID

  # Attribute IDs
  ATTRIBUTE_LOCAL_TEMPERATURE = 0x0000
  ATTRIBUTE_OCCUPIED_COOLING_SETPOINT = 0x0011
  ATTRIBUTE_OCCUPIED_HEATING_SETPOINT = 0x0012
  ATTRIBUTE_CONTROL_SEQUENCE_OF_OPERATION = 0x001b
  ATTRIBUTE_SYSTEM_MODE = 0x001c
  ATTRIBUTE_AC_LOUVER_POSITION = 0x0045
  ATTRIBUTE_OCCUPANCY = 0x0002


class ThermostatControlSequence(enum.IntEnum):
  """Thermostat Control Sequence.

  The enum values are defined in the Matter spec.
  """

  COOLING_ONLY = 0
  COLLING_WITH_REHEAT = 1
  HEATING_ONLY = 2
  HEATING_WITH_REHEAT = 3
  COOLING_AND_HEATING = 4
  COOLING_AND_HEATING_WITH_REHEAT = 5


class ThermostatSystemMode(enum.IntEnum):
  """Thermostat System Mode.

  The enum values are defined in the Matter spec.
  """

  OFF = 0
  AUTO = 1
  COOL = 3
  HEAT = 4
  EMERGENCY_HEAT = 5
  PRECOOLING = 6
  FAN_ONLY = 7
  DRY = 8
  SLEEP = 9


class ThermostatSetpointMode(enum.IntEnum):
  """Thermostat Setpoint Mode.

  The enum values are defined in the Matter spec.
  """

  HEAT = 0
  COOL = 1
  BOTH = 2


class ACLouverPositionEnum(enum.IntEnum):
  """ACLouverPosition attribute enum.

  https://project-chip.github.io/connectedhomeip-spec/appclusters.html#ref_AcLouverPositionEnum
  """

  CLOSED = 1
  OPEN = 2
  QUARTER = 3
  HALF = 4
  THREE_QUARTERS = 5


class WindowCoveringCluster(enum.IntEnum):
  """Window Covering cluster ID and its attribute IDs.

  The enum values are defined in the Matter spec.
  """
  ID = attributes_service_pb2.ClusterType.ZCL_WINDOW_COVERING_CLUSTER_ID

  # Attribute IDs
  ATTRIBUTE_CURRENT_POSITION_LIFT_PERCENTAGE = 0x0008
  ATTRIBUTE_CURRENT_POSITION_TILT_PERCENTAGE = 0x0009
  ATTRIBUTE_TARGET_POSITION_LIFT = 0x00B
  ATTRIBUTE_TARGET_POSITION_TILT = 0x00C


class AirQualityEnum(enum.IntEnum):
  """The Air Quality Enum type.

  The enum values are defined in the Matter spec.
  """
  UNKNOWN = 0
  GOOD = 1
  FAIR = 2
  MODERATE = 3
  POOR = 4
  VERY_POOR = 5
  EXTREMELY_POOR = 6


class ExpressedStateEnum(enum.IntEnum):
  """The Expressed State Enum type.

  The enum values are defined in the Matter spec.
  """

  NORMAL = 0
  SMOKE_ALARM = 1
  CO_ALARM = 2
  BATTERY_ALERT = 3
  TESTING = 4
  HARDWARE_FAULT = 5
  END_OF_SERVICE = 6
  INTERCONNECT_SMOKE = 7
  INTERCONNECT_CO = 8


class AlarmStateEnum(enum.IntEnum):
  """The Alarm State Enum type.

  The enum values are defined in the Matter spec.
  """

  NORMAL = 0
  WARNING = 1
  CRITICAL = 2


class MuteStateEnum(enum.IntEnum):
  """The Alarm State Enum type.

  The enum values are defined in the Matter spec.
  """

  NOT_MUTED = 0
  MUTED = 1


class SensitivityEnum(enum.IntEnum):
  """The Sensitivity Enum type.

  The enum values are defined in the Matter spec.
  """

  HIGH = 0
  STANDARD = 1
  LOW = 2


class OperationalStateEnum(enum.IntEnum):
  """The Operational State Enum type.

  This class contains the generally applicable states (GeneralStates) and
  derived clusters defined states (DerivedClusterStates).

  The enum values are defined in the Matter spec.
  """

  STOPPED = 0
  RUNNING = 1
  PAUSED = 2
  ERROR = 3
  DOCKED = 66


class ErrorStateEnum(enum.IntEnum):
  """The Error State Enum type.

  This class contains the generally applicable states (GeneralStates) and
  derived clusters defined states (DerivedClusterStates).

  The enum values are defined in the Matter spec.
  """

  NO_ERROR = 0
  UNABLE_TO_START_OR_RESUME = 1
  UNABLE_TO_COMPLETE_OPERATION = 2
  COMMAND_INVALID_IN_STATE = 3


class BatChargeStateEnum(enum.IntEnum):
  """The Battery Charging State Enum type.

  The enum values are defined in the Matter spec.
  """

  UNKNOWN = 0
  IS_CHARGING = 1
  IS_AT_FULL_CHARGE = 2
  IS_NOT_CHARGING = 3


class BrightnessStepModeEnum(enum.IntEnum):
  """The Brightness Step Mode Enum type.

  The enum values are defined in the code search link.
  """

  INCREASE = 0
  DECREASE = 1


class RvcRunModeModeTagEnum(enum.IntEnum):
  """The RVC Run Mode Mode Tag Enum type.

  The enum values are defined in the code search link.
  """

  IDLE = 0
  CLEANING = 1
  MAPPING = 2


class ThermostatRunningModeEnum(enum.IntEnum):
  """The ThermostatRunningMode Enum type.

  The enum values are defined in the matter spec.
  """

  OFF = 0
  COOL = 3
  HEAT = 4


class PlaybackStateEnum(enum.IntEnum):
  """The PlaybackStateEnum Enum type.

  The enum values are defined in the matter spec.
  """

  PLAYING = 0
  PAUSED = 1
  NOT_PLAYING = 2
  BUFFERING = 3
