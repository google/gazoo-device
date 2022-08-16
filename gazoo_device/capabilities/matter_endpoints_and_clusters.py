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

"""Matter endpoint and cluster modules."""

from gazoo_device.capabilities.matter_clusters import basic_information_chip_tool
from gazoo_device.capabilities.matter_clusters import boolean_state_pw_rpc
from gazoo_device.capabilities.matter_clusters import color_control_pw_rpc
from gazoo_device.capabilities.matter_clusters import door_lock_pw_rpc
from gazoo_device.capabilities.matter_clusters import flow_measurement_chip_tool
from gazoo_device.capabilities.matter_clusters import flow_measurement_pw_rpc
from gazoo_device.capabilities.matter_clusters import illuminance_measurement_chip_tool
from gazoo_device.capabilities.matter_clusters import illuminance_measurement_pw_rpc
from gazoo_device.capabilities.matter_clusters import level_control_chip_tool
from gazoo_device.capabilities.matter_clusters import level_control_pw_rpc
from gazoo_device.capabilities.matter_clusters import occupancy_sensing_chip_tool
from gazoo_device.capabilities.matter_clusters import occupancy_sensing_pw_rpc
from gazoo_device.capabilities.matter_clusters import on_off_chip_tool
from gazoo_device.capabilities.matter_clusters import on_off_pw_rpc
from gazoo_device.capabilities.matter_clusters import pressure_measurement_chip_tool
from gazoo_device.capabilities.matter_clusters import pressure_measurement_pw_rpc
from gazoo_device.capabilities.matter_clusters import relative_humidity_measurement_chip_tool
from gazoo_device.capabilities.matter_clusters import relative_humidity_measurement_pw_rpc
from gazoo_device.capabilities.matter_clusters import temperature_measurement_chip_tool
from gazoo_device.capabilities.matter_clusters import temperature_measurement_pw_rpc
from gazoo_device.capabilities.matter_clusters import thermostat_chip_tool
from gazoo_device.capabilities.matter_clusters import thermostat_pw_rpc
from gazoo_device.capabilities.matter_endpoints import color_temperature_light
from gazoo_device.capabilities.matter_endpoints import contact_sensor
from gazoo_device.capabilities.matter_endpoints import dimmable_light
from gazoo_device.capabilities.matter_endpoints import door_lock
from gazoo_device.capabilities.matter_endpoints import extended_color_light
from gazoo_device.capabilities.matter_endpoints import flow_sensor
from gazoo_device.capabilities.matter_endpoints import humidity_sensor
from gazoo_device.capabilities.matter_endpoints import light_sensor
from gazoo_device.capabilities.matter_endpoints import occupancy_sensor
from gazoo_device.capabilities.matter_endpoints import on_off_light
from gazoo_device.capabilities.matter_endpoints import on_off_light_switch
from gazoo_device.capabilities.matter_endpoints import on_off_plugin_unit
from gazoo_device.capabilities.matter_endpoints import pressure_sensor
from gazoo_device.capabilities.matter_endpoints import root_node
from gazoo_device.capabilities.matter_endpoints import temperature_sensor
from gazoo_device.capabilities.matter_endpoints import thermostat
import immutabledict


SUPPORTED_ENDPOINTS_PW_RPC = (
    color_temperature_light.ColorTemperatureLightEndpoint,
    contact_sensor.ContactSensorEndpoint,
    dimmable_light.DimmableLightEndpoint,
    door_lock.DoorLockEndpoint,
    extended_color_light.ExtendedColorLightEndpoint,
    flow_sensor.FlowSensorEndpoint,
    humidity_sensor.HumiditySensorEndpoint,
    light_sensor.LightSensorEndpoint,
    occupancy_sensor.OccupancySensorEndpoint,
    on_off_light.OnOffLightEndpoint,
    on_off_light_switch.OnOffLightSwitchEndpoint,
    on_off_plugin_unit.OnOffPluginUnitEndpoint,
    pressure_sensor.PressureSensorEndpoint,
    temperature_sensor.TemperatureSensorEndpoint,
    thermostat.ThermostatEndpoint)

SUPPORTED_CLUSTERS_PW_RPC = (
    color_control_pw_rpc.ColorControlClusterPwRpc,
    boolean_state_pw_rpc.BooleanStateClusterPwRpc,
    door_lock_pw_rpc.DoorLockClusterPwRpc,
    flow_measurement_pw_rpc.FlowMeasurementClusterPwRpc,
    illuminance_measurement_pw_rpc.IlluminanceMeasurementClusterPwRpc,
    level_control_pw_rpc.LevelControlClusterPwRpc,
    occupancy_sensing_pw_rpc.OccupancySensingClusterPwRpc,
    on_off_pw_rpc.OnOffClusterPwRpc,
    pressure_measurement_pw_rpc.PressureMeasurementClusterPwRpc,
    (relative_humidity_measurement_pw_rpc.
     RelativeHumidityMeasurementClusterPwRpc),
    temperature_measurement_pw_rpc.TemperatureMeasurementClusterPwRpc,
    thermostat_pw_rpc.ThermostatClusterPwRpc)

MATTER_DEVICE_TYPE_ID_TO_CLASS_PW_RPC = immutabledict.immutabledict({
    endpoint_class.DEVICE_TYPE_ID: endpoint_class
    for endpoint_class in SUPPORTED_ENDPOINTS_PW_RPC
})

CLUSTER_ID_TO_CLASS_PW_RPC = immutabledict.immutabledict({
    cluster_class.CLUSTER_ID: cluster_class
    for cluster_class in SUPPORTED_CLUSTERS_PW_RPC
})

SUPPORTED_ENDPOINTS_CHIP_TOOL = (
    dimmable_light.DimmableLightEndpoint,
    flow_sensor.FlowSensorEndpoint,
    humidity_sensor.HumiditySensorEndpoint,
    light_sensor.LightSensorEndpoint,
    occupancy_sensor.OccupancySensorEndpoint,
    on_off_light.OnOffLightEndpoint,
    pressure_sensor.PressureSensorEndpoint,
    root_node.RootNodeEndpoint,
    temperature_sensor.TemperatureSensorEndpoint,
    thermostat.ThermostatEndpoint)

SUPPORTED_CLUSTERS_CHIP_TOOL = (
    basic_information_chip_tool.BasicInformationClusterChipTool,
    flow_measurement_chip_tool.FlowMeasurementClusterChipTool,
    illuminance_measurement_chip_tool.IlluminanceMeasurementClusterChipTool,
    level_control_chip_tool.LevelControlClusterChipTool,
    occupancy_sensing_chip_tool.OccupancySensingClusterChipTool,
    on_off_chip_tool.OnOffClusterChipTool,
    pressure_measurement_chip_tool.PressureMeasurementClusterChipTool,
    relative_humidity_measurement_chip_tool.
    RelativeHumidityMeasurementClusterChipTool,
    temperature_measurement_chip_tool.TemperatureMeasurementClusterChipTool,
    thermostat_chip_tool.ThermostatClusterChipTool,
)

MATTER_DEVICE_TYPE_ID_TO_CLASS_CHIP_TOOL = immutabledict.immutabledict({
    endpoint_class.DEVICE_TYPE_ID: endpoint_class
    for endpoint_class in SUPPORTED_ENDPOINTS_CHIP_TOOL
})

CLUSTER_ID_TO_CLASS_CHIP_TOOL = immutabledict.immutabledict({
    cluster_class.CLUSTER_ID: cluster_class
    for cluster_class in SUPPORTED_CLUSTERS_CHIP_TOOL
})
