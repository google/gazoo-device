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

"""Matter endpoint capability wrapper via Pigweed RPC."""
from typing import Any, Callable, List, Set, Tuple, Type

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities import matter_endpoints_and_clusters
from gazoo_device.capabilities.interfaces import matter_endpoints_base
from gazoo_device.capabilities.matter_clusters.interfaces import cluster_base
from gazoo_device.capabilities.matter_endpoints import unsupported_endpoint
from gazoo_device.capabilities.matter_endpoints.interfaces import endpoint_base
from gazoo_device.protos import attributes_service_pb2
from gazoo_device.protos import descriptor_service_pb2
from gazoo_device.switchboard.transports import pigweed_rpc_transport
from gazoo_device.utility import pwrpc_utils

_DESCRIPTOR_SERVICE_NAME = "Descriptor"
_DESCRIPTOR_GET_ENDPOINTS_RPC_NAME = "PartsList"
_DESCRIPTOR_DEVICE_TYPE_RPC_NAME = "DeviceTypeList"
_DESCRIPTOR_GET_CLUSTERS_RPC_NAME = "ServerList"
_ATTRIBUTE_SERVICE_NAME = "Attributes"
_ATTRIBUTE_READ_RPC_NAME = "Read"
_ATTRIBUTE_WRITE_RPC_NAME = "Write"
_ATTRIBUTE_DATA_MODULE_PATH = "gazoo_device.protos.attributes_service_pb2.AttributeData"
_ATTRIBUTE_METADATA_MODULE_PATH = "gazoo_device.protos.attributes_service_pb2.AttributeMetadata"

logger = gdm_logger.get_logger()


