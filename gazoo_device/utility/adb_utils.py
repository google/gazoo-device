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

"""Utility module for interaction with adb.
"""

from __future__ import absolute_import
import json
import os
import subprocess

from gazoo_device import config
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.utility import host_utils

import six

FASTBOOT_TIMEOUT = 10.0
PROPERTY_PATTERN = r"\[(.*)\]: \[(.*)\]\n"
SYSENV_PATTERN = r"(.*)=(.*)\n"
logger = gdm_logger.get_gdm_logger()


def enter_fastboot(adb_serial, adb_path=None):
    """Enters fastboot mode by calling 'adb reboot bootloader' for the adb_serial provided.

    Args:
        adb_serial (str): Device serial number.
        adb_path (str): optional alternative path to adb executable

    Raises:
        RuntimeError: if adb_path is invalid or adb executable was not found by
                      get_adb_path.

    Returns:
        str: Output from calling 'adb reboot' or None if call fails with non-zero
             return code.

    Note:
        If adb_path is not provided then path returned by get_adb_path will be
        used instead. If adb returns a non-zero return code then None will be
        returned.
    """

    return _adb_command(("reboot", "bootloader"), adb_serial, adb_path=adb_path)


def exit_fastboot(fastboot_serial, fastboot_path=None, timeout=FASTBOOT_TIMEOUT):
    """Exits fastboot mode by calling 'fastboot reboot' for the fastboot_serial provided.

    Args:
        fastboot_serial (str): Device fastboot serial number.
        fastboot_path (str): optional alternative path to fastboot executable
        timeout (float): in seconds to wait for fastboot reboot to return

    Raises:
        RuntimeError: if fastboot_path is invalid or fastboot executable was not
                      found by get_fastboot_path.

    Returns:
        str: Output from calling 'fastboot reboot' or None if call fails with non-zero
             return code.

    Note:
        If fastboot_path is not provided then path returned by get_fastboot_path
        will be used instead. If fastboot returns a non-zero return code then
        None will be returned.
    """

    if fastboot_path is None:
        fastboot_path = get_fastboot_path()

    if not os.path.exists(fastboot_path):
        raise RuntimeError("The fastboot_path of {} appears to be invalid.".
                           format(fastboot_path))

    try:
        args = ("timeout", str(timeout),
                fastboot_path, "-s", fastboot_serial, "reboot")
        return subprocess.check_output(args, stderr=subprocess.STDOUT).decode('utf-8', 'replace')
    except subprocess.CalledProcessError:
        return None


def fastboot_unlock_device(fastboot_serial, fastboot_path=None, timeout=FASTBOOT_TIMEOUT):
    """Unlock the device through fastboot.

    Args:
        fastboot_serial (str): Device serial number
        fastboot_path (str): optional alternative path to fastboot executable
        timeout (float): in seconds to wait for fastboot command to return

    Returns:
        str: response from fastboot command
    """
    return _fastboot_command(('flashing', 'unlock'),
                             fastboot_serial=fastboot_serial,
                             fastboot_path=fastboot_path,
                             timeout=timeout)


def fastboot_lock_device(fastboot_serial, fastboot_path=None, timeout=FASTBOOT_TIMEOUT):
    """Lock the device through fastboot.

    Args:
        fastboot_serial (str): Device serial number
        fastboot_path (str): optional alternative path to fastboot executable
        timeout (float): in seconds to wait for fastboot command to return

    Returns:
        str: response from fastboot command
    """
    return _fastboot_command(('flashing', 'lock'),
                             fastboot_serial=fastboot_serial,
                             fastboot_path=fastboot_path,
                             timeout=timeout)


def fastboot_wipe_userdata(fastboot_serial, fastboot_path=None, timeout=FASTBOOT_TIMEOUT):
    """Wipe user data on the device through fastboot.

    Args:
        fastboot_serial (str): Device serial number
        fastboot_path (str): optional alternative path to fastboot executable
        timeout (float): in seconds to wait for fastboot command to return

    Returns:
        str: response from fastboot command
    """
    return _fastboot_command('-w',
                             fastboot_serial=fastboot_serial,
                             fastboot_path=fastboot_path,
                             timeout=timeout)


