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

"""Utility module for local host commands."""
from __future__ import absolute_import
import os
import re
import shutil
import stat
import subprocess

from gazoo_device import config
from gazoo_device import errors
from gazoo_device import gdm_logger

logger = gdm_logger.get_gdm_logger()
ARP_CONNECTED_IPS = r'([\-\w\.]*)\s*ether'
DOCKER_CP_COMMAND = "cp {src} {dest}"
DOWNLOAD_KEY_TIMEOUT = 3
PACKAGE_KEY_DIR = os.path.join(config.PACKAGE_PATH, "keys")
GSUTIL_CLI = None
IP_ADDRESS = r"\d+\.\d+\.\d+\.\d+"
PING_COMMAND = "ping -c 1 -W 2 {}"  # Try to ping ip address and wait for reponse for 2 seconds.
SSHABLE_COMMAND = "nc -z -w 2 {} 22"  # Try to connect to ssh port for up to 2 seconds.

SSH_ARGS = "{options} {user}@{ip_address} {command}"
SCP_COMMAND = "scp {ssh_opt} {src} {dest}"
SSH_TIMEOUT = 3
SSH_CONFIG = ("-oPasswordAuthentication=no -oStrictHostKeyChecking=no -oBatchMode=yes "
              "-oConnectTimeout={timeout}".format(timeout=SSH_TIMEOUT))
_SSH_DISABLE_PSEUDO_TTY = "-T "
DEFAULT_SSH_OPTIONS = _SSH_DISABLE_PSEUDO_TTY + SSH_CONFIG

GET_COMMAND_PATH = "which {}"
GET_CONNECTED_IPS = "/usr/sbin/arp -e"

GSUTIL_DICT = {
}


class _SCP_DIRECTION(object):
    TO_DEVICE = "to_device"
    FROM_DEVICE = "from_device"


def docker_cp_to_device(docker_container,
                        local_file_path,
                        container_file_path):
    """Send a file to a docker container using a docker cp command.

    Args:
        docker_container (str): docker container identifier
        local_file_path (str): path to file on host.
        container_file_path (str): path to destination on device.

    Returns:
        str: command output.
    """
    source, destination = local_file_path, "{}:{}".format(docker_container, container_file_path)
    cmd = DOCKER_CP_COMMAND.format(src=source, dest=destination)
    return _execute_docker_cmd(cmd)


def docker_cp_from_device(docker_container,
                          local_file_path,
                          container_file_path):
    """Receive file from a docker container using a docker cp command.

    Args:
        docker_container (str): docker container identifier
        local_file_path (str): path to file on host.
        container_file_path (str): path to destination on device.

    Returns:
        str: command output.
    """
    destination, source = local_file_path, "{}:{}".format(docker_container, container_file_path)
    cmd = DOCKER_CP_COMMAND.format(src=source, dest=destination)
    return _execute_docker_cmd(cmd)


def download_key(key_type):
    """Download an GDM key (ssh, api, etc.) if it doesn't currently exist locally.

    Args:
        key_type (str): type of key to download.

    Raises:
        DownloadKeyError: if unable to download the key.
    """
    local_path = config.KEYS[key_type]["local_path"]
    key_flavor = config.KEYS[key_type]["flavor"]
    if not os.path.exists(local_path):
        try:
            _obtain_key(key_type)
        except Exception as err:
            raise errors.DownloadKeyError(key_type, [err])
        logger.info(f"{key_type} {key_flavor} key downloaded")
    else:
        logger.debug(f"{key_type} {key_flavor} key found")


