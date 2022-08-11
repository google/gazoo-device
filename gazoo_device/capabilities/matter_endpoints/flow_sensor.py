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

"""Matter Flow Sensor endpoint.

A Flow Sensor device measures and reports the pressure of a fluid.

This endpoint module corresponds to the
"Flow Sensor" Matter device type which defines required and optional
clusters in the Matter spec 1.0.

A Flow Sensor endpoint houses an instance of Flow Sensor Matter device
type with the following defined clusters on this endpoint:

The required clusters for this endpoint: Flow Measurement.
"""
from typing import Union

from gazoo_device import decorators
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters import flow_measurement_chip_tool
from gazoo_device.capabilities.matter_clusters import flow_measurement_pw_rpc
from gazoo_device.capabilities.matter_endpoints.interfaces import flow_sensor_base


class FlowSensorEndpoint(flow_sensor_base.FlowSensorBase):
  """Matter Flow Sensor endpoint."""

  @decorators.CapabilityDecorator([
      flow_measurement_chip_tool.FlowMeasurementClusterChipTool,
      flow_measurement_pw_rpc.FlowMeasurementClusterPwRpc
  ])
  def flow_measurement(
      self
  ) -> Union[
      flow_measurement_chip_tool.FlowMeasurementClusterChipTool,
      flow_measurement_pw_rpc.FlowMeasurementClusterPwRpc]:
    """Matter Flow Measurement cluster instance."""
    return self.cluster_lazy_init(matter_enums.FlowMeasurementCluster.ID)
