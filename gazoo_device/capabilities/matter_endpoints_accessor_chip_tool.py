"""chip-tool implementation of the Matter endpoints accessor capability.

MatterEndpointsAccessorChipTool discovers the available endpoints on a Matter
device and exposes corresponding cluster capabilities, based on the results
retrieved via RaspberryPiMatterController using chip-tool binary. Communications
with the Matter end device are done via Matter protocol, and the end device is
expected to be commissioned by the same RaspberryPiMatterController. Since
chip-tool only supports commissioning a single device at a time, this capability
is attached to RaspberryPiMatterController instead of the Matter end device
for simplicity.
"""

import re
from typing import Callable, TypedDict, Union

from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities import matter_controller_chip_tool
from gazoo_device.capabilities import matter_endpoints_and_clusters
from gazoo_device.capabilities.interfaces import matter_endpoints_base
from gazoo_device.capabilities.matter_clusters.interfaces import cluster_base
from gazoo_device.capabilities.matter_endpoints import unsupported_endpoint
from gazoo_device.capabilities.matter_endpoints.interfaces import endpoint_base
import immutabledict

logger = gdm_logger.get_logger()

_CHIP_TOOL_TRACING_ENABLED = "--trace_decode 1"


class ResponseRegex(TypedDict):
  DESCRIPTOR_ATTRIBUTE_RESPONSE: str
  DEVICE_TYPE_LIST_RESPONSE: str


_COMMANDS = immutabledict.immutabledict({
    "READ_DESCRIPTOR_PARTS_LIST": (
        "{chip_tool} descriptor read parts-list {node_id} {endpoint_id} "
        "{tracing_enable}"
    ),
    "READ_DESCRIPTOR_SERVER_LIST": (
        "{chip_tool} descriptor read server-list {node_id} {endpoint_id} "
        "{tracing_enable}"
    ),
    "READ_DESCRIPTOR_DEVICE_TYPE_LIST": (
        "{chip_tool} descriptor read device-type-list {node_id} {endpoint_id} "
        "{tracing_enable}"
    ),
})


