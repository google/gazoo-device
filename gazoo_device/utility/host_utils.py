# Copyright 2023 Google LLC
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
"""Utility module for local host commands."""
import ipaddress
import os
import re
import shutil
import subprocess
from typing import Any
from typing import Collection, Optional, Sequence

from gazoo_device import config
from gazoo_device import data_types
from gazoo_device import errors
from gazoo_device import extensions
from gazoo_device import gdm_logger

_LOGGER = gdm_logger.get_logger()

_PING_DEFAULT_PACKET_COUNT = 1
_PING_DEFAULT_TIMEOUT_SECONDS = 2

ARP_CONNECTED_IPS = r"([\-\w\.]*)\s*ether"
IP_ADDRESS = r"\d+\.\d+\.\d+\.\d+"
SSHABLE_COMMAND = "nc -z -w 2 {} 22"  # Connect to ssh port for up to 2 seconds.

SSH_TIMEOUT = 3
SSH_CONFIG = (
    "-o", "PasswordAuthentication=no", "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes", "-o", f"ConnectTimeout={SSH_TIMEOUT}"
)

_SSH_DISABLE_PSEUDO_TTY = "-T"
DEFAULT_SSH_OPTIONS = (_SSH_DISABLE_PSEUDO_TTY, *SSH_CONFIG)

GET_COMMAND_PATH = "which {}"
GET_CONNECTED_IPS = "/usr/sbin/arp -e"

_SNMPGET_SYSTEM_DESCRIPTION_COMMAND = (
    "snmpget -v 2c -c private {ip_address} 1.3.6.1.2.1.1.1.0")
_SNMPGET_SYSTEM_DESCRIPTION_TIMEOUT = 3

_GCLOUD_MACOS_PATH = "/usr/local/bin/gcloud"
_gcloud_cli = None  # Set by _set_gcloud_cli().

# Set by _get_scp_command().
_scp_use_legacy_option: Optional[tuple[str, ...]] = None


def get_key_path(key_info: data_types.KeyInfo) -> str:
  """Returns the file path corresponding to the key."""
  return os.path.join(config.KEYS_DIRECTORY,
                      key_info.package, key_info.file_name)


def _download_key(key_info: data_types.KeyInfo) -> None:
  """Delegates the key download to the appopriate key download function.

  Prior to calling the download_key() function from the appropriate package,
  ensures that the package key directory exists. Verifies that the key file
  exists after the download. Also sets appropriate permissions for SSH keys.
  The key is downloaded to location determined by get_key_path().

  Args:
      key_info: Key to download.

  Raises:
      FileNotFoundError: If key file doesn't exist after calling download_key().
  """
  key_path = get_key_path(key_info)
  package_key_folder = os.path.dirname(key_path)
  if not os.path.isdir(package_key_folder):
    os.makedirs(package_key_folder)
  key_download_function = extensions.key_to_download_function[key_info]
  key_download_function(key_info, key_path)
  _LOGGER.info(f"{key_info} key downloaded")
  if not os.path.exists(key_path):
    raise FileNotFoundError(f"Key {key_info} was not downloaded to {key_path} "
                            f"after calling {key_download_function}.")
  if (key_info.type == data_types.KeyType.SSH
      and not key_info.file_name.endswith(".pub")):
    _set_key_permissions(key_path)


def generate_ssh_args(ip_address: str,
                      command: Sequence[str],
                      user: str,
                      options: Sequence[str] = DEFAULT_SSH_OPTIONS,
                      key_info: Optional[data_types.KeyInfo] = None
                      ) -> list[str]:
  """Returns a formatted SSH command to send to subprocess.

  Args:
      ip_address: IP address to ssh to.
      command: Command to run over SSH. Can be an empty sequence.
      user: Username to use for SSH.
      options: Extra SSH command line options.
      key_info: SSH key info to use. If None, don't use an SSH key.
  """
  if key_info:
    verify_key(key_info)
    options = list(options) + ["-i", get_key_path(key_info)]
  return [*options, f"{user}@{ip_address}", *command]


