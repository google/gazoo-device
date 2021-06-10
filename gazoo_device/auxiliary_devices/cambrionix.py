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

"""Cambrionix smart hub module.

This module contains APIs for interfacing with a Cambrionix smart hub device.

The following Cambrionix devices are currently supported::

    PP8S - A commercial quality 8 port smart hub device
    PP15S - A commercial quality 15 port smart hub device
    U16S - An uncased 16 port smart hub device

PP8S - Also known as the PowerPad 8S has 8 ports diagrammed below::

    XX      xxx
    Switch  Power
    xxx Host Port    --- Empty
    --- Empty        --- Empty
    --- Empty        --- Empty
    --- Empty        --- Empty
    xxx Port 1       xxx Port 5
    xxx Port 2       xxx Port 6
    xxx Port 3       xxx Port 7
    xxx Port 4       xxx Port 8

PP15S - Also known as the PowerPad 15S has 15 ports diagrammed below::

    XX      xxx
    Switch  Power

    xxx Host Port    xxx Port 8
    xxx Port 1       xxx Port 9
    xxx Port 2       xxx Port 10
    xxx Port 3       xxx Port 11
    xxx Port 4       xxx Port 12
    xxx Port 5       xxx Port 13
    xxx Port 6       xxx Port 14
    xxx Port 7       xxx Port 15

U16S - An uncased 16 port OEM device::

    xxx     xxx     xxx     xxx
    Port 1  Port 2  Port 3  Port 4                     xxx Host Port

    xxx     xxx     xxx     xxx                         X GND
    Port 5  Port 6  Port 7  Port 8                      X Power
                                                        X GPIO Pins?
    xxx     xxx     xxx     xxx                         X
    Port 9  Port 10 Port 11 Port 12                     X

    xxx     xxx     xxx     xxx         xxx          xxx
    Port 13 Port 14 Port 15 Port 16   Expansion 1  Expansion 2

Each of the above devices offers a serial port that can be used to control
the Cambrionix device. The code below accesses this serial port to allow
for controlling the device. Access the serial port using the following
serial port parameters::

    Baud Rate: 115200
    Data Bits: 8
       Parity: None
    Stop Bits: 1

Typical commands::

    help   - Display all available commands
    health - Display the health of the Cambrionix device
    l      - Live view of all active ports (also allows simple toggling of
    ports)
    mode   - Allows changing mode of a particular port (o-off, c-charge, s-sync)
    state  - Display the state of a particular port
    system - Display system information of the Cambrionix device

"""
import fcntl
import os
import select
import time
import typing

from gazoo_device import decorators
from gazoo_device import detect_criteria
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.base_classes import auxiliary_device
from gazoo_device.capabilities import switch_power_usb_with_charge
from gazoo_device.utility import deprecation_utils
from gazoo_device.utility import usb_config
from gazoo_device.utility import usb_utils
import serial

logger = gdm_logger.get_logger()

COMMANDS = {
    "CLEAR_ERROR_FLAGS": "cef",
    "CLEAR_REBOOTED_FLAG": "crf",
    "LIMITS": "limits",
    "STATE": "state",
    "GET_MODE": "state {}",
    "SYSTEM_STATUS": "system",
    "REBOOT_WATCHDOG": "reboot watchdog",
    "REBOOT": "reboot",
    "SET_MODE": "mode {} {}"
}

REGEXES = {
    "GET_MODE_REGEX": r"\s*\d{1,2},\s+\w+,\s+([A-Z0-9\s]+),",
}

TIMEOUTS = {
    "OPEN":
        30,  # Waits for other interactions. (reboot with watchdog=True takes ~16
    # seconds and is likely the longest running command)
    "PING": 3,
    "REBOOT": 3,
    "REBOOT_WATCHDOG": 15
}

_REBOOT_METHODS = ["watchdog", "shell"]


