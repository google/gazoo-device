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

"""Interface for a Matter endpoint base capability.

Matter endpoint capability houses different required or optional cluster
capabilities, based on the Matter device type the endpoint corresponds to.
The capability is initialized with a set of GDM supported cluster capability
classes, which can be one of the following flavors depending on the device
this capability belongs to:

  - PigweedRPC (e.g. OnOffClusterPwRpc) for Matter devices (ESP32Matter, etc.)

    Directly controls the end devices over PwRpc, bypassing Matter protocol.
    The end devices do not need to be commissioned.

  - ChipTool (e.g. OnOffClusterChipTool) for RaspberryPiMatterController

    Mimics a Matter controller/hub by using chip-tool running on a raspberry pi
    to control commissioned end devices via Matter protocol. The end devices do
    not need to support PigweedRPC.

See https://github.com/google/gazoo-device/blob/master/docs/Matter_endpoints.md
for more details.
"""

from typing import Collection, FrozenSet, List, Optional, Set, Type

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import extensions
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import capability_base
from gazoo_device.capabilities.matter_clusters.interfaces import cluster_base
from gazoo_device.protos import attributes_service_pb2

logger = gdm_logger.get_logger()


class EndpointBase(capability_base.CapabilityBase):
  """Matter endpoint base interface."""

  # Endpoint device type ID defined in the Matter spec.
  DEVICE_TYPE_ID = None

  def __init__(self,
               device_name: str,
               identifier: int,
               supported_clusters: FrozenSet[Type[cluster_base.ClusterBase]],
               device_type_id: Optional[int] = None,
               **cluster_kwargs):
    """Initializes Matter endpoint instance.

    Args:
      device_name: Device name used for logging.
      identifier: ID of this endpoint.
      supported_clusters: Supported cluster classes on this endpoint.
      device_type_id: Device type ID of this endpoint. It's only used for
        unsupported endpoint module, and the supported endpoints use
        cls.DEVICE_TYPE_ID instead.
      **cluster_kwargs: Keyword arguments for PigweedRPC or ChipTool cluster
        initialization.
    """
    super().__init__(device_name=device_name)
    self._id = identifier
    self._device_type_id = device_type_id
    self._supported_clusters = supported_clusters
    self._cluster_kwargs = cluster_kwargs

  def __str__(self) -> str:
    """Overrides string representation of the endpoint."""
    return f"{self.name} (endpoint ID: {self.id}) on {self._device_name}"

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
  def has_clusters(self, cluster_names: Collection[str]) -> bool:
    """Checks whether the endpoint supports all the given cluster names.

    Args:
      cluster_names: The collection of cluster names. The names are
        case-insensitive. Some valid examples are: "color_control",
        "Color_Control".
    Raises:
      ValueError when the given cluster name is invalid or not supported in
      GDM.

    Returns:
      True if the device supports all the clusters, false otherwise.
    """
    valid_cluster_names = set()
    for cluster_name, cluster_class in extensions.capability_flavors.items():
      if issubclass(cluster_class, cluster_base.ClusterBase):
        valid_cluster_names.add(
            cluster_name.replace("_pw_rpc", "").replace("_chip_tool", ""))

    for cluster_name in cluster_names:
      cluster_name = cluster_name.lower()
      if not cluster_name.endswith("_cluster"):
        cluster_name += "_cluster"
      if cluster_name not in valid_cluster_names:
        raise ValueError(f"Cluster {cluster_name} is not recognized. "
                         f"Supported clusters are {list(valid_cluster_names)}")
      if cluster_name not in self.get_supported_clusters():
        return False
    return True

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
      self, cluster_id: attributes_service_pb2.ClusterType
  ) -> cluster_base.ClusterBase:
    """Provides a lazy instantiation mechanism for Matter cluster.

    Args:
      cluster_id: cluster ID to instantiate.

    Returns:
      Initialized Matter cluster instance.
    """
    cluster_id_to_class = {
        cluster.CLUSTER_ID: cluster
        for cluster in self.get_supported_cluster_flavors()
    }
    if cluster_id not in cluster_id_to_class:
      raise errors.DeviceError(
          f"{self._device_name} does not support cluster {cluster_id} on "
          f"endpoint {self.name} (endpoint ID {self.id}).")

    cluster_class = cluster_id_to_class[cluster_id]
    cluster_name = cluster_class.__name__
    if not hasattr(self, cluster_name):
      cluster_inst = cluster_class(
          device_name=self._device_name,
          endpoint_id=self.id,
          **self._cluster_kwargs)
      setattr(self, cluster_name, cluster_inst)
    return getattr(self, cluster_name)
