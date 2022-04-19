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
"""Utility module for local host commands."""
import glob
import ipaddress
import os
import re
import subprocess
from typing import List, Optional, Sequence

from gazoo_device import config
from gazoo_device import data_types
from gazoo_device import extensions
from gazoo_device import gdm_logger

logger = gdm_logger.get_logger()
ARP_CONNECTED_IPS = r"([\-\w\.]*)\s*ether"
_BOTO_ENV_VAR = "BOTO_CONFIG"
_DEFAULT_BOTO = os.path.expanduser("~/.boto")
DOCKER_CP_COMMAND = "cp {src} {dest}"
IP_ADDRESS = r"\d+\.\d+\.\d+\.\d+"
PING_DEFAULT_TIMEOUT_SECONDS = 2
PING_COMMAND = "ping -c 1 -W 2 {}"  # Ping ip address and wait for response.
PING_CUSTOM_TIMEOUT = "ping -c 1 -W {} {}"  # Ping with custom timeout.
SSHABLE_COMMAND = "nc -z -w 2 {} 22"  # Connect to ssh port for up to 2 seconds.

SSH_ARGS = "{options} {user}@{ip_address} {command}"
SCP_COMMAND = "scp -r {ssh_opt} {src} {dest}"
SSH_TIMEOUT = 3
SSH_CONFIG = (
    "-oPasswordAuthentication=no -oStrictHostKeyChecking=no -oBatchMode=yes "
    "-oConnectTimeout={timeout}".format(timeout=SSH_TIMEOUT))
_SSH_DISABLE_PSEUDO_TTY = "-T "
DEFAULT_SSH_OPTIONS = _SSH_DISABLE_PSEUDO_TTY + SSH_CONFIG

GET_COMMAND_PATH = "which {}"
GET_CONNECTED_IPS = "/usr/sbin/arp -e"

_SNMPWALK_COMMAND = "snmpwalk -v 2c -c private {ip_address}"
_SNMPWALK_TIMEOUT = 10

_gsutil_cli = None  # Set by _set_gsutil_cli().


def docker_cp_to_device(docker_container, local_file_path, container_file_path):
  """Send a file to a docker container using a docker cp command.

  Args:
      docker_container (str): docker container identifier
      local_file_path (str): path to file on host.
      container_file_path (str): path to destination on device.

  Returns:
      str: command output.
  """
  source, destination = local_file_path, "{}:{}".format(docker_container,
                                                        container_file_path)
  cmd = DOCKER_CP_COMMAND.format(src=source, dest=destination)
  return _execute_docker_cmd(cmd)


def docker_cp_from_device(docker_container, local_file_path,
                          container_file_path):
  """Receive file from a docker container using a docker cp command.

  Args:
      docker_container (str): docker container identifier
      local_file_path (str): path to file on host.
      container_file_path (str): path to destination on device.

  Returns:
      str: command output.
  """
  destination, source = local_file_path, "{}:{}".format(docker_container,
                                                        container_file_path)
  cmd = DOCKER_CP_COMMAND.format(src=source, dest=destination)
  return _execute_docker_cmd(cmd)


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
  key_download_function = extensions.package_info[key_info.package][
      "key_download_function"]
  key_download_function(key_info, key_path)
  logger.info(f"{key_info} key downloaded")
  if not os.path.exists(key_path):
    raise FileNotFoundError(f"Key {key_info} was not downloaded to {key_path} "
                            f"after calling {key_download_function}.")
  if (key_info.type == data_types.KeyType.SSH
      and not key_info.file_name.endswith(".pub")):
    _set_key_permissions(key_path)


def generate_ssh_args(ip_address: str,
                      command: str,
                      user: str,
                      options: str = DEFAULT_SSH_OPTIONS,
                      key_info: Optional[data_types.KeyInfo] = None) -> str:
  """Returns a formatted SSH command to send to subprocess.

  Args:
      ip_address: IP address to ssh to.
      command: Command to run over SSH. Can be an empty string.
      user: Username to use for SSH.
      options: Extra SSH command line options.
      key_info: SSH key info to use. If None, don't use an SSH key.
  """
  if key_info:
    verify_key(key_info)
    options += " -i " + get_key_path(key_info)
  return SSH_ARGS.format(
      options=options, ip_address=ip_address, user=user, command=command)


def get_command_path(command_name):
  """Return the full path for the given command name.

  Args:
      command_name (str): Name of the command to look for. Example: 'fastboot'

  Raises:
      CalledProcessError: Retrieving the command name path failed.

  Returns:
      str: Output for the given command name.
  """
  try:
    result = subprocess.check_output(["which", command_name],
                                     stderr=subprocess.STDOUT).rstrip()
    return result.decode("utf-8", "replace")
  except subprocess.CalledProcessError:
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
    logger.warning("Retrieval of connected IPs from the ARP table failed. "
                   f"Error: {err!r}. Output: {err.output!r}")
    return []


