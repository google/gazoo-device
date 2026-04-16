# Copyright 2023 Google LLC
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

"""Pigweed RPC implementation of the Matter Basic Information cluster capability.
"""
from typing import Union

from gazoo_device import decorators
from gazoo_device import gdm_logger
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.interfaces import matter_endpoints_base
from gazoo_device.capabilities.matter_clusters.interfaces import basic_information_base
from gazoo_device.protos import attributes_service_pb2
from gazoo_device.utility import tlv_utils
import immutabledict


logger = gdm_logger.get_logger()
BasicInformationCluster = matter_enums.BasicInformationCluster
UINT16_TYPE = attributes_service_pb2.AttributeType.ZCL_INT16U_ATTRIBUTE_TYPE
UINT32_TYPE = attributes_service_pb2.AttributeType.ZCL_INT32U_ATTRIBUTE_TYPE
STRING_TYPE = (
    attributes_service_pb2.AttributeType.ZCL_CHAR_STRING_ATTRIBUTE_TYPE)
_ATTRIBUTE_TYPE_ID_TO_FIELD = immutabledict.immutabledict({
    UINT16_TYPE: "data_uint16",
    UINT32_TYPE: "data_uint32",
})


class BasicInformationClusterPwRpc(
    basic_information_base.BasicInformationClusterBase):
  """Matter Basic Information cluster capability."""

  @decorators.DynamicProperty
  def data_model_revision(self) -> int:
    """The DataModelRevision attribute."""
    return self._get_attribute_value(
        attribute_id=BasicInformationCluster.ATTRIBUTE_DATA_MODEL_REVISION,
        attribute_type=UINT16_TYPE)

  @decorators.DynamicProperty
  def vendor_name(self) -> str:
    """The VendorName attribute."""
    return self._get_attribute_value(
        attribute_id=BasicInformationCluster.ATTRIBUTE_VENDOR_NAME,
        attribute_type=STRING_TYPE)

  @decorators.DynamicProperty
  def vendor_id(self) -> int:
    """The VendorID attribute."""
    return self._get_attribute_value(
        attribute_id=BasicInformationCluster.ATTRIBUTE_VENDOR_ID,
        attribute_type=UINT16_TYPE)

  @decorators.DynamicProperty
  def product_name(self) -> str:
    """The ProductName attribute."""
    return self._get_attribute_value(
        attribute_id=BasicInformationCluster.ATTRIBUTE_PRODUCT_NAME,
        attribute_type=STRING_TYPE)

  @decorators.DynamicProperty
  def product_id(self) -> int:
    """The ProductID attribute."""
    return self._get_attribute_value(
        attribute_id=BasicInformationCluster.ATTRIBUTE_PRODUCT_ID,
        attribute_type=UINT16_TYPE)

  @decorators.DynamicProperty
  def node_label(self) -> str:
    """The NodeLabel attribute."""
    return self._get_attribute_value(
        attribute_id=BasicInformationCluster.ATTRIBUTE_NODE_LABEL,
        attribute_type=STRING_TYPE)

  @decorators.DynamicProperty
  def location(self) -> str:
    """The Location attribute."""
    return self._get_attribute_value(
        attribute_id=BasicInformationCluster.ATTRIBUTE_LOCATION,
        attribute_type=STRING_TYPE)

  @decorators.DynamicProperty
  def hardware_version(self) -> int:
    """The HardwareVersion attribute."""
    return self._get_attribute_value(
        attribute_id=BasicInformationCluster.ATTRIBUTE_HARDWARE_VERSION,
        attribute_type=UINT16_TYPE)

  @decorators.DynamicProperty
  def hardware_version_string(self) -> str:
    """The HardwareVersionString attribute."""
    return self._get_attribute_value(
        attribute_id=BasicInformationCluster.ATTRIBUTE_HARDWARE_VERSION_STRING,
        attribute_type=STRING_TYPE)

  @decorators.DynamicProperty
  def software_version(self) -> int:
    """The SoftwareVersion attribute."""
    return self._get_attribute_value(
        attribute_id=BasicInformationCluster.ATTRIBUTE_SOFTWARE_VERSION,
        attribute_type=UINT32_TYPE)

  @decorators.DynamicProperty
  def software_version_string(self) -> str:
    """The SoftwareVersionString attribute."""
    return self._get_attribute_value(
        attribute_id=BasicInformationCluster.ATTRIBUTE_SOFTWARE_VERSION_STRING,
        attribute_type=STRING_TYPE)

  @decorators.DynamicProperty
  def manufacturing_date(self) -> str:
    """The ManufacturingDate attribute."""
    return self._get_attribute_value(
        attribute_id=BasicInformationCluster.ATTRIBUTE_MANUFACTURING_DATE,
        attribute_type=STRING_TYPE)

  @decorators.DynamicProperty
  def part_number(self) -> str:
    """The PartNumber attribute."""
    return self._get_attribute_value(
        attribute_id=BasicInformationCluster.ATTRIBUTE_PART_NUMBER,
        attribute_type=STRING_TYPE)

  @decorators.DynamicProperty
  def product_url(self) -> str:
    """The ProductURL attribute."""
    return self._get_attribute_value(
        attribute_id=BasicInformationCluster.ATTRIBUTE_PRODUCT_URL,
        attribute_type=STRING_TYPE)

  @decorators.DynamicProperty
  def product_label(self) -> str:
    """The ProductLabel attribute."""
    return self._get_attribute_value(
        attribute_id=BasicInformationCluster.ATTRIBUTE_PRODUCT_LABEL,
        attribute_type=STRING_TYPE)

  @decorators.DynamicProperty
  def serial_number(self) -> str:
    """The SerialNumber attribute."""
    return self._get_attribute_value(
        attribute_id=BasicInformationCluster.ATTRIBUTE_SERIAL_NUMBER,
        attribute_type=STRING_TYPE)

  @decorators.DynamicProperty
  def unique_id(self) -> str:
    """The UniqueID attribute."""
    return self._get_attribute_value(
        attribute_id=BasicInformationCluster.ATTRIBUTE_UNIQUE_ID,
        attribute_type=STRING_TYPE)

  def _get_attribute_value(
      self, attribute_id: int, attribute_type: int) -> Union[int, str]:
    """Gets attribute value by ID and type."""
    data = self._read(
        endpoint_id=matter_endpoints_base.ROOT_NODE_ENDPOINT_ID,
        cluster_id=matter_enums.BasicInformationCluster.ID,
        attribute_id=attribute_id,
        attribute_type=attribute_type)
    field = _ATTRIBUTE_TYPE_ID_TO_FIELD.get(attribute_type)

    # The returned data has a regular field defined by Ember API.
    if field is not None and data.HasField(field):
      return getattr(data, field)
    # The returned data only has tlv_data data field.
    else:
      decoder = tlv_utils.TLVReader(data.tlv_data)
      raw_data = decoder.get()
      # The structure format of the TLV decoded data, ex:
      # {'Any': {1: [{1: {0: 1982833481, 1: [0, 40, 1], 2: 'TEST_VENDOR'}}]}}
      try:
        return raw_data["Any"][1][0][1][2]
      except (KeyError, IndexError):
        return str(raw_data)
