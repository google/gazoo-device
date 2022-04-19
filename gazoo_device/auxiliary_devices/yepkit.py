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

"""This module contains APIs for interfacing with a Yepkit hub device.

Use the following commands to control the On/Off of the devices connected
to the YKUSH board downstream ports.

Power down a device connected to YKUSH board downstream port 1:

$ ykushcmd -d 1

Power up a device connected to YKUSH board downstream port 1:

$ ykushcmd -u 1

To find out the serial number of a YKUSH board, connect it to the host and
execute the command:

$ ykushcmd -l

Power down a device connected to YKUSH board downstream port 2 of YKB4388:

$ ykushcmd -s YKB4388 -d 2

Power up a device connected to YKUSH board downstream port 2 of YKB4388:

$ ykushcmd -s YKB4388 -u 2

To get the current switching status (UP/DOWN) of a downstream port 2.

$ ykushcmd -g 2
"""
import subprocess

from gazoo_device import decorators
from gazoo_device import detect_criteria
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.base_classes import auxiliary_device
from gazoo_device.capabilities import switch_power_usb_default
from gazoo_device.utility import deprecation_utils
from gazoo_device.utility import host_utils

logger = gdm_logger.get_logger()

MODEL = "yepkit"
PRODUCT_ID = "f2f7"
VENDOR_ID = "04d8"
YKUSH_PORT_MAP = {"1": 1, "2": 2, "3": 3}

COMMANDS = {
    "POWER_OFF": "ykushcmd -s {} -d {}",
    "POWER_ON": "ykushcmd -s {} -u {}",
    "GET_MODE": "ykushcmd -s {} -g {}",
    "LIST_YEPKITS": "ykushcmd -l"
}

REGEXES = {
    "GET_MODE_REGEX": r"is[ ]([A-Z]+)",
}

TIMEOUTS = {}


def _check_yepkit_enabled():
  """Checks that the host has 'ykushcmd' installed.

  Raises:
    DependencyUnavailableError: if 'ykushcmd' is not installed.
  """
  if not host_utils.has_command("ykushcmd"):
    raise errors.DependencyUnavailableError("'ykushcmd' is not installed.")


