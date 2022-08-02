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
from typing import Callable, List

from gazoo_device import decorators
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import matter_app_controls_base
from gazoo_device.utility import pwrpc_utils
from gazoo_device.utility import retry
import immutabledict

logger = gdm_logger.get_logger()

_MATTER_APP_PATH = f"/home/pi/{pwrpc_utils.MATTER_LINUX_APP_NAME}"
_APP_START_SEC = 1  # seconds
_POLL_INTERVAL_SEC = 0.1  # seconds
_COMMANDS = immutabledict.immutabledict({
    "CHECK_IF_APP_EXISTS": f"test -f {_MATTER_APP_PATH} && echo exists",
    "GET_RUNNING_PROCESSES": f"pgrep -f {pwrpc_utils.MATTER_LINUX_APP_NAME}",
    "TERMINATE_PROCESS": "sudo kill -9 {}",
    "DELETE_APP": f"sudo rm {_MATTER_APP_PATH}",
})


class MatterSampleAppShell(matter_app_controls_base.MatterSampleAppBase):
  """Matter app controls and management capability over shell."""

  def __init__(
      self,
      device_name: str,
      shell_fn: Callable[..., str],
      close_transport_fn: Callable[[int], None],
      open_transport_fn: Callable[[int], None],
      pigweed_port: int):
    """Initializes an instance of MatterSampleAppShell capability.

    Args:
      device_name: Name of device using this capability.
      shell_fn: The shell method of the device.
      close_transport_fn: switchboard.close_transport method.
      open_transport_fn: switchboard.open_transport method.
      pigweed_port: Pigweed RPC port number.
    """
    super().__init__(device_name=device_name)
    self._shell = shell_fn
    self._close_transport = close_transport_fn
    self._open_transport = open_transport_fn
    self._pigweed_port = pigweed_port

  @decorators.DynamicProperty
  def is_present(self) -> bool:
    """Returns if the app binary presents."""
    return bool(self._shell(_COMMANDS["CHECK_IF_APP_EXISTS"]))

  @decorators.DynamicProperty
  def is_running(self) -> bool:
    """Returns if the app process is running."""
    return bool(self.get_process_ids())

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

    running_processes = " ".join(self.get_process_ids())
    terminate_proc_cmd = (
        _COMMANDS["TERMINATE_PROCESS"].format(running_processes))
    self._shell(terminate_proc_cmd)

    retry.retry(
        func=self.get_process_ids,
        timeout=_APP_START_SEC,
        interval=_POLL_INTERVAL_SEC,
        is_successful=bool,
        reraise=False)

    self._open_transport(port=self._pigweed_port)

  @decorators.CapabilityLogDecorator(logger)
  def upgrade(self, app_file: str) -> None:
    """Upgrades to a new app file.

    Args:
      app_file: Local path to app file on the host.
    """
    raise NotImplementedError(
        f"{self._device_name}'s upgrade method has not implemented yet.")
