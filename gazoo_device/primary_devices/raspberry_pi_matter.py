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

"""Device controller for RPi Matter device.

This device controller populates the supported Matter endpoints on the RPi
platform by using the descriptor RPC service.
"""
from typing import Callable, Dict, List, Optional, Tuple
from gazoo_device import config
from gazoo_device import decorators
from gazoo_device import detect_criteria
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.base_classes import matter_device_base
from gazoo_device.base_classes import ssh_device
from gazoo_device.capabilities import bluetooth_service_linux
from gazoo_device.capabilities import matter_app_controls_shell
from gazoo_device.protos import attributes_service_pb2
from gazoo_device.protos import descriptor_service_pb2
from gazoo_device.protos import device_service_pb2
from gazoo_device.utility import host_utils
from gazoo_device.utility import pwrpc_utils
from gazoo_device.utility import retry
import immutabledict

logger = gdm_logger.get_logger()

_APP_START_SEC = 1  # seconds
_POLL_APP_INTERVAL_SEC = 0.1  # seconds
_RPC_START_SEC = 5  # seconds
_POLL_RPC_INTERVAL_SEC = 1  # seconds

COMMANDS = immutabledict.immutabledict({
    "REBOOT": "sudo reboot",
    "SERIAL_NUMBER_INFO": "cat /proc/cpuinfo",
})

REGEXES = immutabledict.immutabledict({
    "SERIAL_NUMBER_INFO_REGEX": r"Serial\s+: ([^\n]+)"
})