class Cambrionix(auxiliary_device.AuxiliaryDevice):
  """This class serves as a Python interface to a Cambrionix hub.

  Attributes: Hub Device Base Class
  """
  COMMUNICATION_TYPE = "SerialComms"
  DETECT_MATCH_CRITERIA = {
      detect_criteria.SerialQuery.product_name:
          "(ft230x basic uart)|(ps15-usb3)"
  }
  DEVICE_TYPE = "cambrionix"
  _OWNER_EMAIL = "gdm-authors@google.com"
  _instances = {}

  def __new__(cls, manager, device_config, log_file_name, log_directory):
    """Returns the same object for the same serial_port_path.

    Args:
        manager(manager.Manager): Manager object for this device instance.
        device_config(dict): dict of two dicts, 'optional' device parameters
          and 'persistent' device parameters.
        log_file_name(str): file name in the log directory for device logs.
        log_directory(str): directory in which the controller will create
          the log file.

    Returns:
        Cambrionix: Instance matching serial port path

    Note:
        Instantiate a new serial_port_path if not found.
    """
    # slowly migrate away from using 'hub_port_name' but maintain backwards compatibility
    if "console_port_name" not in device_config["persistent"]:
      device_config["persistent"]["console_port_name"] = \
          device_config["persistent"]["hub_port_name"]

    identifier = device_config["persistent"]["console_port_name"]
    if identifier not in cls._instances:
      obj = super(Cambrionix, cls).__new__(cls)
      cls._instances[identifier] = obj

    return cls._instances[identifier]

  def __init__(self, manager, device_config, log_file_name, log_directory):
    """Constructor of the class Cambrionix.

    Args:
        manager(manager.Manager): Manager object for this device instance.
        device_config(dict): dict of two dicts, 'optional' device parameters
          and 'persistent' device parameters.
        log_file_name(str): file name in the log directory for device logs.
        log_directory(str): directory in which the controller will create
          the log file.

    Raises:
        DeviceError: unknown type of cambrionix
    """
    super().__init__(
        manager,
        device_config,
        log_file_name=log_file_name,
        log_directory=log_directory)
    self._commands.update(COMMANDS)
    self._regexes.update(REGEXES)
    self._timeouts.update(TIMEOUTS)
    self._serial_port = None

  def __del__(self):
    self.close()

  @decorators.health_check
  def check_clear_flags(self):
    """clear the error and reboot flags."""
    self._command(self.commands["CLEAR_ERROR_FLAGS"])
    self._command(self.commands["CLEAR_REBOOTED_FLAG"])

  @decorators.DynamicProperty
  def firmware_version(self):
    """Gets the firmware version of the hub.

    Returns:
      str: The firmware version
    """
    return self._get_system_status()["firmware"]

  @decorators.PersistentProperty
  def health_checks(self):
    """Returns list of methods to execute as health checks."""
    return [self.check_device_connected, self.check_clear_flags]

  @decorators.PersistentProperty
  def port_extension_map(self):
    """Map of usb port extensions to port numbers."""
    return usb_config.CAMBRIONIX_PORT_MAP[self.model]

  @decorators.PersistentProperty
  def total_ports(self):
    """Number of usb ports for this device."""
    return len(self.port_extension_map.keys())

  @decorators.LogDecorator(logger, level=decorators.DEBUG)
  def close(self):
    """Closes the serial port connection."""
    if self._serial_port is not None and self._serial_port.is_open:
      self._serial_port.close()

    super(Cambrionix, self).close()

  @decorators.LogDecorator(logger)
  def get_detection_info(self):
    """Gets the persistent and optional attributes of a Cambrionix.

    Returns:
      tuple: (Dict of persistent attributes, dict of optional attributes)

    Raises:
      DeviceError: if device model is not supported.

    Notes:
      persistent: model,
                  hub_port_name,
                  console_port_name,
                  total_ports,
                  ftdi_serial_number,
                  serial_number

      optional:   empty dict
    """
    persistent_dict = self.props["persistent_identifiers"]
    persistent_dict["model"] = self._get_system_hardware()
    if persistent_dict["model"] not in usb_config.CAMBRIONIX_PORT_MAP:
      raise errors.DeviceError(
          "Model {} not supported. Supported models: {}".format(
              persistent_dict["model"],
              ",".join(usb_config.CAMBRIONIX_PORT_MAP.keys())))
    persistent_dict["hub_port_name"] = self.communication_address
    persistent_dict["console_port_name"] = self.communication_address
    persistent_dict["total_ports"] = self.total_ports
    persistent_dict[
        "ftdi_serial_number"] = usb_utils.get_serial_number_from_path(
            self.communication_address)

    # Cambrionix does not have a separate serial number from the one shown
    # in the /dev/serial/by-id/... name.
    persistent_dict["serial_number"] = self.props["persistent_identifiers"][
        "ftdi_serial_number"]

    self.props["options"] = {}

    return persistent_dict, self.props["options"]

  @classmethod
  def is_connected(cls, device_config):
    """Returns true if a Cambrionix is connected to the computer, False otherwise.

    Args:
      device_config (dict): contains "persistent" dict

    Returns:
      bool: Cambrionix is connected

    Notes:
      To return True, the cambrionix_config needs to have
      "console_port_name" in its
      "persistent" dict and that path needs to exist on the computer.
    """
    if "console_port_name" in device_config["persistent"]:
      address = device_config["persistent"]["console_port_name"]
    else:
      address = device_config["persistent"]["hub_port_name"]
    return os.path.exists(address)

  @decorators.LogDecorator(logger)
  def reboot(self, no_wait=False, method="shell"):
    """Reboots the system.

    Args:
      no_wait (bool): Return before boot up is complete. Default: False.
      method (str): Method to invoke reboot. 'shell' | 'watchdog'

    Raises:
      ValueError: if method name not recognized.

    Note:
      (Terminal Command Reference v1.5 page 15).
    """
    if method.lower() not in _REBOOT_METHODS:
      raise ValueError(
          f"Method {method!r} not recognized. Supported methods: {_REBOOT_METHODS}"
      )
    if method == "watchdog":
      self._command(
          self.commands["REBOOT_WATCHDOG"],
          close_delay=self.timeouts["REBOOT_WATCHDOG"])
    else:
      self._command(
          self.commands["REBOOT"], close_delay=self.timeouts["REBOOT"])

  @decorators.LogDecorator(logger)
  def recover(self, error):
    """Attempts to recover device based on the type of error specified.

    Note: The check_device_ready method can raise a number of separate
    exceptions which are passed to this method as exception objects. The
    recovery method is chosen based on the type of the error. A list of errors
    and recovery steps follow (not all recovery steps have been implemented
    yet):

    DeviceNotResponsiveError:
        * Recovery: reboot device.

    Args:
        error (CheckDeviceReadyError): A subclass of CheckDeviceReadyError
        that will be used to identify a possible recovery solution to use.

    Raises:
        DeviceError: If device recovery fails while attempting to perform
        recovery steps.
        CheckDeviceReadyError: If there are no recovery steps available for
        the error argument, it will be re-raised directly.
    """

    if isinstance(error, errors.DeviceNotResponsiveError):
      self.reboot()
    else:
      raise error

  def shell(self,
            command,
            command_name="shell",
            timeout=None,
            port=0,
            include_return_code=False):
    """Sends command and returns response.

    Args:
        command (str): Command to send to the device.
        command_name (str): Optional identifier to use in logs for this
          command.
        timeout (float): Seconds to wait for pattern after command sent.
        port (int): not used.
        include_return_code (bool): flag indicating return code should be
          returned

    Returns:
        str or tuple: response or (response, return_code) if
        include_return_code is True.
            return_code 0 - success
            return_code -1 - error
    """
    timeout = timeout or self.timeouts["SHELL"]
    response = ""
    if include_return_code:
      return_code = 0
      try:
        response = self._command(command)
        response = self._list_to_str(response)
      except errors.DeviceError:
        return_code = -1
      return response, return_code
    response = self._command(command)
    return self._list_to_str(response)

  def shell_with_regex(self,
                       command,
                       regex,
                       regex_group=1,
                       command_name="shell",
                       raise_error=False,
                       tries=1,
                       port=0):
    """Sends a command, searches for a regex in the response, and returns a match group.

    Args:
        command (str): command to issue.
        regex (str): regular expression with one or more capturing groups.
        regex_group (int): number of regex group to return.
        command_name (str): command name to appear in log messages.
        raise_error (bool): whether or not to raise error if unable to find a
          match.
        tries (int): how many times to try executing the command before failing.
        port (int): which port to send the shell command to.

    Returns:
        str: value of the capturing group with index 'regex_group' in the match.

    Raises:
        DeviceError: if command execution fails OR couldn't find the requested
        group in any of the responses.
    """
    return self.command_with_regex(
        command,
        regex,
        self.shell,
        regex_group=regex_group,
        raise_error=raise_error,
        tries=tries,
        command_name=command_name,
        port=port)

  @decorators.CapabilityDecorator(
      switch_power_usb_with_charge.SwitchPowerUsbWithCharge)
  def switch_power(self):
    """Returns a switch_power object to send commands.

    Returns:
        object: switch_power_usb_with_charge
    """
    return self.lazy_init(
        switch_power_usb_with_charge.SwitchPowerUsbWithCharge,
        shell_fn=self.shell,
        regex_shell_fn=self.shell_with_regex,
        command_dict=self.commands,
        regex_dict=self.regexes,
        device_name=self.name,
        serial_number=self.serial_number,
        total_ports=self.total_ports)

  @decorators.PersistentProperty
  def valid_modes(self):
    return ["off", "sync", "charge"]

  def _command(self, command, close_delay=0.0):
    """Opens the control serial port and sends a command.

    Args:
      command (str): Command to send to device
      close_delay (float): Seconds to delay between command and closing
        control port

    Returns:
      list: All strings in the response (except the trailing >> prompt)

    Raises:
      DeviceError: Error in response to command.

    Note:
      Returns response. Delays closing the port afterwards if close_delay >
      0.

      With some commands (e.g. reboot), it is necessary to wait before
      closing the control serial port to prevent other GDM instances from
      accessing the control serial port.
    """
    self._open()
    try:
      self.__write_command(self._serial_port, command)
      if command.startswith("reboot"):
        return

      response = self.__get_response(self._serial_port)
      if response[0].startswith("*E"):
        raise errors.DeviceError("Device {} command failed. "
                                 "Unable to write command: {} "
                                 "to serial port: {}  Err: {!r}".format(
                                     self.name, command, self._serial_port,
                                     response[0]))
    finally:
      if close_delay > 0.0:
        time.sleep(close_delay)
      self.close()

    # Discard the last line which is the prompt
    return response[:-1]

  def _get_system_status(self):
    """Gets hardware and firmware information.

    Returns:
      dict: Information regarding the system

    Note:
      (Terminal Command Reference v1.5 page 6)
      Example output from PP8S device:
      >> system
      cambrionix PP8S 8 Port USB Charge+Sync
      Hardware: PP8S
      Firmware: 1.68
      Compiled: Feb 14 2017 17:30:26
      Group: -
      Panel ID: Absent
    """
    sysinfo_strings = self._command(self.commands["SYSTEM_STATUS"])
    sysinfo_dict = {"name": sysinfo_strings[0]}
    for line in sysinfo_strings:
      if ":" in line:
        key, value = line.split(":", 1)
        sysinfo_dict[key.lower()] = value.strip()

    return sysinfo_dict

  def _get_system_hardware(self):
    """Gets the hardware description of the hub.

    Returns:
      str: Hardware description
    """
    return self._get_system_status()["hardware"]

  def _list_to_str(self, lst):
    if isinstance(lst, list):
      lst = " ".join(map(str, lst))
    return lst

  def _open(self):
    start_time = time.time()
    error = ""
    while time.time() - start_time < self.timeouts["OPEN"]:
      try:
        if self._serial_port is None:
          # Windows is not supported due to use of fcntl.
          # Cast to Posix serial so pytype understands this.
          self._serial_port = typing.cast(
              serial.serialposix.Serial,
              serial.Serial(port=self.communication_address,
                            baudrate=115200,
                            timeout=0.1,
                            exclusive=True))
          # NEP-1852: Prevent inheritance of file descriptors to exec'd child
          # processes.
          file_descriptor = self._serial_port.fd
          flags = fcntl.fcntl(file_descriptor, fcntl.F_GETFD)
          fcntl.fcntl(file_descriptor, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)
          return
        if not self._serial_port.is_open:
          self._serial_port.open()
        return
      except Exception as err:
        error = err
    raise errors.DeviceError("Device {} open failed. "
                             "Unable to open control serial port in {} seconds"
                             "Error: {}".format(self.name,
                                                self.timeouts["OPEN"], error))

  @staticmethod
  def __write_command(serial_port, command):
    """Internal helper for writing to the hub.

    Args:
      serial_port (str): Cambrionix serial port.
      command (str): command to send to device.

    Raises:
      DeviceError: no response from device.
    """
    line_ending = "\r\n"
    ctrl_c_cmd = "\x03" + line_ending

    # Clear any existing text by sending a CTRL-C
    # command and waiting for a prompt
    serial_port.write(ctrl_c_cmd.encode("utf-8"))
    Cambrionix.__get_response(serial_port)

    if not command.endswith(line_ending):
      command += line_ending

    for char in command:
      serial_port.write(char.encode("utf-8"))
      if command.startswith("reboot") and char == "\r":
        break

      while True:
        ready = select.select([serial_port], [], [], 25)[0]
        if ready:
          if serial_port.read(1).decode("utf-8") == char:
            break
        else:
          raise errors.DeviceError("Device cambrionix write command failed. "
                                   "Read timeout on serial port: {} "
                                   "while writing command: {}".format(
                                       serial_port, command))

  @staticmethod
  def __get_response(serial_port):
    """Internal helper returning the response from the hub as a list of lines.

    Args:
      serial_port (str): Cambrionix serial port.

    Returns:
      str: response.

    Raises:
      DeviceError: Device not responding.

    Note:
      The command prompt is always this string: ">> ".
    """
    read_data = ""
    while not read_data.endswith("\n>> "):
      ready = select.select([serial_port], [], [], 25)[0]
      if ready:
        read_data += serial_port.read(serial_port.inWaiting()).decode(
            "utf-8", "replace")
      else:
        raise errors.DeviceError(
            "Device cambrionix get response failed. "
            "Read timeout on serial port: {}".format(serial_port))

    return read_data.splitlines()


deprecation_utils.add_deprecated_attributes(
    Cambrionix, [("set_mode", "switch_power.set_mode", True),
                 ("power_on", "switch_power.power_on", True),
                 ("power_off", "switch_power.power_off", True)])
