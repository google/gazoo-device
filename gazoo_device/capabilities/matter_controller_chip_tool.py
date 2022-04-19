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
"""Matter controller capability using chip-tool command.

See
https://github.com/project-chip/connectedhomeip/tree/master/examples/chip-tool
for chip-tool usage and command references.
"""

import ast
import binascii
from typing import Any, Callable, Optional, Sequence

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import matter_controller_base
import immutabledict

logger = gdm_logger.get_logger()

_CHIP_TOOL_BINARY_PATH = "/usr/local/bin/chip-tool"
_HEX_PREFIX = "hex:"

_COMMANDS = immutabledict.immutabledict({
    "READ_CLUSTER_ATTRIBUTE":
        "{chip_tool} {cluster} read {attribute} {node_id} {endpoint_id}",
    "WRITE_CLUSTER_ATTRIBUTE":
        "{chip_tool} {cluster} write {attribute} {value} {node_id} "
        "{endpoint_id}",
    "SEND_CLUSTER_COMMMAND":
        "{chip_tool} {cluster} {command} {arguments} {node_id} {endpoint_id}",
    "COMMISSION_OVER_BLE_WIFI":
        "{chip_tool} pairing ble-wifi {node_id} {ssid} {password} {setup_code} "
        "{long_discriminator}",
    "COMMISSION_OVER_BLE_THREAD":
        "{chip_tool} pairing ble-thread {node_id} {operational_dataset} "
        "{setup_code} {long_discriminator}",
    "COMMISSION_ON_NETWORK":
        "{chip_tool} pairing onnetwork {node_id} {setup_code}",
    "COMMISSION_ON_NETWORK_LONG":
        "{chip_tool} pairing onnetwork-long {node_id} {setup_code} "
        "{long_discriminator}",
    "DECOMMISSION":
        "{chip_tool} pairing unpair {node_id}",
    "CHIP_TOOL_VERSION":
        "cat ~/.matter_sdk_version",
    "WRITE_CHIP_TOOL_VERSION":
        "echo {chip_tool_version} > ~/.matter_sdk_version",
})

_REGEXES = immutabledict.immutabledict({
    "READ_CLUSTER_ATTRIBUTE_RESPONSE":
        r"CHIP:DMG:\s+Data = (\w+)",
    "WRITE_CLUSTER_ATTRIBUTE_RESPONSE":
        r"CHIP:DMG:\s+status = (0[xX][0-9a-fA-F]+)",
    "SEND_CLUSTER_COMMAND_RESPONSE":
        r"Received Command Response Status for Endpoint=\d+ "
        r"Cluster=0[xX][0-9a-fA-F_]+ Command=0[xX][0-9a-fA-F_]+ "
        r"Status=(0[xX][0-9a-fA-F]+)",
    "COMMAND_FAILURE":
        r"Run command failure: (.*)",
    "COMMISSION_SUCCESS":
        "(CHIP:TOO: Device commissioning completed with success)",
    "DECOMMISSION_COMPLETE":
        "(CHIP:DL: System Layer shutdown)",
})

_TIMEOUTS = immutabledict.immutabledict({
    "COMMISSION": 60,
    "SEND_CLUSTER_COMMAND": 30,
})


def _str_to_hex(value: str) -> str:
  """Formats a string into chip-tool compatible CLI argument.

  If the string starts with "hex:" prefix, then this function
  returns the value as is. Otherwise, the string is converted
  into its two-digit hex numbers form and prefixed with "hex:".
  For example, "password" is converted to "hex:70617373776f7264".

  See
  https://github.com/project-chip/connectedhomeip/tree/master/examples/chip-tool#using-the-client-to-commission-a-device
  for example usage.

  Args:
    value: The string to be converted.

  Returns:
    Value in its two-digit hex numbers form with "hex:" prefix.
  """
  if value.startswith(_HEX_PREFIX):
    return value

  hex_str = binascii.hexlify(str.encode(value))
  return f"{_HEX_PREFIX}{hex_str.decode()}"