class RaspberryPiMatter(
    ssh_device.SshDevice, matter_device_base.MatterDeviceBase):
  """RPi Matter device controller."""
  COMMUNICATION_TYPE = "PigweedSocketComms"
  DETECT_MATCH_CRITERIA = {
      detect_criteria.SshQuery.IS_RPI: True,
      detect_criteria.SshQuery.IS_MATTER_LINUX_APP_RUNNING: True,
  }
  _COMMUNICATION_KWARGS = {"protobufs": (attributes_service_pb2,
                                         descriptor_service_pb2,
                                         device_service_pb2),
                           "port": pwrpc_utils.MATTER_LINUX_APP_DEFAULT_PORT,
                           "args": host_utils.DEFAULT_SSH_OPTIONS,
                           "log_cmd": ssh_device.COMMANDS["LOGGING"],
                           "key_info": config.KEYS["raspberrypi3_ssh_key"],
                           "username": "pi"}
  DEVICE_TYPE = "rpimatter"
  # Overrides to recover from the successive recoverable health check failures
  _RECOVERY_ATTEMPTS = 3

  # RPi Matter controller has transport number 2 for RPC interaction.
  _PIGWEED_PORT = 2

  def __init__(self,
               manager,
               device_config,
               log_file_name=None,
               log_directory=None):
    super().__init__(
        manager,
        device_config,
        log_file_name=log_file_name,
        log_directory=log_directory)
    self._commands.update(COMMANDS)
    self._regexes.update(REGEXES)

  @decorators.PersistentProperty
  def os(self) -> str:
    """OS of RPi linux app."""
    return "Ubuntu"

  @decorators.PersistentProperty
  def platform(self) -> str:
    """Platform of RPi linux app."""
    return "Raspberry Pi 4"

  @decorators.LogDecorator(logger)
  def get_detection_info(self) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Gets the persistent and optional attributes of a device during setup.

    Returns:
      Dictionary of persistent attributes and dictionary of optional attributes.
    """
    persistent_dict, options_dict = super().get_detection_info()
    serial_number = self.shell_with_regex(
        self.commands["SERIAL_NUMBER_INFO"],
        self.regexes["SERIAL_NUMBER_INFO_REGEX"])
    persistent_dict["serial_number"] = serial_number
    persistent_dict["model"] = "PROTO"
    return persistent_dict, options_dict

  @decorators.PersistentProperty
  def health_checks(self) -> List[Callable[[], None]]:
    """Returns the list of methods to execute as health checks."""
    return super().health_checks + [
        self.check_app_present,
        self.check_has_service,
        self.check_is_service_enabled,
        self.check_app_running,
        self.check_rpc_working]

  @decorators.health_check
  def check_app_present(self) -> None:
    """Checks if the Matter sample app is present."""
    if not self.matter_sample_app.is_present:
      raise errors.DeviceBinaryMissingError(
          device_name=self.name,
          msg="The Matter sample app binary does not exist.")

  @decorators.health_check
  def check_has_service(self) -> None:
    """Checks if the Matter sample app service file exists."""
    if not self.matter_sample_app.has_service:
      raise errors.DeviceMissingPackagesError(
          device_name=self.name,
          msg="The Matter sample app service file does not exist.",
          package_list=(
              f"/etc/systemd/system/{pwrpc_utils.MATTER_LINUX_APP_NAME}"
              ".service",))

  @decorators.health_check
  def check_is_service_enabled(self) -> None:
    """Checks if the Matter sample app service is enabled."""
    if not self.matter_sample_app.is_service_enabled:
      raise errors.ServiceNotEnabledError(
          device_name=self.name,
          msg="The Matter sample app service is not enabled.")

  @decorators.health_check
  def check_app_running(self) -> None:
    """Checks if the Matter sample app is running."""
    if not self.matter_sample_app.is_running:
      raise errors.ProcessNotRunningError(
          device_name=self.name,
          msg="The Matter sample app process is not running.")

  @decorators.CapabilityDecorator(
      matter_app_controls_shell.MatterSampleAppShell)
  def matter_sample_app(self):
    """Matter sample app control and management capability over shell."""
    return self.lazy_init(
        matter_app_controls_shell.MatterSampleAppShell,
        device_name=self.name,
        shell_fn=self.shell,
        close_transport_fn=self.switchboard.close_transport,
        open_transport_fn=self.switchboard.open_transport,
        pigweed_port=self._PIGWEED_PORT,
        send_file_to_device_fn=self.file_transfer.send_file_to_device,
        wait_for_bootup_complete_fn=self.wait_for_bootup_complete,
        reset_endpoints_fn=self.matter_endpoints.reset)

  @decorators.LogDecorator(logger)
  def recover(self, error: errors.DeviceError) -> None:
    """Recovers the device from an error.

    1. Restarts the sample app when the RPC is not working.
    2. Enables the sample app service when it's not enabled.
    3. Otherwise trying with a parent recover method.

    Args:
      error: The error we try to recover from.
    """
    if isinstance(error, errors.PigweedRpcTimeoutError):
      self.matter_sample_app.restart()
    elif isinstance(error, errors.ServiceNotEnabledError):
      self.matter_sample_app.enable_service()
    else:
      super().recover(error)

  @decorators.LogDecorator(logger)
  def reboot(self, no_wait: bool = False, method: str = "shell") -> None:
    """Reboots the RPi.

    Args:
      no_wait: Return before reboot completes.
      method: Not used.
    """
    del method
    self.switchboard.send(command=self.commands["REBOOT"])
    if not no_wait:
      self._verify_reboot()

  @decorators.LogDecorator(logger)
  def wait_for_bootup_complete(self, timeout: Optional[int] = None) -> None:
    """Waits until the device finished bootup and becomes responsive."""
    # Wait for the RPi to be back online.
    super().wait_for_bootup_complete(timeout)

    # Wait for the sample app process to run again.
    retry.retry(
        func=self.check_app_running,
        timeout=_APP_START_SEC,
        interval=_POLL_APP_INTERVAL_SEC,
        reraise=False)

    # Wait for the sample app to become RPC responsive
    retry.retry(
        func=self.check_rpc_working,
        timeout=_RPC_START_SEC,
        interval=_POLL_RPC_INTERVAL_SEC,
        reraise=False)

  @decorators.CapabilityDecorator(bluetooth_service_linux.BluetoothServiceLinux)
  def bluetooth_service(self):
    """Bluetooth service controls capability."""
    return self.lazy_init(
        bluetooth_service_linux.BluetoothServiceLinux,
        device_name=self.name,
        shell_fn=self.shell,
        shell_with_regex_fn=self.shell_with_regex)