def is_static_ip(comm_port: str) -> bool:
  return bool(
      re.search(IP_ADDRESS, comm_port)
  )


def get_all_ssh_ips(static_ips: Optional[List[str]] = None) -> List[str]:
  """Returns all IPs that respond to ping and accept SSH connections."""
  static_ips = static_ips or []
  ssh_ips = set(static_ips)

  unpingable_ips = {ip for ip in ssh_ips if not is_pingable(ip)}
  if unpingable_ips:
    logger.info(f"ip_address(es) {unpingable_ips} do not respond to ping.")
  ssh_ips -= unpingable_ips

  unsshable_ips = {ip for ip in ssh_ips if not is_sshable(ip)}
  if unsshable_ips:
    logger.info(f"ip_address(es) {unsshable_ips} do not accept incoming SSH "
                "connections.")
  ssh_ips -= unsshable_ips
  return list(ssh_ips)


def get_all_snmp_ips(static_ips: Optional[Sequence[str]] = None) -> List[str]:
  """Returns all IPs that respond to ping and accept snmp protocol."""
  static_ips = static_ips or []
  snmp_ips = set(static_ips)
  snmp_ips = {ip for ip in snmp_ips if is_pingable(ip)}
  non_snmp_ips = {ip for ip in snmp_ips if not accepts_snmp(ip)}
  if non_snmp_ips:
    logger.info(f"ip_address(es) {non_snmp_ips} do not accept snmp protocol.")
  snmp_ips -= non_snmp_ips
  return list(snmp_ips)


def get_all_yepkit_serials():
  """Returns all Yepkit serials."""
  if not has_command("ykushcmd"):
    logger.warning("'ykushcmd' is not installed. Cannot get Yepkit serials.")
    return []

  try:
    results = subprocess.check_output(["ykushcmd", "-l"],
                                      stderr=subprocess.STDOUT)
  except subprocess.CalledProcessError as err:
    logger.warning("Retrieval of Yepkit serials failed. "
                   f"Error: {err!r}. Output: {err.output!r}")
    return []

  results = results.decode("utf-8", "replace")
  logger.debug("get_all_yepkit_serials returned: {!r}".format(results))
  # If no YKUSH boards are found then the YK21624 line will be this instead:
  #    No YKUSH boards found.
  if "No YKUSH boards found" in results:
    return []

  # Typical ykushcmd -l output looks like this:
  #    Attached YKUSH Boards:\n\nYK21624\n\nYK21623
  # Removes blank lines and header
  results = [line for line in results.splitlines() if line]
  return results[1:]


def get_all_vdl_docker_connections():
  """Returns all VDL docker ids."""
  if not has_command("docker"):
    logger.warning("'docker' is not installed. Cannot get Docker devices.")
    return []

  cmd = ["docker", "ps", "--filter", "name=VDL", "--format", "{{.ID}}"]
  try:
    results = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
  except subprocess.CalledProcessError as err:
    logger.warning("Retrieval of VDL docker containers failed. "
                   f"Error: {err!r}. Output: {err.output!r}")
    return []
  return results.decode().splitlines()


def get_all_pty_process_directories():
  """Returns a list of all PtyProcessComms connection directories."""
  return glob.glob(os.path.join(config.PTY_PROCESS_DIRECTORY, "*", ""))


def gsutil_command(cmd: str,
                   gsutil_path: str,
                   extra_args: Optional[List[str]] = None,
                   boto_path: Optional[str] = None) -> str:
  """Issues a 'gsutil' command using appropriate .boto file and returns output.

  Args:
    cmd: 'gsutil' command to issue (such as "cp").
    gsutil_path: Google Cloud Storage path (gs://).
    extra_args: Other arguments to pass to append to the command.
    boto_path: Path to .boto credential file to use. If None, use the default
      ~/.boto file.

  Returns:
    Output of the command.

  Raises:
    RuntimeError: Command failed, or there's no valid 'gsutil' binary.
  """
  _set_gsutil_cli()
  boto_path = boto_path or _get_default_boto()
  logger.debug(f"Using {boto_path} to access {gsutil_path}")

  cmd_list = [_gsutil_cli, cmd, gsutil_path]
  if extra_args:
    cmd_list += extra_args

  new_env = os.environ.copy()
  new_env.update({_BOTO_ENV_VAR: boto_path})
  try:
    output = subprocess.check_output(
        cmd_list, stderr=subprocess.STDOUT, env=new_env)
    return output.decode("utf-8", "replace")
  except subprocess.CalledProcessError as err:
    raise RuntimeError("{!r} failed. Err: {}".format(" ".join(cmd_list),
                                                     err.output))


def has_command(command_name):
  """Determine if the given command executable is present on the local host.

  Args:
      command_name (str): Name of the command to look for. Example: 'fastboot'

  Returns:
      bool: True if the command is found in the user's $PATH, False otherwise.
  """
  result = get_command_path(command_name)
  return bool(result)


