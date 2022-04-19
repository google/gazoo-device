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

"""Ubiquiti UniFi PoE Switch."""
import time

from gazoo_device import config
from gazoo_device import console_config
from gazoo_device import decorators
from gazoo_device import detect_criteria
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.base_classes import auxiliary_device
from gazoo_device.capabilities import shell_ssh
from gazoo_device.capabilities import switch_power_unifi_switch
from gazoo_device.switchboard import switchboard
from gazoo_device.utility import deprecation_utils
from gazoo_device.utility import host_utils

logger = gdm_logger.get_logger()
CLASS_NAME = "UnifiPoeSwitch"
MARKER = "--- GDM Log Marker ---"
LOGGING_FILE_PATH = "/var/log/messages"
LOG_MARKER_LINE_POS_OR_EMPTY = (
    'grep -n -e "{marker}" {file_path} | tail -n 1 | cut -d '
    '":" -f 1').format(
        marker=MARKER, file_path=LOGGING_FILE_PATH)
LOG_MARKER_LINE_POS = ("line_num=$({cmd}); echo ${{line_num:=1}}".format(
    cmd=LOG_MARKER_LINE_POS_OR_EMPTY))

COMMANDS = {
    "MODEL":
        "mca-cli-op info",
    "FIRMWARE_VERSION":
        "mca-cli-op info",
    "SERIAL_NUMBER":
        "mca-cli-op info",
    "DEVICE_NAME":
        "mca-cli-op info",
    "ADJUST_PORTS_MODE":
        "poe opmode {mode}",
    "GET_PORT_MODE":
        "show poe port 0/{port}",
    "GET_ALL_PORTS_MODE":
        "show poe port all",
    "REBOOT":
        "reboot",
    "NUMBER_OF_PORTS":
        "mca-cli-op info",
    "LOGGING":
        "tail -F -n +$({cmd}) {file_path}".format(
            cmd=LOG_MARKER_LINE_POS, file_path=LOGGING_FILE_PATH),
    "INJECT_LOG_MARKER":
        "sh -c 'echo \"{marker}\" >> {file_path}'".format(
            marker=MARKER, file_path=LOGGING_FILE_PATH),
    "TELNET":
        "echo 'exit' | telnet localhost",
    "MAC_ADDRESS":
        "show hardware"
}

REGEXES = {
    "MODEL_REGEX": r"Model:\s+(\S+)",
    "FIRMWARE_VERSION_REGEX": r"Version:\s+(\S+)",
    "SERIAL_NUMBER_REGEX": r"MAC Address:\s+(\S+)",
    "DEVICE_NAME_REGEX": r"Model:\s+([^-]+)",
    "GET_PORT_MODE_REGEX": r"0/{port}\s+(Auto|Passive24V|Shutdown)",
    "GET_ALL_PORTS_MODE_REGEX": r"(.*)\(Config\)#",
    "NUMBER_OF_PORTS_REGEX": r"Model:\s+\D+(\d+)",
    "MAC_ADDRESS_REGEX": r"Burned In MAC Address\.+ (\S+)"
}

TIMEOUTS = {"SHELL": 10, "SHUTDOWN": 60, "ONLINE": 120}


