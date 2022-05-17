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

"""Class for SSH devices."""
import time

from gazoo_device import config
from gazoo_device import console_config
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.base_classes import gazoo_device_base
from gazoo_device.capabilities import file_transfer_scp
from gazoo_device.capabilities import shell_ssh
from gazoo_device.utility import deprecation_utils
from gazoo_device.utility import host_utils

logger = gdm_logger.get_logger()

# Use a log marker to prevent reading preexisting persistent logs.
_LOG_MARKER = "--- GDM Log Marker ---"
_LOGGING_FILE_PATH = "/var/log/syslog"
_LOG_MARKER_LINE_POS_OR_EMPTY = (
    'grep -n -e "{marker}" {file_path} --text | tail -n 1 | cut -d '
    '":" -f 1').format(
        marker=_LOG_MARKER, file_path=_LOGGING_FILE_PATH)
_LOG_MARKER_LINE_POS = (
    "line_num=$({cmd}); [ -z \"($line_num)\" ] && echo 1 || echo"
    " $line_num".format(cmd=_LOG_MARKER_LINE_POS_OR_EMPTY))

INFO_PREFIX = "INFO_"
COMMANDS = {
    "BOOT_UP_COMPLETE": "echo 'gdm hello'",
    "INJECT_LOG_MARKER": "sudo sh -c 'echo \"{marker}\" >> {file_path}'".format(
        marker=_LOG_MARKER, file_path=_LOGGING_FILE_PATH),
    "LOGGING": "tail -F -n +$({cmd}) {file_path}".format(
        cmd=_LOG_MARKER_LINE_POS, file_path=_LOGGING_FILE_PATH),
    "GDM_HELLO": "echo 'gdm hello'",
}
REGEXES = {}
TIMEOUTS = {
    "BOOT_UP": 60,
    "DISCONNECT": 60,
    "PING_TO_SSH_DELAY": 10,
    "SHELL": 10,
    "SHELL_DEVICE_RESPONSIVENESS": 5,
}


