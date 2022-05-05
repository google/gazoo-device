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

"""Interface for a Matter endpoint base capability."""
from typing import Any, Callable, FrozenSet, List, Optional, Set, Type
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import capability_base
from gazoo_device.capabilities.matter_clusters.interfaces import cluster_base

logger = gdm_logger.get_logger()


class EndpointBase(capability_base.CapabilityBase):
  """Matter endpoint base interface."""

  # Endpoint device type ID defined in the Matter spec.
  DEVICE_TYPE_ID = None

  def __init__(self,
               device_name: str,
               identifier: int,
               supported_clusters: FrozenSet[Type[cluster_base.ClusterBase]],
               read: Callable[..., Any],
               write: Callable[..., Any],
               device_type_id: Optional[int] = None):
    """Initializes Matter endpoint instance.

    Args:
      device_name: Device name used for logging.
      identifier: ID of this endpoint.
      supported_clusters: Supported cluster classes on this endpoint.
      read: Ember API read method.
      write: Ember API write method.
      device_type_id: Device type ID of this endpoint. It's only used for
        unsupported endpoint module, and the supported endpoints use
        cls.DEVICE_TYPE_ID instead.
    """
    super().__init__(device_name=device_name)
    self._id = identifier
    self._device_type_id = device_type_id
    self._supported_clusters = supported_clusters
    self._read = read
    self._write = write

  @decorators.DynamicProperty
  def id(self) -> int:
    """The ID of the endpoint."""
    return self._id

  @decorators.DynamicProperty
  def name(self) -> str:
    """The name of the endpoint."""
    return self.get_capability_name()

  @decorators.PersistentProperty
  def device_type_id(self) -> int:
    """The device type ID of the endpoint."""
    return self.DEVICE_TYPE_ID

  @decorators.CapabilityLogDecorator(logger)
  def get_supported_clusters(self) -> List[str]:
    """Returns names of clusters supported by the endpoint."""
    return sorted(
        cluster.get_capability_name() for cluster in self._supported_clusters)

  @decorators.CapabilityLogDecorator(logger)
  def get_supported_cluster_flavors(
      self) -> Set[Type[cluster_base.ClusterBase]]:
    """Returns flavors of cluster supported by the endpoint."""
    return self._supported_clusters

  @decorators.CapabilityLogDecorator(logger, level=decorators.DEBUG)
  def cluster_lazy_init(
      self, cluster_class: Type[cluster_base.ClusterBase]
  ) -> cluster_base.ClusterBase:
    """Provides a lazy instantiation mechanism for Matter cluster.

    Args:
      cluster_class: cluster class to instantiate.

    Returns:
      Initialized Matter cluster instance.
    """
    if cluster_class not in self.get_supported_cluster_flavors():
      raise errors.DeviceError(
          f"{self._device_name} does not support cluster {cluster_class} on "
          f"endpoint {self.name} (endpoint ID {self.id}).")

    cluster_name = cluster_class.__name__
    if not hasattr(self, cluster_name):
      cluster_inst = cluster_class(
          device_name=self._device_name,
          endpoint_id=self.id,
          read=self._read,
          write=self._write)
      setattr(self, cluster_name, cluster_inst)
    return getattr(self, cluster_name)
