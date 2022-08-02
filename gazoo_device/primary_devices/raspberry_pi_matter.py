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
from typing import Callable, Dict, List, Tuple
from gazoo_device import config
from gazoo_device import decorators
from gazoo_device import detect_criteria
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.base_classes import matter_device_base
from gazoo_device.base_classes import ssh_device
from gazoo_device.capabilities import matter_app_controls_shell
from gazoo_device.protos import attributes_service_pb2
from gazoo_device.protos import descriptor_service_pb2
from gazoo_device.protos import device_service_pb2
from gazoo_device.utility import host_utils
from gazoo_device.utility import pwrpc_utils
import immutabledict

logger = gdm_logger.get_logger()

COMMANDS = immutabledict.immutabledict({
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
  def check_app_running(self) -> None:
    """Checks if the Matter sample app is running."""
    if not self.matter_sample_app.is_running:
      raise errors.ProcessNotRunningError(
          device_name=self.name,
          msg="The Matter sample app process is not running.")

  @decorators.health_check
  def check_rpc_working(self) -> None:
    """Checks if the RPC is working."""
    try:
      self.matter_endpoints.reset()
      self.matter_endpoints.list()
    except errors.DeviceError as e:
      raise errors.PigweedRpcTimeoutError(
          device_name=self.name,
          msg="The Matter sample app process is not responding to RPC.") from e

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
        pigweed_port=self._PIGWEED_PORT)

  @decorators.LogDecorator(logger)
  def recover(self, error: errors.DeviceError) -> None:
    """Restarts the sample app when the RPC is not working."""
    if isinstance(error, errors.PigweedRpcTimeoutError):
      self.matter_sample_app.restart()
    else:
      super().recover(error)
