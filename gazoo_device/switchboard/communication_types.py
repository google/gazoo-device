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

"""Identifies the known communication types and maps them to the appropriate arguments.

Used as a wrapper around switchboard for common communication types and used for detection.
"""
from __future__ import absolute_import
import abc
import os
from gazoo_device import config
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.switchboard import adb_transport
from gazoo_device.switchboard import data_framer
from gazoo_device.switchboard import jlink_transport
from gazoo_device.switchboard import line_identifier
from gazoo_device.switchboard import pty_transport
from gazoo_device.switchboard import serial_transport
from gazoo_device.switchboard import ssh_transport
from gazoo_device.utility import adb_utils
from gazoo_device.utility import host_utils
from gazoo_device.utility import usb_utils
from gazoo_device.utility import usb_config

logger = gdm_logger.get_gdm_logger()

JLINK_COMMS_PRODUCT_NAME = "J-Link"


def get_specific_serial_addresses(match_criteria):
    """Returns addresses for connections that match criteria.

    Args:
      match_criteria (dict): dictionary of match criteria.

    Returns:
      list: list of UsbInfo instances that match criteria.

    Note:
      Excludes Android devices.
      Connections first excluded and then included.
      If there is no include regex, all instances that dont match exclude_regex are included.

      Dictionary entry: {'<key>': 'include_regex': <regex>,
      'exclude_regex': '<regex>'}
    """
    instances = usb_utils.find_matching_connections(match_criteria)
    accessible_instances = [instance for instance in instances
                            if os.access(instance.address, os.R_OK | os.W_OK)]
    inaccessible_addresses = [instance.address for instance in instances
                              if instance not in accessible_instances]
    if inaccessible_addresses:
        logger.info(
            "Warning: no read/write permission for these serial address(es): {}".format(
                inaccessible_addresses))
    return [instance.address for instance in accessible_instances
            if instance.product_name not in usb_config.ANDROID_NAMES]


class CommunicationType():
    """Default settings for a communication type.

    Child classes should at minimum overwrite get_transport_list and get_comms_addresses.
    Child classes will likely overwrite init with their required args.
    """

    def __init__(self, comms_address, **kwargs):
        """Initiates args."""
        self.comms_address = comms_address
        for name, value in kwargs.items():
            setattr(self, name, value)

    def get_button_list(self):
        """Set ups the list of FTDI button instances as needed.

        Notes:
          For non-ftdi devices it just returns an empty list.

        Returns:
          list: list of FTDI button instances.
        """
        return []

    @classmethod
    @abc.abstractmethod
    def get_comms_addresses(cls):
        """Detects the comms addresses that match this communication type.

        Note:
          list can overlap those from other communication types.

        Returns:
          list: list of potential communication addresses.
        """

    def get_data_framers(self, num_transports):
        """Set up framers used to atomicize the raw output of the device.

        Args:
          num_transports (int): number of declared transports.

        Note:
          Deals with interwoven lines as well as tokenized output.
          Default is to use new line character to separate the lines.

        Returns:
           list: list of data framers mapped to each transport.
        """
        return [data_framer.NewlineFramer()] * num_transports

    def get_identifier(self):
        """Setup identifiers used to distinguish loglines from responses.

        Returns:
           LineIdentifier: type of line identifier.

        Notes:
          Defaults to labelling all as unknown.
        """
        return line_identifier.AllUnknownIdentifier()

    def get_partial_line_timeout_list(self, num_transports):
        """Time to wait before returning partial lines for a device.

        Args:
           num_transports (int): number of declared transports.

        Returns:
           list: list of timeouts for each transport.
        """
        return [.1] * num_transports

    def get_switchboard_kwargs(self):
        """Returns the arguments needed to set up switchboard for this communication type.

        Returns:
           dict: transport_list, identifier, framer_list, button_list
        """
        transport_list = self.get_transport_list()
        num_transports = len(transport_list)
        return {
            "transport_list": transport_list,
            "identifier": self.get_identifier(),
            "framer_list": self.get_data_framers(num_transports),
            "button_list": self.get_button_list(),
            "partial_line_timeout_list": self.get_partial_line_timeout_list(num_transports),
        }

    @abc.abstractmethod
    def get_transport_list(self):
        """Setups up the transports which will communicate raw device io.

        Returns:
           list: list of initiated transports.
        """


