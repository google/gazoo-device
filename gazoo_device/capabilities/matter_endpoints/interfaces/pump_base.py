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

"""Interface for a Matter Pump endpoint."""
import abc
from gazoo_device.capabilities.matter_clusters.interfaces import measurement_base
from gazoo_device.capabilities.matter_endpoints.interfaces import endpoint_base


class PumpBase(endpoint_base.EndpointBase, metaclass=abc.ABCMeta):
  """Matter Pump endpoint interface."""

  DEVICE_TYPE_ID = 0x0303
  DEVICE_TYPE_NAME = "Pump"

  @property
  @abc.abstractmethod
  def temperature_measurement(self) -> measurement_base.MeasurementClusterBase:
    """Optional cluster: temperature_measurement cluster."""

  @property
  @abc.abstractmethod
  def pressure_measurement(self) -> measurement_base.MeasurementClusterBase:
    """Optional cluster: pressure_measurement cluster."""

  @property
  @abc.abstractmethod
  def flow_measurement(self) -> measurement_base.MeasurementClusterBase:
    """Optional cluster: flow_measurement cluster."""