class Yepkit(auxiliary_device.AuxiliaryDevice):
  """This class serves as a Python interface to a Yepkit hub."""
  COMMUNICATION_TYPE = "YepkitComms"
  DETECT_MATCH_CRITERIA = {detect_criteria.GenericQuery.ALWAYS_TRUE: True}
  DEVICE_TYPE = "yepkit"
  _MODEL = MODEL
  _OWNER_EMAIL = "gdm-authors@google.com"

  def __init__(self,
               manager,
               device_config,
               log_file_name=None,
               log_directory=None):
    """Initialize the Yepkit class with the serial port information provided.

    Args:
        manager(manager.Manager): Manager object for this device instance.
        device_config (dict): dict of two dicts, 'optional' device parameters
          and 'persistent' device parameters.
        log_file_name (str): file name in the log directory for device logs.
        log_directory (str): directory in which the controller will create
          the log file.

    Raises:
        RuntimeError: if yepkit is not enabled.
    """
    _check_yepkit_enabled()

    super().__init__(
        manager,
        device_config,
        log_file_name=log_file_name,
        log_directory=log_directory)
    self._commands.update(COMMANDS)
    self._regexes.update(REGEXES)
    self._timeouts.update(TIMEOUTS)

  @decorators.LogDecorator(logger)
  def get_console_configuration(self) -> None:
    """Returns None. Console is not supported because there's no Switchboard."""
    del self  # Unused because console is not supported.
    return None

  @decorators.PersistentProperty
  def health_checks(self):
    """Returns list of methods to execute as health checks."""
    return [self.check_device_connected]

  @decorators.PersistentProperty
  def total_ports(self):
    """Number of ports on Yepkit."""
    return 3

  @decorators.CapabilityDecorator(switch_power_usb_default.SwitchPowerUsbDefault
                                 )
  def switch_power(self):
    """Returns a switch_power object to send commands.

    Returns:
        SwitchPowerUsbDefault: switch_power_usb_default
    """
    return self.lazy_init(
        switch_power_usb_default.SwitchPowerUsbDefault,
        shell_fn=self.shell,
        regex_shell_fn=self.shell_with_regex,
        command_dict=self.commands,
        regex_dict=self.regexes,
        device_name=self.name,
        serial_number=self.serial_number,
        total_ports=self.total_ports)

  @decorators.LogDecorator(logger)
  def get_detection_info(self):
    """Gets the persistent and optional attributes of a yepkit.

    Returns:
        tuple: (dict, dict) dictionary of persistent attributes,
               dictionary of optional attributes (set to None).

    Raises:
        RuntimeError: if yepkit is not enabled.

    Notes:
        persistent: device_type, model, console_port_name, serial_number,
                    total_ports

        optional: {}
    """
    if len(self.communication_address) < 4:
      raise RuntimeError("{} serial number {} is too short. "
                         "Length of serial number must be >= 4".format(
                             self.DEVICE_TYPE, self.serial_number))

    self.props["options"] = {}

    persistent_dict = self.props["persistent_identifiers"]
    persistent_dict["serial_number"] = self.communication_address
    persistent_dict["model"] = self._MODEL
    persistent_dict["total_ports"] = 3

    return self.props["persistent_identifiers"], self.props["options"]

  @classmethod
  def is_connected(cls, device_config):
    """Checks whether or not the yepkit is connected to the computer.

    Args:
        device_config (dict): contains "persistent" dict

    Returns:
        bool: whether device serial_number is in
        host_utils.get_all_yepkit_serials

    Raises:
        RuntimeError: if yepkit is not enabled.
    """
    return device_config["persistent"][
        "console_port_name"] in host_utils.get_all_yepkit_serials()

  def shell(self,
            command,
            command_name="shell",
            timeout=None,
            port=0,
            include_return_code=False):
    """Sends command and returns response.

    Args:
        command (str): Command to send to the device.
        command_name (str): Optional identifier to use in logs for this command.
        timeout (float): Seconds to wait for pattern after command sent.
        port (int): no op.
        include_return_code (bool): flag indicating return code should be
          returned

    Returns:
        str or tuple: response or (response, return_code) if
        include_return_code is True.
            return_code 0 - success
            return_code -1 - error

    Raises:
        DeviceError: if command execution fails OR couldn't find the requested
                     group in any of the responses.
    """
    timeout = timeout or self.timeouts["SHELL"]
    if "ykushcmd" not in command:
      raise errors.DeviceError(
          "{} shell expected 'ykushcmd' instead found: {!r}".format(
              self.name, command))
    raw_list = command.split(" ")
    if include_return_code:
      result = subprocess.check_output(raw_list).decode("utf-8", "replace")
      if "Application Help" in result:
        return result, -1  # Error
      return result, 0
    return subprocess.check_output(raw_list).decode("utf-8", "replace")

  def shell_with_regex(self,
                       command,
                       regex,
                       regex_group=1,
                       command_name="shell",
                       raise_error=False,
                       tries=1,
                       port=0,
                       timeout=None):
    """Sends a command, searches for a regex in the response, and returns a match group.

    Args:
        command (str): command to issue.
        regex (str): regular expression with one or more capturing groups.
        regex_group (int): number of regex group to return.
        command_name (str): command name to appear in log messages.
        raise_error (bool): whether or not to raise error if unable to find
          a match.
        tries (int): how many times to try executing the command before failing.
        port (int): which port to send the shell command to.
        timeout (float): Time in seconds to wait for device to respond.

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
        port=port,
        timeout=timeout)


deprecation_utils.add_deprecated_attributes(
    Yepkit, [("power_on", "switch_power.power_on", True),
             ("power_off", "switch_power.power_off", True)])