class AdbComms(CommunicationType):
    """Communication type for devices communicating over ADB.

    Commands/responses go over port 0 while logs are streamed over port 1.
    """

    def __init__(self,
                 comms_address,
                 log_cmd="logcat -v threadtime",
                 shell_cmd="shell",
                 event_log_cmd=None):
        super(AdbComms, self).__init__(comms_address=comms_address,
                                       log_cmd=log_cmd,
                                       shell_cmd=shell_cmd)
        self.event_log_cmd = event_log_cmd

    @classmethod
    def get_comms_addresses(cls):
        return adb_utils.get_adb_devices()

    def get_transport_list(self):
        transports = [
            adb_transport.AdbTransport(comms_address=self.comms_address, command=self.shell_cmd),
            adb_transport.AdbTransport(comms_address=self.comms_address, command=self.log_cmd),
        ]
        if self.event_log_cmd:
            transports.append(adb_transport.AdbTransport(comms_address=self.comms_address,
                                                         command=self.event_log_cmd))
        return transports

    def get_identifier(self):
        return line_identifier.PortLogIdentifier(log_ports=[1, 2])


class DockerComms(CommunicationType):
    """Communication type for VDL Docker devices."""

    def __init__(self, comms_address, secondary_comms_address=None, secondary_log_pattern=None):
        self.comms_address = comms_address
        super().__init__(comms_address=comms_address,
                         secondary_comms_address=secondary_comms_address,
                         secondary_log_pattern=secondary_log_pattern)

    @classmethod
    def get_comms_addresses(cls):
        return host_utils.get_all_vdl_docker_connections()

    def get_transport_list(self):
        docker_exec_args = "exec -i {} /bin/bash".format(self.comms_address)
        docker_logs_args = "logs -f {}".format(self.comms_address)
        return [pty_transport.PtyTransport("docker", docker_exec_args),
                pty_transport.PtyTransport("docker", docker_logs_args)]


class JlinkSerialComms(CommunicationType):
    """Communication type for JLINK and UART communication simultaneously.

    Serial is used for primary communication while jlink is used for log streaming.
    """

    @classmethod
    def get_comms_addresses(cls):
        match_criteria = {"product_name": {"include_regex": JLINK_COMMS_PRODUCT_NAME}}
        return get_specific_serial_addresses(match_criteria)

    def __init__(self, comms_address, baudrate=115200):
        secondary_address = usb_utils.get_serial_number_from_path(comms_address)
        super(JlinkSerialComms, self).__init__(comms_address=comms_address,
                                               secondary_address=secondary_address,
                                               baudrate=baudrate)

    def get_transport_list(self):
        return [serial_transport.SerialTransport(comms_address=self.comms_address,
                                                 baudrate=self.baudrate),
                jlink_transport.JLinkTransport(comms_address=self.secondary_address)]

    def get_identifier(self):
        return line_identifier.PortLogIdentifier()


class PtyProcessComms(CommunicationType):
    """Communication type for communication with a process on the host machine.

    No detection provided.
    """

    @classmethod
    def get_comms_addresses(cls):
        return []

    def __init__(self, comms_address):
        full_command_list = comms_address.split()
        comms_address = full_command_list[0]
        args = " ".join(full_command_list[1:])
        super(PtyProcessComms, self).__init__(comms_address=comms_address, args=args)

    def get_transport_list(self):
        return [pty_transport.PtyTransport(self.comms_address, args=self.args)]

    def get_identifier(self):
        return line_identifier.AllUnknownIdentifier()