def get_command_path(command_name):
  """Return the full path for the given command name.

  Args:
      command_name (str): Name of the command to look for. Example: 'fastboot'.

  Returns:
      str: Output for the given command name.
  """
  path = shutil.which(command_name)
  if path:
    _LOGGER.debug(
        "Found command path for %s using shutil: %s", command_name, path
    )
    return path
  else:
    _LOGGER.error("Failed to get path for %s using shutil", command_name)
    return ""


def get_all_connected_arp_ips():
  """Gets all connected ips from arp -e list.

  Returns:
    list: list of ip addresses.

  Note:
     Does not return ip_addresses listed as 'incomplete'.
  """
  try:
    output = subprocess.check_output(["/usr/sbin/arp", "-e"],
                                     stderr=subprocess.STDOUT)
    addresses = re.findall(ARP_CONNECTED_IPS, output.decode("utf-8", "replace"),
                           re.MULTILINE)
    return addresses
  except subprocess.CalledProcessError as err:
    _LOGGER.warning(
        "Retrieval of connected IPs from the ARP table failed. "
        f"Error: {err!r}. Output: {err.output!r}"
    )
    return []


def is_static_ip(comm_port: str) -> bool:
  return bool(
      re.search(IP_ADDRESS, comm_port)
  )


def get_all_ssh_ips(static_ips: Optional[Collection[str]] = None) -> list[str]:
  """Returns all IPs that respond to ping and accept SSH connections."""
  static_ips = static_ips or []
  ssh_ips = set(static_ips)

  unpingable_ips = {ip for ip in ssh_ips if not is_pingable(ip)}
  if unpingable_ips:
    _LOGGER.info(f"ip_address(es) {unpingable_ips} do not respond to ping.")
  ssh_ips -= unpingable_ips

  unsshable_ips = {ip for ip in ssh_ips if not is_sshable(ip)}
  if unsshable_ips:
    _LOGGER.info(
        f"ip_address(es) {unsshable_ips} do not accept incoming SSH "
        "connections."
    )
  ssh_ips -= unsshable_ips
  return list(ssh_ips)


def get_all_snmp_ips(static_ips: Optional[Sequence[str]] = None) -> list[str]:
  """Returns all IPs that respond to ping and accept snmp protocol."""
  static_ips = static_ips or []
  snmp_ips = set(static_ips)
  snmp_ips = {ip for ip in snmp_ips if is_pingable(ip)}
  non_snmp_ips = {ip for ip in snmp_ips if not accepts_snmp(ip)}
  if non_snmp_ips:
    _LOGGER.info(f"ip_address(es) {non_snmp_ips} do not accept snmp protocol.")
  snmp_ips -= non_snmp_ips
  return list(snmp_ips)


def get_all_yepkit_serials():
  """Returns all Yepkit serials."""
  if not has_command("ykushcmd"):
    _LOGGER.warning("'ykushcmd' is not installed. Cannot get Yepkit serials.")
    return []

  try:
    results = subprocess.check_output(["ykushcmd", "-l"],
                                      stderr=subprocess.STDOUT)
  except subprocess.CalledProcessError as err:
    _LOGGER.warning(
        "Retrieval of Yepkit serials failed. "
        f"Error: {err!r}. Output: {err.output!r}"
    )
    return []

  results = results.decode("utf-8", "replace")
  _LOGGER.debug("get_all_yepkit_serials returned: {!r}".format(results))
  # If no YKUSH boards are found then the YK21624 line will be this instead:
  #    No YKUSH boards found.
  if "No YKUSH boards found" in results:
    return []

  # Typical ykushcmd -l output looks like this:
  #    Attached YKUSH Boards:\n\nYK21624\n\nYK21623
  # Removes blank lines and header
  results = [line for line in results.splitlines() if line]
  return results[1:]


