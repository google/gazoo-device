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

"""Interface for Matter endpoint capability wrapper."""
import abc
from typing import Any, Collection, List, Mapping, Optional, Set, Tuple, Type
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import capability_base
from gazoo_device.capabilities.matter_clusters.interfaces import cluster_base
from gazoo_device.capabilities.matter_endpoints.interfaces import endpoint_base
import immutabledict

ROOT_NODE_ENDPOINT_ID = 0

logger = gdm_logger.get_logger()


class MatterEndpointsBase(capability_base.CapabilityBase):
  """Capability wrapper for accessing the Matter endpoint instances."""

  def __init__(self, device_name: str, **cluster_kwargs: Any):
    """Initializes an instance of MatterEndpoints capability.

    Args:
      device_name: Name of the device instance the capability is attached to.
      **cluster_kwargs: Keyword arguments for initializing PigweedRPC/ChipTool
        based cluster capability.
    """
    super().__init__(device_name=device_name)
    self._cluster_kwargs = cluster_kwargs

    # Endpoint ID to endpoint instance mapping
    self._endpoints = {}

    # The endpoint ID to endpoint class mapping.
    self._endpoint_id_to_class = {}

    # The endpoint class to endpoint ID mapping.
    self._endpoint_class_to_id = {}

    # The endpoint ID to set of cluster classes mapping.
    self._endpoint_id_to_clusters = {}

    # The endpoint ID to device type ID mapping.
    self._endpoint_id_to_device_type_id = {}

  @abc.abstractmethod
  def get_supported_endpoint_ids(self) -> List[int]:
    """Gets the list of supported endpoint ids on the device."""

  @abc.abstractmethod
  def get_endpoint_class_and_device_type_id(
      self, endpoint_id: int) -> Tuple[Type[endpoint_base.EndpointBase], int]:
    """Gets the endpoint class and device type ID by the given endpoint id.

    Args:
      endpoint_id: The given endpoint ID on the device.

    Returns:
      The endpoint class module (or UnsupportedEndpoint if the endpoint is not
      yet supported in GDM) and the device type ID.
    """

  @abc.abstractmethod
  def get_supported_clusters(
      self, endpoint_id: int) -> Set[Type[cluster_base.ClusterBase]]:
    """Retrieves the supported clusters from the given endpoint ID.

    Args:
      endpoint_id: The given endpoint ID on the device.

    Returns:
      Set of supported cluster capability classes.
    """

  @decorators.DynamicProperty
  def endpoint_id_to_class(
      self) -> Mapping[int, Optional[Type[endpoint_base.EndpointBase]]]:
    """Returns the endpoint_id_to_class mapping."""
    self._fetch_endpoints_and_clusters()
    return immutabledict.immutabledict(self._endpoint_id_to_class)

  @decorators.DynamicProperty
  def endpoint_class_to_id(
      self) -> Mapping[Type[endpoint_base.EndpointBase], int]:
    """Returns the endpoint_class_to_id mapping."""
    self._fetch_endpoints_and_clusters()
    return immutabledict.immutabledict(self._endpoint_class_to_id)

  @decorators.DynamicProperty
  def endpoint_id_to_clusters(
      self) -> Mapping[int, Set[Type[cluster_base.ClusterBase]]]:
    """Returns the endpoint ID to cluster classes mapping."""
    self._fetch_endpoints_and_clusters()
    return immutabledict.immutabledict(self._endpoint_id_to_clusters)

  @decorators.DynamicProperty
  def endpoint_id_to_device_type_id(self) -> Mapping[int, int]:
    """Returns the endpoint ID to device type ID mapping."""
    self._fetch_endpoints_and_clusters()
    return immutabledict.immutabledict(self._endpoint_id_to_device_type_id)

  def _fetch_endpoints_and_clusters(self):
    """Retrieves the supported endpoints and clusters from descriptor cluster.

    The descriptor cluster should only be queried if it has not previously been
    called or the reset method is called.
    """
    if not self._endpoint_id_to_class:
      for endpoint_id in self.get_supported_endpoint_ids():
        endpoint_cls, device_type_id = (
            self.get_endpoint_class_and_device_type_id(endpoint_id))

        # Store the endpoint ID to endpoint class mapping.
        self._endpoint_id_to_class[endpoint_id] = endpoint_cls

        # Store the endpoint ID to device type ID mapping.
        self._endpoint_id_to_device_type_id[endpoint_id] = device_type_id

        # Ensuring we store the first endpoint ID handled by this class.
        # This mapping will be used in get_endpoint_instance_by_class method
        if endpoint_cls not in self._endpoint_class_to_id:
          self._endpoint_class_to_id[endpoint_cls] = endpoint_id

        # Store the endpoint ID to clusters mapping.
        self._endpoint_id_to_clusters[endpoint_id] = (
            self.get_supported_clusters(endpoint_id))

  @decorators.CapabilityLogDecorator(logger)
  def get(self, endpoint_id: int) -> endpoint_base.EndpointBase:
    """Gets the specific endpoint instance by endpoint ID.

    Args:
      endpoint_id: Endpoint ID on the device.

    Returns:
      The endpoint class for the given endpoint ID.

    Raises:
      DeviceError: The given endpoint ID does not exist on the device. Or the
      endpoint class for the given endpoint ID is not implemented yet.
    """
    if endpoint_id not in self.endpoint_id_to_class:
      raise errors.DeviceError(
          f"Endpoint ID {endpoint_id} on {self._device_name} does not exist.")

    if endpoint_id not in self._endpoints:
      endpoint_class = self.endpoint_id_to_class[endpoint_id]
      supported_clusters = self.endpoint_id_to_clusters[endpoint_id]
      device_type_id = self.endpoint_id_to_device_type_id[endpoint_id]

      self._endpoints[endpoint_id] = endpoint_class(
          device_name=self._device_name,
          identifier=endpoint_id,
          device_type_id=device_type_id,
          supported_clusters=frozenset(supported_clusters),
          **self._cluster_kwargs)

    return self._endpoints[endpoint_id]

  @decorators.CapabilityLogDecorator(logger)
  def list(self) -> Mapping[int, Type[endpoint_base.EndpointBase]]:
    """Returns a mapping of endpoint ID to the supported endpoint class."""
    return self.endpoint_id_to_class

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
    if endpoint_class not in self.endpoint_class_to_id:
      raise errors.DeviceError(
          f"Class {endpoint_class} is not supported on {self._device_name}.")
    endpoint_id = self.endpoint_class_to_id[endpoint_class]
    return self.get(endpoint_id)

  @decorators.CapabilityLogDecorator(logger)
  def reset(self) -> None:
    """Resets the endpoint ID and endpoint class mappings."""
    self._endpoint_id_to_class.clear()
    self._endpoint_class_to_id.clear()
    self._endpoint_id_to_clusters.clear()
    self._endpoint_id_to_device_type_id.clear()
    self._endpoints.clear()

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
        for endpoint_class in self._SUPPORTED_ENDPOINTS
    }
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
    return sorted(endpoint.get_capability_name()
                  for endpoint in self.get_supported_endpoint_flavors())

  @decorators.CapabilityLogDecorator(logger)
  def get_supported_endpoint_flavors(
      self) -> List[Type[endpoint_base.EndpointBase]]:
    """Returns flavors of endpoints supported by the device."""
    return [
        endpoint for endpoint in self.list().values() if endpoint is not None
    ]

  @decorators.CapabilityLogDecorator(logger)
  def get_supported_endpoints_and_clusters(self) -> Mapping[int, Set[str]]:
    """Returns the supported endpoint IDs and set of cluster names mapping."""
    return {
        endpoint_id: self.get(endpoint_id).get_supported_clusters()
        for endpoint_id in self.list()
    }

  @decorators.CapabilityLogDecorator(logger)
  def get_supported_endpoint_instances_and_cluster_flavors(
      self
  ) -> Mapping[Type[endpoint_base.EndpointBase],
               Set[Type[cluster_base.ClusterBase]]]:
    """Returns the supported endpoint instance and cluster flavors mapping."""
    mapping = {}
    for endpoint_id in self.list():
      endpoint = self.get(endpoint_id)
      mapping[endpoint] = endpoint.get_supported_cluster_flavors()
    return mapping
