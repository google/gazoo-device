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

"""This module defines errors raised by GDM.

The error subclasses are intended to make it easier to distinguish between and
handle different types of error exceptions.

error codes:
    1           Generic catch-all for GazooDeviceError
    10 - 19     TimeoutError exceptions
    20 - 29     DevToolsError exceptions
    30 - ...    CheckDeviceReadyError exceptions
"""
from gazoo_device import gdm_logger
from gazoo_device._version import version as gdm_version
logger = gdm_logger.get_gdm_logger()


class GazooDeviceError(Exception):
    """Basic exception for errors raised by devices.

    Attributes:
        err_code (int): numeric code of the error.
    """
    err_code = 1

    def __init__(self, msg):
        """Inits GazooDeviceError with 'msg' (an error message string).

        Args:
            msg (str or Exception): an error message string or an Exception instance.

        Note:
            Additionally, logs 'msg' to debug log level file.
            example:
            msg = 'Device {} failed to upgrade to target version {}. It is now at version {}'
            GazooDeviceError(msg.format(self.name, target_version, new_version)).
        """
        super().__init__(msg)
        logger.debug(repr(self))


class GazooParserError(GazooDeviceError):
    """Raised when log parser fails."""
    err_code = 5


class CommunicationTimeoutError(GazooDeviceError):
    """Exceptions raised due to a timeout."""
    err_code = 10


class TransportNotAvailableError(GazooDeviceError):
    """Exception raised when a transport is not available."""
    err_code = 22


class CheckDeviceReadyError(GazooDeviceError):
    """GazooDeviceError variant used in device ready checks."""
    err_code = 30

    def __init__(self, device_name, msg, reason=None, details=None, recovery=None):
        """Inits a CheckDeviceReadyError exception.

        Args:
            device_name (str): The name of the device.
            msg (str): An error message string of the form <error_message> <details>.
            reason (str): An optional message string describing the reason for the error.
            details (str): An optional message string describing error details.
            recovery (str): An optional message string describing further recovery
                            options if attempted recover does not work.

        Note:
            Default suggested recovery is to reflash the device with a valid build.
        """
        error_str = "{} {}.".format(device_name, msg)
        if reason:
            error_str += " Reason: {}.".format(reason)
        if details:
            error_str += " Details: {}.".format(details)
        if recovery:
            error_str += " Recovery: {}.".format(recovery)
        error_str += " GDM Version: {}.".format(gdm_version)

        self.properties = {}     # persistent properties of the device
        self.checks_passed = []  # names of health check methods that passed prior to the failure

        super(CheckDeviceReadyError, self).__init__(error_str)


class DeviceNotConnectedError(CheckDeviceReadyError):
    """Raised when device does not appear to be connected to host computer."""
    err_code = 31


class DeviceNotBootupCompleteError(CheckDeviceReadyError):
    """Raised when device is still booting up."""
    err_code = 32


class DeviceNotResponsiveError(CheckDeviceReadyError):
    """Raised when a command sent to the device times out without receiving a response."""
    err_code = 33

    def __init__(self, device_name, msg, timeout=None, details=None):
        """Inits a DeviceNotResponsiveError exception.

        Args:
            device_name (str): The name of the device.
            msg (str): An error message string of the form <error_message> <details>.
            timeout (int): Number of seconds before timing out while talking to device.
            details (str): An optional message string describing error details.
        """
        reason = "timed out "
        if timeout:
            reason += "after {} seconds ".format(timeout)
        reason += "when talking to the DUT"
        super(DeviceNotResponsiveError, self).__init__(device_name,
                                                       msg,
                                                       reason=reason,
                                                       details=details)


class NoLogsStreamingError(CheckDeviceReadyError):
    """Raised when expected log output is not seen from the device."""
    err_code = 34

    def __init__(self, device_name, patterns, command=None, timeout=None):
        """Inits a NoLogsStreamingError exception.

        Args:
            device_name (str): The name of the device.
            patterns (list): Pattern list that was expected from the device.
            command (str): Command that was issued in an attempt to find streaming logs.
            timeout (int): Number of seconds spent waiting for logs.
        """
        msg = "patterns {!r} not found in logs".format(patterns)
        if command:
            msg += " after issuing {!r} command".format(command)
        reason = "no logs streaming from UART"
        if timeout:
            reason += " in {} seconds".format(timeout)
        super(NoLogsStreamingError, self).__init__(device_name,
                                                   msg=msg,
                                                   reason=reason)


