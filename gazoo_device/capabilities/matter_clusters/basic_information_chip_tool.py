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
"""chip-tool implementation of Matter Basic Information cluster capability.
"""

from gazoo_device import decorators
from gazoo_device import gdm_logger
from gazoo_device.capabilities.matter_clusters.interfaces import basic_information_base

logger = gdm_logger.get_logger()
_CLUSTER_NAME = "basic"


class BasicInformationClusterChipTool(
    basic_information_base.BasicInformationClusterBase):
  """Matter Basic Information cluster capability."""

  @decorators.DynamicProperty
  def data_model_revision(self) -> int:
    """The DataModelRevision attribute."""
    return self._read(self._endpoint_id, _CLUSTER_NAME, "data-model-revision")

  @decorators.DynamicProperty
  def vendor_name(self) -> str:
    """The VendorName attribute."""
    return self._read(self._endpoint_id, _CLUSTER_NAME, "vendor-name")

  @decorators.DynamicProperty
  def vendor_id(self) -> int:
    """The VendorID attribute."""
    return self._read(self._endpoint_id, _CLUSTER_NAME, "vendor-id")

  @decorators.DynamicProperty
  def product_name(self) -> str:
    """The ProductName attribute."""
    return self._read(self._endpoint_id, _CLUSTER_NAME, "product-name")

  @decorators.DynamicProperty
  def product_id(self) -> int:
    """The ProductID attribute."""
    return self._read(self._endpoint_id, _CLUSTER_NAME, "product-id")

  @decorators.DynamicProperty
  def node_label(self) -> str:
    """The NodeLabel attribute."""
    return self._read(self._endpoint_id, _CLUSTER_NAME, "node-label")

  @decorators.DynamicProperty
  def location(self) -> str:
    """The Location attribute."""
    return self._read(self._endpoint_id, _CLUSTER_NAME, "location")

  @decorators.DynamicProperty
  def hardware_version(self) -> int:
    """The HardwareVersion attribute."""
    return self._read(self._endpoint_id, _CLUSTER_NAME, "hardware-version")

  @decorators.DynamicProperty
  def hardware_version_string(self) -> str:
    """The HardwareVersionString attribute."""
    return self._read(
        self._endpoint_id, _CLUSTER_NAME, "hardware-version-string")

  @decorators.DynamicProperty
  def software_version(self) -> int:
    """The SoftwareVersion attribute."""
    return self._read(self._endpoint_id, _CLUSTER_NAME, "software-version")

  @decorators.DynamicProperty
  def software_version_string(self) -> str:
    """The SoftwareVersionString attribute."""
    return self._read(
        self._endpoint_id, _CLUSTER_NAME, "software-version-string")

  @decorators.DynamicProperty
  def capability_minima(self) -> int:
    """The CapabilityMinima attribute."""
    return self._read(
        self._endpoint_id, _CLUSTER_NAME, "capability-minima")