def enter_sideload(adb_serial, adb_path=None, auto_reboot=False):
    """Enters sideload mode by calling 'adb reboot sideload' for the adb_serial provided.

    Args:
        adb_serial (str): Device serial number.
        adb_path (str): optional alternative path to adb executable.
        auto_reboot (bool): whether to auto reboot after sideload complete.

    Raises:
        RuntimeError: if adb_path is invalid or adb executable was not found by
                      get_adb_path.

    Returns:
        str: Output from command call.
    """
    if auto_reboot:
        command = ('reboot', 'sideload-auto-reboot')
    else:
        command = ('reboot', 'sideload')
    return _adb_command(command, adb_serial=adb_serial, adb_path=adb_path)


def is_sideload_mode(adb_serial, adb_path=None):
    """Checks if device is in sideload mode.

    Args:
        adb_serial (str): Device serial number.
        adb_path (str): optional alternative path to adb executable

    Raises:
        RuntimeError: if adb_path is invalid or adb_path executable was not found by
                      get_adb_path().

    Returns:
        bool: True if device is in sideload mode. False otherwise.

    Note:
        If adb_path is not provided then path returned by get_adb_path will be used instead.
    """
    return adb_serial in get_sideload_devices(adb_path=adb_path)


def sideload_package(package_path, adb_serial, adb_path=None):
    """Perform "adb sideload <package>" command.

    Args:
        package_path (str): the path of the package to sideload.
        adb_serial (str): Device serial number.
        adb_path (str): optional alternative path to adb executable.

    Returns:
        str: the command output.

    Raises:
        RuntimeError: if package_path is invalid.
    """
    if not os.path.isfile(package_path):
        raise RuntimeError('sideload_package failed: {} is not a file.'.format(package_path))
    return _adb_command(('sideload', package_path), adb_serial=adb_serial, adb_path=adb_path)


def get_sideload_devices(adb_path=None):
    """Returns a list of adb devices in sideload mode.

    Args:
        adb_path (str): optional alternative path to adb executable

    Raises:
        RuntimeError: if adb_path is invalid or adb executable was not found by
                      get_adb_path.

    Returns:
        list: A list of device serial numbers that are in sideload mode.

    Note:
        If adb_path is not provided then path returned by get_adb_path will be
        used instead.
    """
    try:
        output = _adb_command("devices", adb_path=adb_path)
    except RuntimeError as err:
        logger.info("WARNING: {}".format(err))
        return []
    device_lines = [x for x in output.splitlines() if u"\tsideload" in x]
    return [x.split()[0] for x in device_lines]


def get_adb_devices(adb_path=None):
    """Returns a list of available adb devices.

    Args:
        adb_path (str): optional alternative path to adb executable

    Raises:
        RuntimeError: if adb_path is invalid or adb executable was not found by
                      get_adb_path.

    Returns:
        list: A list of device serial numbers returned by 'adb devices'.

    Note:
        If adb_path is not provided then path returned by get_adb_path will be
        used instead.
    """
    try:
        output = _adb_command("devices", adb_path=adb_path)
    except RuntimeError as err:
        logger.info("WARNING: {}".format(err))
        return []
    device_lines = [x for x in output.splitlines() if u"\tdevice" in x]
    return [x.split()[0] for x in device_lines]


def get_adb_path(adb_path=None):
    """Returns the correct adb path to use.

    Args:
        adb_path (str): path to "adb" executable.

    Notes:
       Starts with passed in path, then looks at config,
       and finally system's default adb if available.

    Raises:
        RuntimeError: if no valid adb path could be found

    Returns:
        str: Path to correct adb executable to use.
    """
    if is_valid_path(adb_path):
        return adb_path
    try:
        with open(config.DEFAULT_GDM_CONFIG_FILE, "r") as config_file:
            gdm_config = json.load(config_file)
        adb_path = gdm_config[config.ADB_BIN_PATH_CONFIG]
    except (IOError, KeyError, ValueError):
        pass

    if is_valid_path(adb_path):
        return adb_path
    elif adb_path:
        logger.info("WARNING: adb path {} stored in {} does not exist.".format(
            adb_path, config.DEFAULT_GDM_CONFIG_FILE))

    if host_utils.has_command(u"adb"):
        return host_utils.get_command_path(u"adb")
    raise RuntimeError(
        "No valid adb path found using 'which adb'")


def is_valid_path(path):
    return path and os.path.exists(path)


def shell(adb_serial, command, adb_path=None):
    """Issues a command to the shell of the adb_serial provided.

    Args:
        adb_serial (str): Device serial number
        command (str): command to send
        adb_path (str): optional alternative path to adb executable

    Returns:
        str: response from adb command

    Note:
        If adb_path is not provided then path returned by get_adb_path will be
        used instead.
    """
    return _adb_command(['shell', command], adb_serial, adb_path=adb_path)


