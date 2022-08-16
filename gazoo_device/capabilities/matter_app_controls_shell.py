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
"""Matter linux sample app controls and management capability over shell."""
import os
import time
from typing import Callable, List

from gazoo_device import decorators
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import matter_app_controls_base
from gazoo_device.utility import pwrpc_utils
from gazoo_device.utility import retry
import immutabledict

logger = gdm_logger.get_logger()

_MATTER_APP_PATH = f"/home/pi/{pwrpc_utils.MATTER_LINUX_APP_NAME}"
_MATTER_APP_SERVICE = f"{pwrpc_utils.MATTER_LINUX_APP_NAME}.service"
_MATTER_APP_SERVICE_FULL_PATH = f"/etc/systemd/system/{_MATTER_APP_SERVICE}"
_APP_START_SEC = 3  # seconds
_POLL_INTERVAL_SEC = 1  # seconds
_COOL_DOWN_SEC = 1  # seconds
_COMMANDS = immutabledict.immutabledict({
    "CHECK_IF_APP_EXISTS": f"test -f {_MATTER_APP_PATH}",
    "CHECK_IF_SERVICE_EXISTS": f"test -f {_MATTER_APP_SERVICE_FULL_PATH}",
    "CHECK_SERVICE_ENABLED": f"sudo systemctl is-enabled {_MATTER_APP_SERVICE}",
    "GET_RUNNING_PROCESSES": f"pgrep -f {pwrpc_utils.MATTER_LINUX_APP_NAME}",
    "TERMINATE_PROCESS": "sudo kill -9 {}",
    "ENABLE_SERVICE": f"sudo systemctl enable {_MATTER_APP_SERVICE}",
    "START_SERVICE": f"sudo systemctl start {_MATTER_APP_SERVICE}",
    "STOP_SERVICE": f"sudo systemctl stop {_MATTER_APP_SERVICE}",
})


class MatterSampleAppShell(matter_app_controls_base.MatterSampleAppBase):
  """Matter app controls and management capability over shell."""

  def __init__(
      self,
      device_name: str,
      shell_fn: Callable[..., str],
      close_transport_fn: Callable[[int], None],
      open_transport_fn: Callable[[int], None],
      pigweed_port: int,
      send_file_to_device_fn: Callable[..., None],
      wait_for_bootup_complete_fn: Callable[[int], None],
      reset_endpoints_fn: Callable[[], None]):
    """Initializes an instance of MatterSampleAppShell capability.

    Args:
      device_name: Name of device using this capability.
      shell_fn: The shell method of the device.
      close_transport_fn: switchboard.close_transport method.
      open_transport_fn: switchboard.open_transport method.
      pigweed_port: Pigweed RPC port number.
      send_file_to_device_fn: The send_file_to_device method.
      wait_for_bootup_complete_fn: The wait_for_bootup_complete method.
      reset_endpoints_fn: The matter_endpoinst.reset method.
    """
    super().__init__(device_name=device_name)
    self._shell = shell_fn
    self._close_transport = close_transport_fn
    self._open_transport = open_transport_fn
    self._pigweed_port = pigweed_port
    self._send_file_to_device = send_file_to_device_fn
    self._wait_for_bootup_complete = wait_for_bootup_complete_fn
    self._reset_endpoints = reset_endpoints_fn

  @decorators.DynamicProperty
  def is_present(self) -> bool:
    """Returns if the app binary presents."""
    _, return_code = self._shell(
        _COMMANDS["CHECK_IF_APP_EXISTS"], include_return_code=True)
    return return_code == 0

  @decorators.DynamicProperty
  def is_running(self) -> bool:
    """Returns if the app process is running."""
    return bool(self.get_process_ids())

  @decorators.DynamicProperty
  def has_service(self) -> bool:
    """Returns if the sample app service file exists."""
    _, return_code = self._shell(
        _COMMANDS["CHECK_IF_SERVICE_EXISTS"], include_return_code=True)
    return return_code == 0

  @decorators.DynamicProperty
  def is_service_enabled(self) -> bool:
    """Returns if the sample app service is enabled."""
    return self._shell(_COMMANDS["CHECK_SERVICE_ENABLED"]) == "enabled"

  @decorators.CapabilityLogDecorator(logger)
  def get_process_ids(self) -> List[str]:
    """Gets all currently active linux app process IDs.

    Returns:
      The list of active linux app process IDs.
    """
    output = self._shell(_COMMANDS["GET_RUNNING_PROCESSES"])
    return list(output.splitlines()) if output else []

  @decorators.CapabilityLogDecorator(logger)
  def restart(self) -> None:
    """Restarts the linux app process.

    Note that the Matter sample app process is supposed to run as a linux system
    service, so no need to restart it manually after sending a termination
    command.

    Raises:
      CommunicationTimeoutError when the sample app didn't restart successfully.
    """
    self._close_transport(port=self._pigweed_port)

    # Terminate the process and wait for it to restart.
    running_processes = " ".join(self.get_process_ids())
    terminate_proc_cmd = (
        _COMMANDS["TERMINATE_PROCESS"].format(running_processes))
    self._shell(terminate_proc_cmd)

    # Poll until the sample app process is up.
    retry.retry(
        func=self.get_process_ids,
        timeout=_APP_START_SEC,
        interval=_POLL_INTERVAL_SEC,
        is_successful=bool,
        reraise=False)

    self._open_transport(port=self._pigweed_port)

    # Wait for the sample app to become responsive to RPCs.
    self._wait_for_bootup_complete()

  @decorators.CapabilityLogDecorator(logger)
  def enable_service(self) -> None:
    """Enables the sample app service.

    Does nothing if the service is already enabled.
    """
    if not self.is_service_enabled:
      self._shell(_COMMANDS["ENABLE_SERVICE"])

  @decorators.CapabilityLogDecorator(logger)
  def upgrade(self, sample_app_file_path: str) -> None:
    """Upgrades to a new sample app binary.

    Args:
      sample_app_file_path: Local path to the sample app file on the host.

    Raises:
      FileNotFoundError: when the given sample app file does not exist.
      PermissionError: when the sample app file is not executable.
    """
    if not os.path.exists(sample_app_file_path):
      raise FileNotFoundError(
          f"Sample app file {sample_app_file_path} does not exist.")

    if not os.access(sample_app_file_path, os.X_OK):
      raise PermissionError(
          f"Sample app file {sample_app_file_path} is not executable.")

    self._close_transport(port=self._pigweed_port)

    # Stop the service daemon, scp the sample app binary and start again.
    self._shell(_COMMANDS["STOP_SERVICE"])
    self._send_file_to_device(src=sample_app_file_path, dest=_MATTER_APP_PATH)
    self._shell(_COMMANDS["START_SERVICE"])

    # Poll until the sample app process is up.
    retry.retry(
        func=self.get_process_ids,
        timeout=_APP_START_SEC,
        interval=_POLL_INTERVAL_SEC,
        is_successful=bool,
        reraise=False)

    # Sometimes process being up doesn't mean it's able to connect.
    # A cool down period is needed to prevent connection failure.
    time.sleep(_COOL_DOWN_SEC)

    self._open_transport(port=self._pigweed_port)

    # Wait for the sample app to become responsive to RPCs and reset the cached
    # endpoints.
    self._wait_for_bootup_complete()
    self._reset_endpoints()