class NonRootUserError(CheckDeviceReadyError):
    """Raised when the device is logged in as a non-root user."""
    err_code = 35

    def __init__(self, device_name, msg, details=None):
        """Inits a NonRootUserError exception.

        Args:
            device_name (str): The name of the device.
            msg (str): An error message string of the form <error_message> <details>.
            details (str): An optional message string describing additional error details.
        """

        super(NonRootUserError, self).__init__(device_name,
                                               msg,
                                               reason="logged in as non-root user",
                                               details=details)


class LoggingAgentNotEnabledError(CheckDeviceReadyError):
    """Raised when GDM detects that the autolog agent is not installed."""
    err_code = 36

    def __init__(self, device_name, msg):
        """Inits a LoggingAgentNotEnabledError exception.

        Args:
            device_name (str): The name of the device.
            msg (str): An error message string of the form <error_message> <details>.
        """

        super(LoggingAgentNotEnabledError, self).__init__(device_name,
                                                          msg,
                                                          reason="agent not installed")


class BootloaderModeError(CheckDeviceReadyError):
    """Raised when GDM detects that the device is at the bootloader prompt."""
    err_code = 37

    def __init__(self, device_name, msg):
        """Inits a BootloaderModeError exception.

        Args:
            device_name (str): The name of the device.
            msg (str): An error message string of the form <error_message> <details>.
        """

        super(BootloaderModeError, self).__init__(device_name,
                                                  msg,
                                                  reason="found a bootloader prompt")


class DfuModeError(CheckDeviceReadyError):
    """Raised when GDM detects that the device is at the DFU prompt."""
    err_code = 38

    def __init__(self, device_name, msg):
        """Inits a DfuModeError exception.

        Args:
            device_name (str): The name of the device.
            msg (str): An error message string of the form <error_message> <details>.
        """

        super(DfuModeError, self).__init__(device_name,
                                           msg,
                                           reason="found a DFU Linux prompt")


class DeviceNotLoggedInError(CheckDeviceReadyError):
    """Raised when the device is at a login prompt."""
    err_code = 39

    def __init__(self, device_name, msg, details=None):
        """Inits a DeviceNotLoggedInError exception.

        Args:
            device_name (str): The name of the device.
            msg (str): An error message string of the form <error_message> <details>.
            details (str): An optional message string describing additional error details.
        """

        super(DeviceNotLoggedInError, self).__init__(device_name,
                                                     msg,
                                                     reason="device not logged in",
                                                     details=details)


class UnterminatedQuoteError(CheckDeviceReadyError):
    """Raised when GDM detects a shell continuation prompt."""
    err_code = 40

    def __init__(self, device_name, msg):
        """Inits a UnterminatedQuoteError exception.

        Args:
            device_name (str): The name of the device.
            msg (str): An error message string of the form <error_message> <details>.
        """

        super(UnterminatedQuoteError, self).__init__(device_name,
                                                     msg,
                                                     reason="found an 'unterminated quote' prompt")


class StorageNotHealthyError(CheckDeviceReadyError):
    """Raised when GDM detects a problem with device storage."""
    err_code = 41

    def __init__(self, device_name, msg, details=None, recovery=None):
        """Inits a StorageNotHealthyError exception.

        Args:
            device_name (str): The name of the device.
            msg (str): An error message string of the form <error_message> <details>.
            details (str): An optional message string describing additional error details.
            recovery (str): An optional message string describing further recovery
                            options if attempted recover does not work.
        """
        recovery = recovery or "reflash the device with a valid build"
        super(StorageNotHealthyError, self).__init__(device_name,
                                                     msg,
                                                     details=details,
                                                     recovery=recovery)


class BatteryTooLowError(CheckDeviceReadyError):
    """Raised when GDM detects the device in a low battery state preventing normal function."""
    err_code = 42

    def __init__(self, device_name, msg):
        """Inits a BatteryTooLowError exception.

        Args:
            device_name (str): The name of the device.
            msg (str): An error message string of the form <error_message> <details>.
        """

        super(BatteryTooLowError, self).__init__(device_name,
                                                 msg,
                                                 reason="battery is too low or dead")


class PasswordNotDisabledError(CheckDeviceReadyError):
    """Raised when the device root user has a password set unexpectedly."""
    err_code = 43

    def __init__(self, device_name, msg):
        """Inits a PasswordNotDisabledError exception.

        Args:
            device_name (str): The name of the device.
            msg (str): An error message string of the form <error_message> <details>.
        """

        super(PasswordNotDisabledError, self).__init__(device_name,
                                                       msg,
                                                       reason="root user still has a password")


