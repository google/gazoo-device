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

"""Utility module for interaction with adb."""
import enum
import json
import os
import re
import subprocess
import time
from typing import Any, List, Optional, Tuple

from gazoo_device import config
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.utility import host_utils
from gazoo_device.utility import retry

ADB_RETRY_SLEEP = 10
DEFAULT_PORT = 5555
FASTBOOT_TIMEOUT = 10.0
PROPERTY_PATTERN = r"\[(.*)\]: \[(.*)\]\n"
SYSENV_PATTERN = r"(.*)=(.*)\n"


class AdbDeviceState(enum.Enum):
  """ADB device states as found in output of 'adb devices'.

  The values come from connection_state_name() in
  https://android.googlesource.com/platform/system/adb/+/refs/heads/master/transport.cpp#759.
  """
  BOOTLOADER = "bootloader"
  DEVICE = "device"
  HOST = "host"
  OFFLINE = "offline"
  NO_PERMISSIONS = "no permissions"
  RECOVERY = "recovery"
  SIDELOAD = "sideload"
  UNAUTHORIZED = "unauthorized"
  UNKNOWN = "unknown"
  # Not defined by ADB (in case we fail to parse the state).
  UNRECOGNIZED = "unrecognized"


logger = gdm_logger.get_logger()


def bugreport(adb_identifier: str,
              destination_path: str = "./",
              adb_path: Optional[str] = None) -> str:
  """Gets a bugreport to destination_path on host for the adb_identifier.

  Args:
      adb_identifier: Device ADB identifier, a serial number ("abcde123") or an
          IP address and a port number ("12.34.56.78:5555").
      destination_path: Path to destination on host computer where bugreport
          should copied to.
      adb_path: optional alternative path to adb executable. If adb_path is not
          provided then path returned by get_adb_path will be used instead.

  Raises:
      RuntimeError: if adb_path is invalid or adb executable was not found by
          get_adb_path or bugreport failed.
      ValueError: if destination_path does not exist.

  Returns:
      Output from calling 'adb bugreport'.
  """
  destination_dir = os.path.dirname(destination_path)
  if not os.path.exists(destination_dir):
    raise ValueError(f"The destination_path directory {destination_dir} does "
                     "not exist.")
  output, returncode = _adb_command(command=["bugreport", destination_path],
                                    adb_serial=adb_identifier,
                                    adb_path=adb_path,
                                    include_return_code=True)
  if returncode != 0:
    raise RuntimeError(f"Getting bugreport on ADB device {adb_identifier} to "
                       f"{destination_path} failed. "
                       f"Error: {output!r} with return code {returncode}")
  return output


def enter_fastboot(adb_serial, adb_path=None):
  """Enters fastboot mode by calling 'adb reboot bootloader' for the adb_serial provided.

  Args:
      adb_serial (str): Device serial number.
      adb_path (str): optional alternative path to adb executable

  Raises:
      RuntimeError: if adb_path is invalid or adb executable was not found by
                    get_adb_path.

  Returns:
      str: Output from calling 'adb reboot' or None if call fails with
      non-zero
           return code.

  Note:
      If adb_path is not provided then path returned by get_adb_path will be
      used instead. If adb returns a non-zero return code then None will be
      returned.
  """
  return _adb_command(("reboot", "bootloader"), adb_serial, adb_path=adb_path)


def exit_fastboot(fastboot_serial,
                  fastboot_path=None,
                  timeout=FASTBOOT_TIMEOUT):
  """Exits fastboot mode by calling 'fastboot reboot' for the fastboot_serial provided.

  Args:
      fastboot_serial (str): Device fastboot serial number.
      fastboot_path (str): optional alternative path to fastboot executable
      timeout (float): in seconds to wait for fastboot reboot to return

  Raises:
      RuntimeError: if fastboot_path is invalid or fastboot executable was not
                    found by get_fastboot_path.

  Returns:
      str: Output from calling 'fastboot reboot' or None if call fails with
      non-zero
           return code.

  Note:
      If fastboot_path is not provided then path returned by get_fastboot_path
      will be used instead. If fastboot returns a non-zero return code then
      None will be returned.
  """
  if fastboot_path is None:
    fastboot_path = get_fastboot_path()

  if not os.path.exists(fastboot_path):
    raise RuntimeError(
        "The fastboot_path of {} appears to be invalid.".format(fastboot_path))

  try:
    args = ("timeout", str(timeout), fastboot_path, "-s", fastboot_serial,
            "reboot")
    return subprocess.check_output(
        args, stderr=subprocess.STDOUT).decode("utf-8", "replace")
  except subprocess.CalledProcessError:
    return None