class SshDevice(gazoo_device_base.GazooDeviceBase):
  """Base class for SSH devices."""
  COMMUNICATION_TYPE = "SshComms"
  _COMMUNICATION_KWARGS = {
      "args": host_utils.DEFAULT_SSH_OPTIONS,
      "log_cmd": COMMANDS["LOGGING"],
      "key_info": None,
      "username": "root",
  }

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

  @decorators.LogDecorator(logger)
  def _after_boot_hook(self):
    """Executes after the device boots up.

    No-op by default. Override in derived classes as necessary.
    Methods as upgrade, factory reset may also reboot the device.
    """
    pass

  @decorators.health_check
  def check_device_responsiveness(self):
    """Checks if the device is responsive on console.

    Raises:
      DeviceNotResponsiveError: if device is not responsive on console.
    """
    cmd, timeout = self.commands["GDM_HELLO"], self.timeouts[
        "SHELL_DEVICE_RESPONSIVENESS"]
    try:
      self.shell(cmd, timeout=timeout)
    except errors.DeviceError as err:
      raise errors.DeviceNotResponsiveError(
          self.name,
          "unable to execute command {!r} on device's shell".format(cmd),
          timeout=timeout,
          details=str(err))

  @classmethod
  def _convert_build_date(cls, build_date):
    """Hook for build date conversion.

    No-op by default. Override if necessary.

    Args:
      build_date: build_date to convert.

    Returns:
      The converted build date.
    """
    return build_date

  @decorators.CapabilityDecorator(file_transfer_scp.FileTransferScp)
  def file_transfer(self):
    """File transfer capability for moving files from and to the device."""
    return self.lazy_init(
        file_transfer_scp.FileTransferScp,
        ip_address_or_fn=self.ip_address,
        device_name=self.name,
        add_log_note_fn=self.switchboard.add_log_note,
        user=self._COMMUNICATION_KWARGS["username"],
        key_info=self._COMMUNICATION_KWARGS["key_info"])

  def get_console_configuration(self) -> console_config.ConsoleConfiguration:
    """Returns the interactive console configuration."""
    return console_config.get_log_response_separate_port_configuration(
        self.switchboard.get_line_identifier())

  @decorators.LogDecorator(logger)
  def get_detection_info(self):
    """Gets the persistent and optional attributes of a device.

    Returns:
      tuple: (persistent properties dict, optional properties dict)
    """
    self._set_optional_props()
    self._set_persistent_properties()
    self._format_persistent_properties()

    # Reset all capabilities which could have been instantiated
    # during get_detection_info.
    self.reset_all_capabilities()

    return self.props["persistent_identifiers"], self.props["options"]

  @decorators.PersistentProperty
  def health_checks(self):
    """Returns list of methods to execute as health checks."""
    return [
        self.check_device_connected, self.check_create_switchboard,
        self.check_device_responsiveness
    ]

  @decorators.PersistentProperty
  def ip_address(self):
    return self.communication_address

  @classmethod
  def is_connected(cls, device_config):
    """Checks whether or not the device is connected to the computer.

    Args:
      device_config (dict): contains "persistent" dict

    Returns:
      bool: True if device is pingable, False otherwise.
    """
    ip_address = device_config["persistent"]["console_port_name"]
    return host_utils.is_pingable(ip_address)

  @decorators.PersistentProperty
  def os(self):
    return "Linux"

  @decorators.LogDecorator(logger)
  def recover(self, error):
    """Attempts to recover device based on the type of error specified.

    Args:
      error(CheckDeviceReadyError): The exception thrown that will be used to
        identify a possible recovery solution to use.

    Raises:
      DeviceError: If device recovery fails while attempting to perform
        recovery steps.
      CheckDeviceReadyError: If there are no recovery steps available for
        the error argument, it will be re-raised directly.
    """
    if isinstance(error, errors.DeviceNotBootupCompleteError):
      logger.info("%s not fully booted up. Waiting for complete bootup.",
                  self.name)
      self.wait_for_bootup_complete()
    else:
      super().recover(error)

  def shell(self,
            command,
            command_name="shell",
            timeout=None,
            port=0,
            searchwindowsize=config.SEARCHWINDOWSIZE,
            include_return_code=False):
    """Sends command and returns response and optionally return code.

    Can try multiple times as connection can sometimes fail.
    See shell_capability init args for setting the number of retry
    attempts.

    Args:
      command (str): Command to send to the device.
      command_name (str): Identifier for command.
      timeout (float): Time in seconds to wait for device to respond.
      port (int): Which port to send on, 0 or 1.
      searchwindowsize (int): Number of the last bytes to look at
      include_return_code (bool): flag indicating return code should be
        returned.

    Raises:
      DeviceError: If communication fails.

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
        searchwindowsize=searchwindowsize,
        include_return_code=include_return_code)

  @decorators.CapabilityDecorator(shell_ssh.ShellSSH)
  def shell_capability(self):
    return self.lazy_init(
        shell_ssh.ShellSSH,
        send_and_expect=self.switchboard.send_and_expect,
        device_name=self.name,
        timeout=self.timeouts["SHELL"],
        tries=2)

  @decorators.LogDecorator(logger)
  def wait_for_bootup_complete(self, timeout=None):
    """Wait until the device finishes booting up and is ready for testing.

    Args:
      timeout (int): max time to wait for the device to finish booting up.

    Raises:
      DeviceNotBootupCompleteError: device failed to finish booting up
        before the timeout.
    """
    timeout = timeout or self.timeouts["BOOT_UP"]
    shell_resp = ""
    is_shell_responsive = False
    err_msg = ("wait_for_bootup_complete failed. "
               "Device hasn't finished booting in {}s.".format(timeout))

    try:
      shell_resp, return_code = self.shell(
          self.commands["BOOT_UP_COMPLETE"],
          include_return_code=True,
          timeout=timeout)
      is_shell_responsive = return_code == 0

    except errors.DeviceError as err:
      reason = "shell error: {!r}".format(err)
      raise errors.DeviceNotBootupCompleteError(
          self.name, err_msg, reason=reason)

    if not is_shell_responsive:
      reason = ("Shell responded with a non-zero return code. "
                "Response: {}, code: {}.".format(shell_resp, return_code))
      raise errors.DeviceNotBootupCompleteError(
          self.name, err_msg, reason=reason)

  def _format_persistent_properties(self):
    """Cleans up the format of certain persistent properties."""
    persistent_dict = self.props["persistent_identifiers"]
    for key, value in persistent_dict.items():
      if value:
        if "mac_address" in key:
          persistent_dict[key] = value.replace(":", "")
        elif "code" in key:
          persistent_dict[key] = value.splitlines()[-1]
        elif key == "build_date":
          persistent_dict[key] = self._convert_build_date(value)

  def _inject_log_marker(self):
    """Adds a log marker to /var/log/syslog to prevent reading preexisting logs.

    Device logs are read starting with the last log marker (if present).
    """
    self.shell(self.commands["INJECT_LOG_MARKER"])

  def _set_optional_props(self):
    """Sets the optional properties for the device during detection."""
    self.props["options"] = {
        "user_account": None,
        "user_name": None,
    }

  def _set_persistent_properties(self):
    """Obtains persistent properties from the device during detection."""
    for key in [
        cmd for cmd in list(self.commands) if cmd.startswith(INFO_PREFIX)
    ]:
      prop = key.lower()[len(INFO_PREFIX):]  # Remove INFO_ from key.
      response = ""
      resp_list = self.shell(self.commands[key]).split("=")
      if resp_list:
        response = resp_list[-1]

      self.props["persistent_identifiers"][prop] = response

  def _verify_reboot(self, disconnect_timeout=None, bootup_timeout=None):
    """Verifies the device reboots correctly.

    Ensures the device goes offline, comes back online, and finishes booting up.

    Args:
      disconnect_timeout (int): max time to wait for device to go offline & come
          back online.
      bootup_timeout (int): max time to wait for device to finish booting up.

    Raises:
      DeviceNotBootupCompleteError: device failed to boot up.
    """
    disconnect_timeout = disconnect_timeout or self.timeouts["DISCONNECT"]
    bootup_timeout = bootup_timeout or self.timeouts["BOOT_UP"]

    start_time = time.time()
    max_disconnect_time = start_time + disconnect_timeout

    last_ping = True
    while time.time() < max_disconnect_time:
      ping = host_utils.is_pingable(self.ip_address)
      if not ping and not last_ping:
        logger.info("{} offline in {}s.".format(self.name,
                                                int(time.time() - start_time)))
        break
      time.sleep(.5)
      last_ping = ping
    else:
      raise errors.DeviceNotBootupCompleteError(
          self.name, "failed to go offline in {}s".format(disconnect_timeout))

    # close ssh transport as the ssh connection is disconnected.
    self.switchboard.close_all_transports()

    time.sleep(5)  # wait for a bit
    start_time = time.time()
    while time.time() < max_disconnect_time:
      if host_utils.is_pingable(self.ip_address):
        logger.info("{} online in {}s".format(self.name,
                                              int(time.time() - start_time)))
        break
      time.sleep(.5)
    else:
      raise errors.DeviceNotBootupCompleteError(
          self.name,
          "failed to come online {}s".format(int(time.time() - start_time)))

    # There's a delay between the device being responsive to ping
    # and being able to open SSH connections
    time.sleep(self.timeouts["PING_TO_SSH_DELAY"])

    # Reopen ssh transport as ssh connection is once more available.
    self.switchboard.open_all_transports()

    self.wait_for_bootup_complete(timeout=bootup_timeout)
    logger.info("{} booted up successfully in {}s.".format(
        self.name, int(time.time() - start_time)))

    self._after_boot_hook()


deprecation_utils.add_deprecated_attributes(
    SshDevice,
    [("send_file_to_device", "file_transfer.send_file_to_device", True),
     ("recv_file_from_device", "file_transfer.recv_file_from_device", True),
     ("has_command", "shell_capability.has_command", True)])