def generate_ssh_args(ip_address, command, user, options=DEFAULT_SSH_OPTIONS, ssh_key_type=None):
    """Generate list of ssh args to send to subprocess.

    Args:
      ip_address (str): ip address to ssh to.
      command (str): command to send.
      user (str): user for ip address.
      options (str): extra args for ssh command.
      ssh_key_type (str): type of ssh key

    Returns:
        str: str of args to send to subprocess.
    """
    if ssh_key_type:
        verify_ssh_key(ssh_key_type)
        options += " -i " + config.KEYS[ssh_key_type]["local_path"]
    return SSH_ARGS.format(options=options, ip_address=ip_address, user=user,
                           command=command)


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
        result = subprocess.check_output(
            ['which', command_name], stderr=subprocess.STDOUT).rstrip()
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
        output = subprocess.check_output([u"/usr/sbin/arp", u"-e"], stderr=subprocess.STDOUT)
        addresses = re.findall(ARP_CONNECTED_IPS, output.decode("utf-8", "replace"), re.MULTILINE)
        return addresses
    except subprocess.CalledProcessError:
        return []


def is_static_ip(comm_port):
    return re.search(IP_ADDRESS, comm_port)


def get_all_ssh_ips(static_ips=None):
    """Returns all ips that are not ISA3."""
    if not static_ips:
        static_ips = []
    pingable_static_ips = [ip for ip in static_ips if is_pingable(ip)]
    unpingable_static_ips = [ip for ip in static_ips if ip not in pingable_static_ips]
    if unpingable_static_ips:
        logger.info("Warning: ip_address(es) provided are not pingable: {}".format(
            unpingable_static_ips))
    possible_ips = sorted(set(pingable_static_ips))
    sshable_ips = [ip for ip in possible_ips if is_sshable(ip)]
    unsshable_ips = [ip for ip in possible_ips if ip not in sshable_ips]
    if unsshable_ips:
        logger.info(
            "Warning: ip_address(es) provided do not have ssh port 22 open: {}".format(
                unsshable_ips))
    return sshable_ips


def get_all_yepkit_serials():
    """Returns all Yepkit serials."""
    try:
        if not has_command("ykushcmd"):
            logger.debug("Ykushcmd is not installed on machine. Cannot get yepkit serials.")
            return []

        results = subprocess.check_output(["ykushcmd", "-l"], stderr=subprocess.STDOUT)
        results = results.decode("utf-8", "replace")
        logger.debug("get_all_yepkit_serials returned: {!r}".format(results))
    except subprocess.CalledProcessError as err:
        logger.debug("Checking get_all_yepkit_serial returned err: {!r}".format(err))
        return []

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
    try:
        cmd = ['docker', 'ps', '--filter', 'name=VDL', '--format', '{{.ID}}']
        results = subprocess.check_output(cmd)
    except subprocess.CalledProcessError as err:
        logger.debug("Checking get_all_vdl_docker_connections returned err: {!r}".format(err))
        return []
    return results.decode().splitlines()


def gsutil_command(cmd, gsutil_path, extra_args=None):
    """Send a gsutil command using a valid gsutil path.

    Args:
      cmd (str): gsutil command.
      gsutil_path (str): path in gsutil directory.
      extra_args (list): any other args needed.

    Returns:
      str: output of command.

    Raises:
      RuntimeError: if unable to send command or find valid gsutil.
    """
    _set_gsutil_cli()
    _set_boto_file(gsutil_path)

    cmd_list = [GSUTIL_CLI, cmd, gsutil_path]
    if extra_args:
        cmd_list += extra_args

    try:
        output = subprocess.check_output(cmd_list, stderr=subprocess.STDOUT)
        return output.decode("utf-8", "replace")
    except subprocess.CalledProcessError as err:
        raise RuntimeError("{!r} failed. Err: {}".format(" ".join(cmd_list), err.output))


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


def is_pingable(ip_address):
    """Determine if the given IP address is pingable.

    Args:
        ip_address (str): to ping

    Returns:
        bool: True if IP address is pingable with no loss within 1 second.
    """
    try:
        cmd_list = PING_COMMAND.format(ip_address).split()
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


