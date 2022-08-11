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
"""Matter Root Node endpoint.

This endpoint module corresponds to the
"Root Node" Matter device type which defines required and optional clusters
in the Matter spec 1.0.

A Root Node endpoint houses an instance of Root Node Matter device type with
the following defined clusters on this endpoint:

The required clusters for this endpoint: Basic Information, Access Control,
  Group Key Management, General Commissioning, Administrator Commissioning,
  Node Operational Credentials, General Diagnostics.
The optional clusters for this endpoint: Power Source Configuration, Time
  Synchronization, Diagnostic Logs, Software Diagnostics.
"""

from gazoo_device import decorators
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters import basic_information_chip_tool
from gazoo_device.capabilities.matter_endpoints.interfaces import root_node_base


class RootNodeEndpoint(root_node_base.RootNodeBase):
  """Matter Root Node endpoint."""

  @decorators.CapabilityDecorator(
      basic_information_chip_tool.BasicInformationClusterChipTool)
  def basic_information(
      self) -> basic_information_chip_tool.BasicInformationClusterChipTool:
    """Matter Root Node cluster instance."""
    return self.cluster_lazy_init(matter_enums.BasicInformationCluster.ID)

  # TODO(b/241164443): implement additional clusters for root node.

  # def access_control(self):
  #   """Matter access control cluster instance."""

  # def group_key_management(self):
  #   """Matter group key management cluster instance."""

  # def general_commissioning(self):
  #   """Matter general commissioning cluster instance."""

  # def administrator_commissioning(self):
  #   """Matter administrator commissioning cluster instance."""

  # def node_operational_credentials(self):
  #   """Matter node_operational_credentials cluster instance."""

  # def general_diagnostics(self):
  #   """Matter general diagnostics cluster instance."""

  # def power_source_configuration(self):
  #   """Matter power source configuration cluster instance."""

  # def time_synchronization(self):
  #   """Matter time synchronization cluster instance."""

  # def diagnostic_logs(self):
  #   """Matter diagnostic logs cluster instance."""

  # def software_diagnostics(self):
  #   """Matter software diagnostics cluster instance."""