def is_in_arp_table(ip_address):
  """Determine if the given IP address is present in arp table.

  Args:
      ip_address (str): to check for in arp table

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


def is_pingable(
    ip_address: str, timeout: float = PING_DEFAULT_TIMEOUT_SECONDS) -> bool:
  """Returns True if the ip_address responds to network pings.

  Args:
      ip_address: IP address to ping.
      timeout: Timeout in seconds to wait for ping response.
  """
  try:
    cmd_list = PING_CUSTOM_TIMEOUT.format(timeout, ip_address).split()
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
    snmpwalk_command = _SNMPWALK_COMMAND.format(ip_address=ip_address).split()
    subprocess.check_output(snmpwalk_command, timeout=_SNMPWALK_TIMEOUT)
    return True
  except subprocess.CalledProcessError:
    return False


def ssh_command(ip_address: str,
                command: str,
                user: str = "root",
                options: str = DEFAULT_SSH_OPTIONS,
                key_info: Optional[data_types.KeyInfo] = None,
                timeout: Optional[float] = None) -> str:
  """Sends an SSH command to the given IP address and returns the response.

  Args:
      ip_address: IP address of the device to execute the SSH command on.
      command: Command to execute on the device.
      user: Username to log in as.
      options: Extra command line args for the SSH command.
      key_info: SSH key to use. If None, don't use an SSH key.
      timeout: Timeout for the SSH command.

  Returns:
      SSH command output.

  Raises:
      RuntimeError: If SSH command fails.
  """
  ssh_args = generate_ssh_args(ip_address, command, user, options, key_info)
  ssh_list = ["ssh"] + ssh_args.split()
  try:
    result = subprocess.check_output(
        ssh_list, stderr=subprocess.STDOUT, timeout=timeout)
    result = result.decode("utf-8", "replace")
    logger.debug("Ssh command {} to {} returned {!r}".format(
        command, ip_address, result))
    return result
  except subprocess.CalledProcessError as err:
    msg = "Command {} failed. Err: {!r}".format(" ".join(ssh_list), err.output)
    logger.debug(msg)
    raise RuntimeError(msg)


def _scp(source: str, destination: str, options: str = SSH_CONFIG,
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
    options += " -i " + get_key_path(key_info)

  command = SCP_COMMAND.format(ssh_opt=options, src=source, dest=destination)
  try:
    logger.debug("Executing {!r}".format(command))
    result = subprocess.check_output(command.split(), stderr=subprocess.STDOUT)
    return result.decode("utf-8", "replace")
  except subprocess.CalledProcessError as err:
    raise RuntimeError("Scp {!r} failed. Error: {!r}. Output: {}.".format(
        command, err, err.output))


def scp_to_device(ip_address: str,
                  local_file_path: str,
                  remote_file_path: str,
                  user: str = "root",
                  options: str = SSH_CONFIG,
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
                    options: str = SSH_CONFIG,
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


def _get_default_boto() -> str:
  """Returns the absolute path to the default ~/.boto file if it exists.

  Raises:
    RuntimeError: If the default ~/.boto is missing.
  """
  if not os.path.exists(_DEFAULT_BOTO):
    raise RuntimeError(
        f"Default GCS access credentials file {_DEFAULT_BOTO} does not exist. "
        "Run 'gsutil config' to configure GCS access credentials.")
  return _DEFAULT_BOTO


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


def _set_gsutil_cli():
  """Finds a valid gsutil executable and sets the _gsutil_cli variable.

  Raises:
      RuntimeError: unable to find a valid "gsutil" binary.
  """
  global _gsutil_cli
  if not _gsutil_cli:
    possible_clis = [
        os.path.join(os.path.expanduser("~"), "gazoo", "bin", "gsutil"),
        get_command_path("gsutil"),
        "/usr/local/bin/gsutil",
    ]
    for cli in possible_clis:
      if os.path.exists(cli):
        logger.debug("Setting {} to be the gsutil cli".format(cli))
        _gsutil_cli = cli
        return
    raise RuntimeError("Unable to find valid 'gsutil' binary.")


def _execute_docker_cmd(cmd):
  """Send file to or from the device using "docker cp" utility.

  Args:
      cmd (str): command

  Returns:
      str: command output.

  Raises:
      RuntimeError: If unable to run the command
  """
  full_cmd = "docker {}".format(cmd)
  try:
    logger.debug("Executing {!r}".format(full_cmd))
    result = subprocess.check_output(full_cmd.split(), stderr=subprocess.STDOUT)
    return result.decode("utf-8", "replace")
  except subprocess.CalledProcessError as err:
    raise RuntimeError(
        "Docker command: {!r} failed, with error: {!r}. Output: {}.".format(
            full_cmd, err, err.output))
