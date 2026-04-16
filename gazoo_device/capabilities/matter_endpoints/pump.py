# Copyright 2025 Google LLC
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

"""Matter pump endpoint."""


from gazoo_device import decorators
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters import flow_measurement_chip_tool
from gazoo_device.capabilities.matter_clusters import flow_measurement_pw_rpc
from gazoo_device.capabilities.matter_clusters import pressure_measurement_chip_tool
from gazoo_device.capabilities.matter_clusters import pressure_measurement_pw_rpc
from gazoo_device.capabilities.matter_clusters import temperature_measurement_chip_tool
from gazoo_device.capabilities.matter_clusters import temperature_measurement_pw_rpc
from gazoo_device.capabilities.matter_endpoints.interfaces import pump_base


class PumpEndpoint(pump_base.PumpBase):
  """Matter Pump endpoint."""

  @decorators.CapabilityDecorator([
      temperature_measurement_chip_tool.TemperatureMeasurementClusterChipTool,
      temperature_measurement_pw_rpc.TemperatureMeasurementClusterPwRpc,
  ])
  def temperature_measurement(
      self,
  ) -> (
      temperature_measurement_chip_tool.TemperatureMeasurementClusterChipTool
      | temperature_measurement_pw_rpc.TemperatureMeasurementClusterPwRpc
  ):
    """Matter Temperature Measurement cluster instance."""
    return self.cluster_lazy_init(matter_enums.TemperatureMeasurementCluster.ID)

  @decorators.CapabilityDecorator([
      pressure_measurement_chip_tool.PressureMeasurementClusterChipTool,
      pressure_measurement_pw_rpc.PressureMeasurementClusterPwRpc,
  ])
  def pressure_measurement(
      self,
  ) -> (
      pressure_measurement_chip_tool.PressureMeasurementClusterChipTool
      | pressure_measurement_pw_rpc.PressureMeasurementClusterPwRpc
  ):
    """Matter Pressure Measurement cluster instance."""
    return self.cluster_lazy_init(matter_enums.PressureMeasurementCluster.ID)

  @decorators.CapabilityDecorator([
      flow_measurement_chip_tool.FlowMeasurementClusterChipTool,
      flow_measurement_pw_rpc.FlowMeasurementClusterPwRpc,
  ])
  def flow_measurement(
      self,
  ) -> (
      flow_measurement_chip_tool.FlowMeasurementClusterChipTool
      | flow_measurement_pw_rpc.FlowMeasurementClusterPwRpc
  ):
    """Matter Flow Measurement cluster instance."""
    return self.cluster_lazy_init(matter_enums.FlowMeasurementCluster.ID)