class SshComms(CommunicationType):
    """Communication type for device communication over ssh.

    Login is handled by ssh-keys on machine (or device does not require password).

    Commands/responses are on port 0 while log streaming happens on port 1.
    """

    @classmethod
    def get_comms_addresses(cls, static_ips):
        return host_utils.get_all_ssh_ips(static_ips)

    def __init__(self,
                 comms_address,
                 log_cmd="tail -F -n /var/log/messages",
                 args=host_utils.DEFAULT_SSH_OPTIONS,
                 ssh_key_type=None,
                 username="root"):
        super(SshComms, self).__init__(comms_address=comms_address,
                                       log_cmd=log_cmd,
                                       args=args,
                                       username=username,
                                       ssh_key_type=ssh_key_type)

    def get_transport_list(self):
        return [
            ssh_transport.SSHTransport(comms_address=self.comms_address,
                                       args=self.args,
                                       ssh_key_type=self.ssh_key_type,
                                       username=self.username),
            ssh_transport.SSHTransport(comms_address=self.comms_address,
                                       args=self.args,
                                       username=self.username,
                                       ssh_key_type=self.ssh_key_type,
                                       log_cmd=self.log_cmd)]

    def get_identifier(self):
        return line_identifier.PortLogIdentifier(log_ports=[1])


class SerialComms(CommunicationType):
    """Communication type for device communication over basic serial."""

    def __init__(self, comms_address,
                 log_line_regex=None,
                 baudrate=serial_transport.DEFAULT_BAUDRATE):

        super(SerialComms, self).__init__(comms_address=comms_address,
                                          log_line_regex=log_line_regex,
                                          baudrate=baudrate)

    @classmethod
    def get_comms_addresses(cls):
        exclude_products = [JLINK_COMMS_PRODUCT_NAME]
        match_criteria = {
            "product_name": {"exclude_regex": "|".join(exclude_products)},
            "ftdi_interface": {"include_regex": "0"}
        }
        return get_specific_serial_addresses(match_criteria)

    def get_transport_list(self):
        return [serial_transport.SerialTransport(comms_address=self.comms_address,
                                                 baudrate=self.baudrate)]

    def get_identifier(self):
        if self.log_line_regex:
            return line_identifier.RegexLogIdentifier(self.log_line_regex)
        return super(SerialComms, self).get_identifier()


class YepkitComms(CommunicationType):
    """Communication type for yepkit devices.

    Currently supports just detection as communication does not yet work as expected.
    """

    @classmethod
    def get_comms_addresses(cls):
        return host_utils.get_all_yepkit_serials()

    def get_transport_list(self):
        return []


SUPPORTED_CLASSES = [
    AdbComms,
    DockerComms,
    JlinkSerialComms,
    PtyProcessComms,
    SerialComms,
    SshComms,
    YepkitComms]


DETECTION_METHODS_MAP = {a_class.__name__: a_class.get_comms_addresses
                         for a_class in SUPPORTED_CLASSES}
SUPPORTED_TYPES_MAP = {a_class.__name__: a_class for a_class in SUPPORTED_CLASSES}
SUPPORTED_TYPES = list(SUPPORTED_TYPES_MAP.keys())


def detect_connections(static_ips):
    """Detects all the communication addresses for the different devices."""
    connections_dict = {}
    for comms_name, detection_method in DETECTION_METHODS_MAP.items():

        logger.info("\tdetecting potential {} communication addresses".format(comms_name))
        try:
            try:
                comms_addresses = detection_method(static_ips=static_ips)
            except TypeError:  # method does not static static_ips
                comms_addresses = detection_method()
            connections_dict[comms_name] = comms_addresses
            logger.debug(
                "Found {} potential communication addresses".format(
                    len(comms_addresses)))

            # Verify ssh keys exist if ssh connections are detected
            if comms_name == "SshComms" and comms_addresses:
                warnings = []
                missing_keys = []
                ssh_key_types = [key_type for key_type in config.KEYS
                                 if config.KEYS[key_type]["flavor"] == config.KEY_FLAVOR_SSH]
                for ssh_key_type in ssh_key_types:
                    try:
                        host_utils.verify_ssh_key(ssh_key_type)
                    except ValueError as err:
                        warnings.append(str(err))
                    except errors.DownloadKeyError as err:
                        missing_keys.append(err.key_type)
                if warnings:
                    logger.warning("\t\tWARNING: " + "\n\t\t".join(warnings))
                if missing_keys:
                    logger.info(f"WARNING: Found {len(missing_keys)} missing ssh keys: "
                                f"{missing_keys}\nPlease run 'gdm download-keys'. "
                                "See GDM installation documentation for more details")
        except Exception as err:
            logger.info(
                "Unable to detect {} communication addresses. Err: {!r}".format(
                    comms_name, err))
    return connections_dict