class FastbootModeError(CheckDeviceReadyError):
    """Raised when GDM detects that the device is in fast-boot mode."""
    err_code = 44

    def __init__(self, device_name, msg, details=None):
        """Inits a FastbootModeError exception.

        Args:
            device_name (str): The name of the device.
            msg (str): An error message string of the form <error_message> <details>.
            details (str): An optional message string describing additional error details.
        """

        super(FastbootModeError, self).__init__(device_name,
                                                msg,
                                                reason="device is in fastboot mode",
                                                details=details)


class DeviceNotRootedError(CheckDeviceReadyError):
    """Raised when GDM detects that the device is not rooted."""
    err_code = 45

    def __init__(self, device_name, msg):
        """Inits a DeviceNotRootedError exception.

        Args:
            device_name (str): The name of the device.
            msg (str): An error message string of the form <error_message> <details>.
        """

        super(DeviceNotRootedError, self).__init__(device_name,
                                                   msg,
                                                   reason="device is not rooted")


class DeviceNotADBConnectedError(CheckDeviceReadyError):
    """Raised when the device is not available through ADB."""
    err_code = 46

    def __init__(self, device_name, msg, details=None):
        """Inits a DeviceNotADBConnectedError exception.

        Args:
            device_name (str): The name of the device.
            msg (str): An error message string of the form <error_message> <details>.
            details (str): An optional message string describing additional error details.
        """

        super(DeviceNotADBConnectedError, self).__init__(device_name,
                                                         msg,
                                                         reason="device not connected to ADB",
                                                         details=details)


class DeviceBaudrateMismatchError(CheckDeviceReadyError):
    """Raised when the device baudrate doesn't match the target baudrate."""
    err_code = 47

    def __init__(self, device_name, msg, target_baudrate=None):
        """Inits a DeviceBaudrateMismatchError exception.

        Args:
            device_name (str): The name of the device.
            msg (str): An error message string of the form <error_message> <details>.
            target_baudrate (int): The baudrate that the device should be at.
        """
        if not target_baudrate:
            target_baudrate = "UNKNOWN"
        self.target_baudrate = target_baudrate
        reason = "Target baudrate: {}".format(target_baudrate)
        super(DeviceBaudrateMismatchError, self).__init__(device_name,
                                                          msg,
                                                          reason=reason)


class HubFailedToRespondError(CheckDeviceReadyError):
    """Raised when Hub device failes to respond."""
    err_code = 48

    def __init__(self, device_name, msg, details=None):
        """Inits a HubFailedToRespondError exception.

        Args:
            device_name (str): The name of the hub device.
            msg (str): An error message string of the form <error_message> <details>.
            details (str): An optional message string describing error details.
        """

        super(HubFailedToRespondError, self).__init__(device_name,
                                                      msg,
                                                      reason="hub needs reboot",
                                                      details=details)


class DeviceMissingPackagesError(CheckDeviceReadyError):
    """Raised when the device is missing some packages required for testing."""
    err_code = 49

    def __init__(self, device_name, msg, package_list=None, details=None):
        """Initializes a DeviceMissingPackagesError exception.

        Args:
            device_name (str): The name of the device.
            msg (str): An error message string of the form <error_message> <details>.
            package_list (list or None): list of missing package names (strings).
            details (str): An optional message string describing additional error details.
        """
        self.package_list = package_list

        if package_list is None:
            packages = "[<no package list available>]"
        else:
            packages = str(package_list)

        super(DeviceMissingPackagesError, self).__init__(
            device_name, msg, reason="missing testing packages {}".format(packages),
            details=details)


class DevicePropertiesNotAvailableError(CheckDeviceReadyError):
    """Raised when a device without shell does not have all properties set."""
    err_code = 51

    def __init__(self, device_name, msg, details=None):
        """Inits a DevicePropertiesNotAvailableError exception.

        Args:
            device_name (str): The name of the device.
            msg (str): An error message string of the form <error_message> <details>.
            details (str): An optional message string describing additional error details.
        """

        super(DevicePropertiesNotAvailableError, self).__init__(
            device_name,
            msg,
            reason="not all required properties parsed from logs",
            details=details)


class DeviceBinaryMissingError(CheckDeviceReadyError):
    """Raised when a device does not have a required binary installed."""
    err_code = 52

    def __init__(self, device_name, msg):
        """Inits a DeviceBinaryMissingError exception.

        Args:
            device_name (str): The name of the device.
            msg (str): An error message string of the form <error_message> <details>.
        """

        super(DeviceBinaryMissingError, self).__init__(
            device_name,
            msg,
            reason="Required binary not found on device")


class SwitchboardCreationError(CheckDeviceReadyError):
    """Raised if unable to initiate switchboard."""
    err_code = 53

    def __init__(self, device_name, msg):
        """Inits a SwitchboardCreationError exception.

        Args:
            device_name (str): The name of the device.
            msg (str): An error message string of the form <error_message> <details>.
        """

        super(SwitchboardCreationError, self).__init__(
            device_name,
            msg,
            reason="Unable to create switchboard.")