class MatterControllerChipTool(matter_controller_base.MatterControllerBase):
  """Matter controller capability using chip-tool CLI commands."""

  def __init__(self,
               device_name: str,
               shell_fn: Callable[..., str],
               regex_shell_fn: Callable[..., str],
               send_file_to_device: Callable[[str, str], None],
               chip_tool_path: str = _CHIP_TOOL_BINARY_PATH):
    """Creates an instance of MatterControllerChipTool capability.

    Args:
      device_name: Name of the device this capability is attached to.
      shell_fn: Bound 'shell' method of the device class instance.
      regex_shell_fn: Bound 'shell_with_regex' method of the device class
        instance.
      send_file_to_device: Bound 'send_file_to_device' method of the device's
        file transfer capability instance.
      chip_tool_path: Path to chip-tool binary on the device.
    """
    super().__init__(device_name)

    self._chip_tool_path = chip_tool_path
    self._shell_with_regex = regex_shell_fn
    self._shell = shell_fn
    self._send_file_to_device = send_file_to_device

  @decorators.DynamicProperty
  def version(self) -> str:
    """Matter SDK version of the controller."""
    return self._shell(_COMMANDS["CHIP_TOOL_VERSION"])

  @decorators.CapabilityLogDecorator(logger)
  def commission(self,
                 node_id: int,
                 setup_code: str,
                 long_discriminator: Optional[int] = None,
                 ssid: Optional[str] = None,
                 password: Optional[str] = None,
                 operational_dataset: Optional[str] = None) -> None:
    """Commissions a device into the controller's fabric.

    Commissioning protocol is based on specified arguments:
      - When operational dataset is provided, pairs the device over ble-thread.
      - When Wi-Fi SSID and password are provided, pairs the device over
        ble-wifi.
      - Otherwise, discover the devices on the network and pairs with the first
        one that matches the setup code and long discriminator if one is
        specified.

    Args:
      node_id: Node ID to assign to the node being commissioned.
      setup_code: Set up PIN code of the remote device.
      long_discriminator: Discriminator of the remote device.
      ssid: Wi-Fi SSID either as a string, or in the form hex:XXXXXXXX where the
        bytes of the SSID are encoded as two-digit hex numbers.
      password: Wi-Fi password, either as a string or as hex data.
      operational_dataset: Thread dataset in base-64. This argument is mutually
        exclusive with ssid and password.
    """
    if ssid and not password:
      raise ValueError("Wi-Fi password is not specified.")

    if operational_dataset:
      command = _COMMANDS["COMMISSION_OVER_BLE_THREAD"]
      operational_dataset = _str_to_hex(operational_dataset)
    elif ssid:
      command = _COMMANDS["COMMISSION_OVER_BLE_WIFI"]
      ssid = _str_to_hex(ssid)
      password = _str_to_hex(password)
    elif long_discriminator is not None:
      # Commission the first device found on the network with provided
      # setup code and long discriminator.
      command = _COMMANDS["COMMISSION_ON_NETWORK_LONG"]
    else:
      # Commission the first device found on the network with provided
      # setup code.
      command = _COMMANDS["COMMISSION_ON_NETWORK"]

    command = command.format(
        chip_tool=self._chip_tool_path,
        node_id=node_id,
        setup_code=setup_code,
        long_discriminator=long_discriminator,
        ssid=ssid,
        password=password,
        operational_dataset=operational_dataset,
    )
    self._shell_with_regex(
        command,
        _REGEXES["COMMISSION_SUCCESS"],
        raise_error=True,
        timeout=_TIMEOUTS["COMMISSION"])

  @decorators.CapabilityLogDecorator(logger)
  def decommission(self, node_id: int) -> None:
    """Forgets a commissioned device with the given node id.

    Args:
      node_id: Assigned node id to decommission.
    """
    command = _COMMANDS["DECOMMISSION"].format(
        chip_tool=self._chip_tool_path, node_id=node_id)
    self._shell_with_regex(
        command, _REGEXES["DECOMMISSION_COMPLETE"], raise_error=True)

  def read(self, node_id: int, endpoint_id: int, cluster: str,
           attribute: str) -> Any:
    """Reads a cluster's attribute for the given node id and endpoint.

    Only primitive attribute values (integer, float, boolean and string)
    are supported.

    Args:
      node_id: Node ID assigned to the commissioned end device.
      endpoint_id: Endpoint ID within the node to read attribute from.
      cluster: Name of the cluster to read the attribute value from.
      attribute: Name of the cluster attribute to read.

    Returns:
      Attribute value of the cluster.
    """
    command = _COMMANDS["READ_CLUSTER_ATTRIBUTE"].format(
        chip_tool=self._chip_tool_path,
        node_id=node_id,
        endpoint_id=endpoint_id,
        cluster=cluster,
        attribute=attribute,
    )
    response = self._shell_with_regex(
        command, _REGEXES["READ_CLUSTER_ATTRIBUTE_RESPONSE"], raise_error=True)

    try:
      return ast.literal_eval(response)
    except ValueError:
      if response.lower() in ["true", "false"]:
        return response.lower() == "true"
    return response

  @decorators.CapabilityLogDecorator(logger)
  def write(self, node_id: int, endpoint_id: int, cluster: str, attribute: str,
            value: Any) -> None:
    """Writes a cluster's attribute for the given node id and endpoint.

    Args:
      node_id: Node ID assigned to the commissioned end device.
      endpoint_id: Endpoint ID within the node to write attribute to.
      cluster: Name of the cluster to write the attribute value to (e.g. onoff).
      attribute: Name of the cluster attribute to write (e.g. on-time).
      value: New attribute value to update the cluster with.
    """
    command = _COMMANDS["WRITE_CLUSTER_ATTRIBUTE"].format(
        chip_tool=self._chip_tool_path,
        node_id=node_id,
        endpoint_id=endpoint_id,
        cluster=cluster,
        attribute=attribute,
        value=value,
    )
    status_code = self._shell_with_regex(
        command, _REGEXES["WRITE_CLUSTER_ATTRIBUTE_RESPONSE"], raise_error=True)
    if int(status_code, 0) != 0:
      raise errors.DeviceError(
          f"{self._device_name} '{command}' responded with a non-zero "
          f"status code: {status_code}")

  @decorators.CapabilityLogDecorator(logger)
  def send(self, node_id: int, endpoint_id: int, cluster: str, command: str,
           arguments: Sequence[Any]) -> None:
    """Sends a command to a device with the given node id and endpoint.

    Args:
      node_id: Node ID assigned to the commissioned end device.
      endpoint_id: Endpoint ID within the node to read attribute from.
      cluster: Name of the cluster to send the command to (e.g. onoff).
      command: Name of the command to send (e.g. toggle).
      arguments: Command arguments.
    """
    command = _COMMANDS["SEND_CLUSTER_COMMMAND"].format(
        chip_tool=self._chip_tool_path,
        node_id=node_id,
        endpoint_id=endpoint_id,
        cluster=cluster,
        command=command,
        arguments=" ".join(map(str, arguments)),
    )
    status_code = self._shell_with_regex(
        command,
        _REGEXES["SEND_CLUSTER_COMMAND_RESPONSE"],
        raise_error=True,
        timeout=_TIMEOUTS["SEND_CLUSTER_COMMAND"])
    if int(status_code, 0) != 0:
      raise errors.DeviceError(
          f"{self._device_name} '{command}' responded with a non-zero "
          f"status code: {status_code}")

  @decorators.CapabilityLogDecorator(logger)
  def upgrade(self, build_file: str, build_id: str) -> None:
    """Installs chip-tool binary to the controller device.

    Args:
      build_file: Path to chip-tool binary on the host machine.
      build_id: Commit SHA the chip-tool binary is built at.
    """
    self._send_file_to_device(build_file, self._chip_tool_path)
    self._shell(
        _COMMANDS["WRITE_CHIP_TOOL_VERSION"].format(chip_tool_version=build_id))