def fastboot_unlock_device(fastboot_serial,
                           fastboot_path=None,
                           timeout=FASTBOOT_TIMEOUT):
  """Unlock the device through fastboot.

  Args:
      fastboot_serial (str): Device serial number
      fastboot_path (str): optional alternative path to fastboot executable
      timeout (float): in seconds to wait for fastboot command to return

  Returns:
      str: response from fastboot command
  """
  return _fastboot_command(("flashing", "unlock"),
                           fastboot_serial=fastboot_serial,
                           fastboot_path=fastboot_path,
                           timeout=timeout)


def fastboot_lock_device(fastboot_serial,
                         fastboot_path=None,
                         timeout=FASTBOOT_TIMEOUT):
  """Lock the device through fastboot.

  Args:
      fastboot_serial (str): Device serial number
      fastboot_path (str): optional alternative path to fastboot executable
      timeout (float): in seconds to wait for fastboot command to return

  Returns:
      str: response from fastboot command
  """
  return _fastboot_command(("flashing", "lock"),
                           fastboot_serial=fastboot_serial,
                           fastboot_path=fastboot_path,
                           timeout=timeout)


def fastboot_check_is_unlocked(fastboot_serial: str,
                               fastboot_path: Optional[str] = None,
                               timeout: float = FASTBOOT_TIMEOUT) -> bool:
  """Checks if the device is unlocked.

  Args:
      fastboot_serial: Device serial number
      fastboot_path: Optional alternative path to fastboot executable
      timeout: In seconds to wait for fastboot command to return

  Raises:
      RuntimeError: If the response is not in the expected format.

  Returns:
      True if the device is unlocked, else False.
  """
  raw_result = _fastboot_command(("getvar", "unlocked"),
                                 fastboot_serial=fastboot_serial,
                                 fastboot_path=fastboot_path,
                                 timeout=timeout)
  # Raw result would be like "unlocked: yes"
  match = re.search(r"unlocked: (yes|no)", raw_result)
  if not match:
    raise RuntimeError(
        f"Unknown output from fastboot getvar unlocked: {raw_result}")
  return match.group(1) == "yes"