class DeviceInFactoryTestModeError(CheckDeviceReadyError):
    """Raised when device is in factory test mode."""
    err_code = 54

    def __init__(self, device_name):
        """Inits DeviceInFactoryTestModeError.

        Args:
            device_name (str): The name of the device.

        """
        super(DeviceInFactoryTestModeError, self).__init__(device_name,
                                                           "Device in factory test mode")


class DeviceIpRouteError(CheckDeviceReadyError):
    """Raised when device defaults to IP routing over the Ethernet interface instead of Wi-Fi."""
    err_code = 55

    def __init__(self, device_name, msg=None, reason=None, details=None, recovery=None):
        if msg is None:
            msg = "defaults to routing IP packets over the Ethernet interface instead of Wi-Fi"

        super(DeviceIpRouteError, self).__init__(device_name, msg=msg, reason=reason,
                                                 details=details, recovery=recovery)


class DeviceServiceNotYetStartedError(CheckDeviceReadyError):
    """Raised when device services are still getting ready."""
    err_code = 57


class CheckTestbedReadyError(GazooDeviceError):
    """GazooDeviceError variant used in testbed readiness checks."""
    err_code = 58

    def __init__(self, msg, details=None, recovery=None):
        """Inits a CheckTestbedReadyError exception.

        Args:
            msg (str): An error message string of the form <error_message> <details>.
            details (str): An optional message string describing error details.
            recovery (str): An optional message string describing further recovery
                            options if attempted recover does not work.
        """
        error_str = "testbed {}.".format(msg)
        if details:
            error_str += " Details: {}.".format(details)
        if recovery:
            error_str += " Recovery: {}.".format(recovery)
        error_str += " GDM Version: {}.".format(gdm_version)

        self.properties = {}     # testing properties of the testbed
        self.checks_passed = []  # names of health check methods that passed prior to the failure

        super(CheckTestbedReadyError, self).__init__(error_str)


class TestbedWifiNotAvailableError(CheckTestbedReadyError):
    """Raised when a the SSID of a wifi network is not available to the testbed."""
    err_code = 59

    def __init__(self, ssid, available_networks, details=None, recovery=None):
        """Inits a TestbedWifiNotAvailableError exception.

        Args:
            ssid (str): SSID of wifi network.
            available_networks (list): List of available wifi network SSIDs.
            details (str): An optional message string describing error details.
            recovery (str): An optional message string describing further recovery
                            options if attempted recover does not work.
        """
        msg = "unable to find available wifi network with ssid {!r}.".format(ssid)
        msg += " Available networks: {}".format(available_networks or "none")
        super(TestbedWifiNotAvailableError, self).__init__(msg, details, recovery)


class ProcessNotRunningError(CheckDeviceReadyError):
    """Raised when an expected process is not running on the device."""
    err_code = 60

    def __init__(self, device_name, msg, details=None):
        """Inits a ProcessNotRunningError exception.

        Args:
            device_name (str): The name of the device.
            msg (str): An error message string of the form <error_message> <details>.
            details (str): An optional message string describing error details.
        """
        super(ProcessNotRunningError, self).__init__(device_name,
                                                     msg,
                                                     details=details)


class IncompatibleFirmwareError(CheckDeviceReadyError):
    """Raised when the device has a firmware build incompatible with GDM."""
    err_code = 63


class DownloadKeyError(GazooDeviceError):
    """Raised when the host is unable to download a key required by GDM."""
    err_code = 64

    def __init__(self, key_type, download_errors):
        """Inits a DownloadKeyError exception.

        Args:
            key_type (str): type of key.
            download_errors (list): errors that occurred when attempting to download the key.
        """
        self.key_type = key_type
        super().__init__("unable to download {!r} key to host: {}"
                         .format(key_type, ", ".join(repr(err) for err in download_errors)))


class TestbedMissingExternalStorageError(CheckTestbedReadyError):
    """Raised when devices in the testbed are missing external storage."""
    err_code = 65

    def __init__(self, device_names, details=None, recovery=None):
        """Initializes a TestbedMissingExternalStorageError exception.

        Args:
            device_names (list): names of devices missing external storage.
            details (str): An optional message string describing error details.
            recovery (str): An optional message string describing further recovery
                            options if attempted recovery does not work.
        """
        msg = "devices missing external storage: {}".format(device_names)
        super().__init__(msg, details, recovery)


class CapabilityNotReadyError(CheckDeviceReadyError):
    """Raised when capability not ready."""
    err_code = 66