def get_fastboot_devices(fastboot_path=None):
    """Returns list of ADB devices in fastboot (bootloader) mode.

    Args:
        fastboot_path (str): optional alternative path to fastboot executable

    Returns:
        list: A list of ADB device serial numbers in fastboot mode.

    Note:
        If fastboot_path is not provided then path returned by get_fastboot_path
        will be used instead.
        If fastboot path invalid, will return empty list.
    """
    try:
        fastboot_path = get_fastboot_path(fastboot_path)
    except RuntimeError as err:
        logger.info("WARNING: {}".format(err))
        return []

    try:
        output = subprocess.check_output((fastboot_path, "devices"),
                                         stderr=subprocess.STDOUT)
        output = output.decode('utf-8', 'replace')
        device_lines = [x for x in output.splitlines() if "\tfastboot" in x]
        return [x.split()[0] for x in device_lines]
    except subprocess.CalledProcessError:
        return []


def get_fastboot_path(fastboot_path=None):
    """Returns the fastboot executable path to use.

    Args:
        fastboot_path (str): path to "fastboot" executable.

    Raises:
        RuntimeError: if no valid fastboot executable could be found

    Returns:
        str: Path to correct fastboot executable to use.
    """
    if is_valid_path(fastboot_path):
        return fastboot_path
    if host_utils.has_command(u"fastboot"):
        return host_utils.get_command_path(u"fastboot")
    raise RuntimeError("No valid fastboot path found using 'which fastboot'")


def is_adb_mode(adb_serial, adb_path=None):
    """Checks if device is in adb mode.

    Args:
        adb_serial (str): Device serial number.
        adb_path (str): optional alternative path to adb executable

    Raises:
        RuntimeError: if adb_path is invalid or adb executable was not found by
                      get_adb_path.

    Returns:
        bool: True if device is in adb mode. False otherwise.

    Note:
        If adb_path is not provided then path returned by get_adb_path will be
        used instead.
    """

    return adb_serial in get_adb_devices(adb_path=adb_path)


def is_device_online(adb_serial, adb_path=None, fastboot_path=None):
    """Returns true if the device appears in either 'adb devices' or 'fastboot devices'.

    Args:
        adb_serial (str): Device serial number.
        adb_path (str): optional alternative path to adb executable
        fastboot_path (str): optional alternative path to fastboot executable

    Returns:
        bool: True if device is in adb or fastboot mode. False otherwise.

    Note:
        If adb_path is not provided then path returned by get_adb_path will be
        used instead. If fastboot_path is not provided then path returned by
        get_fastboot_path will be used instead.
    """
    return (is_adb_mode(adb_serial, adb_path=adb_path) or
            is_fastboot_mode(adb_serial, fastboot_path=fastboot_path))


def is_fastboot_mode(adb_serial, fastboot_path=None):
    """Checks if device is in fastboot mode.

    Args:
        adb_serial (str): Device serial number.
        fastboot_path (str): optional alternative path to fastboot executable

    Raises:
        RuntimeError: if fastboot_path is invalid or fastboot executable was
                      not found by get_fastboot_path.

    Returns:
        bool: True if device is in fastboot mode. False otherwise.

    Note:
        If fastboot_path is not provided then path returned by get_fastboot_path
        will be used instead.
    """

    return adb_serial in get_fastboot_devices(fastboot_path=fastboot_path)


def pull_from_device(adb_serial, sources, destination_path="./", adb_path=None):
    """Pulls sources from device to destination_path on host for adb_serial provided.

    Args:
        adb_serial (str): Device serial number.
        sources (str or list): Path to one or more source files on device to copy
                               to host.
        destination_path (str): Path to destination on host computer where file
                                should copied to.
        adb_path (str): optional alternative path to adb executable

    Raises:
        RuntimeError: if adb_path is invalid or adb executable was not found by
                      get_adb_path or push failed.
        ValueError: if destination_path directory doesn't exist.

    Returns:
        str: Output from calling 'adb push' or None if call raises an erroro
             return code.

    Note:
        If adb_path is not provided then path returned by get_adb_path will be
        used instead. If adb returns a non-zero return code then None will be
        returned. If no destination_path is provided the file will be copied to
        the current working directory on the host computer.
    """
    destination_dir = os.path.dirname(destination_path)
    if destination_dir != "." and not os.path.exists(destination_dir):
        raise ValueError("The destination_path directory {} appears to be invalid.".
                         format(destination_dir))

    args = ["pull"]
    if isinstance(sources, list):
        for source_path in sources:
            args.append(source_path)
    else:
        args.append(sources)
    args.append(destination_path)
    output, returncode = _adb_command(args,
                                      adb_serial,
                                      adb_path=adb_path,
                                      include_return_code=True)
    if returncode != 0:
        raise RuntimeError("Pulling file(s) {} on ADB device {} to {} failed. "
                           "Error: {!r}".
                           format(sources, adb_serial, destination_path, output))
    return output


