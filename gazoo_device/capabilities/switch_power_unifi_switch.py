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

"""Implementation of the switch_power_unifi_switch capability."""
import re

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger

from gazoo_device.capabilities.interfaces import switch_power_base

logger = gdm_logger.get_logger()

TELNET_COMMANDS = {
    "ENTER_TELNET": {
        "ENTER_CMD": ["telnet localhost", "enable"],
        "ENTER_REGEX": [r"\s+>", r"\s+#"],
        "EXIT_CMD": ["exit", "exit"],
        "EXIT_REGEX": [r"\s+>", "Connection closed by foreign host"]
    },
    "ENTER_TELNET_CONFIG": {
        "ENTER_CMD": ["telnet localhost", "enable", "config"],
        "ENTER_REGEX": [r"\s+>", r"\s+#", r"\(Config\)#"],
        "EXIT_CMD": ["exit", "exit", "exit"],
        "EXIT_REGEX": [r"\s+#", r"\s+>", "Connection closed by foreign host"]
    },
    "ENTER_TELNET_PORT_CONFIG": {
        "ENTER_CMD": ["telnet localhost", "enable", "config"],
        "ENTER_REGEX": [r"\s+>", r"\s+#", r"\(Config\)#"],
        "EXIT_CMD": ["exit", "exit", "exit", "exit"],
        "EXIT_REGEX": [
            r"\(Config\)#", r"\s+#", r"\s+>",
            "Connection closed by foreign host"
        ]
    }
}

OFF = "off"
ON = "on"


