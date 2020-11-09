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

"""Testbed module."""
from __future__ import absolute_import
import subprocess
import sys
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.utility import host_utils

logger = gdm_logger.get_gdm_logger()

COMMANDS = {
    "FILE_SYSTEMS": "df",
    "WIFI_SCAN": "nmcli -t -f SSID device wifi",
    "WIFI_SCAN_MAC": "airport -s"
}


class Testbed(object):
    """Class for testbed interaction."""

    def __init__(self, devices, testing_props, name="testbed"):
        """Initialize a Testbed object.

        Args:
            devices (list): list of device instances.
            testing_props (dict): properties of the testbed used for testing.
            name (str): optional name of the testbed, defaulted to "testbed".
        """
        self.name = name
        self.devices = devices
        self.testing_props = testing_props
        self.commands = COMMANDS

        # map from testing prop to corresponding testbed health check method
        # e.g. if { "wifi_ssid": self.check_wifi_ssid_available }, then the
        #      check_wifi_ssid_available method will be executed if the "wifi_ssid" prop is
        #      provided during Testbed initialization.
        self._PROP_TO_HEALTH_CHECK = {
            "external_storage": self.check_external_storage_mounted,
            "wifi_ssid": self.check_wifi_ssid_available
        }

    @decorators.health_check
    def check_external_storage_mounted(self, enabled):
        """Check if external USB storage is mounted on devices in the testbed.

        Args:
            enabled (str): whether to run this health check, "true" or "false".

        Raises:
            TestbedMissingExternalStorageError: if devices are missing external USB storage.
        """
        if enabled.lower() == "false":
            return

        file_system_cmd = self.commands["FILE_SYSTEMS"]
        usb_storage_location = "/data/usb"
        devices_missing_external_storage = []
        for device in self.devices:
            file_system_output = device.shell(file_system_cmd)
            file_system_mounts = self._get_filesystem_mounts(file_system_output)
            if usb_storage_location not in file_system_mounts:
                devices_missing_external_storage.append(device.name)

        if devices_missing_external_storage:
            raise errors.TestbedMissingExternalStorageError(
                device_names=devices_missing_external_storage,
                details=(f"command {file_system_cmd!r} did not display any filesystems "
                         f"mounted on {usb_storage_location!r}"),
                recovery="mount external USB storage")

    @decorators.health_check
    def check_wifi_ssid_available(self, wifi_ssid):
        """Check if a wifi network is available given a service set identifier (SSID).

        Args:
            wifi_ssid (str): SSID of wifi network.

        Raises:
            TestbedWifiNotAvailableError: if wifi network is not available.

        """
        available_wifi_networks = self._get_available_wifi_networks()
        if wifi_ssid not in available_wifi_networks:
            raise errors.TestbedWifiNotAvailableError(wifi_ssid, available_wifi_networks)

    @decorators.LogDecorator(logger)
    def check_testbed_ready(self):
        """Checks if the testbed is healthy by executing a series of health check methods."""
        health_check_call = []  # list of tuples: (health check method, prop value)
        for prop in self.testing_props:
            if prop in self._PROP_TO_HEALTH_CHECK:
                health_check_call.append((self._PROP_TO_HEALTH_CHECK[prop],
                                          self.testing_props[prop]))
        self._execute_health_check_methods(health_check_call)

    @decorators.LogDecorator(logger)
    def make_testbed_ready(self, setting="on"):
        """Check testbed readiness and attempt recovery if allowed.

        Args:
            setting (str): 'on'|'off'|'check_only'.

        Raises:
            GazooDeviceError: if testbed health checks fail.
        """
        if setting not in ["on", "off", "check_only"]:
            raise errors.GazooDeviceError(
                "{} failed make_testbed_ready. Setting '{}' is invalid.".format(
                    self.name, setting))
        elif setting == "off":
            return

        # check testbed health
        try:
            self.check_testbed_ready()
        except errors.GazooDeviceError as err:
            if setting == "check_only":
                logger.info("{} skipping recovery".format(self.name))
                raise

            logger.info("{} failed check_testbed_ready with {}".format(self.name, repr(err)))

            # attempt to recover the testbed
            self.recover(err)
            logger.info("{} re-checking readiness after recovery attempt".format(self.name))
            self.check_testbed_ready()
            logger.info("{} successfully recovered to ready state".format(self.name))

    @decorators.LogDecorator(logger)
    def recover(self, error):
        """Attempts to recover testbed based on the type of error specified.

        Args:
            error (CheckTestbedReadyError): The exception thrown that will be used to
                                            identify a possible recovery solution to use.

        Raises:
            CheckTestbedReadyError: If recovery fails.
        """
        raise error

    def _execute_health_check_methods(self, health_check_calls):
        """Execute health checks on the testbed.

        Args:
            health_check_calls (list): list of tuples as (health check method, argument)
                                       to execute as health checks.

        Raises:
            CheckTestbedReadyError: if health check fails.

        Notes:
            - The value of the property that triggered the health check is passed to the health
            check method as an argument; therefore, health check methods will accept a single
            argument (unlike device health checks). All property values will be strings.
            - Some health checks will have "true" / "false" argument values. The health check
            should be skipped when the argument is "false".
            - Order of health check methods matter. Health check execution will stop at the first
            failing health check.
        """
        checks_passed = []
        for step, health_check_call in enumerate(health_check_calls):
            health_check_method, arg = health_check_call
            method_name = health_check_method.__name__
            health_check_name = method_name.replace("_", " ").strip().capitalize()

            try:
                health_check_method(arg)
            except errors.CheckTestbedReadyError as err:
                logger.info("testbed health check {}/{} failed: {}.".format(
                    step + 1, len(health_check_calls), health_check_name))
                err.checks_passed = checks_passed
                err.properties = self.testing_props.copy()
                raise

            checks_passed.append("{}.{}".format(type(self).__name__, method_name))
            logger.info("testbed health check {}/{} succeeded: {}.".format(
                step + 1, len(health_check_calls), health_check_name))

    def _get_available_wifi_networks(self):
        """Scan host for available wifi networks.

        Returns:
            list: of available wifi network SSIDs.

        Raises:
            GazooDeviceError: if required nmcli binary does not exist on host.
        """
        command = "WIFI_SCAN_MAC" if "darwin" in sys.platform else "WIFI_SCAN"
        command_args = self.commands[command].split()
        command_name = command_args[0]
        if not host_utils.has_command(command_name):
            raise errors.GazooDeviceError(
                "'{}' command not found and is required to perform wifi scan".format(
                    command_name))

        available_wifi_networks = subprocess.check_output(command_args).decode("utf-8", "replace")

        # wifi scan on mac requires some additional string parsing
        if "darwin" in sys.platform:
            available_network_ssids = []
            ssid_column_end_index = available_wifi_networks.index("SSID") + len("SSID")
            for network_info in available_wifi_networks.splitlines()[1:]:
                if network_info.strip():
                    available_network_ssids.append(network_info[:ssid_column_end_index].strip())
        else:
            available_network_ssids = available_wifi_networks.strip().splitlines()

        return available_network_ssids

    def _get_filesystem_mounts(self, file_system_output):
        """Parse locations that file systems are mounted on from command output.

        Args:
            file_system_output (str): output of command listing device file systems.

        Returns:
            list: locations that file systems are mounted on on the device.
        """
        file_system_mounts = []
        for file_system in file_system_output.splitlines():
            if not file_system:
                continue
            file_system_info = file_system.split()

            # 6 columns of information
            # Filesystem,1K-blocks,Used,Available,Use%,Mounted on
            if len(file_system_info) == 6:
                file_system_mounts.append(file_system_info[5])

        return file_system_mounts