def push_to_device(adb_serial, sources, destination_path, adb_path=None):
    """Pushes sources to destination_path on device for adb_serial provided.

    Args:
        adb_serial (str): Device serial number.
        sources (str or list): Path to one or more source files on host computer
                               to copy to device.
        destination_path (str): Path to destination on device where file should copied to.
        adb_path (str): optional alternative path to adb executable

    Raises:
        RuntimeError: if adb_path is invalid or adb executable was not found by
                      get_adb_path or push failed.
        ValueError: if source_path doesn't exist.

    Returns:
        str: Output from calling 'adb push' or None if call raises an erroro
             return code.

    Note:
        If adb_path is not provided then path returned by get_adb_path will be
        used instead. If adb returns a non-zero return code then None will be
        returned.
    """

    args = ["push"]
    if isinstance(sources, list):
        for source_path in sources:
            args.append(source_path)
            if not os.path.exists(source_path):
                raise ValueError("The source file {} appears to be invalid.".
                                 format(source_path))
    else:
        args.append(sources)
        if not os.path.exists(sources):
            raise ValueError("The source file {} appears to be invalid.".
                             format(sources))

    args.append(destination_path)
    output, returncode = _adb_command(args,
                                      adb_serial,
                                      adb_path=adb_path,
                                      include_return_code=True)
    if returncode != 0:
        raise RuntimeError("Pushing file(s) {} to {} on ADB device {} failed. "
                           "Error: {!r}".
                           format(sources, destination_path, adb_serial, output))
    return output


def reboot_device(adb_serial, adb_path=None):
    """Calls 'adb reboot' for the adb_serial provided using adb_path.

    Args:
        adb_serial (str): Device serial number.
        adb_path (str): optional alternative path to adb executable

    Raises:
        RuntimeError: if adb_path is invalid or adb executable was not found by
                      get_adb_path.

    Returns:
        str: Output from calling 'adb reboot'.

    Note:
        If adb_path is not provided then path returned by get_adb_path will be
        used instead. If adb returns a non-zero return code then None will be
        returned.
    """

    return _adb_command("reboot", adb_serial, adb_path=adb_path)


def root_device(adb_serial, adb_path=None):
    """Calls 'adb root' for the adb_serial provided using adb_path.

    Args:
        adb_serial (str): Device serial number.
        adb_path (str): optional alternative path to adb executable

    Raises:
        RuntimeError: if adb_path is invalid or adb executable was not found by
                      get_adb_path.

    Returns:
        str: Output from calling 'adb root'.

    Note:
        If adb_path is not provided then path returned by get_adb_path will be
        used instead. If adb returns a non-zero return code then None will be
        returned.
    """

    return _adb_command("root", adb_serial, adb_path=adb_path)


def verify_user_has_fastboot(device_name):
    """Verifies fastboot available and user is root or in plugdev group.

    Args:
        device_name (str): Device name to use in error output.

    Raises:
        GazooDeviceError: Fastboot is not on computer OR
                         'plugdev' group doesn't exist OR
                         current user is not in the 'plugdev' group.
    """

    if not host_utils.has_command('fastboot'):
        raise errors.GazooDeviceError("Device {} verify user has fastboot failed. "
                                      "Fastboot executable is not installed. "
                                      "See readme about installing adb (which installs "
                                      "fastboot) then su -$USER (or logout and back in) "
                                      "to add user to plugdev group".
                                      format(device_name))


