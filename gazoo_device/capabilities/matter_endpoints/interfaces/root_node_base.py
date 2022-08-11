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

"""Interface for a Matter Root Node endpoint."""
import abc
from gazoo_device.capabilities.matter_endpoints.interfaces import endpoint_base


class RootNodeBase(endpoint_base.EndpointBase, metaclass=abc.ABCMeta):
  """Matter Root Node endpoint interface."""

  DEVICE_TYPE_ID = 0x0016

  @property
  @abc.abstractmethod
  def basic_information(self):
    """Required cluster: basic_information cluster."""

  # TODO(b/241164443): implement additional clusters for root node.

  # @property
  # @abc.abstractmethod
  # def access_control(self):
  #   """Required cluster: access_control cluster."""

  # @property
  # @abc.abstractmethod
  # def group_key_management(self):
  #   """Required cluster: group_key_management cluster."""

  # @property
  # @abc.abstractmethod
  # def general_commissioning(self):
  #   """Required cluster: general_commissioning cluster."""

  # @property
  # @abc.abstractmethod
  # def administrator_commissioning(self):
  #   """Required cluster: administrator_commissioning cluster."""

  # @property
  # @abc.abstractmethod
  # def node_operational_credentials(self):
  #   """Required cluster: node_operational_credentials cluster."""

  # @property
  # @abc.abstractmethod
  # def general_diagnostics(self):
  #   """Required cluster: general_diagnostics cluster."""

  # @property
  # @abc.abstractmethod
  # def power_source_configuration(self):
  #   """Optional cluster: power_source_configuration cluster."""

  # @property
  # @abc.abstractmethod
  # def time_synchronization(self):
  #   """Optional cluster: time_synchronization cluster."""

  # @property
  # @abc.abstractmethod
  # def diagnostic_logs(self):
  #   """Optional cluster: diagnostic_logs cluster."""

  # @property
  # @abc.abstractmethod
  # def software_diagnostics(self):
  #   """Optional cluster: software_diagnostics cluster."""
