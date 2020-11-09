# Copyright 2020 Google LLC
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

"""Base class for all raspbian devices."""
import re
import time

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.base_classes import auxiliary_device
from gazoo_device.capabilities import file_transfer_scp
from gazoo_device.capabilities import shell_ssh
from gazoo_device.utility import host_utils

logger = gdm_logger.get_gdm_logger()

MARKER = "--- GDM Log Marker ---"
LOGGING_FILE_PATH = "/var/log/syslog"
LOG_MARKER_LINE_POS_OR_EMPTY = ('grep -n -e "{marker}" {file_path} --text | tail -n 1 | cut -d '
                                '":" -f 1').format(marker=MARKER, file_path=LOGGING_FILE_PATH)
LOG_MARKER_LINE_POS = ("line_num=$({cmd}); [ -z \"($line_num)\" ] && echo 1 || echo"
                       " $line_num".format(cmd=LOG_MARKER_LINE_POS_OR_EMPTY))

COMMANDS = {
    "BOOTUP_COMPLETE": "sudo systemctl --wait is-system-running\n",
    "FIRMWARE_VERSION": "cat /etc/os-release\n",
    "INJECT_LOG_MARKER": "sudo bash -c 'echo \"{marker}\" >> {file_path}'".format(
        marker=MARKER, file_path=LOGGING_FILE_PATH),
    "KERNEL_VERSION": "uname -r\n",
    "LOGGING": "tail -F -n +$({cmd}) {file_path}".format(cmd=LOG_MARKER_LINE_POS,
                                                         file_path=LOGGING_FILE_PATH),
    "MODEL_INFO": "cat /proc/device-tree/model\n",
    "REBOOT": "sudo reboot\n",
    "RESET_FAILED": "sudo systemctl reset-failed\n",
    "SERIAL_NUMBER_INFO": "cat /proc/cpuinfo\n",
    "WEAVE_WBR_INSTALLED": "ls /usr/sbin/nldaemon-cli"
}

REGEXES = {
    "COMMAND_UNSUPPORTED": r"-bash: \S+: command not found",
    "device_type": "raspberrypi",
    "FIRMWARE_VERSION_REGEX": r"VERSION=\"(\d+ \(\w+\))\"",
    "KERNEL_VERSION_REGEX": r"(.*)",
    "MODEL_INFO_REGEX": r"Raspberry Pi ([^\n]+)",
    "SERIAL_NUMBER_INFO_REGEX": r"Serial\s+: ([^\n]+)"
}

TIMEOUTS = {
    "SHELL": 10,
    "SHUTDOWN": 60,
    "ONLINE": 120
}


