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

"""Base class for all primary and virtual device classes."""
# pylint: disable=comparison-with-callable
import difflib
import functools
import inspect

import os
import re
import shutil
import time
import weakref

from gazoo_device import config
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.base_classes import first_party_device_base
from gazoo_device.switchboard import log_process
from gazoo_device.switchboard import parser
from gazoo_device.utility import build_utils
from gazoo_device.utility import supported_classes

logger = gdm_logger.get_gdm_logger()

# Number of times to retry urllib action (e.g. urlopen, urlretrieve...)
MAX_RETRY_URLLIB_ACTION = 3
ERROR_PREFIX = "Exception_"

TIMEOUTS = {
    "CONNECTED": 3,
    "SHELL": 60
}


def create_symlink(file_path, symlink_file_name):
    """Creates or updates a symlink symlink_file_name to the file_path specified.

    Args:
        file_path (path): to file to create symlink to
        symlink_file_name (str): to create or update in directory of file_path.

    Returns:
        str: Path to symlink file created or updated
    """

    directory = os.path.dirname(file_path)
    filename = os.path.basename(file_path)

    tmp_symlink_path = os.path.join(directory, symlink_file_name + ".tmp")
    symlink_path = os.path.join(directory, symlink_file_name)

    # We use a tmp name first in case this is already linked
    if os.path.lexists(tmp_symlink_path):
        os.remove(tmp_symlink_path)
    os.symlink(filename, tmp_symlink_path)
    os.rename(tmp_symlink_path, symlink_path)
    return symlink_path


def get_log_filename(log_directory, device_name, name_prefix=""):
    """Returns the full path of log filename using the information provided.

    Args:
        log_directory (path): to where the log file should be created.
        device_name (str): to use in the log filename
        name_prefix (str): string to prepend to the start of the log file.

    Returns:
        str: Path to log filename using the information provided.
    """

    log_timestamp = time.strftime("%Y%m%d-%H%M%S")
    if name_prefix:
        log_file_name = "{}-{}-{}.txt".format(name_prefix, device_name, log_timestamp)
    else:
        log_file_name = "{}-{}.txt".format(device_name, log_timestamp)
    return os.path.join(log_directory, log_file_name)


