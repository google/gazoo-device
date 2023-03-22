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

"""Interface for a Matter Heating Cooling Unit endpoint."""
import abc
from gazoo_device.capabilities.matter_clusters.interfaces import fan_control_base
from gazoo_device.capabilities.matter_clusters.interfaces import level_control_base
from gazoo_device.capabilities.matter_clusters.interfaces import on_off_base
from gazoo_device.capabilities.matter_endpoints.interfaces import endpoint_base


class HeatingCoolingUnitBase(endpoint_base.EndpointBase, metaclass=abc.ABCMeta):
  """Matter Heating Cooling Unit endpoint interface."""

  DEVICE_TYPE_ID = 0x0300

  @property
  @abc.abstractmethod
  def on_off(self) -> on_off_base.OnOffClusterBase:
    """Required cluster: ZCL on_off cluster."""

  @property
  @abc.abstractmethod
  def level_control(self) -> level_control_base.LevelControlClusterBase:
    """Optional cluster: ZCL level cluster."""

  @property
  @abc.abstractmethod
  def fan_control(self) -> fan_control_base.FanControlClusterBase:
    """Optional cluster: fan control cluster instance."""

  # TODO(b/254205233): Add the following clusters
  # def scenes(self):
  #   """Matter scenes cluster instance."""

  # def groups(self):
  #   """Matter groups cluster instance."""