def fastboot_wipe_userdata(fastboot_serial,
                           fastboot_path=None,
                           timeout=FASTBOOT_TIMEOUT):
  """Wipe user data on the device through fastboot.

  Args:
      fastboot_serial (str): Device serial number
      fastboot_path (str): optional alternative path to fastboot executable
      timeout (float): in seconds to wait for fastboot command to return

  Returns:
      str: response from fastboot command
  """
  return _fastboot_command(
      "-w",
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
    command = ("reboot", "sideload-auto-reboot")
  else:
    command = ("reboot", "sideload")
  return _adb_command(command, adb_serial=adb_serial, adb_path=adb_path)


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
    raise RuntimeError(
        "sideload_package failed: {} is not a file.".format(package_path))
  return _adb_command(("sideload", package_path),
                      adb_serial=adb_serial,
                      adb_path=adb_path)


def adb_devices(
    adb_path: Optional[str] = None,
    state: Optional[AdbDeviceState] = None
) -> List[Tuple[str, AdbDeviceState]]:
  """Returns parsed output of 'adb devices'.

  Args:
    adb_path: Optional alternative path to the 'adb' executable. Defaults to the
      path returned by get_adb_path().
    state: If provided, only include devices in the given ADB state.

  Returns:
    List of (device identifier, device ADB state) tuples found in
    'adb devices'. The device identifiers are either serial numbers
    ("abcde123") or IP addresses and ports ("12.34.56.78:5555").
  """
  try:
    output = _adb_command("devices", adb_path=adb_path)
  except RuntimeError as err:
    logger.warning(repr(err))
    return []

  output_lines = output.splitlines()
  output_start_marker = "List of devices attached"
  if output_start_marker not in output_lines:
    return []

  output_start_index = output_lines.index(output_start_marker) + 1
  device_lines = [line for line in output_lines[output_start_index:]
                  if line and "\t" in line]

  identifiers_and_states = []
  for device_line in device_lines:
    identifier, _, device_state_str = device_line.partition("\t")
    if "no permissions" in device_state_str:
      # Reasons and URLs vary: "no permissions (<reason>); see [<url>]".
      device_state = AdbDeviceState.NO_PERMISSIONS
    else:
      try:
        device_state = AdbDeviceState(device_state_str)
      except ValueError as e:
        logger.debug(
            f"Failed to parse ADB state {device_state_str!r}. Error: {e!r}")
        device_state = AdbDeviceState.UNRECOGNIZED
    if state is None or state == device_state:
      identifiers_and_states.append((identifier, device_state))
  return identifiers_and_states


def get_adb_devices(adb_path: Optional[str] = None) -> List[str]:
  """Returns ADB device identifiers of available ("device") ADB devices.

  Args:
    adb_path: Optional alternative path to the 'adb' executable. Defaults to the
      path returned by get_adb_path().

  Returns:
    Returns ADB device identifiers of available ("device") ADB devices. The
    device identifiers are either serial numbers ("abcde123") or IP addresses
    and ports ("12.34.56.78:5555").
  """
  return [identifier
          for identifier, _ in adb_devices(adb_path, AdbDeviceState.DEVICE)]


def get_sideload_devices(adb_path: Optional[str] = None) -> List[str]:
  """Returns ADB device identifiers of devices in "sideload" mode.

  Args:
    adb_path: Optional alternative path to the 'adb' executable. Defaults to
        the path returned by get_adb_path().

  Returns:
    Returns ADB device identifiers of devices in "sideload" mode. The device
    identifiers are either serial numbers ("abcde123") or IP addresses and ports
    ("12.34.56.78:5555").
  """
  return [identifier
          for identifier, _ in adb_devices(adb_path, AdbDeviceState.SIDELOAD)]


def is_adb_mode(adb_identifier: str, adb_path: Optional[str] = None) -> bool:
  """Returns whether the ADB identifier is shown as a "device" in 'adb devices'.

  Args:
    adb_identifier: Device ADB identifier, a serial number ("abcde123") or an IP
      address and a port number ("12.34.56.78:5555").
    adb_path: An optional alternative path to the 'adb' executable. If not
        provided, the path returned by get_adb_path() is used instead.
  """
  is_available = adb_identifier in get_adb_devices(adb_path=adb_path)
  if not re.search(host_utils.IP_ADDRESS, adb_identifier):
    return is_available
  ip_address = adb_identifier.split(":")[0]  # Remove the port number.
  # Devices connected through ADB over IP can show up as available ("device") in
  # 'adb devices' even if the device is offline.
  return is_available and host_utils.is_pingable(ip_address)


def is_sideload_mode(
    adb_identifier: str, adb_path: Optional[str] = None) -> bool:
  """Returns True if the adb_identifier is in sideload mode.

  Args:
    adb_identifier: Device ADB identifier, a serial number ("abcde123") or an IP
      address and a port number ("12.34.56.78:5555").
    adb_path: An optional alternative path to the 'adb' executable. If not
        provided, the path returned by get_adb_path() is used instead.
  """
  return adb_identifier in get_sideload_devices(adb_path=adb_path)


def get_adb_path(adb_path=None):
  """Returns the correct adb path to use.

  Args:
      adb_path (str): path to "adb" executable.

  Notes: Starts with passed in path, then looks at config, and finally
    system's default adb if available.

  Raises:
      RuntimeError: if no valid adb path could be found

  Returns:
      str: Path to correct adb executable to use.
  """
  if is_valid_path(adb_path):
    return adb_path
  try:
    with open(config.DEFAULT_GDM_CONFIG_FILE) as config_file:
      gdm_config = json.load(config_file)
    adb_path = gdm_config[config.ADB_BIN_PATH_CONFIG]
  except (IOError, KeyError, ValueError):
    pass

  if is_valid_path(adb_path):
    return adb_path
  elif adb_path:
    logger.warning("adb path {!r} stored in {} does not exist."
                   .format(adb_path, config.DEFAULT_GDM_CONFIG_FILE))

  if host_utils.has_command("adb"):
    return host_utils.get_command_path("adb")
  raise RuntimeError("No valid adb path found using 'which adb'")


def is_valid_path(path):
  return path and os.path.exists(path)


def get_adb_over_ip_identifier(
    adb_identifier: str, port: int = DEFAULT_PORT) -> str:
  """Returns an ADB over IP identifier in the format 'IP_address:port'.

  If the provided adb_identifier does not contain a port number, the default
  port (":5555") is appended to the identifier.

  Args:
    adb_identifier: IP address or IP address and a port number.
    port: TCP port number.

  Raises:
    ValueError: if adb_identifier is not an IP address.
  """
  if not re.search(host_utils.IP_ADDRESS, adb_identifier):
    raise ValueError(f"ADB identifier {adb_identifier!r} is not an IP address.")
  if ":" not in adb_identifier:
    adb_identifier = f"{adb_identifier}:{port}"
  return adb_identifier


def _is_connect_successful(output_and_return_code: Tuple[str, int]) -> bool:
  """Returns whether the connect() call was successful.

  Args:
    output_and_return_code: Output and return code of 'adb connect' command.

  Returns:
    True if the return code of 'adb connect' is 0 and there are no failure
    markers in the command output. Note that 'adb connect' can return a 0 exit
    code even when it fails, which is why we have to check for failure markers.
  """
  output, return_code = output_and_return_code
  failure_markers = [
      "failed to connect",
      "failed to resolve host",
      "missing port in specification",
      "unable to connect",
  ]
  return (return_code == 0 and
          all(marker not in output for marker in failure_markers))


def connect(adb_identifier: str, attempts: int = 3) -> str:
  """Connects to the device via ADB and returns the command output.

  Args:
    adb_identifier: IP address ("12.34.56.78") or IP address and a port number
      ("12.34.56.78:5555"). If a port number is not provided, defaults to 5555.
    attempts: Number of attempts for performing 'adb connect'.

  Raises:
    DeviceError: if 'adb connect' fails, or adb_identifier is not found in
      'adb devices' after 'adb connect'.

  Returns:
    Output of the 'adb connect' command.
  """
  adb_identifier = get_adb_over_ip_identifier(adb_identifier)

  retry_interval_s = 3
  try:
    output, _ = retry.retry(
        func=_adb_command,
        func_kwargs={
            "command": ["connect", adb_identifier],
            "include_return_code": True,
        },
        is_successful=_is_connect_successful,
        timeout=retry_interval_s * attempts,
        interval=retry_interval_s,
        reraise=False)
  except errors.CommunicationTimeoutError as e:
    raise errors.DeviceError(
        f"Unable to connect to device {adb_identifier!r} via ADB. Error: {e!r}")

  try:
    retry.retry(
        func=is_adb_mode,
        func_args=[adb_identifier],
        is_successful=bool,
        timeout=retry_interval_s * attempts,
        interval=retry_interval_s)
  except errors.CommunicationTimeoutError as e:
    raise errors.DeviceError(
        f"{adb_identifier!r} was not found in 'adb devices' after "
        f"'adb connect'. Error: {e!r}")
  return output


def _is_disconnected(adb_identifier: str) -> bool:
  """Returns True if adb_identifier is not present in 'adb devices'."""
  return adb_identifier not in [adb_id for adb_id, _ in adb_devices()]


def disconnect(adb_identifier: str, attempts: int = 3) -> str:
  """Disconnects ADB from the device and returns the command output.

  Args:
    adb_identifier: IP address ("12.34.56.78") or IP address and a port number
      ("12.34.56.78:5555"). If a port number is not provided, defaults to 5555.
    attempts: Number of attempts for performing 'adb disconnect'.

  Raises:
    DeviceError: if 'adb disconnect' fails, or if adb_identifier is still
      present in 'adb devices' after 'adb disconnect'.

  Returns:
    Output of the 'adb disconnect' command.
  """
  adb_identifier = get_adb_over_ip_identifier(adb_identifier)

  retry_interval_s = 3
  try:
    output, _ = retry.retry(
        func=_adb_command,
        func_kwargs={
            "command": ["disconnect", adb_identifier],
            "include_return_code": True,
        },
        is_successful=lambda output_and_code: output_and_code[1] == 0,
        timeout=retry_interval_s * attempts,
        interval=retry_interval_s,
        reraise=False)
  except errors.CommunicationTimeoutError as e:
    raise errors.DeviceError(
        f"Unable to disconnect ADB from device {adb_identifier!r}. "
        f"Error: {e!r}")

  try:
    retry.retry(
        func=_is_disconnected,
        func_kwargs={"adb_identifier": adb_identifier},
        is_successful=bool,
        timeout=retry_interval_s * attempts,
        interval=retry_interval_s)
  except errors.CommunicationTimeoutError as e:
    raise errors.DeviceError(
        f"{adb_identifier!r} was still found in 'adb devices' after "
        f"'adb connect'. Error: {e!r}")
  return output


def shell(adb_serial: str,
          command: str,
          adb_path: Optional[str] = None,
          timeout: Optional[int] = None,
          retries: int = 1,
          include_return_code: bool = False) -> Any:
  """Issues a command to the shell of the adb_serial provided.

  Args:
    adb_serial: Device serial number.
    command: Command to send.
    adb_path: Optional alternative path to adb executable.
    timeout: Time in seconds to wait for adb process to complete.
    retries: Number of times to retry adb command.
    include_return_code: A flag indicating return code should also be
      returned.

  Returns:
    Response string if include_return_code is False; (response, return code)
      tuple otherwise.
  """
  return _adb_command(["shell", command], adb_serial,
                      adb_path=adb_path, timeout=timeout, retries=retries,
                      include_return_code=include_return_code)


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
    logger.warning(repr(err))
    return []

  try:
    output = subprocess.check_output((fastboot_path, "devices"),
                                     stderr=subprocess.STDOUT)
    output = output.decode("utf-8", "replace")
    device_lines = [x for x in output.splitlines() if "astboot" in x]
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
  if host_utils.has_command("fastboot"):
    return host_utils.get_command_path("fastboot")
  raise RuntimeError("No valid fastboot path found using 'which fastboot'")


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
      sources (str or list): Path to one or more source files on device to
        copy to host.
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
    raise ValueError(
        "The destination_path directory {} appears to be invalid.".format(
            destination_dir))

  args = ["pull"]
  if isinstance(sources, list):
    for source_path in sources:
      args.append(source_path)
  else:
    args.append(sources)
  args.append(destination_path)
  output, returncode = _adb_command(
      args, adb_serial, adb_path=adb_path, include_return_code=True)
  if returncode != 0:
    raise RuntimeError("Pulling file(s) {} on ADB device {} to {} failed. "
                       "Error: {!r}".format(sources, adb_serial,
                                            destination_path, output))
  return output


def push_to_device(adb_serial, sources, destination_path, adb_path=None):
  """Pushes sources to destination_path on device for adb_serial provided.

  Args:
      adb_serial (str): Device serial number.
      sources (str or list): Path to one or more source files on host computer
        to copy to device.
      destination_path (str): Path to destination on device where file should
        copied to.
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
        raise ValueError(
            "The source file {} appears to be invalid.".format(source_path))
  else:
    args.append(sources)
    if not os.path.exists(sources):
      raise ValueError(
          "The source file {} appears to be invalid.".format(sources))

  args.append(destination_path)
  output, returncode = _adb_command(
      args, adb_serial, adb_path=adb_path, include_return_code=True)
  if returncode != 0:
    raise RuntimeError("Pushing file(s) {} to {} on ADB device {} failed. "
                       "Error: {!r}".format(sources, destination_path,
                                            adb_serial, output))
  return output


def reboot_device(adb_serial, adb_path=None, retries=1):
  """Calls 'adb reboot' for the adb_serial provided using adb_path.

  Args:
      adb_serial (str): Device serial number.
      adb_path (str): optional alternative path to adb executables
      retries (int): number of times to retry adb command.

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
  return _adb_command("reboot", adb_serial, adb_path=adb_path, retries=retries)


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
      DeviceError: Fastboot is not on computer OR
                   'plugdev' group doesn't exist OR
                   current user is not in the 'plugdev' group.
  """
  if not host_utils.has_command("fastboot"):
    raise errors.DeviceError("Device {} verify user has fastboot failed. "
                             "Fastboot executable is not installed. "
                             "See readme about installing adb (which installs "
                             "fastboot) then su -$USER (or logout and back in) "
                             "to add user to plugdev group".format(device_name))


def wait_for_device(adb_identifier: str, timeout: float) -> None:
  """Waits until the device is detected by ADB.

  Args:
      adb_identifier: ADB device identifier, e.g. serial number or IP address.
      timeout: Time in seconds to wait before giving up.

  Raises:
      CommunicationTimeoutError: Timed out waiting for device detection.
  """
  _, return_code = _adb_command(command="wait-for-device",
                                adb_serial=adb_identifier,
                                timeout=timeout,
                                include_return_code=True)
  if return_code != 0:
    raise errors.CommunicationTimeoutError(
        f"Timeout waiting for device {adb_identifier} after {timeout} seconds")


def wait_for_device_offline(adb_identifier: str, timeout: float = 20,
                            check_interval: float = 1) -> None:
  """Waits until the device is not seen via adb, e.g. reboot started.

  Args:
      adb_identifier: ADB device identifier, e.g. serial number or IP address.
      timeout: Time in seconds to wait before raising timeout.
      check_interval: Interval between checks to see if device is offline.

  Raises:
      CommunicationTimeoutError: Timed out waiting for device to go offline.
  """
  end_time = time.time() + timeout
  while is_adb_mode(adb_identifier):
    if time.time() > end_time:
      raise errors.CommunicationTimeoutError(
          f"Device {adb_identifier} did not go offline in {timeout} seconds.")
    time.sleep(check_interval)


def _adb_command(command,
                 adb_serial=None,
                 adb_path=None,
                 include_return_code=False,
                 timeout=None,
                 retries=1):
  """Returns the output of the adb command and optionally the return code.

  Args:
      command (str or tuple): ADB command and optionally arguments to execute.
      adb_serial (str): Device serial number
      adb_path (str): optional alternative path to adb executable
      include_return_code (bool): flag indicating return code should also be
        returned.
      timeout (int): time in seconds to wait for adb process to complete.
      retries (int): number of times to retry adb command.

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
  if isinstance(command, str):
    args.append(command)
  elif isinstance(command, (list, tuple)):
    args.extend(command)
  for i in range(0, retries):
    proc = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
      output, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
      proc.terminate()
      output, _ = proc.communicate()
    output = output.decode("utf-8", "replace")
    logger.debug("adb command {!r} to {} returned {!r}".format(
        command, adb_serial, output))
    if include_return_code:
      return output, proc.returncode
    adb_failure_messages = ["error: closed", "adb: device offline"]
    if not any(msg in output for msg in adb_failure_messages):
      return output
    if i < retries - 1:
      logger.info(f"Retrying adb command: {command} in {ADB_RETRY_SLEEP}s")
      time.sleep(ADB_RETRY_SLEEP)
  raise errors.DeviceError(
      f"ADB command failed: {command} with output: {output}")


def _fastboot_command(command,
                      fastboot_serial=None,
                      fastboot_path=None,
                      include_return_code=False,
                      timeout=FASTBOOT_TIMEOUT):
  """Returns the output of the fastboot command and optionally the return code.

  Args:
      command (str or tuple): fastboot command and optionally arguments to
        execute.
      fastboot_serial (str): Device fastboot serial number.
      fastboot_path (str): optional alternative path to fastboot executable
      include_return_code (bool): flag indicating return code should also be
        returned.
      timeout (float): in seconds to wait for fastboot command to return

  Raises:
      RuntimeError: if fastboot_path provided or obtained from
      get_fastboot_path is invalid (executable at path doesn't exist).

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
    raise RuntimeError(
        "The fastboot_path of {} appears to be invalid.".format(fastboot_path))

  if fastboot_serial is None:
    args = ["timeout", str(timeout), fastboot_path]
  else:
    args = ["timeout", str(timeout), fastboot_path, "-s", fastboot_serial]

  if isinstance(command, str):
    args.append(command)
  elif isinstance(command, (list, tuple)):
    args.extend(command)

  proc = subprocess.Popen(
      args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  output, _ = proc.communicate()
  output = output.decode("utf-8", "replace")
  if include_return_code:
    return output, proc.returncode
  return output


def install_package_on_device(package_path: str,
                              adb_serial: Optional[str] = None,
                              adb_path: Optional[str] = None,
                              allow_downgrade: bool = False,
                              allow_test_apk: bool = False,
                              reinstall: bool = False,
                              all_permissions: bool = False) -> None:
  """Installs an apk on a target device.

  Use adb install command to install a package to the system.
  The options are subjected to the adb install command. See the doc.
  https://developer.android.com/studio/command-line/adb#shellcommands

  Args:
      package_path: The path to the package on host machine.
      adb_serial: The device serial, optional.
      adb_path: An optional alternative path to adb executable.
      allow_downgrade: Allows version code downgrade.
      allow_test_apk: Allows test APKs to be installed.
      reinstall: Reinstalls an existing app and keeps its data.
      all_permissions: Grants all runtime permission to the app.

  Raises:
      ValueError: when package_path is not valid.
      DeviceError: when installation failed.
  """
  if not os.path.exists(package_path):
    raise ValueError(
        "install_package_on_device received invalid package_path: {}".format(
            package_path))

  flags_map = {
      "-d": allow_downgrade,
      "-t": allow_test_apk,
      "-r": reinstall,
      "-g": all_permissions,
  }
  command_list = ["install"]
  flags = sorted([flag for flag, value in flags_map.items() if value])
  command_list.extend(flags)
  command_list.append(package_path)
  response = _adb_command(
      tuple(command_list), adb_serial=adb_serial, adb_path=adb_path)
  if "Success\n" not in response:
    raise errors.DeviceError(
        "install_package_on_device failed: {}".format(response))


def uninstall_package_on_device(package_name, adb_serial=None, adb_path=None):
  """Uninstall a package on a target device.

  Args:
      package_name (str): the name of the package, e.g.,
        "com.google.android.apps.somepackage.someapp".
      adb_serial (str): the device serial, optional.
      adb_path (str): optional alternative path to adb executable.

  Raises:
      DeviceError: when uninstall failed.
  """
  response = _adb_command(("uninstall", package_name),
                          adb_serial=adb_serial,
                          adb_path=adb_path)
  if "Success\n" not in response:
    raise errors.DeviceError("uninstall_package_on_device failed.")


def add_port_forwarding(host_port: int,
                        device_port: int,
                        adb_serial: Optional[str] = None,
                        adb_path: Optional[str] = None) -> str:
  """Forwards the socket connection from host to device.

  Args:
      host_port: The port on the host side.
      device_port: The port on the device side.
      adb_serial: The device serial, optional.
      adb_path: Alternative path to adb executable.

  Raises:
      RuntimeError: If the port forwarding doesn't exist.

  Returns:
      The command output.
  """
  commands = ("forward", f"tcp:{host_port}", f"tcp:{device_port}")
  output, returncode = _adb_command(commands,
                                    adb_serial=adb_serial,
                                    adb_path=adb_path,
                                    include_return_code=True)
  if returncode != 0:
    raise RuntimeError(
        f"Failed to add port forwarding on device serial:{adb_serial} from "
        f"host port {host_port} to device port {device_port}. {output}")
  return output


def remove_port_forwarding(host_port: int,
                           adb_serial: Optional[str] = None,
                           adb_path: Optional[str] = None) -> str:
  """Removes a forward socket connection.

  Args:
      host_port: The port on the host side.
      adb_serial: The device serial, optional.
      adb_path: Alternative path to adb executable.

  Raises:
      RuntimeError: If the port forwarding doesn't exist.

  Returns:
      The command output.
  """
  commands = ("forward", "--remove", f"tcp:{host_port}")
  output, returncode = _adb_command(commands,
                                    adb_serial=adb_serial,
                                    adb_path=adb_path,
                                    include_return_code=True)
  if returncode != 0:
    raise RuntimeError(
        f"Failed to remove port forwarding on device serial: {adb_serial} "
        f"on host port {host_port}. {output}")
  return output


def tcpip(adb_serial: Optional[str] = None,
          port: Optional[int] = DEFAULT_PORT,
          adb_path: Optional[str] = None) -> str:
  """Restarts adbd listening on the provided TCP port for the adb_serial.

  Args:
    adb_serial: ADB serial number.
    port: TCP port to listen on.
    adb_path: Alternative path to 'adb' executable.

  Raises:
    RuntimeError: If the command fails.

  Returns:
    The command output.
  """
  output, return_code = _adb_command(
      ["tcpip", str(port)],
      adb_serial=adb_serial,
      adb_path=adb_path,
      include_return_code=True)
  if return_code != 0:
    raise RuntimeError(
        f"ADB failed to start listening on port {port} for ADB serial "
        f"{adb_serial}. Return code: {return_code}, output: {output}.")
  return output