class MatterEndpointsAccessorPwRpc(matter_endpoints_base.MatterEndpointsBase):
  """Capability wrapper for accessing the Matter endpoint instances."""

  _SUPPORTED_ENDPOINTS = matter_endpoints_and_clusters.SUPPORTED_ENDPOINTS_PW_RPC

  def __init__(self, device_name: str, switchboard_call: Callable[..., Any],
               rpc_timeout_s: int):
    """Constructor of MatterEndpointsAccessorPwRpc.

    Args:
      device_name: Device name used for logging.
      switchboard_call: The switchboard.call method.
      rpc_timeout_s: Timeout (s) for RPC calls.
    """
    super().__init__(device_name=device_name, read=self.read, write=self.write)
    self._switchboard_call = switchboard_call
    self._rpc_timeout_s = rpc_timeout_s

  def get_supported_endpoint_ids(self) -> List[int]:
    """Gets the list of supported endpoint ids on the device."""
    ack, list_of_supported_endpoints = self._switchboard_call(
        method_name=pigweed_rpc_transport.RPC_METHOD_NAME,
        method_args=(_DESCRIPTOR_SERVICE_NAME,
                     _DESCRIPTOR_GET_ENDPOINTS_RPC_NAME),
        method_kwargs={
            "endpoint": matter_endpoints_base.ROOT_NODE_ENDPOINT_ID,
            "pw_rpc_timeout_s": self._rpc_timeout_s})
    if not ack:
      raise errors.DeviceError(
          f"Device {self._device_name} getting {_DESCRIPTOR_SERVICE_NAME} "
          f"{_DESCRIPTOR_GET_ENDPOINTS_RPC_NAME} failed.")
    supported_endpoint_ids = []
    for endpoint_in_bytes in list_of_supported_endpoints:
      endpoint = descriptor_service_pb2.Endpoint.FromString(endpoint_in_bytes)
      supported_endpoint_ids.append(endpoint.endpoint)
    return supported_endpoint_ids

  def get_endpoint_class_and_device_type_id(
      self, endpoint_id: int) -> Tuple[Type[endpoint_base.EndpointBase], int]:
    """Gets the endpoint class and device type ID by the given endpoint id.

    Args:
      endpoint_id: The given endpoint ID on the device.

    Returns:
      The endpoint class module (or UnsupportedEndpoint if the endpoint is not
      yet supported in GDM) and the device type ID.
    """
    ack, device_types = self._switchboard_call(
        method_name=pigweed_rpc_transport.RPC_METHOD_NAME,
        method_args=(_DESCRIPTOR_SERVICE_NAME,
                     _DESCRIPTOR_DEVICE_TYPE_RPC_NAME),
        method_kwargs={
            "endpoint": endpoint_id, "pw_rpc_timeout_s": self._rpc_timeout_s})
    if not ack:
      raise errors.DeviceError(
          f"Device {self._device_name} getting {_DESCRIPTOR_SERVICE_NAME} "
          f"{_DESCRIPTOR_DEVICE_TYPE_RPC_NAME} failed.")
    device_type = descriptor_service_pb2.DeviceType.FromString(device_types[0])
    device_type_id = device_type.device_type

    endpoint_class = (
        matter_endpoints_and_clusters.MATTER_DEVICE_TYPE_ID_TO_CLASS_PW_RPC.
        get(device_type_id, unsupported_endpoint.UnsupportedEndpoint))

    return endpoint_class, device_type_id

  def get_supported_clusters(
      self, endpoint_id: int) -> Set[Type[cluster_base.ClusterBase]]:
    """Retrieves the supported clusters from the given endpoint ID."""
    ack, clusters = self._switchboard_call(
        method_name=pigweed_rpc_transport.RPC_METHOD_NAME,
        method_args=(_DESCRIPTOR_SERVICE_NAME,
                     _DESCRIPTOR_GET_CLUSTERS_RPC_NAME),
        method_kwargs={
            "endpoint": endpoint_id, "pw_rpc_timeout_s": self._rpc_timeout_s})
    if not ack:
      raise errors.DeviceError(
          f"Device {self._device_name} getting {_DESCRIPTOR_SERVICE_NAME} "
          f"{_DESCRIPTOR_GET_CLUSTERS_RPC_NAME} failed.")
    cluster_classes = set()
    for cluster_in_bytes in clusters:
      cluster = descriptor_service_pb2.Cluster.FromString(cluster_in_bytes)
      cluster_class = matter_endpoints_and_clusters.CLUSTER_ID_TO_CLASS_PW_RPC.get(
          cluster.cluster_id)
      if cluster_class is None:
        logger.warning(
            f"Cluster class for cluster ID {hex(cluster.cluster_id)} has not "
            "been implemented yet.")
        continue
      cluster_classes.add(cluster_class)
    return cluster_classes

  @decorators.CapabilityLogDecorator(logger)
  def read(
      self,
      endpoint_id: int,
      cluster_id: attributes_service_pb2.ClusterType,
      attribute_id: int,
      attribute_type: attributes_service_pb2.AttributeType
  ) -> attributes_service_pb2.AttributeData:
    """Ember API read method.

    Reads attribute data from the given endpoint ID, cluster ID and
    attribute ID with the given attribute type. The endpoint ID is retrieved
    via descriptor cluster. The attribute type is defined in the
    attributes_service.proto, while cluster ID and attribute ID are defined in
    the Matter spec.

    Args:
      endpoint_id: Endpoint ID to read from.
      cluster_id: Cluster ID to read from.
      attribute_id: Attribute ID to read from.
      attribute_type: Attribute data type to read.

    Returns:
      Attribute data.

    Raises:
      Device error when ack value is false.
    """
    read_kwargs = {
        "endpoint": endpoint_id, "cluster": cluster_id,
        "attribute_id": attribute_id, "type": attribute_type,
        "pw_rpc_timeout_s": self._rpc_timeout_s}

    ack, data_in_bytes = self._switchboard_call(
        method_name=pigweed_rpc_transport.RPC_METHOD_NAME,
        method_args=(_ATTRIBUTE_SERVICE_NAME, _ATTRIBUTE_READ_RPC_NAME),
        method_kwargs=read_kwargs)
    if not ack:
      error_message = (
          f"Device {self._device_name} reading attribute (endpoint ID = "
          f"{endpoint_id}, cluster ID = {cluster_id}, attribute ID = "
          f"{attribute_id}) with attribute type {attribute_type} failed.")
      raise errors.DeviceError(error_message)

    return attributes_service_pb2.AttributeData.FromString(data_in_bytes)

  @decorators.CapabilityLogDecorator(logger)
  def write(
      self,
      endpoint_id: int,
      cluster_id: attributes_service_pb2.ClusterType,
      attribute_id: int,
      attribute_type: attributes_service_pb2.AttributeType,
      **data_kwargs: Any) -> None:
    """Ember API write method.

    Write attribute data to the given endpoint ID, cluster ID and
    attribute ID with the given attribute type. The endpoint ID is retrieved
    via descriptor cluster. The attribute type is defined in the
    attributes_service.proto, while cluster ID and attribute ID are defined in
    the Matter spec. data_kwargs is the data we want to write to the device, the
    supported data types are defined in AttributeData enum of
    attributes_service.proto.

    Args:
      endpoint_id: Endpoint ID to write to.
      cluster_id: Cluster ID to write to.
      attribute_id: Attribute ID to write to.
      attribute_type: Attribute data type to write.
      **data_kwargs: Attribute data to write.

    Raises:
      Device error when ack value is false.
    """
    data = attributes_service_pb2.AttributeData(**data_kwargs)
    metadata = attributes_service_pb2.AttributeMetadata(
        endpoint=endpoint_id,
        cluster=cluster_id,
        attribute_id=attribute_id,
        type=attribute_type)

    serialized_data = pwrpc_utils.PigweedProtoState(
        data, _ATTRIBUTE_DATA_MODULE_PATH)
    serialized_metadata = pwrpc_utils.PigweedProtoState(
        metadata, _ATTRIBUTE_METADATA_MODULE_PATH)
    write_kwargs = {"data": serialized_data, "metadata": serialized_metadata}

    ack, _ = self._switchboard_call(
        method_name=pigweed_rpc_transport.RPC_METHOD_NAME,
        method_args=(_ATTRIBUTE_SERVICE_NAME, _ATTRIBUTE_WRITE_RPC_NAME),
        method_kwargs=write_kwargs)
    if not ack:
      error_message = (
          f"Device {self._device_name} writing data: {data} to attribute ("
          f"endpoint ID = {endpoint_id}, cluster ID = {cluster_id}, attribute "
          f"ID = {attribute_id}) with attribute type {attribute_type} failed.")
      raise errors.DeviceError(error_message)