class MatterEndpointsAccessorChipTool(matter_endpoints_base.MatterEndpointsBase
                                     ):
  """Capability for accessing the Matter endpoint instances via chip-tool."""

  _SUPPORTED_ENDPOINTS = matter_endpoints_and_clusters.SUPPORTED_ENDPOINTS

  def __init__(
      self,
      device_name: str,
      node_id_getter: Callable[[], int],
      shell_fn: Callable[..., str],
      shell_with_regex: Callable[..., str],
      matter_controller: matter_controller_chip_tool.MatterControllerChipTool,
      device_type: str,
      response_regex: ResponseRegex,
  ) -> None:
    """Initializes an instance of MatterEndpoints capability.

    Args:
      device_name: Name of the device instance the capability is attached to.
      node_id_getter: Getter method for Matter node ID of the commissioned end
        device.
      shell_fn: Bound 'shell' method of the device class instance.
      shell_with_regex: Bound 'shell_with_regex' method of the device class
        instance.
      matter_controller: An instance of MatterController capability.
      device_type: Type of the device instance.
      response_regex: Regex of each response from CHIP tool.
    """
    super().__init__(
        device_name=device_name,
        read=matter_controller.read,
        write=matter_controller.write,
        send=matter_controller.send)

    self._matter_controller = matter_controller
    self._node_id_getter = node_id_getter
    self._shell_fn = shell_fn
    self._shell_with_regex = shell_with_regex
    self._device_type = device_type
    self._response_regex = response_regex

  @classmethod
  def get_sub_capability_flavors(
      cls
  ) -> set[type[Union[endpoint_base.EndpointBase, cluster_base.ClusterBase]]]:
    """Returns the flavors of sub-capabilities used by this capability.

    Capabilities normally don't have sub-capabilities, but this is required for
    the matter_endpoints capability.
    """
    return set(
        matter_endpoints_and_clusters.SUPPORTED_ENDPOINTS +
        matter_endpoints_and_clusters.SUPPORTED_CLUSTERS_CHIP_TOOL +
        (unsupported_endpoint.UnsupportedEndpoint,))

  def get_supported_endpoint_ids(self) -> list[int]:
    """Returns the list of supported endpoint ids on the device."""
    # Descriptor cluster does not explicitly list root node endpoint.
    endpoint_ids = [matter_endpoints_base.ROOT_NODE_ENDPOINT_ID]
    response = self._shell_fn(
        _COMMANDS["READ_DESCRIPTOR_PARTS_LIST"].format(
            chip_tool=self._matter_controller.path,
            endpoint_id=matter_endpoints_base.ROOT_NODE_ENDPOINT_ID,
            node_id=self._node_id_getter(),
            tracing_enable=_CHIP_TOOL_TRACING_ENABLED,
        )
    )
    endpoints = re.findall(
        self._response_regex["DESCRIPTOR_ATTRIBUTE_RESPONSE"], response
    )
    if not endpoints:
      return endpoint_ids
    endpoint_ids += [
        int(endpoint.replace(" (unsigned)", ""))
        for endpoint in endpoints[0].split(",")]
    return endpoint_ids

  def get_endpoint_class_and_device_type_id(
      self, endpoint_id: int) -> tuple[type[endpoint_base.EndpointBase], int]:
    """Gets the endpoint class and device type ID by the given endpoint id.

    Args:
      endpoint_id: The given endpoint ID on the device.

    Returns:
      The endpoint class module (or UnsupportedEndpoint if the endpoint is not
      yet supported in GDM) and the device type ID.

    Raises:
      DeviceError when the device type ID of this endpoint cannot be obtained.
    """
    device_type_id = None
    command = _COMMANDS["READ_DESCRIPTOR_DEVICE_TYPE_LIST"].format(
        chip_tool=self._matter_controller.path,
        endpoint_id=endpoint_id,
        node_id=self._node_id_getter(),
        tracing_enable=_CHIP_TOOL_TRACING_ENABLED,
    )
    output = self._shell_with_regex(
        command, self._response_regex["DEVICE_TYPE_LIST_RESPONSE"]
    )
    if output.isdigit():
      device_type_id = int(output)
    if device_type_id is None:
      raise errors.DeviceError(
          f"Failed to get device type from endpoint {endpoint_id} on "
          f"{self._device_name}")

    endpoint_class = (
        matter_endpoints_and_clusters.MATTER_DEVICE_TYPE_ID_TO_CLASS.
        get(device_type_id, unsupported_endpoint.UnsupportedEndpoint))

    return endpoint_class, device_type_id

  def get_supported_clusters(
      self, endpoint_id: int) -> set[type[cluster_base.ClusterBase]]:
    """Retrieves the supported clusters from the given endpoint ID.

    Args:
      endpoint_id: The given endpoint ID on the device.

    Returns:
      Set of supported cluster capability classes.
    """
    response = self._shell_fn(
        _COMMANDS["READ_DESCRIPTOR_SERVER_LIST"].format(
            chip_tool=self._matter_controller.path,
            endpoint_id=endpoint_id,
            node_id=self._node_id_getter(),
            tracing_enable=_CHIP_TOOL_TRACING_ENABLED,
        )
    )
    clusters_raw = re.findall(
        self._response_regex["DESCRIPTOR_ATTRIBUTE_RESPONSE"], response
    )
    if not clusters_raw:
      return set()
    if self._device_type == "chip_tool":
      # Example response
      # [1653012222.680056][1030572:1030577] [DMG] Data = 44,
      clusters = clusters_raw
    else:
      # Example response
      # [1653012051.834362][1030538:1030543] [DMG] Data = [
      # [1653012051.834396][1030538:1030543] [DMG]         1 (unsigned),
      # [1653012051.834439][1030538:1030543] [DMG] ],
      clusters = clusters_raw[0].split(",")
    cluster_classes = []
    for cluster in clusters:
      cluster_id = int(cluster.replace(" (unsigned)", ""))
      if (cluster_id in
          matter_endpoints_and_clusters.CLUSTER_ID_TO_CLASS_CHIP_TOOL):
        cluster_classes.append(matter_endpoints_and_clusters
                               .CLUSTER_ID_TO_CLASS_CHIP_TOOL[cluster_id])
      else:
        logger.warning(f"Cluster class for cluster ID {hex(cluster_id)} has not"
                       " been implemented yet.")

    return set(cluster_classes)
