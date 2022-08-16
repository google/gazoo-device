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

"""Thermostat endpoint.

This endpoint module corresponds to the
"Thermostat" Matter device type which defines required and optional clusters
in the Matter spec 1.0.

A Thermostat endpoint houses an instance of Thermostat Matter device type with
the following defined clusters on this endpoint:

The required clusters for this endpoint: Thermostat.
The optional clusters for this endpoint: Groups, Scenes, Alarms,
Thermostat User Interface Configuration, Relative Humidity Measurement,
Fan Control, Time, TimeSync, Temperature Measurement, Occupancy Sensing.
"""
from typing import Union

from gazoo_device import decorators
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters import occupancy_sensing_chip_tool
from gazoo_device.capabilities.matter_clusters import occupancy_sensing_pw_rpc
from gazoo_device.capabilities.matter_clusters import relative_humidity_measurement_pw_rpc
from gazoo_device.capabilities.matter_clusters import temperature_measurement_pw_rpc
from gazoo_device.capabilities.matter_clusters import thermostat_chip_tool
from gazoo_device.capabilities.matter_clusters import thermostat_pw_rpc
from gazoo_device.capabilities.matter_endpoints.interfaces import thermostat_base


class ThermostatEndpoint(thermostat_base.ThermostatBase):
  """Matter Thermostat endpoint."""

  @decorators.CapabilityDecorator([
      thermostat_chip_tool.ThermostatClusterChipTool,
      thermostat_pw_rpc.ThermostatClusterPwRpc
  ])
  def thermostat(
      self
  ) -> Union[thermostat_chip_tool.ThermostatClusterChipTool,
             thermostat_pw_rpc.ThermostatClusterPwRpc]:
    """Matter Thermostat cluster instance."""
    return self.cluster_lazy_init(matter_enums.ThermostatCluster.ID)

  @decorators.CapabilityDecorator(
      relative_humidity_measurement_pw_rpc.
      RelativeHumidityMeasurementClusterPwRpc)
  def relative_humidity_measurement(
      self) -> (relative_humidity_measurement_pw_rpc.
                RelativeHumidityMeasurementClusterPwRpc):
    """Matter Relative Humidity Measurement cluster instance."""
    return self.cluster_lazy_init(
        matter_enums.RelativeHumidityMeasurementCluster.ID)

  @decorators.CapabilityDecorator(
      temperature_measurement_pw_rpc.TemperatureMeasurementClusterPwRpc)
  def temperature_measurement(
      self
  ) -> temperature_measurement_pw_rpc.TemperatureMeasurementClusterPwRpc:
    """Matter Temperature Measurement cluster instance."""
    return self.cluster_lazy_init(matter_enums.TemperatureMeasurementCluster.ID)

  @decorators.CapabilityDecorator([
      occupancy_sensing_chip_tool.OccupancySensingClusterChipTool,
      occupancy_sensing_pw_rpc.OccupancySensingClusterPwRpc
  ])
  def occupancy_sensing(
      self
  ) -> Union[occupancy_sensing_chip_tool.OccupancySensingClusterChipTool,
             occupancy_sensing_pw_rpc.OccupancySensingClusterPwRpc]:
    """Matter Occupancy Sensing cluster instance."""
    return self.cluster_lazy_init(matter_enums.OccupancySensingCluster.ID)

  # TODO(b/239741839): add optional clusters below
  # def scenes(self):
  #   """Matter scenes cluster instance."""

  # def groups(self):
  #   """Matter groups cluster instance."""

  # def alarms(self):
  #   """Matter alarms cluster instance."""

  # def thermostat_user_interface_configuration(self):
  #   """Matter thermostat UI configuration cluster instance."""

  # def time(self):
  #   """Matter time cluster instance."""

  # def time_sync(self):
  #   """Matter time sync cluster instance."""

  # def fan_control(self):
  #   """Matter fan control cluster instance."""
