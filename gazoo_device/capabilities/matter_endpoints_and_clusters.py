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

from gazoo_device.capabilities.matter_clusters import color_control_pw_rpc
from gazoo_device.capabilities.matter_clusters import door_lock_pw_rpc
from gazoo_device.capabilities.matter_clusters import level_control_pw_rpc
from gazoo_device.capabilities.matter_clusters import occupancy_pw_rpc
from gazoo_device.capabilities.matter_clusters import on_off_pw_rpc
from gazoo_device.capabilities.matter_clusters import temperature_measurement_pw_rpc
from gazoo_device.capabilities.matter_endpoints import color_temperature_light
from gazoo_device.capabilities.matter_endpoints import dimmable_light
from gazoo_device.capabilities.matter_endpoints import door_lock
from gazoo_device.capabilities.matter_endpoints import on_off_light
from gazoo_device.capabilities.matter_endpoints import temperature_sensor
import immutabledict


SUPPORTED_ENDPOINTS = (
    color_temperature_light.ColorTemperatureLightEndpoint,
    dimmable_light.DimmableLightEndpoint,
    door_lock.DoorLockEndpoint,
    on_off_light.OnOffLightEndpoint,
    temperature_sensor.TemperatureSensorEndpoint)

SUPPORTED_CLUSTERS = (
    color_control_pw_rpc.ColorControlClusterPwRpc,
    door_lock_pw_rpc.DoorLockClusterPwRpc,
    level_control_pw_rpc.LevelControlClusterPwRpc,
    occupancy_pw_rpc.OccupancyClusterPwRpc,
    on_off_pw_rpc.OnOffClusterPwRpc,
    temperature_measurement_pw_rpc.TemperatureMeasurementClusterPwRpc)

MATTER_DEVICE_TYPE_ID_TO_CLASS = immutabledict.immutabledict({
    endpoint_class.DEVICE_TYPE_ID: endpoint_class
    for endpoint_class in SUPPORTED_ENDPOINTS
})

CLUSTER_ID_TO_CLASS = immutabledict.immutabledict({
    cluster_class.CLUSTER_ID: cluster_class
    for cluster_class in SUPPORTED_CLUSTERS
})
