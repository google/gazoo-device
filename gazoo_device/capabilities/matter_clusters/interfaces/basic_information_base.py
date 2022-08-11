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

"""Interface for the Matter Basic Information cluster capability."""
import abc
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters.interfaces import cluster_base


class BasicInformationClusterBase(
    cluster_base.ClusterBase, metaclass=abc.ABCMeta):
  """Matter Boolean State cluster capability."""

  CLUSTER_ID = matter_enums.BasicInformationCluster.ID

  @property
  @abc.abstractmethod
  def data_model_revision(self) -> int:
    """The DataModelRevision attribute."""

  @property
  @abc.abstractmethod
  def vendor_name(self) -> str:
    """The VendorName attribute."""

  @property
  @abc.abstractmethod
  def vendor_id(self) -> int:
    """The VendorID attribute."""

  @property
  @abc.abstractmethod
  def product_name(self) -> str:
    """The ProductName attribute."""

  @property
  @abc.abstractmethod
  def product_id(self) -> int:
    """The ProductID attribute."""

  @property
  @abc.abstractmethod
  def node_label(self) -> str:
    """The NodeLabel attribute."""

  @property
  @abc.abstractmethod
  def location(self) -> str:
    """The Location attribute."""

  @property
  @abc.abstractmethod
  def hardware_version(self) -> int:
    """The HardwareVersion attribute."""

  @property
  @abc.abstractmethod
  def hardware_version_string(self) -> str:
    """The HardwareVersionString attribute."""

  @property
  @abc.abstractmethod
  def software_version(self) -> int:
    """The SoftwareVersion attribute."""

  @property
  @abc.abstractmethod
  def software_version_string(self) -> str:
    """The SoftwareVersionString attribute."""

  @property
  @abc.abstractmethod
  def capability_minima(self) -> int:
    """The CapabilityMinima attribute."""