class GazooDeviceBase(first_party_device_base.FirstPartyDeviceBase):
    """Base class for all primary and virtual device classes."""
    _has_button_support = False
    # Paths to event filters relative to the filter directory
    _default_filters = []
    _CONNECTION_TIMEOUT = 3
    _COMMUNICATION_KWARGS = {}
    _OWNER_LDAP = ""  # override in child classes

    def __init__(self,
                 manager,
                 device_config,
                 log_file_name=None,
                 log_directory=None):
        self._log_object_lifecycle_event("__init__")
        self.manager_weakref = weakref.ref(manager)

        # Create a dictionary to store "properties".  For now keep the
        # classification of "persistent" and "optional".
        self.props = {'persistent_identifiers': device_config["persistent"],
                      'optional': device_config["options"]}

        self._make_device_ready_setting = device_config.get("make_device_ready", "on")
        if not isinstance(device_config.get("make_device_ready", "on"), str):
            raise errors.GazooDeviceError("Device creation failed. 'make_device_ready' "
                                          "should be a string. but instead it is a {}".
                                          format(str(type(device_config["make_device_ready"]))))
        self._make_device_ready_setting = self._make_device_ready_setting.lower()

        if self._make_device_ready_setting not in ["on", "off", "check_only"]:
            raise errors.GazooDeviceError("Device creation failed. 'make_device_ready' "
                                          "should be 'on', 'off' or 'check_only' not {}".
                                          format(device_config["make_device_ready"]))

        self._commands = {}
        self._regexes = {}
        self._timeouts = TIMEOUTS.copy()
        self.filter_paths = self._get_default_filters()
        self.filter_paths += device_config.get("filters") or []

        self._build_autocompleter = build_utils.BuildAutoCompleter(self.owner)
        if not hasattr(self, "_build_obtainer"):
            self._build_obtainer = build_utils.BuildObtainer(self.name, owner=self.owner)

        logger.debug("{} device_config: {}", self.name, self.props['persistent_identifiers'])
        logger.debug("{} device_options: {}", self.name, self.props['optional'])

        # Initialize log files
        self.log_directory = log_directory
        if log_file_name:
            self._log_file_name = os.path.join(log_directory, log_file_name)
        else:
            log_name_prefix = device_config["log_name_prefix"]
            self._log_file_name = get_log_filename(log_directory,
                                                   self.name,
                                                   name_prefix=log_name_prefix)
        self._update_event_filename_and_symlinks()
        if hasattr(self, "_COMMUNICATION_TYPE"):
            self.COMMUNICATION_TYPE = self._COMMUNICATION_TYPE
        if hasattr(self, "_DEVICE_TYPE"):
            self.DEVICE_TYPE = self._DEVICE_TYPE
        self.device_type = self.DEVICE_TYPE

    @decorators.SettableProperty
    def alias(self):
        """Returns the user-defined device alias (string)."""
        return self.props['optional']['alias']

    @decorators.PersistentProperty
    def commands(self):
        """Dictionary of commands issued to the device via shell."""
        return self._commands

    @decorators.PersistentProperty
    def communication_address(self):
        """Returns the address of the main communication port.

        Returns:
            str: path or address of main communication port.
        """
        name = self.props['persistent_identifiers'].get('console_port_name')
        if name:
            return name

        return self.props['persistent_identifiers'].get('adb_serial', 'None')

    @decorators.DynamicProperty
    def connected(self):
        """Returns whether or not device is connected."""
        device_config = {'persistent': self.props["persistent_identifiers"]}
        return self.is_connected(device_config)

    @decorators.PersistentProperty
    def health_checks(self):
        """Returns list of methods to execute as health checks."""
        return [self.check_usb_hub_ready,
                self.device_is_connected,
                self.check_create_switchboard]

    @decorators.DynamicProperty
    def log_file_name(self):
        """Returns current log file name in use.

        Returns:
            str: Path to current log file name.

        Note:
            When the device has been recently created it might be possible that
            the log file path does not yet exist but will be created very soon.
            The caller is still expected to check if the file path returned
            exists. The caller should refer to this property often because log
            rotation might cause the log path to change depending on the
            max_log_size value currently in use.
        """
        current_log_filename = self._log_file_name

        # Check if log file has rotated to next log filename
        next_log_filename = log_process.get_next_log_filename(current_log_filename)
        while os.path.exists(next_log_filename):
            current_log_filename = next_log_filename
            next_log_filename = log_process.get_next_log_filename(current_log_filename)
        return current_log_filename

    @decorators.PersistentProperty
    def model(self):
        return self.props['persistent_identifiers']['model']

    @decorators.PersistentProperty
    def name(self):
        return self.props['persistent_identifiers']['name']

    @decorators.PersistentProperty
    def owner(self):
        """LDAP associated with the owner of this device class."""
        return getattr(self, "_OWNER_LDAP", "")

    @decorators.PersistentProperty
    def serial_number(self):
        return self.props['persistent_identifiers'].get('serial_number')

    @property
    def event_parser(self):
        """Allows one to query events that have happened in the logs."""
        if not hasattr(self, "_event_parser"):
            self._event_parser = parser.Parser(
                self.filter_paths, device_name=self.name, event_file_path=self.event_file_name)
        return self._event_parser

    @decorators.PersistentProperty
    def regexes(self):
        """Regular expressions used to retrieve properties, events and states from device output.

        Returns:
            dict: mapping of name to regular expression.
        """
        return self._regexes

    @decorators.PersistentProperty
    def timeouts(self):
        """Dictionary of default timeouts to use when expecting certain actions."""
        return self._timeouts

    @decorators.PersistentProperty
    def build_properties(self):
        return self._build_autocompleter.get_default_values(self.DEVICE_TYPE)

    @decorators.LogDecorator(logger)
    def add_new_filter(self, filter_path):
        """Adds new log filter at path specified.

        Args:
            filter_path (str): filter file to add

        Raises:
            GazooDeviceError: if feature is not available for this device or
                             if filter_path doesn't exist
        """
        self.event_parser.load_filter_file(filter_path)
        self.switchboard.add_new_filter(filter_path)

    @decorators.health_check
    def check_create_switchboard(self):
        """Checks connection and creates switchboard through invocation."""
        self.switchboard.add_log_note("{} switchboard successfully started.".format(self.name))

    @decorators.health_check
    def device_is_connected(self):
        """Checks that device shows up as a connection on the host machine.

        Raises:
           DeviceNotConnectedError: if device is not connected.
        """
        logger.info(
            "{} waiting up to {}s for device to be connected.".format(
                self.name, self.timeouts["CONNECTED"]))
        end_time = time.time() + self.timeouts["CONNECTED"]
        while time.time() < end_time:
            if self.connected:  # pylint: disable=using-constant-test
                return
            time.sleep(.5)
        raise errors.DeviceNotConnectedError(
            self.name, msg="device not reachable from host machine.")

    @decorators.LogDecorator(logger, decorators.DEBUG)
    def close(self):
        """Calls close on the communication ports and resets anything needed.

        Note:
            Resets the buttons and terminates the child processes.
        """
        if hasattr(self, '_switchboard'):
            self.switchboard.close()
            self.switchboard.ensure_path_unlocked(self.name, self.communication_address)
            del self._switchboard
            self.reset_all_capabilities()

        if hasattr(self, '_event_parser'):
            del self._event_parser

        if hasattr(self, '_build_obtainer'):
            self._build_obtainer.close()
            del self._build_obtainer

        if hasattr(self, "manager_weakref"):
            manager_instance = self.manager_weakref()
            if manager_instance is not None:
                if self.name in manager_instance._open_devices:
                    self._log_object_lifecycle_event("close")
                    del manager_instance._open_devices[self.name]
            del manager_instance

    @decorators.LogDecorator(logger)
    def check_device_ready(self):
        """Checks if the device is healthy by executing a series of health check methods."""
        self._execute_health_check_methods(self.health_checks)

    @decorators.health_check
    def check_usb_hub_ready(self):
        """Check if the device's USB hub is configured and ready, if it exists."""
        if not self.is_detected():
            return
        if not hasattr(type(self), 'usb_hub'):
            return

        usb_hub_props = ["device_usb_hub_name", "device_usb_port"]
        unset_props = [prop for prop in usb_hub_props
                       if hasattr(type(self), prop) and not getattr(self, prop)]
        unset_persistent_props = [
            prop for prop in unset_props
            if isinstance(getattr(type(self), prop), decorators.PersistentProperty)]
        unset_settable_props = [
            prop for prop in unset_props
            if isinstance(getattr(type(self), prop), decorators.SettableProperty)]

        if unset_persistent_props or unset_settable_props:
            persistent_msg, settable_msg = "", ""
            if unset_persistent_props:
                persistent_msg = "use 'gdm redetect {}' to set {}".format(
                    self.name, ", ".join(unset_persistent_props))
            if unset_settable_props:
                settable_msg = "use 'gdm set-prop {} <property> <value>' to set {}".format(
                    self.name, ", ".join(unset_settable_props))
            if unset_persistent_props and unset_settable_props:
                how_to_fix_msg = f"{persistent_msg} and {settable_msg}"
            else:
                how_to_fix_msg = persistent_msg or settable_msg
            logger.info(f"{self.name} usb_hub capability is not available. "
                        f"If a USB hub is connected, {how_to_fix_msg}.")
            return

        try:
            logger.info("{} device usb port is set to {}".format(self.name,
                                                                 self.usb_hub.get_device_power()))
        except ValueError as err:
            logger.info("{} did not initiate usb_hub capability. Error: {!r}".format(self.name,
                                                                                     err))

    def get_dynamic_properties(self):
        """Returns a dictionary of prop, value for each dynamic property."""
        names = self.get_dynamic_property_names()
        return self._get_properties(names)

    def get_persistent_properties(self):
        """Returns a dictionary of prop, value for each persistent property."""
        names = self.get_persistent_property_names()
        return self._get_properties(names)

    def get_property(self, name, raise_error=False):
        """Retrieves a property value (can be nested).

        Args:
            name (str): name of a single property to fetch.
            raise_error (bool): raise error if unable to retrieve property

        Returns:
            object: value of the specified dynamic property.

        Raises:
            GazooDeviceError: property value is not a plain data object.
            AttributeError: property doesn't exist.
            Exception: property is not retrieveable for arbitrary reason.

        Note:
           Expects property value to be a plain data object.
           Returns a string when property doesn't exist or property raises an error.
           Able to process both device properties (firmware_version) and
           capability properties (wpan.ncp_address)
        """
        instance = self
        original_name = name
        try:
            if '.' in name:  # capability property
                instance = getattr(self, name.split('.')[0])
                name = name.split('.')[1]
            value = getattr(instance, name)
            if callable(value):
                raise errors.GazooDeviceError("{}'s {} is a method"
                                              .format(self.name, original_name))
            return value
        except AttributeError:
            if name in self.props['optional']:
                return self.props['optional'][name]
            if raise_error:
                raise
            close_matches = difflib.get_close_matches(name, self.get_property_names())
            return "{} does not have a known property '{}'. Close matches: {}".format(
                self.name,
                name,
                " or ".join(close_matches))
        except Exception as err:
            if raise_error:
                raise
            error_type = type(err).__name__
            logger.info("{} for {}, exception: {}".format(error_type, name, str(err)))
            return ERROR_PREFIX + error_type

    def get_property_names(self):
        """Returns a list of all property names."""
        full_list = list(self.get_dynamic_property_names())
        full_list.extend(self.get_persistent_property_names())
        full_list.extend(self.get_settable_property_names())
        full_list.extend(self.props['optional'])
        return list(set(full_list))

    def get_settable_properties(self):
        """Returns a dictionary of prop, value for each settable property."""
        names = self.get_settable_property_names()
        return self._get_properties(names)

    @decorators.LogDecorator(logger, decorators.DEBUG)
    def set_property(self, prop, value):
        """Set a settable property.

        Args:
          prop (str): property name
          value (object): value of the property name.

        Raises:
            ValueError: if property not settable.
        """
        if prop in self.get_persistent_property_names():
            raise ValueError("{}'s {} is a persistent property and not settable. "
                             "Redetect device if it's wrong.".format(self.name, prop))
        if prop in self.get_dynamic_property_names():
            raise ValueError("{}'s {} is a dynamic property and not settable. ".format(
                self.name, prop))
        self.props['optional'][prop] = value

    @decorators.LogDecorator(logger)
    def start_new_log(self, log_directory=None, log_name_prefix=""):
        """Start a new log and filter event file in the log directory specified.

        Args:
            log_directory (path): to where the new log file should be created.
            log_name_prefix (str): string to prepend to the start of the log file name.

        Note:
            If log_directory is not specified the new log file will be created
            in the same directory as the last log file.
        """
        if not log_directory:
            log_directory = self.log_directory
        new_log_filename = get_log_filename(log_directory,
                                            self.name,
                                            name_prefix=log_name_prefix)
        # Make sure new log file name is different from old log file name
        while self.log_file_name == new_log_filename:  # pylint: disable=comparison-with-callable
            time.sleep(0.5)
            new_log_filename = get_log_filename(log_directory,
                                                self.name,
                                                name_prefix=log_name_prefix)
        self.switchboard.start_new_log(new_log_filename)
        self.log_directory = log_directory
        self._log_file_name = new_log_filename
        if hasattr(self, "_event_parser"):
            del self._event_parser  # stops current log parser to allow update of event file.
        self._update_event_filename_and_symlinks()

    def get_firmware_version_type_or_skip(self, build_info):
        """Retrieves target firmware version and type from info and checks if version on device.

        Args:
            build_info (dict): dictionary of build information from parent method.

        Returns:
            tuple: firmware info as (str: target_version, str: target_firmware_type)

        Raises:
            GazooDeviceError: if unable to find file.
            SkipExceptionError: already on the target build.

        Notes:
            target_version may be:
                'UNKNOWN' if cannot regex version.
            target_firmware_type may be:
                'UNKNOWN' if build_info does not specify a type or if target_version is 'UNKNOWN'.
        """
        if 'build_file' in build_info:
            return "UNKNOWN", "UNKNOWN"  # unable to extract version from local file
        try:
            target_version = self._build_obtainer.get_version(self.DEVICE_TYPE, build_info)
        except Exception:
            return "UNKNOWN", "UNKNOWN"
        try:
            target_firmware_type = self._build_obtainer.get_firmware_type(
                self.DEVICE_TYPE, build_info)
        except Exception:
            target_firmware_type = "UNKNOWN"

        if not build_info.get('forced_upgrade'):
            logger.info("{} checking if build already on device".format(self.name))

            # Skip upgrade if current and target firmware is the same
            cur_firmware_version, cur_firmware_type = self._get_current_firmware()
            if self._is_on_firmware(cur_firmware_version,
                                    cur_firmware_type,
                                    target_version,
                                    target_firmware_type):
                raise decorators.SkipExceptionError("Already on {}{}".format(
                    target_firmware_type + " " if target_firmware_type != "UNKNOWN" else "",
                    target_version))

        return target_version, target_firmware_type

    def is_detected(self):
        """Returns whether or not persistent info has already been retrieved for device."""
        return bool(self.serial_number)

    @decorators.LogDecorator(logger, decorators.DEBUG)
    def make_device_ready(self, setting="on"):
        """Check device readiness and attempt recovery if allowed.

        Args:
            setting (str): 'on'|'off'|'check_only'|'flash_build'.

        Raises:
            GazooDeviceError: if device communication fails.

        Note:
            If setting is 'check_only', will skip recovery.
            If setting is 'off', will skip check_device_ready and recover.
            If setting is 'flash_build', will force upgrade if recovery is unsuccessful.
        """
        if setting == "off":
            return

        # check if the device is ready
        try:
            self.check_device_ready()
        except errors.GazooDeviceError as err:
            if setting == "check_only":
                logger.info("{} skipping device recovery", self.name)
                raise

            logger.info("{} failed check_device_ready with {}".format(self.name, repr(err)))

            # attempt to recover the device
            try:
                self.recover(err)
                logger.info("{} re-checking device readiness after recovery attempt", self.name)
                self.check_device_ready()
            except errors.GazooDeviceError as err:
                if setting != "flash_build":
                    raise

                # force upgrade the device
                logger.info("{} failed check_device_ready after recovery with {}".format(
                    self.name, repr(err)))
                logger.info("{} re-flashing device with a valid build".format(self.name))
                self.upgrade(forced_upgrade=True)

                # check if the device is ready after force upgrade
                logger.info("{} re-checking device readiness after flashing build", self.name)
                self.check_device_ready()
            logger.info("{} successfully recovered to ready state", self.name)

    def obtain_build(self, build_info=None):
        """Obtains build from known source and places it in /tmp/device_name.

        Args:
            build_info (dict): dictionary of build information from parent method.

        Raises:
            GazooDeviceError: if target file does not exist.

        Returns:
            str: local location of build file.

        Note:
            Automatically extracts .tgz files.
        """
        if not build_info:
            build_info = {}
        if build_info.get('method', 0) == 'dropbox':
            build_info['is_dropbox'] = True
            extract_build = False
        else:
            build_info['is_dropbox'] = False
            extract_build = build_info.get('extract_build', True)

        if 'build_file' in build_info:
            build_file = build_info['build_file']
            if not os.path.exists(build_file):
                raise errors.GazooDeviceError("Device {} upgrade failed. Unable to obtain build."
                                              " File {} does not exist".
                                              format(self.name, build_file))
            else:
                local_file_path = os.path.join(
                    self._build_obtainer.local_build_dir,
                    os.path.basename(build_file))
                if build_file != local_file_path:
                    shutil.copy(build_file, self._build_obtainer.local_build_dir)

        else:
            try:
                local_file_path = self._build_obtainer.locate_and_obtain_build(
                    self.DEVICE_TYPE, build_info)
            except Exception as err:
                raise errors.GazooDeviceError("Device {} upgrade failed. "
                                              "Unable to obtain build. Err: {!r}"
                                              .format(self.name, err))

        if extract_build:
            if local_file_path.endswith('.tgz'):
                local_file_path = self._build_obtainer.extract_tgz_build(local_file_path)
            elif local_file_path.endswith('.zip'):
                local_file_path = self._build_obtainer.extract_zip_build(local_file_path)
        return local_file_path

    @decorators.LogDecorator(logger)
    def verify_good_upgrade(self, target_firmware_version, target_firmware_type):
        """Verifies good upgrade by comparing expected firmware to current firmware.

        Args:
            target_firmware_version (str): firmware_version expected to be on device.
            target_firmware_type (str): firmware_type expected to be on device.

        Raises:
            GazooDeviceError: if target firmware does not match current firmware.

        Note:
            will skip target check if
                - target firmware version is unknown.
                - target firmware type is unknown or "unittest" and device supports firmware type.
        """
        supports_firmware_type = hasattr(self.__class__, "firmware_type")

        # determine if verification should be skipped
        if target_firmware_version == "UNKNOWN":  # unable to extract a version
            logger.info("{} target version {}. Skipping verification.".format(
                self.name, target_firmware_version))
            return
        elif target_firmware_type == "unittest" or (supports_firmware_type
                                                    and target_firmware_type == "UNKNOWN"):
            logger.info("{} target firmware type {}. Skipping verification.".format(
                self.name, target_firmware_type))
            return

        # verify current firmware matches target firmware
        cur_firmware_version, cur_firmware_type = self._get_current_firmware()
        if not self._is_on_firmware(cur_firmware_version,
                                    cur_firmware_type,
                                    target_firmware_version,
                                    target_firmware_type):
            raise errors.GazooDeviceError("Expected version {}{} but found {}{}".format(
                target_firmware_type + " " if supports_firmware_type else "",
                target_firmware_version,
                cur_firmware_type + " " if supports_firmware_type else "",
                cur_firmware_version))

    def _upgrade_wrapper(self, stage_number, transfer_and_recover_func, build_info):
        """Wraps around device-specific upgrade stages to obtain build and verify success.

        Args:
            stage_number (int): Total number of stages in upgrade. Varies between 2 and 5.
            transfer_and_recover_func (func): function to transfer build and recover from upgrade.
            build_info (dict): All the user given arguments

        Note:
            Before obtaining build, gets version and checks it against current device version.
            If version on device and not a forced_upgrade skips upgrade.
            If unable to get version from file, proceeds with upgrade and skips
                final version check.
            It leaves other stages like transferring the build, monitoring it, and recovering
                to the device class.
        """
        start_time = time.time()
        user_info = {name: value for name, value in build_info.items()
                     if value is not None and name != "self"}
        build_info_dict = {}
        default_values = self._build_autocompleter.get_default_values(self.device_type)
        build_info_dict.update(default_values)
        build_info_dict.update(user_info)  # user_info overwrites default values

        target_version, target_firmware_type = self.get_firmware_version_type_or_skip(
            build_info_dict)

        logger.info("{} Stage 1/{}: Obtain build", self.name, stage_number)

        local_file_path = self.obtain_build(build_info_dict)

        # Copy firmware image filename to device
        try:
            transfer_and_recover_func(local_file_path, build_info_dict)
        finally:
            try:
                if os.path.isdir(local_file_path):
                    shutil.rmtree(local_file_path)
                elif os.path.isfile(local_file_path):
                    os.remove(local_file_path)
            except Exception as err:
                logger.warning("{} Error while removing build file. Err: {!r}"
                               .format(self.name, err))

        # Verify firmware image is accepted by device and on new version
        self.verify_good_upgrade(target_version, target_firmware_type)
        upgrade_time = time.time() - start_time
        target_firmware_type_str = ""
        if target_firmware_type and target_firmware_type != "UNKNOWN":
            target_firmware_type_str = target_firmware_type + " "
        logger.info("{} successfully flashed with {}build {}", self.name, target_firmware_type_str,
                    target_version, upgrade_time)

    @classmethod
    def get_dynamic_property_names(cls):
        """Returns a list of dynamic property names including capability ones."""
        return cls._get_property_names(decorators.DynamicProperty)

    @classmethod
    def get_settable_property_names(cls):
        """Returns a list of settable property names including capability ones."""
        return cls._get_property_names(decorators.SettableProperty)

    @classmethod
    def get_persistent_property_names(cls):
        """Returns a list of persistent property names including capability ones."""
        names = cls._get_property_names(decorators.PersistentProperty)
        for property_value in config.CLASS_PROPERTY_TYPES:
            names += cls._get_property_names(property_value)
        return sorted(names)

    @classmethod
    def get_supported_capabilities(cls):
        """Returns a list of names of capabilities supported by this device class."""
        # Deduplicate names: there may be several flavors which share the same interface
        capability_names = {capability_class.get_capability_name()
                            for capability_class in cls.get_supported_capability_flavors()}
        return sorted(list(capability_names))

    @classmethod
    def get_supported_capability_flavors(cls):
        """Returns a set of all capability flavor classes supported by this device class."""
        capability_classes = [member.capability_classes for _, member in inspect.getmembers(cls)
                              if isinstance(member, decorators.CapabilityProperty)]
        return functools.reduce(set.union, capability_classes, set())

    @classmethod
    def has_capabilities(cls, capability_names):
        """Check whether this device class supports all of the given capabilities.

        Args:
            capability_names (list): names of capabilities to check for.

        Note:
            capability names are strings. They can be:
            - capability names ("keypad"),
            - capability interface names ("keypadbase"),
            - capability flavor names ("keypaddefault").
            If an interface name or capability name is specified, the behavior is identical:
                any capability flavor which implements the given interface will match.
            If a flavor name is specified, only that capability flavor will match.
            Different kinds of capability names can be used together (["wifi", "keypaddefault"]).

        Returns:
            bool: True if all of the given capabilities are supported by this device class,
                  False otherwise.

        Raises:
            GazooDeviceError: invalid type of capability_names argument OR
                             one of the capability names provided isn't recognized by GDM.
        """
        valid_capability_names_types = (list, tuple, set)
        if not isinstance(capability_names, valid_capability_names_types):
            raise errors.GazooDeviceError(
                "Invalid type of capability_names. Expected one of: {}, found: {}."
                .format(valid_capability_names_types, type(capability_names)))
        if not all(isinstance(cap_name, str) for cap_name in capability_names):
            raise errors.GazooDeviceError(
                "All capability names must be of string type. Found: {}.".format(capability_names))

        capabilities = []  # Interface or flavor classes
        for cap_name in capability_names:
            cap_name = cap_name.lower()
            if cap_name in supported_classes.SUPPORTED_CAPABILITY_FLAVORS:
                interface_or_flavor = supported_classes.SUPPORTED_CAPABILITY_FLAVORS[cap_name]
            elif cap_name in supported_classes.SUPPORTED_CAPABILITY_INTERFACES:
                interface_or_flavor = supported_classes.SUPPORTED_CAPABILITY_INTERFACES[cap_name]
            elif cap_name in supported_classes.SUPPORTED_CAPABILITIES:
                interface_name = supported_classes.SUPPORTED_CAPABILITIES[cap_name]
                interface_or_flavor = supported_classes.SUPPORTED_CAPABILITY_INTERFACES[
                    interface_name]
            else:
                msg = "\n".join([
                    "Capability {} is not recognized.".format(cap_name),
                    "Supported capability interfaces: {}".format(
                        supported_classes.SUPPORTED_CAPABILITY_INTERFACES.keys()),
                    "Supported capability flavors: {}".format(
                        supported_classes.SUPPORTED_CAPABILITY_FLAVORS.keys()),
                    "Supported capabilities: {}".format(
                        supported_classes.SUPPORTED_CAPABILITIES.keys())
                ])
                raise errors.GazooDeviceError(msg)
            capabilities.append(interface_or_flavor)

        supported_capabilities = cls.get_supported_capability_flavors()
        for requested_capability in capabilities:
            if not any(issubclass(supported_capability, requested_capability)
                       for supported_capability in supported_capabilities):
                return False
        return True

    def lazy_init(self, capability_class, *args, **kwargs):
        """Provides a lazy instantiation mechanism for capabilities.

        The capability instance will not be created until it is accessed for the first time.
        Subsequent accesses will return the same capability instance.
        In other words, no more than one capability instance will be created.
        If a capability is not accessed, the capability instance is not created.

        Args:
            capability_class (class): capability class to instantiate.
            *args (tuple): positional args to the capability's __init__.
                           Prefer using keyword arguments over positional arguments.
            **kwargs (dict): keyword arguments to the capability's __init__.

        Returns:
            CapabilityBase: initialized capability instance.
        """
        capability_name = self._get_private_capability_name(capability_class)
        if not hasattr(self, capability_name):
            capability_inst = capability_class(*args, **kwargs)
            setattr(self, capability_name, capability_inst)
        return getattr(self, capability_name)

    @decorators.LogDecorator(logger, decorators.DEBUG)
    def reset_all_capabilities(self):
        """Resets all capabilities which have been initialized by deleting them.

        Capabilities will be re-initialized on next use (when they're accessed).
        """
        for capability_class in self.get_supported_capability_flavors():
            self.reset_capability(capability_class)

    @decorators.LogDecorator(logger, decorators.DEBUG)
    def reset_capability(self, capability_class):
        """Resets the capability if it's already initialized by deleting it.

        The capability will be re-initialized on next capability use (when it's accessed).

        Args:
            capability_class (object): class of the capability to reset.
        """
        capability_name = self._get_private_capability_name(capability_class)
        if hasattr(self, capability_name):
            delattr(self, capability_name)

    def shell_with_regex(self,
                         command,
                         regex,
                         regex_group=1,
                         command_name="shell",
                         raise_error=False,
                         tries=2,
                         port=0,
                         searchwindowsize=config.SEARCHWINDOWSIZE,
                         check_return_code=False):
        """Sends a command, searches for a regex in the response, and returns a match group.

        Args:
            command (str): command to issue.
            regex (str): regular expression with one or more capturing groups.
            regex_group (int): number of regex group to return.
            command_name (str): command name to appear in log messages.
            raise_error (bool): whether or not to raise error if unable to find a match.
            tries (int): how many times to try executing the command before failing.
            port (int): which port to send the shell command to.
            searchwindowsize (int): Number of the last bytes to look at
            check_return_code (bool): whether to check the shell return code.

        Returns:
            str: value of the capturing group with index 'regex_group' in the match.

        Raises:
            GazooDeviceError: if command execution fails, shell return code is non-zero, or
                             couldn't find the requested group in any of the responses.
        """
        for _ in range(tries):
            try:
                response, code = self.shell(command,
                                            command_name=command_name,
                                            port=port,
                                            searchwindowsize=searchwindowsize,
                                            include_return_code=True)
            except errors.GazooDeviceError:
                continue

            if check_return_code and code != 0:
                logger.warning(
                    "{} shell responded with a non-zero return code. "
                    "Output: {}, return code: {}.".format(self.name, response, code))
                continue

            match = re.search(regex, response, re.MULTILINE | re.DOTALL)
            if match:
                max_group = match.lastindex
                if max_group is None:
                    max_group = 0

                if regex_group > max_group:
                    logger.warning(
                        "{}: requested group index ({}) exceeds index of last matched group ({}). "
                        "Matched groups: {}, response: {!r}, regex: {!r}."
                        .format(self.name, regex_group, max_group, match.groups(), response,
                                regex))
                else:
                    return str(match.group(regex_group))
            else:
                logger.debug("{} couldn't find {!r} in {!r}".format(self.name, regex, response))

        msg = "{} unable to retrieve {!r} from {!r} after {} tries".format(self.name, regex,
                                                                           command, tries)

        if raise_error:
            raise errors.GazooDeviceError(msg)
        else:
            logger.warning(msg)
            return ""

    @property
    def switchboard(self):
        """Instance for communicating with the device."""
        if not hasattr(self, "_switchboard"):
            switchboard_kwargs = self._COMMUNICATION_KWARGS.copy()
            switchboard_kwargs["communication_address"] = self.communication_address
            switchboard_kwargs["communication_type"] = self.COMMUNICATION_TYPE
            switchboard_kwargs["log_path"] = self.log_file_name
            switchboard_kwargs["device_name"] = self.name
            switchboard_kwargs["event_parser"] = self.event_parser
            self._switchboard = self.manager_weakref().create_switchboard(**switchboard_kwargs)

        return self._switchboard

    def _log_object_lifecycle_event(self, method_name):
        """Logs a message about a lifecycle event of a python object.

        Args:
            method_name (str): name of the method called on the object.
        """
        logger.debug("{} called on {} (id = {}) in process {}.".format(
            method_name, self, id(self), os.getpid()))

    def _execute_health_check_methods(self, health_checks):
        """Execute health checks on the device.

        Args:
            health_checks (list): list of methods to execute as health checks.

        Raises:
            CheckDeviceReadyError: if health check fails.

        Note:
            Order of health check methods matter. Health check execution will stop at the first
            failing health check.
        """
        checks_passed = []
        for step, health_check_method in enumerate(health_checks):
            method_name = health_check_method.__name__
            health_check_name = method_name.replace("_", " ").strip().capitalize()

            try:
                health_check_method()
            except errors.CheckDeviceReadyError as err:
                logger.info("{} health check {}/{} failed: {}.".format(
                    self.name, step + 1, len(health_checks), health_check_name))
                err.checks_passed = checks_passed
                err.properties = self.props["persistent_identifiers"].copy()
                raise

            checks_passed.append("{}.{}".format(type(self).__name__, method_name))
            logger.info("{} health check {}/{} succeeded: {}.".format(
                self.name, step + 1, len(health_checks), health_check_name))

    def _get_current_firmware(self):
        """Retrieve the current firmware version and type.

        Returns:
            tuple: (str: current firmware version, str: current firmware type)

        Raises:
            GazooDeviceError: if firmware properties could not be retrieved.
        """
        try:
            cur_firmware_version = self.firmware_version
        except Exception as err:
            raise errors.GazooDeviceError("{} unable to get firmware version. Error {!r}".format(
                self.name, err))

        try:
            # not all devices support firmware type
            # use getattr to skip device classes that don't have a firmware_type property
            cur_firmware_type = getattr(self, "firmware_type", None)
        except Exception as err:
            raise errors.GazooDeviceError("{} unable to get firmware type. Error {!r}".format(
                self.name, err))

        return cur_firmware_version, cur_firmware_type

    @classmethod
    def _get_default_filters(cls):
        """Returns the list of full paths to default device event filters.

        Returns:
            list: list of full paths (strings) to default device event filters.
        """
        filters = [os.path.join(config.FILTER_DIRECTORY, filter_path)
                   for filter_path in cls._default_filters]

        if not filters:
            logger.warning("Class {} has no default event filters defined.".format(cls.__name__))

        return filters

    @classmethod
    def _get_private_capability_name(cls, capability_class):
        """Returns the name of the private attribute to use for a given capability class.

        Args:
            capability_class (class): capability class object.

        Returns:
            str: name of the private capability attribute to be used.
        """
        return "_{}".format(capability_class.get_capability_name())

    def _get_properties(self, property_names):
        """Returns a dictionary of prop, value for each property."""
        property_dict = {}
        for name in property_names:
            value = self.get_property(name)
            if isinstance(value, str) and "does not have a known property" in value:
                continue  # property not supported in current flavor
            property_dict[name] = value

        return property_dict

    @classmethod
    def _get_property_names(cls, property_type):
        """Returns the property names for all public properties of the type."""
        classes = cls.get_supported_capability_flavors().copy()
        classes.add(cls)
        property_names = []
        for a_class in classes:
            prefix = "" if a_class == cls else a_class.get_capability_name() + "."
            for name, member in inspect.getmembers(a_class):
                if isinstance(member, property_type) and not name.startswith("_"):
                    property_names.append("{}{}".format(prefix, name))
        return list(set(property_names))

    def _is_on_firmware(self,
                        cur_firmware_version,
                        cur_firmware_type,
                        target_firmware_version,
                        target_firmware_type):
        """Determines if device is on expected firmware.

        Args:
            cur_firmware_version (str): current firmware version on the device.
            cur_firmware_type (str): current firmware type on the device, or None if device does
                                     not support firmware type.
            target_firmware_version (str): expected firmware version.
            target_firmware_type (str): expected firmware type.

        Returns:
            bool: if current firmware matches expected.
        """
        is_on_firmware_version = target_firmware_version in cur_firmware_version
        is_on_firmware_type = (not cur_firmware_type
                               or cur_firmware_type.lower() == target_firmware_type.lower())

        return is_on_firmware_version and is_on_firmware_type

    def _update_event_filename_and_symlinks(self):
        self.log_file_symlink = None
        if self.log_directory == config.DEFAULT_LOG_DIRECTORY:
            log_symlink_name = "{}-latest.txt".format(self.name)
            self.log_file_symlink = create_symlink(self._log_file_name, log_symlink_name)

        self.event_file_name = log_process.get_event_filename(self._log_file_name)
        self.event_file_symlink = None
        if self.log_directory == config.DEFAULT_LOG_DIRECTORY:
            event_symlink_name = "{}-latest-events.txt".format(self.name)
            self.event_file_symlink = create_symlink(self.event_file_name, event_symlink_name)

    def __del__(self):
        self._log_object_lifecycle_event("__del__")
        if hasattr(self, 'close'):
            self.close()