class SwitchPowerUnifiSwitch(switch_power_base.SwitchPowerBase):
  """Definition of the switch_power_unifi_switch capability."""
  _REQUIRED_COMMANDS = [
      "GET_PORT_MODE", "ADJUST_PORTS_MODE", "GET_ALL_PORTS_MODE"
  ]
  _REQUIRED_REGEXS = ["GET_PORT_MODE_REGEX", "GET_ALL_PORTS_MODE_REGEX"]

  def __init__(self, device_name, command_dict, regex_dict, total_ports,
               send_and_expect_fn, send_fn):
    """Create an instance of the poe switch power capability.

    Args:
        device_name (str): Name of the device this capability is attached
          to.
        command_dict (dict): A dictionary containing the command used for
          each method.
        regex_dict (dict): A dictionary containing the Regex used to
          validate device states or command success.
        total_ports (int): Total number of device ports.
        send_and_expect_fn (func): send_and_expect method of Switchboard
          capability.
        send_fn (func): send method of Switchboard capability.
    """

    super().__init__(device_name=device_name)
    self._command_dict = command_dict
    self._regex_dict = regex_dict
    self._total_ports = total_ports
    self._send_and_expect_fn = send_and_expect_fn
    self._send_fn = send_fn

    self.validate_required_keys(self._REQUIRED_COMMANDS, self._command_dict,
                                "command_dict")
    self.validate_required_keys(self._REQUIRED_REGEXS, self._regex_dict,
                                "regex_dict")

  @decorators.PersistentProperty
  def supported_modes(self):
    """Get the Poe switch power modes supported by the unifi_switch."""
    return [OFF, ON]

  @decorators.PersistentProperty
  def total_ports(self):
    """Get the number of device ports.

    Returns:
        int: the number of device ports
    """
    return int(self._total_ports)

  @decorators.CapabilityLogDecorator(logger)
  def power_on(self, port):
    """Powers on the specified port.

    Args:
        port (int): device port number
    """
    port = int(port)
    self._validate_port("power_on", port)
    telnet_commands = self._create_port_config_command_and_regex(port)
    logger.debug(f"{self._device_name} Powering on unifi_switch port {port}")
    self._telnet_port_config_send(
        telnet_commands=telnet_commands,
        func=self._send_fn,
        func_args=(self._command_dict["ADJUST_PORTS_MODE"].format(
            mode="auto"),))
    self._verify_mode("power_on", port, ON)

  @decorators.CapabilityLogDecorator(logger)
  def power_off(self, port):
    """Powers off the specified port.

    Args:
        port (int): device port number
    """
    port = int(port)
    self._validate_port("power_off", port)
    telnet_commands = self._create_port_config_command_and_regex(port)
    logger.debug(f"{self._device_name} Powering off unifi_switch port {port}")
    self._telnet_port_config_send(
        telnet_commands=telnet_commands,
        func=self._send_fn,
        func_args=(self._command_dict["ADJUST_PORTS_MODE"].format(
            mode="shutdown"),))
    self._verify_mode("power_off", port, OFF)

  @decorators.CapabilityLogDecorator(logger)
  def set_mode(self, mode, port):
    """Sets the given Ethernet port to the mode specified.

    Args:
        mode (str): Mode to set the specified unifi_switch port. e.g. 'off',
          'on'
        port (int): The port to set.
    Note: Not all devices support 'charge'

    Raises:
      DeviceError: invalid port, or mode.
    """
    self._validate_mode(mode)
    if mode == OFF:
      self.power_off(port)
    else:
      self.power_on(port)

  @decorators.CapabilityLogDecorator(logger)
  def set_all_ports_mode(self, mode):
    """Set all device ports to the specified mode.

    Args:
        mode (str): Mode to set all unifi_switch ports to. Valid modes are
          "on" (auto) or "off (shutdown)".
    """
    self._validate_mode(mode)
    for poe_port in range(1, self._total_ports + 1):
      self.set_mode(mode, poe_port)

  def get_mode(self, port):
    """Get mode of the specified port.

    Args:
        port (int): device port number

    Returns:
        str: mode of specified port, either 'on'(auto), 'passive24V', or
        'off'(shutdown).
    """
    port = int(port)
    self._validate_port("get_mode", port)
    response = self._telnet_config_send(
        func=self._poe_telnet_send_and_expect,
        func_args=([self._command_dict["GET_PORT_MODE"].format(port=port)],
                   [self._regex_dict["GET_PORT_MODE_REGEX"].format(port=port)]),
        func_kwargs={"regex_group": 1})

    if response == "Auto":
      return ON
    elif response == "Shutdown":
      return OFF
    else:
      return response

  def get_all_ports_mode(self):
    """Get mode of all the device ports.

    Returns:
        list: a list of the all the ports mode.
    """
    result = self._telnet_config_send(
        func=self._poe_telnet_send_and_expect,
        func_args=([self._command_dict["GET_ALL_PORTS_MODE"]],
                   [self._regex_dict["GET_ALL_PORTS_MODE_REGEX"]]),
        func_kwargs={"regex_group": 1})
    ports_status = []
    for poe_port in range(1, self._total_ports + 1):
      match = re.search(
          self._regex_dict["GET_PORT_MODE_REGEX"].format(port=poe_port), result)
      if match:
        if match.group(1) == "Auto":
          ports_status.append(ON)
        elif match.group(1) == "Shutdown":
          ports_status.append(OFF)
        else:
          ports_status.append(match.group(1))
      else:
        ports_status.append("")
    return ports_status

  def _create_port_config_command_and_regex(self, poe_port):
    """Create the port config command and regex for the specified poe_port."""
    telnet_commands = TELNET_COMMANDS["ENTER_TELNET_PORT_CONFIG"].copy()
    telnet_commands["ENTER_CMD"].append(fr'interface 0/{poe_port}')
    telnet_commands["ENTER_REGEX"].append(fr'\(Interface 0/{poe_port}\)#')
    return telnet_commands

  def _telnet_port_config_send(self,
                               telnet_commands,
                               func,
                               func_args=(),
                               func_kwargs=None):
    """Send commands at the telnet_port_config menu level."""
    if func_kwargs is None:
      func_kwargs = {}
    self._poe_telnet_send_and_expect(telnet_commands["ENTER_CMD"],
                                     telnet_commands["ENTER_REGEX"])
    func_result = func(*func_args, **func_kwargs)
    self._poe_telnet_send_and_expect(telnet_commands["EXIT_CMD"],
                                     telnet_commands["EXIT_REGEX"])
    return func_result

  def _telnet_config_send(self, func, func_args=(), func_kwargs=None):
    """Send commands at the telnet_config menu level."""
    if func_kwargs is None:
      func_kwargs = {}
    self._poe_telnet_send_and_expect(
        TELNET_COMMANDS["ENTER_TELNET_CONFIG"]["ENTER_CMD"],
        TELNET_COMMANDS["ENTER_TELNET_CONFIG"]["ENTER_REGEX"])
    func_result = func(*func_args, **func_kwargs)
    self._poe_telnet_send_and_expect(
        TELNET_COMMANDS["ENTER_TELNET_CONFIG"]["EXIT_CMD"],
        TELNET_COMMANDS["ENTER_TELNET_CONFIG"]["EXIT_REGEX"])
    return func_result

  def _telnet_send(self, func, func_args=(), func_kwargs=None):
    """Send commands at the telnet menu level."""
    if func_kwargs is None:
      func_kwargs = {}
    self._poe_telnet_send_and_expect(
        TELNET_COMMANDS["ENTER_TELNET"]["ENTER_CMD"],
        TELNET_COMMANDS["ENTER_TELNET"]["ENTER_REGEX"])
    func_result = func(*func_args, **func_kwargs)
    self._poe_telnet_send_and_expect(
        TELNET_COMMANDS["ENTER_TELNET"]["EXIT_CMD"],
        TELNET_COMMANDS["ENTER_TELNET"]["EXIT_REGEX"])
    return func_result

  def _validate_port(self, method_name, port):
    """Ensure port is a valid port number.

    Args:
        method_name(str): name of the method where _validate_port is being
          called
        port (int): device port number

    Raises:
         DeviceError: if input port is not valid
    """
    if port is None or port <= 0 or port > self._total_ports:
      raise errors.DeviceError("Device {} {} failed. "
                               "Port {} is invalid.".format(
                                   self._device_name, method_name, port))

  def _validate_mode(self, mode):
    """Verify mode given resides in the valid mode list.

    Args:
        mode (str): mode e.g. 'off', 'on'

    Raises:
        DeviceError: if mode given is not found in the valid mode list.
    """
    if mode not in list(self.supported_modes):
      raise errors.DeviceError("Mode {} not found in supported modes{}".format(
          mode, self.supported_modes))

  def _verify_mode(self, method_name, port, mode):
    """Ensure port is set to specified mode.

    Args:
        method_name(str): name of the method where _validate_port is being
          called
        port (int): device port number
        mode (str): mode of the specified port. Valid modes are 'auto' or
          'shutdown'.

    Raises:
         DeviceError: if port is not in specified mode
    """
    active_mode = self.get_mode(port)
    if active_mode != mode:
      raise errors.DeviceError(
          f"Device {self._device_name} {method_name} failed. "
          f"Mode is {active_mode} not {mode}.")

  def _poe_telnet_send_and_expect(self,
                                  commands,
                                  loglines,
                                  timeout=30.0,
                                  command_tries=1,
                                  raise_for_timeout=True,
                                  regex_group=0):
    """Helper method to send multiple send_and_expect commands during a telnet session.

    Args:
        commands (list): list of commands to send via send_and_expect.
        loglines (list): list of regex expressions to match with the
          corresponding command.
        timeout (float): timeout of send and expect.
        command_tries (int): number of times to retry the command.
        raise_for_timeout(bool): raise exception in event of timeout of
          send_and_expect.
        regex_group (int): regext match group to return.

    Returns:
        str: match of specified regex group.

    Raises:
         DeviceError: if each command doesn't have a corresponding regex.
    """
    if len(loglines) != len(commands):
      raise errors.DeviceError(
          f"The number of commands {len(commands)} does not equal "
          f"the number of loglines {len(loglines)}. "
          f"The number of commands and loglines must be equal.")
    for cmd_num in range(len(commands)):
      response = self._send_and_expect_fn(
          command=commands[cmd_num],
          pattern_list=[loglines[cmd_num]],
          timeout=timeout,
          command_tries=command_tries,
          raise_for_timeout=raise_for_timeout,
          expect_type="response")

    return response.match.group(regex_group)