def _adb_command(command, adb_serial=None, adb_path=None, include_return_code=False):
    """Returns the output of the adb command and optionally the return code.

    Args:
        command (str or tuple): ADB command and optionally arguments to execute.
        adb_serial (str): Device serial number
        adb_path (str): optional alternative path to adb executable
        include_return_code (bool): flag indicating return code should also be
                                    returned.

    Raises:
        RuntimeError: if adb_path provided or obtained from get_adb_path is
                      invalid (executable at path doesn't exist).

    Returns:
        str: The ADB command output (including stderr)
        tuple: The ADB command output (including stderr) and return code

    Note:
        The stderr is redirected to stdout so callers should use the return code
        or search the output for known errors if they want to determine if the
        command succeeded or not.
    """
    adb_path = get_adb_path(adb_path)

    if adb_serial is None:
        args = [adb_path]
    else:
        args = [adb_path, "-s", adb_serial]
    if isinstance(command, (str, six.text_type)):
        args.append(command)
    elif isinstance(command, (list, tuple)):
        args.extend(command)
    proc = subprocess.Popen(args,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    output, _ = proc.communicate()
    output = output.decode("utf-8", "replace")
    logger.debug("adb command {!r} to {} returned {!r}".format(command, adb_serial, output))
    if include_return_code:
        return output, proc.returncode
    return output


def _fastboot_command(command,
                      fastboot_serial=None,
                      fastboot_path=None,
                      include_return_code=False,
                      timeout=FASTBOOT_TIMEOUT):
    """Returns the output of the fastboot command and optionally the return code.

    Args:
        command (str or tuple): fastboot command and optionally arguments to execute.
        fastboot_serial (str): Device fastboot serial number.
        fastboot_path (str): optional alternative path to fastboot executable
        include_return_code (bool): flag indicating return code should also be
                                    returned.
        timeout (float): in seconds to wait for fastboot command to return

    Raises:
        RuntimeError: if fastboot_path provided or obtained from get_fastboot_path is
                      invalid (executable at path doesn't exist).

    Returns:
        str: The fastboot command output (including stderr)
        tuple: The fastboot command output (including stderr) and return code

    Note:
        The stderr is redirected to stdout so callers should use the return code
        or search the output for known errors if they want to determine if the
        command succeeded or not.
    """
    if fastboot_path is None:
        fastboot_path = get_fastboot_path()
    if not os.path.exists(fastboot_path):
        raise RuntimeError('The fastboot_path of {} appears to be invalid.'.format(fastboot_path))

    if fastboot_serial is None:
        args = ["timeout", str(timeout), fastboot_path]
    else:
        args = ["timeout", str(timeout), fastboot_path, '-s', fastboot_serial]

    if isinstance(command, (str, six.text_type)):
        args.append(command)
    elif isinstance(command, (list, tuple)):
        args.extend(command)

    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output, _ = proc.communicate()
    output = output.decode('utf-8', 'replace')
    if include_return_code:
        return output, proc.returncode
    return output


def install_package_on_device(package_path,
                              adb_serial=None,
                              adb_path=None,
                              allow_downgrade=False,
                              allow_test_apk=False,
                              reinstall=False):
    """Installs an apk on a target device.

    Use adb install command to install a package to the system.
    The options are subjected to the adb install command. See the doc.
    https://developer.android.com/studio/command-line/adb#shellcommands

    Args:
        package_path (str): the path to the package on host machine.
        adb_serial (str): the device serial, optional.
        adb_path (str): optional alternative path to adb executable.
        allow_downgrade (bool): allows version code downgrade.
        allow_test_apk (bool): allows test APKs to be installed.
        reinstall (bool): reinstalls an existing app and keeps its data.

    Raises:
        ValueError: when pacakge_path is not valid.
        GazooDeviceError: when installation failed.
    """
    if not os.path.exists(package_path):
        raise ValueError(
            'install_package_on_device received invalid package_path: {}'.format(package_path))

    flags_map = {
        '-d': allow_downgrade,
        '-t': allow_test_apk,
        '-r': reinstall
    }
    command_list = ['install']
    flags = sorted([flag for flag, value in flags_map.items() if value])
    command_list.extend(flags)
    command_list.append(package_path)
    response = _adb_command(tuple(command_list), adb_serial=adb_serial, adb_path=adb_path)
    if 'Success\n' not in response:
        raise errors.GazooDeviceError('install_package_on_device failed: {}'.format(response))


def uninstall_package_on_device(package_name, adb_serial=None, adb_path=None):
    """Uninstall a package on a target device.

    Args:
        package_name (str): the name of the package, e.g., "com.google.android.apps.tv.launcherx".
        adb_serial (str): the device serial, optional.
        adb_path (str): optional alternative path to adb executable.

    Raises:
        GazooDeviceError: when uninstall failed.
    """
    response = _adb_command(('uninstall', package_name), adb_serial=adb_serial, adb_path=adb_path)
    if 'Success\n' not in response:
        raise errors.GazooDeviceError('uninstall_package_on_device failed.')
