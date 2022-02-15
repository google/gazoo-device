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
"""SNMP implementation of switch_power."""
import re
import subprocess
from typing import List
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import switch_power_base
from typing_extensions import Literal

logger = gdm_logger.get_logger()

PRIVATE_COMMUNITY = "private"

_GET = "snmpget"
_SET = "snmpset"

_SNMP_TIMEOUT_S = 10

# 1.3.6.1.2.1.2.2.1.7 is the SNMP object identifier (OID) for ifAdminStatus.
# This OID specifies the SNMP endpoint for the status of the switch's ports.
# Querying this OID will list all possible ports and their status.
# ref: https://oidref.com/1.3.6.1.2.1.2.2.1.7
_GET_MODE_SNMP_COMMAND = (
    "{snmp_command} -v 2c -c {community} {ip}:161 1.3.6.1.2.1.2.2.1.7.{port}")
_SET_MODE_SNMP_COMMAND = _GET_MODE_SNMP_COMMAND + " i {mode}"
_MODE_RESPONSE_REG_EX = r".+INTEGER:.+?(\d+)"

# The ifAdminStatus endpoint defines port statuses as 1 or 2.
# The states map like: 1 = ON and 2 = OFF.
_ON = "ON"
_OFF = "OFF"
_GET_MODE_MAPPING = {"1": _ON, "2": _OFF}
_SET_MODE_MAPPING = {_ON: "1", _OFF: "2"}


class SwitchPowerSnmp(switch_power_base.SwitchPowerBase):
  """Switch power flavor for snmp switches."""

  def __init__(self,
               device_name: str,
               ip_address: str,
               total_ports: int,
               community: str = PRIVATE_COMMUNITY):
    """Initializes switch power with SNMP capability.

    Args:
      device_name: Name of the device attached to this capability.
      ip_address: Function to get port status.
      total_ports: Number of network ports present on the device.
      community: Community string configured on switch.
    """
    super().__init__(device_name=device_name)
    self._ip_address = ip_address
    self._total_ports = total_ports
    self._community = community

  @decorators.PersistentProperty
  def supported_modes(self) -> List[str]:
    """Get the power modes supported by the switch."""
    return [_ON, _OFF]

  @decorators.PersistentProperty
  def total_ports(self) -> int:
    """Number of device ports."""
    return int(self._total_ports)

  def get_mode(self, port: int) -> str:
    """Gets the mode for the specified port.

    Args:
      port: Use this port to get the mode.

    Returns:
      Port mode settings "OFF", "ON".

    Raises:
      DeviceError: Raised if passed invalid port.
    """
    self._validate_port(port)
    get_mode_command = _GET_MODE_SNMP_COMMAND.format(
        snmp_command=_GET,
        community=self._community,
        ip=self._ip_address,
        port=port)

    # A command that query's port 1's status looks like:
    # "snmpget -v 2c -c private 123.45.67.89:161 1.3.6.1.2.1.2.2.1.7.1"
    # And its expected response should look like:
    # "iso.3.6.1.2.1.2.2.1.7.1 = INTEGER: 1"
    response = subprocess.check_output(
        get_mode_command.split(), text=True, timeout=_SNMP_TIMEOUT_S)

    match = re.search(_MODE_RESPONSE_REG_EX, response)
    if match and match.group(1) in _GET_MODE_MAPPING.keys():
      return _GET_MODE_MAPPING[match.group(1)]
    raise errors.DeviceError(f"{self._device_name} failed to get port status"
                             f"with command: {get_mode_command}\n"
                             f"Unexpected output: {response}")

  @decorators.CapabilityLogDecorator(logger)
  def set_mode(self, mode: Literal[_ON, _OFF], port: int):
    """Sets the given port to the mode specified.

    Args:
      mode: Mode to set. Options: "OFF", "ON".
      port: The port to set.

    Raises:
      DeviceError: Raised if passed an invalid port or mode.
    """
    self._validate_port(port)
    if mode.upper() not in list(self.supported_modes):
      raise ValueError(f"Attempting to set invalid mode: {mode}. "
                       f"Valid modes are: {self.supported_modes()}.")

    mode = mode.upper()
    set_mode_command = _SET_MODE_SNMP_COMMAND.format(
        snmp_command=_SET,
        community=self._community,
        ip=self._ip_address,
        port=port,
        mode=_SET_MODE_MAPPING[mode])

    # A command that sets port 1's mode to OFF looks like:
    # "snmpset -v 2c -c private 123.45.67.89:161 1.3.6.1.2.1.2.2.1.7.1 i 2"
    # And it's expected response should look like:
    # "iso.3.6.1.2.1.2.2.1.7.1 = INTEGER: 2"
    response = subprocess.check_output(
        set_mode_command.split(), text=True, timeout=_SNMP_TIMEOUT_S)

    match = re.search(_MODE_RESPONSE_REG_EX, response)
    if not match or match.group(1) != _SET_MODE_MAPPING[mode]:
      raise errors.DeviceError(
          f"{self._device_name} Failed to turn {mode.lower()} "
          f"the port using command: '{set_mode_command}'. "
          f"Output: '{response}'")

  @decorators.CapabilityLogDecorator(logger)
  def power_off(self, port: int):
    """This command powers off the port specified.

    Args:
      port: Identifies which hub port to power off.
    """
    self.set_mode(_OFF, port)

  @decorators.CapabilityLogDecorator(logger)
  def power_on(self, port: int):
    """This command powers on the port specified.

    Args:
      port: Identifies which hub port to power on.
    """
    self.set_mode(_ON, port)

  def _validate_port(self, port: int):
    """Ensures port is a valid port number.

    Args:
      port: Device port number.

    Raises:
      DeviceError: if input port is not valid.
    """
    if port <= 0 or port > self._total_ports:
      raise errors.DeviceError(
          f"Port {port} does not exist on {self._device_name}.")
