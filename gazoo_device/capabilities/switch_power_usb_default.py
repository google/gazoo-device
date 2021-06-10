# Copyright 2021 Google LLC
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

"""Implementation of the switch_power_usb_default capability."""
from typing import Any, Callable, Dict

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import switch_power_base

logger = gdm_logger.get_logger()

SYNC = "sync"
OFF = "off"


class SwitchPowerUsbDefault(switch_power_base.SwitchPowerBase):
  """Definition of the switch_power_usb_default capability."""
  _REQUIRED_COMMANDS = ["POWER_ON", "POWER_OFF", "GET_MODE"]
  _REQUIRED_REGEXS = ["GET_MODE_REGEX"]

  def __init__(self,
               shell_fn: Callable[..., Any],
               regex_shell_fn: Callable[..., Any],
               command_dict: Dict[str, str],
               regex_dict: Dict[str, str],
               device_name: str,
               serial_number: str,
               total_ports: int):
    """Initializes an instance of SwitchPowerUsbDefault capability.

    Args:
      shell_fn: shell() function of the device.
      regex_shell_fn: shell_with_regex() function of the device.
      command_dict: A dictionary containing the command used for each method.
      regex_dict: Response regexes to use to when identifying command responses.
      device_name: name of the device this capability is attached to.
      serial_number: serial number of device this capability is attached to.
      total_ports: Number of ports on the device.
    """
    super().__init__(device_name=device_name)
    self._shell_fn = shell_fn
    self._regex_shell_fn = regex_shell_fn
    self._command_dict = command_dict
    self._regex_dict = regex_dict
    self._serial_number = serial_number
    self._total_ports = total_ports

    self.validate_required_keys(self._REQUIRED_COMMANDS, command_dict,
                                "command_dict")
    self.validate_required_keys(self._REQUIRED_REGEXS, regex_dict, "regex_dict")

  @decorators.PersistentProperty
  def supported_modes(self):
    """Get the USB power modes supported by the USB hub."""
    return [OFF, SYNC]

  @decorators.PersistentProperty
  def total_ports(self):
    """Get the number of device ports.

    Returns:
        int: the number of device ports
    """
    return int(self._total_ports)

  def get_all_ports_mode(self):
    """Gets the USB mode for all ports on this hub.

    Returns:
      list: Returns a list of port modes with port number as index.
    """
    mode_list = []
    for port in range(1, self._total_ports + 1):
      mode_list.append(self.get_mode(port=port))
    return mode_list

  def get_mode(self, port):
    """Get the USB mode for specified port.

    Args:
      port (int): The port to get mode.

    Returns:
        str: USB port mode settings 'off', 'sync'

    Raises:
      DeviceError: invalid port.
    """
    port = int(port)
    self._validate_port("get_mode", port)
    cmd = self._command_dict["GET_MODE"].format(self._serial_number, port)
    result = self._regex_shell_fn(
        command=cmd,
        regex=self._regex_dict["GET_MODE_REGEX"],
        command_name="get_mode",
        tries=5)
    if "ON" in result.upper():
      return SYNC
    return OFF

  @decorators.CapabilityLogDecorator(logger)
  def power_on(self, port, data_sync=True):
    """This command powers on the port specified.

    Args:
        port (int): identifying which hub port to power on
        data_sync (bool): Ignored in default implementation

    Raises:
       DeviceError: if data_sync is False or if a valid port is not
       provided.
    """
    port = int(port)
    if not data_sync:
      raise errors.DeviceError(
          "Device {} {} power_on failed. "
          "data_sync=False not supported in default implementation.".format(
              self._device_name, self._serial_number))

    self._validate_port("power_on", port)
    logger.debug("{} Powering on usb port {}".format(self._device_name, port))
    self._shell_fn(self._command_dict["POWER_ON"].format(
        self._serial_number, port))

  @decorators.CapabilityLogDecorator(logger)
  def power_off(self, port):
    """This command powers off the port specified.

    Args:
        port (int): identifies which hub port to power off

    Raises:
       DeviceError: if operation failed or if a valid port is not provided.
    """
    port = int(port)
    self._validate_port("power_off", port)
    logger.debug("{} Powering off usb port {}".format(self._device_name, port))
    self._shell_fn(self._command_dict["POWER_OFF"].format(
        self._serial_number, port))

  @decorators.CapabilityLogDecorator(logger)
  def set_all_ports_mode(self, mode):
    """Sets all USB hub ports to the mode specified.

    Args:
      mode (str): USB hub mode to set. The mode must be in one of the
        supported_modes Example, 'off', 'sync'

    Raises:
      DeviceError: invalid mode.
    """
    self._validate_mode(mode)
    for port in range(1, self._total_ports + 1):
      self.set_mode(mode=mode, port=port)

  @decorators.CapabilityLogDecorator(logger)
  def set_mode(self, mode, port):
    """Sets the specified USB port to the mode specified.

    Args:
      mode (str): USB mode to set. Options: 'off', 'sync'
      port (int): The port to set.

    Raises:
      DeviceError: invalid mode or port.
    """
    port = int(port)
    mode = mode.lower()
    self._validate_port("set_mode", port)
    self._validate_mode(mode)

    if mode in OFF:
      self.power_off(port)
    else:  # "sync"
      self.power_on(port)

  def _validate_mode(self, mode):
    """Verify mode given resides in the valid mode list.

    Args:
        mode (str): mode e.g. 'off', 'sync'

    Raises:
        DeviceError: if mode given is not found in the valid mode list.
    """
    if mode not in list(self.supported_modes):
      raise errors.DeviceError(
          "Mode {} not found in supported modes {!r}".format(
              mode, self.supported_modes))

  def _validate_port(self, method_name, port):
    """Verify port given is within the bounds defined.

    Args:
        method_name (str): name of method requesting validation.
        port (int): value provided must be >= 1 and <= _total_ports.

    Raises:
        DeviceError: if port given is not within the bounds defined.
    """
    if not port or port > self._total_ports:
      raise errors.DeviceError("Device {} {} failed. "
                               "Port {} is invalid.".format(
                                   self._device_name, method_name, port))
