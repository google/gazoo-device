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

"""Matter endpoint capability wrapper."""
import copy
from typing import Any, Callable, Collection, List, Mapping, Optional, Set, Type

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


class _DescriptorServiceHandler:
  """Descriptor RPC service handler.

  Handler which leverages the descriptor RPC service on Matter device to get
  the list of supported endpoint IDs and their device types. It allows the
  implementation of generic Matter device controller on different platforms.
  """

  def __init__(
      self,
      device_name: str,
      switchboard_call: Callable[..., Any],
      rpc_timeout_s: int):
    """Creates a descriptor service handler instance.

    Args:
      device_name: Device name used for logging.
      switchboard_call: The switchboard.call method.
      rpc_timeout_s: Timeout (s) for RPC calls.
    """
    self._switchboard_call = switchboard_call
    self._rpc_timeout_s = rpc_timeout_s
    self._device_name = device_name

    # The endpoint ID to endpoint class mapping.
    self._endpoint_id_to_class = {}

    # The endpoint class to endpoint ID mapping.
    self._endpoint_class_to_id = {}

    # The endpoint ID to set of cluster classes mapping.
    self._endpoint_id_to_clusters = {}

    # The endpoint ID to device type ID mapping.
    self._endpoint_id_to_device_type_id = {}

  @property
  def endpoint_id_to_class(
      self) -> Mapping[int, Optional[Type[endpoint_base.EndpointBase]]]:
    """Returns the endpoint_id_to_class mapping."""
    self._fetch_endpoints_and_clusters()
    return copy.deepcopy(self._endpoint_id_to_class)

  @property
  def endpoint_class_to_id(
      self) -> Mapping[Type[endpoint_base.EndpointBase], int]:
    """Returns the endpoint_class_to_id mapping."""
    self._fetch_endpoints_and_clusters()
    return copy.deepcopy(self._endpoint_class_to_id)

  @property
  def endpoint_id_to_clusters(
      self) -> Mapping[int, Set[Type[cluster_base.ClusterBase]]]:
    """Returns the endpoint ID to cluster classes mapping."""
    self._fetch_endpoints_and_clusters()
    return copy.deepcopy(self._endpoint_id_to_clusters)

  @property
  def endpoint_id_to_device_type_id(self) -> Mapping[int, int]:
    """Returns the endpoint ID to device type ID mapping."""
    self._fetch_endpoints_and_clusters()
    return copy.deepcopy(self._endpoint_id_to_device_type_id)

  def reset(self) -> None:
    """Resets the endpoint ID and endpoint class mapping."""
    self._endpoint_id_to_class.clear()
    self._endpoint_class_to_id.clear()
    self._endpoint_id_to_clusters.clear()
    self._endpoint_id_to_device_type_id.clear()

  def _fetch_endpoints_and_clusters(self) -> None:
    """Retrieves the supported endpoints from the descriptor RPC service.

    The set of supported clusters is also obtained by the descriptor RPC. Note
    that RPC is only triggered when endpoint_id_to_class mapping is None.
    """
    if not self._endpoint_id_to_class:
      for endpoint_id in self._get_supported_endpoint_ids():
        endpoint_cls = self._get_endpoint_class(endpoint_id)
        self._endpoint_id_to_class[endpoint_id] = endpoint_cls
        # Ensuring we store the first endpoint ID handled by this class.
        # This mapping will be used in get_endpoint_instance_by_class method
        if endpoint_cls not in self._endpoint_class_to_id:
          self._endpoint_class_to_id[endpoint_cls] = endpoint_id
        self._endpoint_id_to_clusters[endpoint_id] = (
            self._get_supported_clusters(endpoint_id))

  def _get_supported_endpoint_ids(self) -> List[int]:
    """Gets the list of supported endpoint ids on the device."""
    ack, list_of_supported_endpoints = self._switchboard_call(
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
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

  def _get_endpoint_class(
      self, endpoint_id: int) -> Type[endpoint_base.EndpointBase]:
    """Gets the endpoint class by the given endpoint id.

    Args:
      endpoint_id: The given endpoint ID on the device.

    Returns:
      The endpoint class module. The method returns None if the given endpoint
      ID does not have device type.
    """
    ack, device_types = self._switchboard_call(
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
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

    # Store the endpoint ID to device type ID mapping.
    self._endpoint_id_to_device_type_id[endpoint_id] = device_type_id

    return matter_endpoints_and_clusters.MATTER_DEVICE_TYPE_ID_TO_CLASS.get(
        device_type_id, unsupported_endpoint.UnsupportedEndpoint)

  def _get_supported_clusters(
      self, endpoint_id: int) -> Set[Type[cluster_base.ClusterBase]]:
    """Retrieves the supported clusters from the given endpoint ID."""
    ack, clusters = self._switchboard_call(
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
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
      cluster_class = matter_endpoints_and_clusters.CLUSTER_ID_TO_CLASS.get(
          cluster.cluster_id)
      if cluster_class is None:
        logger.warning(
            f"Cluster class for cluster ID {hex(cluster.cluster_id)} has not "
            "been implemented yet.")
        continue
      cluster_classes.add(cluster_class)
    return cluster_classes


class MatterEndpointsAccessor(matter_endpoints_base.MatterEndpointsBase):
  """Capability wrapper for accessing the Matter endpoint instances."""

  def __init__(
      self,
      device_name: str,
      switchboard_call: Callable[..., Any],
      rpc_timeout_s: int):
    """Constructor of MatterEndpointsAccessor.

    Args:
      device_name: Device name used for logging.
      switchboard_call: The switchboard.call method.
      rpc_timeout_s: Timeout (s) for RPC calls.
    """
    super().__init__(device_name=device_name)

    # DescriptorServiceHandler instance for accessing endpoints and clusters
    # information via Matter descriptor cluster.
    self._descriptor_service_handler = _DescriptorServiceHandler(
        device_name=device_name,
        switchboard_call=switchboard_call,
        rpc_timeout_s=rpc_timeout_s)

    # Endpoint ID to endpoint instance mapping
    self._endpoints = {}

    # Arguments for Ember APIs.
    self._switchboard_call = switchboard_call
    self._rpc_timeout_s = rpc_timeout_s

  @decorators.CapabilityLogDecorator(logger)
  def get(self, endpoint_id: int) -> endpoint_base.EndpointBase:
    """Gets the specific endpoint instance by ID.

    Args:
      endpoint_id: Endpoint ID on the device.

    Returns:
      The endpoint class for the given endpoint ID.

    Raises:
      DeviceError: The given endpoint ID does not exist on the device. Or the
      endpoint class for the given endpoint ID is not implemented yet.
    """
    if endpoint_id not in self._endpoints:

      if (endpoint_id not in
          self._descriptor_service_handler.endpoint_id_to_class):
        raise errors.DeviceError(
            f"Endpoint ID {endpoint_id} on {self._device_name} does not exist.")

      # Obtain endpoint information from the descriptor handler.
      endpoint_class = (self._descriptor_service_handler.
                        endpoint_id_to_class[endpoint_id])

      supported_clusters = (self._descriptor_service_handler.
                            endpoint_id_to_clusters[endpoint_id])

      device_type_id = (self._descriptor_service_handler.
                        endpoint_id_to_device_type_id[endpoint_id])

      # Create endpoint instance.
      self._endpoints[endpoint_id] = endpoint_class(
          device_name=self._device_name,
          identifier=endpoint_id,
          device_type_id=device_type_id,
          supported_clusters=frozenset(supported_clusters),
          read=self.read,
          write=self.write)

    return self._endpoints[endpoint_id]

  @decorators.CapabilityLogDecorator(logger)
  def list(self) -> Mapping[int, Type[endpoint_base.EndpointBase]]:
    """Returns a mapping of endpoint ID to the supported endpoint class."""
    return self._descriptor_service_handler.endpoint_id_to_class

  @decorators.CapabilityLogDecorator(logger)
  def get_endpoint_instance_by_class(
      self, endpoint_class: Type[endpoint_base.EndpointBase]
  ) -> endpoint_base.EndpointBase:
    """Gets the endpoint instance by the given endpoint class.

    Args:
      endpoint_class: The given Matter endpoint class.

    Raises:
      DeviceError: When the given endpoint class is not supported on the device.

    Returns:
      The endpoint instance.
    """
    if (endpoint_class not in
        self._descriptor_service_handler.endpoint_class_to_id):
      raise errors.DeviceError(
          f"Class {endpoint_class} is not supported on {self._device_name}.")
    endpoint_id = (
        self._descriptor_service_handler.endpoint_class_to_id[endpoint_class])
    return self.get(endpoint_id)

  @decorators.CapabilityLogDecorator(logger)
  def reset(self) -> None:
    """Resets the endpoint ID and endpoint class mapping."""
    self._descriptor_service_handler.reset()

  @decorators.CapabilityLogDecorator(logger)
  def has_endpoints(self, endpoint_names: Collection[str]) -> bool:
    """Checks whether the device supports all the given endpoint names.

    Args:
      endpoint_names: The collection of endpoint names. The names are
        case-insensitive. Some valid examples are: "on_off_light",
        "On_Off_Light".

    Raises:
      ValueError when the given endpoint name is invalid or not supported in
      GDM.

    Returns:
      True if the device supports all the endpoints, false otherwise.
    """
    valid_endpoint_name_to_class = {
        endpoint_class.get_capability_name(): endpoint_class
        for endpoint_class in matter_endpoints_and_clusters.SUPPORTED_ENDPOINTS}
    supported_endpoints = set(self.list().values())
    for endpoint_name in endpoint_names:
      endpoint = valid_endpoint_name_to_class.get(endpoint_name.lower())
      if endpoint is None:
        raise ValueError(f"Endpoint {endpoint_name} is not recognized. "
                         "Valid endpoints are: "
                         f"{list(valid_endpoint_name_to_class.keys())}")
      if endpoint not in supported_endpoints:
        return False
    return True

  @decorators.CapabilityLogDecorator(logger)
  def get_supported_endpoints(self) -> List[str]:
    """Returns names of endpoints supported by the device."""
    return sorted(endpoint.get_capability_name() for endpoint in
                  self.get_supported_endpoint_flavors())

  @decorators.CapabilityLogDecorator(logger)
  def get_supported_endpoint_flavors(
      self) -> List[Type[endpoint_base.EndpointBase]]:
    """Returns flavors of endpoints supported by the device."""
    return [
        endpoint for endpoint in self.list().values() if endpoint is not None]

  @decorators.CapabilityLogDecorator(logger)
  def get_supported_endpoints_and_clusters(self) -> Mapping[int, Set[str]]:
    """Returns the supported endpoint IDs and set of cluster names mapping."""
    return {
        endpoint_id: self.get(endpoint_id).get_supported_clusters()
        for endpoint_id in self.list()}

  @decorators.CapabilityLogDecorator(logger)
  def get_supported_endpoint_instances_and_cluster_flavors(self) -> Mapping[
      Type[endpoint_base.EndpointBase], Set[Type[cluster_base.ClusterBase]]]:
    """Returns the supported endpoint instance and cluster flavors mapping."""
    mapping = {}
    for endpoint_id in self.list():
      endpoint = self.get(endpoint_id)
      mapping[endpoint] = endpoint.get_supported_cluster_flavors()
    return mapping

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
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
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
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
        method_args=(_ATTRIBUTE_SERVICE_NAME, _ATTRIBUTE_WRITE_RPC_NAME),
        method_kwargs=write_kwargs)
    if not ack:
      error_message = (
          f"Device {self._device_name} writing data: {data} to attribute ("
          f"endpoint ID = {endpoint_id}, cluster ID = {cluster_id}, attribute "
          f"ID = {attribute_id}) with attribute type {attribute_type} failed.")
      raise errors.DeviceError(error_message)