def gcs_command(cmd: str,
                gcs_path: str,
                extra_args: Optional[list[str]] = None,
                cmd_args: Optional[list[str]] = None) -> str:
  """Issues a 'gcloud storage' command and returns the output.

  'gcloud storage' CLI has replaced the legacy 'gsutil' CLI:
  https://cloud.google.com/blog/products/storage-data-transfer/new-gcloud-storage-cli-for-your-data-transfers.

  Args:
    cmd: 'gcloud storage' command to issue (such as "cp").
    gcs_path: Google Cloud Storage path (gs://).
    extra_args: Other arguments to pass to append to the command.
    cmd_args: Command args. Will be appended to command (before gcs_path).
      e.g. ["-R"] can be used with `cp` command. "cp -R <path>"

  Returns:
    Output of the command.

  Raises:
    RuntimeError: Command failed, or there's no valid 'gcloud' binary.
  """
  _set_gcloud_cli()

  cmd_args = cmd_args or []
  extra_args = extra_args or []
  cmd_list = [_gcloud_cli, "storage", cmd, *cmd_args, gcs_path, *extra_args]
  try:
    _LOGGER.debug("[GCS] Calling gcloud with: %r", cmd_list)
    output = subprocess.check_output(
        cmd_list,
        stderr=subprocess.STDOUT,
        text=True)
    _LOGGER.debug("[GCS] Returning from gcloud call with: %r", output)
    return output
  except subprocess.CalledProcessError as err:
    message = f"{' '.join(cmd_list)!r} failed. Output: {err.output}"
    if "Invalid Credentials" in err.output:
      raise errors.GcloudUnauthenticatedError(
          "The OAuth 2.0 token may have expired.\n"
          f"{message}"
      ) from err
    if "gcloud auth login" in err.output:
      raise errors.GcloudUnauthenticatedError(
          f"Run '{_gcloud_cli} auth login' to authenticate as a user "
          f"or '{_gcloud_cli} auth login --cred-file=/path/to/service-account-key.json' "  # pylint: disable=line-too-long
          f"to authenticate using a service account.\n"
          f"{message}"
      ) from err
    raise RuntimeError(message) from err


def has_command(command_name):
  """Determine if the given command executable is present on the local host.

  Args:
      command_name (str): Name of the command to look for. Example: 'fastboot'.

  Returns:
      bool: True if the command is found in the user's $PATH, False otherwise.
  """
  result = get_command_path(command_name)
  return bool(result)


def is_in_arp_table(ip_address):
  """Determine if the given IP address is present in arp table.

  Args:
      ip_address (str): to check for in arp table.

  Returns:
      bool: True if IP or MAC address is in arp table, False otherwise.

  Note:
      The MAC address provided must be in the format of '##:##:##:##:##:##'
      for this method to work correctly.
  """
  return ip_address in get_all_connected_arp_ips()


def is_in_ifconfig(ip_or_mac_address):
  """Determine if the given IP or MAC address is present in ifconfig output.

  Args:
      ip_or_mac_address (str): to check for in ifconfig output

  Returns:
      bool: True if IP or MAC address is in ifconfig output, False otherwise.

  Note:
      The MAC address provided must be in the format of '##:##:##:##:##:##'
      for this method to work correctly.
  """
  try:
    output = subprocess.check_output(["ifconfig"], stderr=subprocess.STDOUT)
    return ip_or_mac_address in output.decode("utf-8", "replace")
  except subprocess.CalledProcessError:
    return False


def _validate_ip_address(ip_address: str) -> bool:
  """Validates the IP address format.

  Args:
    ip_address: IP address to ping.
  Returns:
    True if the IP address is valid else False
  """
  try:
    ipaddress.ip_address(ip_address)
  except ValueError:
    return False
  return True