def ssh_command(ip_address, command, user="root", options=DEFAULT_SSH_OPTIONS, ssh_key_type=None):
    """Send an ssh command.

    Args:
        ip_address (str): device
        command (str): command to send to device.
        user (str): user to login to ip.
        options (str): extra args for ssh command.
        ssh_key_type (str): which ssh key to use. Key types stored in config.

    Returns:
        str: output

    Raises:
       RuntimeError: if ssh command fails.
    """
    ssh_args = generate_ssh_args(ip_address, command, user, options, ssh_key_type)
    ssh_list = ["ssh"] + ssh_args.split()
    try:
        result = subprocess.check_output(ssh_list, stderr=subprocess.STDOUT)
        result = result.decode("utf-8", "replace")
        logger.debug("Ssh command {} to {} returned {!r}".format(command, ip_address, result))
        return result
    except subprocess.CalledProcessError as err:
        msg = "Command {} failed. Err: {!r}".format(" ".join(ssh_list), err.output)
        logger.debug(msg)
        raise RuntimeError(msg)


def _scp(source,
         destination,
         options=SSH_CONFIG,
         ssh_key_type=None):
    """Send file to or from the device using "scp" utility.

    Args:
        source (str): source file.
        destination (str): where to copy te file to.
        options (str): SSH options to pass to scp.
        ssh_key_type (str): type of ssh key

    Returns:
        str: command output.

    Raises:
        ValueError: invalid direction value provided.
        RuntimeError: if scp fails.
    """
    if ssh_key_type:
        verify_ssh_key(ssh_key_type)
        options += " -i " + config.KEYS[ssh_key_type]["local_path"]

    command = SCP_COMMAND.format(ssh_opt=options, src=source, dest=destination)
    try:
        logger.debug("Executing {!r}".format(command))
        result = subprocess.check_output(command.split(), stderr=subprocess.STDOUT)
        return result.decode("utf-8", "replace")
    except subprocess.CalledProcessError as err:
        raise RuntimeError(
            "Scp {!r} failed. Error: {!r}. Output: {}.".format(command, err, err.output))


def scp_to_device(ip_address,
                  local_file_path,
                  remote_file_path,
                  user="root",
                  options=SSH_CONFIG,
                  ssh_key_type=None):
    """Send file to device via scp.

    Args:
        ip_address (str): ip_address
        local_file_path (str): source file.
        remote_file_path (str): where to copy te file to.
        user (str): username for scp to use on the device.
        options (str): SSH options to pass to scp.
        ssh_key_type (str): type of ssh key.

    Returns:
        str: command output.
    """
    remote_file_path = "{user}@{host}:{path}".format(user=user,
                                                     host=ip_address,
                                                     path=remote_file_path)
    return _scp(source=local_file_path,
                destination=remote_file_path,
                options=options,
                ssh_key_type=ssh_key_type)


def scp_from_device(ip_address,
                    local_file_path,
                    remote_file_path,
                    user="root",
                    options=SSH_CONFIG,
                    ssh_key_type=None):
    """Send file from device via scp.

    Args:
        ip_address (str): ip_address
        local_file_path (str): where to copy the file to.
        remote_file_path (str): source file.
        user (str): username for scp to use on the device.
        options (str): SSH options to pass to scp.
        ssh_key_type (str): type of ssh key.

    Returns:
        str: command output.
    """
    remote_file_path = "{user}@{host}:{path}".format(user=user,
                                                     host=ip_address,
                                                     path=remote_file_path)
    return _scp(source=remote_file_path,
                destination=local_file_path,
                options=options,
                ssh_key_type=ssh_key_type)


def verify_ssh_key(ssh_key_type):
    """Verifies ssh key exists and has permissions correctly set.

    Args:
        ssh_key_type (str): device type for error message purposes.

    Raises:
        GazooDeviceError: if ssh key inaccessible.
        ValueError: if unable to set permissions of ssh key.
    """
    local_path = config.KEYS[ssh_key_type]["local_path"]
    if not os.path.isfile(local_path):
        download_key(ssh_key_type)
        if not os.path.isfile(local_path):
            raise errors.GazooDeviceError(
                f"{ssh_key_type} ssh key missing. Please run 'gdm download-keys'")

    permissions = oct(os.stat(local_path).st_mode)[-3:]
    if not (permissions == "400" or permissions == "600"):
        try:
            os.chmod(local_path, 0o400)
        except OSError:
            raise ValueError(
                "Unable to communicate to {} ssh key. Permissions are {}."
                "'chmod 400 {}'".format(
                    ssh_key_type,
                    permissions,
                    local_path))