class UnifiPoeSwitch(auxiliary_device.AuxiliaryDevice):
  """Device class for a Ubiquiti UniFi PoE Switch."""
  COMMUNICATION_TYPE = "SshComms"
  DETECT_MATCH_CRITERIA = {detect_criteria.SshQuery.IS_UNIFI: True}
  DEVICE_TYPE = "unifi_switch"
  _COMMUNICATION_KWARGS = {
      "log_cmd": COMMANDS["LOGGING"],
      "key_info": config.KEYS["unifi_switch_ssh_key"],
      "username": "admin"
  }
  _OWNER_EMAIL = "gdm-authors@google.com"

  def __init__(self,
               manager,
               device_config,
               log_file_name=None,
               log_directory=None):
    super().__init__(
        manager,
        device_config,
        log_file_name=log_file_name,
        log_directory=log_directory)
    self._commands.update(COMMANDS)
    self._regexes.update(REGEXES)
    self._timeouts.update(TIMEOUTS)

  @decorators.PersistentProperty
  def ip_address(self):
    """IP address."""
    return self.communication_address

  @decorators.DynamicProperty
  def firmware_version(self):
    """Version of UniFi PoE Switch.

    Returns:
        str: UniFi PoE Switch firmware version.
    """
    return self.shell_with_regex(
        command=self.commands["FIRMWARE_VERSION"],
        regex=self._regexes["FIRMWARE_VERSION_REGEX"])

  def get_console_configuration(self) -> console_config.ConsoleConfiguration:
    """Returns the interactive console configuration."""
    return console_config.get_log_response_separate_port_configuration(
        self.switchboard.get_line_identifier())

  @decorators.PersistentProperty
  def health_checks(self):
    """Returns list of methods to execute as health checks."""
    return [
        self.check_device_connected, self.check_create_switchboard,
        self.check_telnet_connect
    ]

  @decorators.DynamicProperty
  def total_ports(self):
    """Gets the number of ports for the attached unifi_switch.

    Returns:
        int: number of device ports.
    """
    return int(
        self.shell_with_regex(
            command=self.commands["NUMBER_OF_PORTS"],
            regex=self._regexes["NUMBER_OF_PORTS_REGEX"]))

  @decorators.CapabilityDecorator(
      switch_power_unifi_switch.SwitchPowerUnifiSwitch)
  def switch_power(self):
    """switch_power capability to send telnet commands to the device.

    Returns:
        SwitchPowerUnifiSwitch: switch_power_unifi_switch capability.
    """
    return self.lazy_init(
        switch_power_unifi_switch.SwitchPowerUnifiSwitch,
        device_name=self.name,
        command_dict=self.commands,
        regex_dict=self.regexes,
        total_ports=self.total_ports,
        send_and_expect_fn=self.switchboard.send_and_expect,
        send_fn=self.switchboard.send)

  @decorators.CapabilityDecorator(shell_ssh.ShellSSH)
  def shell_capability(self):
    return self.lazy_init(
        shell_ssh.ShellSSH,
        self.switchboard.send_and_expect,
        self.name,
        timeout=self.timeouts["SHELL"],
        tries=2)

  def shell(self,
            command,
            command_name="shell",
            timeout=None,
            port=0,
            include_return_code=False):
    """Sends command and returns response and optionally return code.

    Args:
        command (str): Command to send to the device.
        command_name (str): Identifier for command.
        timeout (float): Time in seconds to wait for device to respond.
        port (int): Which port to send on, 0 or 1.
        include_return_code (bool): flag indicating return code should be
          returned.

    Raises:
        DeviceError: if communication fails.

    Note:
        Can try multiple times as connection can sometimes fail.
        See shell_capability init args for setting the number of retry attempts.

    Returns:
        str: If include_return_code is False return the device response to
        the command.
        tuple: If include_return_code is True return the device response and
        return code.
    """
    timeout = timeout or self.timeouts["SHELL"]
    return self.shell_capability.shell(
        command,
        command_name=command_name,
        timeout=timeout,
        port=port,
        include_return_code=include_return_code)

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

  @decorators.health_check
  def check_telnet_connect(self):
    """Verify it's possible to establish a telnet connection to the CLI.

    Raises:
        DeviceError: if telnet command returns a non zero exit status.
        DeviceNotResponsiveError: if no response to telnet command before
        the timeout.
    """
    try:
      response, return_code = self.shell(
          self.commands["TELNET"], include_return_code=True)

      if return_code != 0:
        raise errors.DeviceError(
            f'{self.name} command {self.commands["TELNET"]}'
            f' returned {return_code} exit status.')

    except Exception as err:
      raise errors.DeviceNotResponsiveError(
          self.name,
          "failed to establish telnet connection",
          timeout=self.timeouts["SHELL"],
          details=str(err))

  @decorators.LogDecorator(logger)
  def get_detection_info(self):
    """Gets the persistent and optional attributes of the unifi_poe_switch.

    Returns:
      tuple: (dict, dict) dictionary of persistent attributes,
              dictionary of optional attributes.

    Notes:
        persistent: model, serial_number
    """
    self.props["optional"] = {}
    self.props["persistent_identifiers"]["model"] = self.shell_with_regex(
        command=self.commands["MODEL"], regex=self._regexes["MODEL_REGEX"])
    self.props["persistent_identifiers"][
        "serial_number"] = self.shell_with_regex(
            command=self.commands["SERIAL_NUMBER"],
            regex=self._regexes["SERIAL_NUMBER_REGEX"]).replace(":", "")
    return self.props["persistent_identifiers"], self.props["optional"]

  @classmethod
  def is_connected(cls, device_config):
    """Checks whether or not the unifi_poe_switch is connected.

    Args:
        device_config (dict): contains "persistent" dict

    Returns:
        bool: whether the device responds to a ping.
    """
    return host_utils.is_pingable(
        device_config["persistent"]["console_port_name"])

  @decorators.LogDecorator(logger)
  def reboot(self, no_wait=False, method="shell"):
    """Reboots the device.

    Verifies device fully boots up afterwards.

    Args:
        no_wait (bool): Return before reboot completes. Default: False
        method (str): reboot technique to use.
    """
    self._inject_log_marker()
    self.switchboard.add_log_note("GDM triggered reboot")
    self.shell(command=self.commands["REBOOT"])
    if not no_wait:
      self._verify_reboot()

  @decorators.LogDecorator(logger)
  def recover(self, error):
    """Attempts to recover device based on the type of error specified."""
    if isinstance(error, errors.DeviceNotResponsiveError):
      self.reboot()
    else:
      raise error

  def _verify_reboot(self):
    """Verifies reboot actually occurred."""
    self._ensure_device_goes_offline()
    self._ensure_device_is_online()

  @decorators.CapabilityDecorator(switchboard.SwitchboardDefault)
  def switchboard(self):
    """Instance for communicating with the device."""
    switchboard_name = self._get_private_capability_name(
        switchboard.SwitchboardDefault)
    if not hasattr(self, switchboard_name):
      switchboard_kwargs = self._COMMUNICATION_KWARGS.copy()
      switchboard_kwargs.update({
          "communication_address": self.communication_address,
          "communication_type": self.COMMUNICATION_TYPE,
          "log_path": self.log_file_name,
          "device_name": self.name,
          "event_parser": None})
      setattr(self, switchboard_name,
              self.get_manager().create_switchboard(**switchboard_kwargs))

    return getattr(self, switchboard_name)

  def _ensure_device_goes_offline(self, timeout=None):
    """Ensure device is no longer pingable over ssh.

    Args:
        timeout (float): Time in seconds to wait for device to respond.

    Raises:
        DeviceError: Device failed to go offline before the timeout
    """
    timeout = timeout or self.timeouts["SHUTDOWN"]
    start_time = time.time()
    max_disconnect_time = start_time + timeout
    count = 0
    while time.time() < max_disconnect_time:
      if not host_utils.is_pingable(self.ip_address):
        count += 1  # Ensure device is really offline not just a blip
      else:
        count = 0
      if count == 2:
        logger.info("{} offline in {}s.".format(self.name,
                                                int(time.time() - start_time)))
        # close ssh transport as the ssh connection is disconnected.
        self.switchboard.close_all_transports()
        time.sleep(5)  # to ensure offline
        return
      time.sleep(.5)

    raise errors.DeviceError("Failed to go offline within {}s.".format(timeout))

  def _inject_log_marker(self):
    """Adds a log marker to /var/log/syslog.

    This is to prevent reading stale logs.

    Note:
        Device logs are read starting with the last log marker (if present).
    """
    self.shell(self.commands["INJECT_LOG_MARKER"])

  def _ensure_device_is_online(self, timeout=None):
    """Ensure device is online and configs are fully loaded.

    Args:
        timeout (float): Time in seconds to wait for device to respond.

    Raises:
        DeviceError: Device failed to come online before the timeout.
    """
    timeout = timeout or self.timeouts["ONLINE"]
    start_time = time.time()
    max_disconnect_time = start_time + timeout
    while time.time() < max_disconnect_time:
      if host_utils.is_pingable(self.ip_address):
        # There's a delay between the device being responsive to ping
        # and being able to open SSH connections
        time.sleep(10)
        self.switchboard.open_all_transports()
        break
      time.sleep(.5)
    else:
      raise errors.DeviceError("{} failed to become pingable in {}s.".format(
          self.name, timeout))

    output = "Device still offline"
    while time.time() < max_disconnect_time:
      try:
        output, return_code = self.shell(
            self.commands["TELNET"], include_return_code=True)
        if return_code == 0:  # command executed
          logger.info("{} online in {}s".format(self.name,
                                                int(time.time() - start_time)))
          return
      except errors.DeviceError:
        logger.debug(
            "{} failed to respond to {!r}.".format(self.name,
                                                   self.commands["TELNET"]),
            exc_info=True)
      time.sleep(.5)
    raise errors.DeviceError(
        "Failed to come online and respond to {!r} in {}s. Response: {}".format(
            self.commands["TELNET"], timeout, output))


deprecation_utils.add_deprecated_attributes(
    UnifiPoeSwitch,
    [("do_and_expect", "switchboard.do_and_expect", True),
     ("expect", "switchboard.expect", True),
     ("send", "switchboard.send", True),
     ("send_and_expect", "switchboard.send_and_expect", True)])