def is_pingable(
    ip_address: str,
    timeout: float = _PING_DEFAULT_TIMEOUT_SECONDS,
    packet_count: int = _PING_DEFAULT_PACKET_COUNT,
    deadline: Optional[float] = None) -> bool:
  """Checks if the ip_address responds to network pings.

  Args:
    ip_address: IP address to ping.
    timeout: Timeout in seconds to wait for a ping response. The option
      affects only timeout in absence of any responses.
    packet_count: How many packets will be sent before the deadline.
    deadline: Timeout in seconds before ping exits regardless of how many
      packets have been sent or received.

  Returns:
    True if the IP is pingable. False if the ping command fails or if the
      IP address is not valid.
  """
  if not _validate_ip_address(ip_address):
    return False

  flags_map = {
      "-c": packet_count,
      "-W": timeout,
      "-w": deadline,
  }
  cmd_list = ["ping"]
  for flag, flag_value in flags_map.items():
    if flag_value is not None:
      cmd_list.append(flag)
      cmd_list.append(str(flag_value))
  cmd_list.append(ip_address)

  try:
    subprocess.check_output(cmd_list, stderr=subprocess.STDOUT)
    return True
  except subprocess.CalledProcessError:
    return False


def is_sshable(ip_address):
  """Determine if the given IP address has an open ssh port.

  Args:
      ip_address (str): to ping

  Returns:
      bool: True if nc can see port 22 open.
  """
  try:
    cmd_list = SSHABLE_COMMAND.format(ip_address).split()
    subprocess.check_output(cmd_list, stderr=subprocess.STDOUT)
    return True
  except subprocess.CalledProcessError:
    return False


def accepts_snmp(ip_address: str) -> bool:
  """Determine if a given IP address accepts snmp protocol.

  Args:
    ip_address: IP to query snmpwalk.

  Returns:
    True if IP returns anything from snmpwalk command; False if not.
  """
  try:
    snmpwalk_command = _SNMPGET_SYSTEM_DESCRIPTION_COMMAND.format(
        ip_address=ip_address).split()
    subprocess.check_output(
        snmpwalk_command, timeout=_SNMPGET_SYSTEM_DESCRIPTION_TIMEOUT)
    return True
  except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as err:
    _LOGGER.debug(
        f"IP {ip_address} may not be snmp enabled or snmp is not "
        f"installed on host machine. Error: {err!r}. "
        f"Output: {err.output!r}"
    )
    return False


def ssh_command(
    ip_address: str,
    command: Sequence[str],
    user: str = "root",
    options: Sequence[str] = DEFAULT_SSH_OPTIONS,
    key_info: data_types.KeyInfo | None = None,
    timeout: float | None = None,
    include_return_code: bool = False,
) -> Any:
  """Sends an SSH command to the given IP address and returns the response.

  Args:
      ip_address: IP address of the device to execute the SSH command on.
      command: Command to execute on the device.
      user: Username to log in as.
      options: Extra command line args for the SSH command.
      key_info: SSH key to use. If None, don't use an SSH key.
      timeout: Timeout for the SSH command.
      include_return_code: Flag indicating return code should be returned

  Returns:
      str: If include_return_code is False return the SSH response to
        the command.
      tuple: If include_return_code is True return the SSH response and
        return code.

  Raises:
      RuntimeError: If SSH command fails.
  """
  if not isinstance(command, (list, tuple)):
    raise errors.DeviceError("command {} is not list nor tuple".format(command))
  ssh_args = generate_ssh_args(ip_address, command, user, options, key_info)
  ssh_list = ["ssh"] + ssh_args
  try:
    if include_return_code:
      result = subprocess.run(
          ssh_list, capture_output=True, text=True, check=False
      )
      if result.returncode == 0:
        return (result.stdout, result.returncode)
      return (result.stderr, result.returncode)

    result = subprocess.check_output(
        ssh_list, stderr=subprocess.STDOUT, timeout=timeout)
    result = result.decode("utf-8", "replace")
    _LOGGER.debug(
        "Ssh command {} to {} returned {!r}".format(command, ip_address, result)
    )
    return result
  except subprocess.CalledProcessError as err:
    msg = "Command {} failed. Err: {!r}".format(" ".join(ssh_list), err.output)
    _LOGGER.debug(msg)
    raise RuntimeError(msg)


