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

"""Implementation of the switch_power_dli_powerswitch capability."""
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import switch_power_base

logger = gdm_logger.get_logger()

OFF = "off"
ON = "on"


class SwitchPowerDliPowerswitch(switch_power_base.SwitchPowerBase):
  """Definition of the switch_power_dli_powerswitch capability."""
  _REQUIRED_COMMANDS = ["ADJUST_PORTS_MODE"]
  _REQUIRED_HEADERS = ["GET_PROP", "SET_PROP"]

  def __init__(self, http_fn, ip_address, command_dict, headers_dict,
               device_name, total_ports):
    """Create an instance of the powerswitch power capability.

    Args:
        http_fn (func): A function to send GET and PUT http commands
        ip_address (str): The IP address of the Powerswitch.
        command_dict (dict): A dictionary containing the command used for
          each method.
                             The dictionary must contain the following keys:
                               - ADJUST_PORTS_MODE
        headers_dict (dict): A dictionary containg the required headers for
          the HTTP requests. - GET_PROP - SET_PROP
        device_name (str): name of the device this capability is attached
          to.
        total_ports (int): number of ports on device
    """

    super().__init__(device_name=device_name)
    self._http_fn = http_fn
    self._ip_address = ip_address
    self._command_dict = command_dict
    self._headers_dict = headers_dict
    self._total_ports = total_ports

    self.validate_required_keys(self._REQUIRED_COMMANDS, command_dict,
                                "command_dict")
    self.validate_required_keys(self._REQUIRED_HEADERS, headers_dict,
                                "headers_dict")

  @decorators.PersistentProperty
  def supported_modes(self):
    """Get the Powerswitch power modes supported by the dli_powerswitch."""
    return [OFF, ON]

  @decorators.PersistentProperty
  def total_ports(self):
    """Get the number of device ports.

    Returns:
        int: the number of device ports
    """
    return int(self._total_ports)

  def get_all_ports_mode(self):
    """Get mode of all the device ports.

    Returns:
        list: a list of the all the ports mode.
    """
    response = self._http_fn(
        "GET",
        self._command_dict["ADJUST_PORTS_MODE"].format(
            "all;", ip=self._ip_address),
        headers=self._headers_dict["GET_PROP"])
    ports_value = response.split(",")
    ports_mode = [ON if port == "true" else OFF for port in ports_value]
    return ports_mode

  def get_mode(self, port):
    """Get mode of the specified port.

    Args:
        port (int): device port number

    Raises:
        DeviceError: if port is None, port < 0, or port >= total_ports

    Returns:
        str: mode of specified port, either 'on' or 'off'.
    """
    self._validate_port("get_mode", port)
    response = self._http_fn(
        "GET",
        self._command_dict["ADJUST_PORTS_MODE"].format(
            "=" + str(port), ip=self._ip_address),
        headers=self._headers_dict["GET_PROP"])
    if response == "true":
      return ON
    else:
      return OFF

  @decorators.CapabilityLogDecorator(logger)
  def power_on(self, port):
    """Powers on the specified port.

    Args:
        port (int): device port number

    Raises:
        DeviceError: if port is None, port < 0, or port >= total_ports
    """
    self._validate_port("power_on", port)
    logger.debug("{} Powering on powerswitch port {}".format(
        self._device_name, port))
    self._http_fn(
        "POST",
        self._command_dict["ADJUST_PORTS_MODE"].format(
            "=" + str(port), ip=self._ip_address),
        headers=self._headers_dict["SET_PROP"],
        data={"value": "true"})

  @decorators.CapabilityLogDecorator(logger)
  def power_off(self, port):
    """Powers off the specified port.

    Args:
        port (int): device port number

    Raises:
        DeviceError: if port is None, port < 0, or port >= total_ports
    """
    self._validate_port("power_off", port)
    logger.debug("{} Powering off powerswitch port {}".format(
        self._device_name, port))
    self._http_fn(
        "POST",
        self._command_dict["ADJUST_PORTS_MODE"].format(
            "=" + str(port), ip=self._ip_address),
        headers=self._headers_dict["SET_PROP"],
        data={"value": "false"})

  @decorators.CapabilityLogDecorator(logger)
  def set_mode(self, mode, port):
    """Sets the given Powerswitch port to the mode specified.

    Args:
        mode (str): mode to set Powerswitch ports to. e.g. 'off', 'on'
        port (int): the port to set.

    Raises:
        DeviceError: invalid mode.
    """
    self._validate_mode(mode)
    if mode == ON:
      self.power_on(port=port)
    else:
      self.power_off(port=port)

  @decorators.CapabilityLogDecorator(logger)
  def set_all_ports_mode(self, mode):
    """Set all device ports to the specified mode.

    Args:
        mode (str): Mode to set all Powerswitch ports to. Valid modes are
          "on" or "off".

    Raises:
        DeviceError: if input mode is not either 'on' or 'off'
    """
    self._validate_mode(mode)
    if mode == ON:
      data_value = "true"
    else:
      data_value = "false"

    self._http_fn(
        "POST",
        self._command_dict["ADJUST_PORTS_MODE"].format(
            "all;", ip=self._ip_address),
        headers=self._headers_dict["SET_PROP"],
        data={"value": data_value})

  def _validate_mode(self, mode):
    """Verify mode given resides in the valid mode list.

    Args:
        mode (str): mode e.g. 'off', 'on'

    Raises:
        DeviceError: if mode given is not found in the valid mode list.
    """
    if mode not in list(self.supported_modes):
      raise errors.DeviceError(
          "Mode {} not found in supported modes {!r}".format(
              mode, self.supported_modes))

  def _validate_port(self, method_name, port):
    """Ensure port is a valid port number.

    Args:
        method_name(str): name of the method where _validate_port is being
          called
        port (int): device port number

    Raises:
         DeviceError: if input port is not valid
    """
    if port is None or port <= -1 or port >= self._total_ports:
      raise errors.DeviceError("Device {} {} failed. "
                               "Port {} is invalid.".format(
                                   self._device_name, method_name, port))