class RaspbianDevice(auxiliary_device.AuxiliaryDevice):
    """Base Class for Raspbian Devices."""

    COMMUNICATION_TYPE = "SshComms"
    _COMMUNICATION_KWARGS = {"log_cmd": COMMANDS["LOGGING"],
                             "ssh_key_type": "raspbian",
                             "username": "pi"}

    def __init__(self,
                 manager,
                 device_config,
                 log_file_name=None,
                 log_directory=None):
        super().__init__(manager,
                         device_config,
                         log_file_name=log_file_name,
                         log_directory=log_directory)
        self._commands.update(COMMANDS)
        self._regexes.update(REGEXES)
        self._timeouts.update(TIMEOUTS)

    @decorators.DynamicProperty
    def kernel_version(self):
        """Version of Raspbian kernel.

        Returns:
            str: Raspbian kernel version.
        """
        return self.shell_with_regex(self.commands["KERNEL_VERSION"],
                                     self.regexes["KERNEL_VERSION_REGEX"],
                                     raise_error=True)

    @decorators.DynamicProperty
    def firmware_version(self):
        """Version of Raspbian.

        Returns:
            str: Raspbian version.
        """
        return self.shell_with_regex(self.commands["FIRMWARE_VERSION"],
                                     self.regexes["FIRMWARE_VERSION_REGEX"],
                                     raise_error=True)

    @decorators.PersistentProperty
    def health_checks(self):
        """Returns list of methods to execute as health checks."""
        return [self.device_is_connected,
                self.check_create_switchboard,
                self._ensure_device_is_online]

    @decorators.PersistentProperty
    def ip_address(self):
        """Global IP address."""
        return self.communication_address

    @decorators.CapabilityDecorator(shell_ssh.ShellSSH)
    def shell_capability(self):
        return self.lazy_init(shell_ssh.ShellSSH, self.switchboard.send_and_expect, self.name,
                              timeout=self.timeouts["SHELL"], tries=2)

    @decorators.CapabilityDecorator(file_transfer_scp.FileTransferScp)
    def file_transfer(self):
        """File transfer capability for moving files from and to the device.

        Returns:
            FileTransferScp: file transfer capability using "scp" command.
        """
        return self.lazy_init(file_transfer_scp.FileTransferScp,
                              ip_address_or_fn=self.ip_address,
                              device_name=self.name,
                              add_log_note_fn=self.switchboard.add_log_note,
                              user=self._COMMUNICATION_KWARGS["username"],
                              ssh_key_type=self._COMMUNICATION_KWARGS["ssh_key_type"])

    @decorators.LogDecorator(logger)
    def recover(self, error):
        """Recovers the device from an error detected by check_device_ready()."""
        if isinstance(error, errors.DeviceNotResponsiveError):
            self.reboot()
        else:
            raise error

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
        self.switchboard.send(command=self.commands["REBOOT"])
        if not no_wait:
            self._verify_reboot()

    @decorators.LogDecorator(logger)
    def get_detection_info(self):
        """Gets the persistent and optional attributes of a device during setup.

        Returns:
          tuple: (dict, dict) dictionary of persistent attributes,
                  dictionary of optional attributes (set to None).
        """
        self.props = self.props.copy()
        for cmd_name, command in self.commands.items():
            if not cmd_name.endswith("INFO"):
                continue
            regex = self._regexes[cmd_name + "_REGEX"]
            cmd_name = cmd_name.lower()[:-5]  # remove _INFO
            value = self.shell_with_regex(command, regex)
            if re.search(self.regexes["COMMAND_UNSUPPORTED"], value):
                value = "Raspbian detection did not support '{}'".format(command)
            self.props["persistent_identifiers"][cmd_name] = value

        return self.props["persistent_identifiers"], self.props["optional"]

    @classmethod
    def is_connected(cls, device_config):
        """Checks whether or not the device is connected to the computer.

        Args:
            device_config (dict): contains "persistent" dict

        Returns:
            bool: True if device is pingable, False otherwise.

        Notes:
            device_config is typically the device_config from manager.
            It checks if the device is reachable or not.
        """
        ip_address = device_config["persistent"]["console_port_name"]
        return host_utils.is_pingable(ip_address)

    def shell(self,
              command,
              command_name="shell",
              timeout=None,
              port=0,
              include_return_code=False):
        """Sends command and returns response and optionally return code.

        Args:
            command(str): Command to send to the device.
            command_name(str): Identifier for command.
            timeout(float): Time in seconds to wait for device to respond.
            port(int): Which port to send on, 0 or 1.
            include_return_code(bool): flag indicating return code should be returned.

        Raises:
            GazooDeviceError: if communication fails.

        Note:
            Can try multiple times as connection can sometimes fail.
            See shell_capability init args for setting the number of retry attempts.

        Returns:
            str: If include_return_code is False return the device response to the command.
            tuple: If include_return_code is True return the device response and return code.
        """
        timeout = timeout or self.timeouts["SHELL"]
        return self.shell_capability.shell(
            command, command_name=command_name, timeout=timeout, port=port,
            include_return_code=include_return_code)

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
            command(str): command to issue.
            regex(str): regular expression with one or more capturing groups.
            regex_group(int): number of regex group to return.
            command_name(str): command name to appear in log messages.
            raise_error(bool): whether or not to raise error if unable to find a match.
            tries(int): how many times to try executing the command before failing.
            port(int): which port to send the shell command to.

        Returns:
            str: value of the capturing group with index 'regex_group' in the match.

        Raises:
            GazooDeviceError: if command execution fails OR
                             couldn't find the requested group in any of the responses.
        """
        return self.command_with_regex(command,
                                       regex,
                                       self.shell,
                                       regex_group=regex_group,
                                       raise_error=raise_error,
                                       tries=tries,
                                       command_name=command_name,
                                       port=port)

    def _ensure_device_goes_offline(self, timeout=None):
        """Ensure device is no longer pingable over ssh.

        Args:
            timeout(float): Time in seconds to wait for device to respond.

        Raises:
            GazooDeviceError: Deviced failed to go offline before the timeout
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
                logger.info("{} offline in {}s.".format(
                    self.name,
                    int(time.time() - start_time)))
                # close ssh transport as the ssh connection is disconnected.
                self.switchboard.close_all_transports()
                time.sleep(5)  # to ensure offline
                return
            time.sleep(.5)

        raise errors.GazooDeviceError(
            "Failed to go offline within {}s.".format(timeout))

    def _inject_log_marker(self):
        """Add GDM log marker to / var / log / syslog. This is to prevent reading stale logs.

        Note:
            Device logs are read starting with the last log marker(if present).
        """
        self.shell(self.commands["INJECT_LOG_MARKER"])

    def _ensure_device_is_online(self, timeout=None):
        """Ensure device is online and configs are fully loaded.

        Args:
            timeout(float): Time in seconds to wait for device to respond.

        Raises:
            GazooDeviceError: Device failed to come online before the timeout.
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
            raise errors.GazooDeviceError(
                "{} failed to become pingable in {}s.".format(self.name, timeout))

        output = "Device still offline"
        while time.time() < max_disconnect_time:
            # Ensure the BOOTUP_COMPLETE command is only sent once
            boot_up_complete_timeout = max_disconnect_time - time.time()
            try:
                output, return_code = self.shell(
                    self.commands["BOOTUP_COMPLETE"],
                    timeout=boot_up_complete_timeout,
                    include_return_code=True)
                if return_code == 0:  # command executed
                    logger.info(
                        "{} online in {}s".format(self.name, int(time.time() - start_time)))
                    return
                self.shell(self.commands["RESET_FAILED"])
            except errors.GazooDeviceError:
                logger.debug("{} failed to respond to {!r}.".format(
                    self.name, self.commands["BOOTUP_COMPLETE"]), exc_info=True)
            time.sleep(.5)
        raise errors.GazooDeviceError(
            "Failed to come online and respond to {!r} in {}s. Response: {}".format(
                self.commands["BOOTUP_COMPLETE"], timeout, output))

    def _verify_reboot(self):
        """Verifies reboot actually occurred."""
        self._ensure_device_goes_offline()
        self._ensure_device_is_online()

    def _list_properties_dynamic_raspbian(self):
        dyn_list = ["firmware_version",
                    "kernel_version"]
        return set(dyn_list)

    def __del__(self):
        self._log_object_lifecycle_event("__del__")
        if hasattr(self, 'close'):
            self.close()