def _get_scp_command(src: str, dest: str,
                     ssh_opt: Sequence[str]) -> Sequence[str]:
  """Returns a formatted 'scp' shell command."""
  global _scp_use_legacy_option
  if _scp_use_legacy_option is None:
    # From ssh 9.0, it requires an option -O to order scp use legacy method
    # instead of sftp, but it doesn't provide a way to check the version.
    #
    # Here "scp -O" is called, if it returns "unknown option -- O", then it is
    # less than 9.0, we should not provide the option, otherwise add the option.
    # Linux returns "unknown option -- O". MacOS returns "illegal option -- O".
    process = subprocess.run(["scp", "-O"],
                             capture_output=True,
                             text=True,
                             check=False)
    if not re.search("(unknown|illegal) option -- O", process.stderr):
      _scp_use_legacy_option = ("-O",)
    else:
      _scp_use_legacy_option = ()
  return ["scp", "-r", *_scp_use_legacy_option, *ssh_opt, src, dest]


def _scp(source: str, destination: str,
         options: Sequence[str] = SSH_CONFIG,
         key_info: Optional[data_types.KeyInfo] = None) -> str:
  """Sends file to or from the device using "scp" utility.

  Args:
      source: Source file.
      destination: Where to copy the file to.
      options: SSH command-line options to pass to scp.
      key_info: SSH key to use. If None, don't use an SSH key.

  Returns:
      "scp" command output.

  Raises:
      ValueError: Invalid direction value provided.
      RuntimeError: If scp fails.
  """
  if key_info:
    verify_key(key_info)
    options = [*options, "-i", get_key_path(key_info)]

  command = _get_scp_command(src=source, dest=destination, ssh_opt=options)
  try:
    _LOGGER.debug("Executing {!r}".format(command))
    result = subprocess.check_output(command, stderr=subprocess.STDOUT)
    return result.decode("utf-8", "replace")
  except subprocess.CalledProcessError as err:
    raise RuntimeError("Scp {!r} failed. Error: {!r}. Output: {}.".format(
        command, err, err.output))


def scp_to_device(ip_address: str,
                  local_file_path: str,
                  remote_file_path: str,
                  user: str = "root",
                  options: Sequence[str] = SSH_CONFIG,
                  key_info: Optional[data_types.KeyInfo] = None) -> str:
  """Sends file from host to device via "scp".

  Args:
      ip_address: IP address of the device.
      local_file_path: Local (host) file to send.
      remote_file_path: Remote (device) file name to copy the file to.
      user: Username for scp to use on the device.
      options: SSH options to pass to scp.
      key_info: SSH key to use. If None, don't use an SSH key.

  Returns:
      "scp" command output.
  """
  if ipaddress.ip_address(ip_address).version == 6:  # If ip_address is Ipv6.
    ip_address = "[" + ip_address + "]"
  remote_file_path = "{user}@{host}:{path}".format(
      user=user, host=ip_address, path=remote_file_path)
  return _scp(
      source=local_file_path,
      destination=remote_file_path,
      options=options,
      key_info=key_info)


def scp_from_device(ip_address: str,
                    local_file_path: str,
                    remote_file_path: str,
                    user: str = "root",
                    options: Sequence[str] = SSH_CONFIG,
                    key_info: Optional[data_types.KeyInfo] = None) -> str:
  """Sends file from device to host via "scp".

  Args:
      ip_address: IP address of the device.
      local_file_path (str): Local (host) file name to copy the file to.
      remote_file_path (str): Remote (device) source file to send.
      user: Username for scp to use on the device.
      options: SSH options to pass to scp.
      key_info: SSH key to use. If None, don't use an SSH key.

  Returns:
      "scp" command output.
  """
  if ipaddress.ip_address(ip_address).version == 6:  # If ip_address is Ipv6.
    ip_address = "[" + ip_address + "]"
  remote_file_path = "{user}@{host}:{path}".format(
      user=user, host=ip_address, path=remote_file_path)
  return _scp(
      source=remote_file_path,
      destination=local_file_path,
      options=options,
      key_info=key_info)


