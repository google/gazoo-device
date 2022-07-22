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
from typing import Callable, List, Set, Tuple, Type

from gazoo_device import gdm_logger
from gazoo_device.capabilities import matter_endpoints_and_clusters
from gazoo_device.capabilities.interfaces import matter_controller_base
from gazoo_device.capabilities.interfaces import matter_endpoints_base
from gazoo_device.capabilities.matter_clusters.interfaces import cluster_base
from gazoo_device.capabilities.matter_endpoints import unsupported_endpoint
from gazoo_device.capabilities.matter_endpoints.interfaces import endpoint_base
import immutabledict

logger = gdm_logger.get_logger()

_COMMANDS = immutabledict.immutabledict({
    "READ_DESCRIPTOR_PARTS_LIST":
        "{chip_tool} descriptor read parts-list {node_id} {endpoint_id}",
    "READ_DESCRIPTOR_SERVER_LIST":
        "{chip_tool} descriptor read server-list {node_id} {endpoint_id}",
    "READ_DESCRIPTOR_DEVICE_LIST":
        "{chip_tool} descriptor read device-list {node_id} {endpoint_id}",
})

_REGEXES = immutabledict.immutabledict({
    "DESCRIPTOR_ATTRIBUTE_RESPONSE": r"CHIP:DMG:\s+Data = (\w+)",
    "DEVICE_LIST_RESPONSE": r"CHIP:TOO:\s+Type: (\d+)",
})


class MatterEndpointsAccessorChipTool(matter_endpoints_base.MatterEndpointsBase
                                     ):
  """Capability for accessing the Matter endpoint instances via chip-tool."""

  _SUPPORTED_ENDPOINTS = matter_endpoints_and_clusters.SUPPORTED_ENDPOINTS_CHIP_TOOL

  def __init__(
      self,
      device_name: str,
      node_id_getter: Callable[[], int],
      shell_fn: Callable[..., str],
      shell_with_regex: Callable[..., str],
      matter_controller: matter_controller_base.MatterControllerBase,
  ) -> None:
    """Initializes an instance of MatterEndpoints capability.

    Args:
      device_name: Name of the device instance the capability is attached to.
      node_id_getter: Getter method for Matter node ID of the commissioned
        end device.
      shell_fn: Bound 'shell' method of the device class instance.
      shell_with_regex: Bound 'shell_with_regex' method of the device class
        instance.
      matter_controller: An instance of MatterController capability.
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

  def get_supported_endpoint_ids(self) -> List[int]:
    """Returns the list of supported endpoint ids on the device."""
    response = self._shell_fn(_COMMANDS["READ_DESCRIPTOR_PARTS_LIST"].format(
        chip_tool=self._matter_controller.path,
        endpoint_id=matter_endpoints_base.ROOT_NODE_ENDPOINT_ID,
        node_id=self._node_id_getter()))
    endpoints = re.findall(_REGEXES["DESCRIPTOR_ATTRIBUTE_RESPONSE"], response)
    return [int(endpoint) for endpoint in endpoints]

  def get_endpoint_class_and_device_type_id(
      self, endpoint_id: int) -> Tuple[Type[endpoint_base.EndpointBase], int]:
    """Gets the endpoint class and device type ID by the given endpoint id.

    Args:
      endpoint_id: The given endpoint ID on the device.

    Returns:
      The endpoint class module (or UnsupportedEndpoint if the endpoint is not
      yet supported in GDM) and the device type ID.
    """
    command = _COMMANDS["READ_DESCRIPTOR_DEVICE_LIST"].format(
        chip_tool=self._matter_controller.path,
        endpoint_id=endpoint_id,
        node_id=self._node_id_getter())
    device_type_id = int(
        self._shell_with_regex(command, _REGEXES["DEVICE_LIST_RESPONSE"]))

    endpoint_class = (
        matter_endpoints_and_clusters.MATTER_DEVICE_TYPE_ID_TO_CLASS_CHIP_TOOL.
        get(device_type_id, unsupported_endpoint.UnsupportedEndpoint))

    return endpoint_class, device_type_id

  def get_supported_clusters(
      self, endpoint_id: int) -> Set[Type[cluster_base.ClusterBase]]:
    """Retrieves the supported clusters from the given endpoint ID.

    Args:
      endpoint_id: The given endpoint ID on the device.

    Returns:
      Set of supported cluster capability classes.
    """
    response = self._shell_fn(_COMMANDS["READ_DESCRIPTOR_SERVER_LIST"].format(
        chip_tool=self._matter_controller.path,
        endpoint_id=endpoint_id,
        node_id=self._node_id_getter()))
    clusters = map(
        int, re.findall(_REGEXES["DESCRIPTOR_ATTRIBUTE_RESPONSE"], response))

    cluster_classes = []
    for cluster in clusters:
      if cluster in matter_endpoints_and_clusters.CLUSTER_ID_TO_CLASS_CHIP_TOOL:
        cluster_classes.append(matter_endpoints_and_clusters
                               .CLUSTER_ID_TO_CLASS_CHIP_TOOL[cluster])
      else:
        logger.warning(f"Cluster class for cluster ID {hex(cluster)} has not "
                       "been implemented yet.")

    return set(cluster_classes)