def _set_gsutil_cli():
    """Finds a valid gsutil executable and sets the module-level GSUTIL_CLI constant.

    Raises:
        RuntimeError: unable to find a valid "gsutil" binary.
    """
    global GSUTIL_CLI
    if not GSUTIL_CLI:
        possible_clis = [
            get_command_path("gsutil"),
            "/usr/local/bin/gsutil"
        ]
        for cli in possible_clis:
            if os.path.exists(cli):
                logger.debug("Setting {} to be the gsutil cli".format(cli))
                GSUTIL_CLI = cli
                return
        raise RuntimeError("Unable to find valid gsutil binary."
                           "Refer to GDM installation documentation.")


def _choose_boto_file(path):
    """Choose the correct .boto file for the given gsutil path.

    Args:
        path (str): gs address of file to copy.

    Raises:
       RuntimeError: if no relevant boto file found.

    Returns:
      str: boto_file_path to use.
    """
    for prefix, values in GSUTIL_DICT.items():
        if prefix in path:
            if values["verified"]:
                return values["boto_file"]
            elif os.path.exists(values["boto_file"]):
                values["verified"] = True
                return values["boto_file"]
            elif os.path.exists(config.DEFAULT_BOTO):
                logger.warning("WARNING: Unable to locate appropriate GDM boto file ({})."
                               " Using default .boto file ({}) for access."
                               .format(values["boto_file"], config.DEFAULT_BOTO))
                values["verified"] = True
                values["boto_file"] = config.DEFAULT_BOTO
                return config.DEFAULT_BOTO

    if os.path.exists(config.DEFAULT_BOTO):
        logger.warning("Unrecognized gsutil location. Using default .boto file ({}) for access."
                       .format(config.DEFAULT_BOTO))
        return config.DEFAULT_BOTO
    raise RuntimeError(
        "No .boto file {} found to give access to gcs storage."
        " Has 'gsutil config' been run to set up gcs access?".format(config.DEFAULT_BOTO))


def _obtain_key(key_type):
    """Downloads an GDM key (ssh, api, etc.) and stores it in a local file.

    Args:
        key_type (str): type of key to download.
    """
    local_path = config.KEYS[key_type]["local_path"]
    remote_filename = config.KEYS[key_type]["remote_filename"]
    shutil.copyfile(src=os.path.join(PACKAGE_KEY_DIR, remote_filename),
                    dst=local_path)
    if not local_path.endswith(".pub"):  # Private SSH key
        os.chmod(local_path, stat.S_IRUSR)
    # The keys included with GDM are not secret, so it's okay to
    # include them in the repo for the GDM prototype.
    # TODO: package keys somewhere else (like GCS?).


def _set_boto_file(path):
    """Sets the appropriate boto file for that gs path.

    Args:
      path (str): gs address of file to copy.

    Raises:
       RuntimeError: if no boto file exists.
    """
    boto_file = _choose_boto_file(path)

    if os.path.exists(boto_file):
        logger.debug("Using {} to access {}".format(boto_file, path))
        os.environ["BOTO_CONFIG"] = boto_file
    else:
        raise RuntimeError("Expecting .boto {boto_file} to exist to access {path} but it doesn't."
                           " Copy ~/.boto to {boto_file} if you have access on the "
                           "gsutil command line".format(boto_file=boto_file, path=path))


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
            "Docker command: {!r} failed, with error: {!r}. Output: {}.".format(full_cmd,
                                                                                err,
                                                                                err.output))
