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
from typing import Any, Callable, FrozenSet, List, Set, Type
from gazoo_device import decorators
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
               switchboard_call: Callable[..., Any],
               rpc_timeout_s: int):
    """Initializes Matter endpoint instance.

    Args:
      device_name: Device name used for logging.
      identifier: ID of this endpoint.
      supported_clusters: Supported cluster classes on this endpoint.
      switchboard_call: The switchboard.call method.
      rpc_timeout_s: Timeout (s) for RPC call.
    """
    super().__init__(device_name=device_name)
    self._id = identifier
    self._supported_clusters = supported_clusters
    self._switchboard_call = switchboard_call
    self._rpc_timeout_s = rpc_timeout_s

  @decorators.PersistentProperty
  def id(self) -> int:
    """The ID of the endpoint on the device."""
    return self._id

  @decorators.PersistentProperty
  def name(self) -> str:
    """The name of the endpoint on the device."""
    return self.get_capability_name()

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
      self,
      cluster_class: Type[cluster_base.ClusterBase],
      *args: Any,
      **kwargs: Any) -> cluster_base.ClusterBase:
    """Provides a lazy instantiation mechanism for Matter cluster.

    Args:
      cluster_class: cluster class to instantiate.
      *args: positional args to the cluster's __init__. Prefer
        using keyword arguments over positional arguments.
      **kwargs: keyword arguments to the cluster's __init__.

    Returns:
      Initialized Matter cluster instance.
    """
    # TODO(gdm-authors) Unblock the check once b/228923824 is resolved
    # if cluster_class not in self.get_supported_cluster_flavors():
    #  raise errors.DeviceError(
    #      f"{self._device_name} does not support cluster {cluster_class} on "
    #      f"endpoint {self.name} (endpoint ID {self.id}).")

    cluster_name = cluster_class.__name__
    if not hasattr(self, cluster_name):
      cluster_inst = cluster_class(*args, **kwargs)
      setattr(self, cluster_name, cluster_inst)
    return getattr(self, cluster_name)