def verify_key(key_info: data_types.KeyInfo) -> None:
  """Downloads the key if it doesn't exist and (for SSH keys) sets permissions.

  Args:
      key_info: Key information.
  """
  local_path = get_key_path(key_info)
  if not os.path.exists(local_path):
    _download_key(key_info)
  if (key_info.type == data_types.KeyType.SSH
      and not key_info.file_name.endswith(".pub")):
    _set_key_permissions(local_path)


def _set_key_permissions(key_path: str) -> None:
  """Sets key file permissions to be readable only by the current user.

  Args:
      key_path: Path to the key file.

  Raises:
      ValueError: Unable to set key file permissions.
  """
  permissions = oct(os.stat(key_path).st_mode)[-3:]
  if not (permissions == "400" or permissions == "600"):
    try:
      os.chmod(key_path, 0o400)
    except OSError as err:
      raise ValueError(
          f"Unable to change permissions on {key_path} key. "
          f"Error: {err!r}. Permissions are {permissions}. "
          f"Run 'chmod 400 {key_path}' manually.")


def _set_gcloud_cli():
  """Finds a valid GCS executable and sets the _gcloud_cli variable.

  Raises:
      DependencyUnavailableError: unable to find a 'gcloud' binary.
  """
  global _gcloud_cli
  if not _gcloud_cli:
    possible_clis = [
        get_command_path("gcloud"),
        os.path.join(os.path.expanduser("~"), "gazoo", "bin", "gcloud"),
        # b/290310555: /usr/local/bin/ is not in $PATH in MacOS tests.
        _GCLOUD_MACOS_PATH,
    ]
    for cli in possible_clis:
      if os.path.exists(cli):
        _LOGGER.debug("Setting {} to be the GCS CLI".format(cli))
        _gcloud_cli = cli
        return
    raise errors.DependencyUnavailableError("Unable to find a 'gcloud' binary.")


def curl_command(cmd_list: Sequence[str], raise_error: bool = True):
  """Run a curl command.

  Args:
    cmd_list: Command list.
    raise_error: Whether to raise an error if the command fails.

  Raises:
    RuntimeError: If curl command fails.
  """
  full_cmd_list = ["curl", *cmd_list]
  if raise_error and "--fail-with-body" not in cmd_list:
    full_cmd_list.append("--fail-with-body")
  try:
    subprocess.run(full_cmd_list, capture_output=True, text=True, check=True)
  except subprocess.CalledProcessError as err:
    message = f"{err.cmd!r} failed. Output: {err.stderr}"
    raise RuntimeError(message) from err


def delete_path(device_name: str, path: str, check_path_exists: bool = False):
  """Delete the folder/file at the given path.

  Args:
    device_name: The name of the device.
    path: The path to remove.
    check_path_exists: Whether to check if the path exists before deleting.
  """
  try:
    _LOGGER.info("clean up by removing folder/file at %s", path)
    if check_path_exists and not os.path.exists(path):
      raise FileNotFoundError(f"Path {path} does not exist.")
    if os.path.isdir(path):
      shutil.rmtree(path)
    elif os.path.isfile(path):
      os.remove(path)
  except (FileNotFoundError, OSError, PermissionError) as err:
    _LOGGER.warning(
        "%s failed to remove path %s. Err: %s",
        device_name,
        path,
        str(err),
    )


def run_command(command: str, timeout: int | None = None) -> str:
  """Runs the command on the host.

  Args:
    command: The command to be run.
    timeout: The timeout for the command. If not provided, the default timeout
      is used.

  Returns:
    The output of the command.
  """
  output = subprocess.check_output(command.split(), timeout=timeout)
  return output.decode("utf-8", "replace")
