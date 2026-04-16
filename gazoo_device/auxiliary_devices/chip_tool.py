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

"""Controller for chip-tool running on the host."""
import os
import platform
from typing import Any, Callable, List, Optional, Tuple, Union

from gazoo_device import config
from gazoo_device import console_config
from gazoo_device import custom_types
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device import mobly_controller
from gazoo_device import version
from gazoo_device.base_classes import auxiliary_device
from gazoo_device.base_classes import matter_endpoints_mixin
from gazoo_device.capabilities import matter_controller_chip_tool
from gazoo_device.capabilities import matter_endpoints_accessor_chip_tool
from gazoo_device.capabilities import shell_ssh
from gazoo_device.detect_criteria import host_shell_detect_criteria
from gazoo_device.switchboard import switchboard
from gazoo_device.switchboard.communication_types import host_shell_comms
from gazoo_device.utility import host_utils
import immutabledict

_logger = gdm_logger.get_logger()

_CHIP_TOOL = "chip-tool"
_LOGGING_CMD = ("tail", "-F", matter_controller_chip_tool.LOGGING_FILE_PATH)
_REGEXES = immutabledict.immutabledict({
    "USAGE": "Usage:",
})
_TIMEOUTS = immutabledict.immutabledict({
    "SHELL": 10,
})


def _raise_not_implemented_error(*args, **kwargs):
  raise NotImplementedError("Not available when running on the host")


class ChipTool(
    auxiliary_device.AuxiliaryDevice,
    matter_endpoints_mixin.MatterEndpointAliasesMixin,
):
  """Base Class for CHIP tool on x86 host."""

  COMMUNICATION_TYPE = host_shell_comms.HostShellComms
  DETECT_MATCH_CRITERIA = immutabledict.immutabledict({
      host_shell_detect_criteria.HostShellQuery.IS_CHIP_TOOL_PRESENT: True,
  })
  DEVICE_TYPE = "chip_tool"
  _COMMUNICATION_KWARGS = immutabledict.immutabledict({
      "command": "bash",
      "args": (),
      "log_cmd": ("tail", "-F", matter_controller_chip_tool.LOGGING_FILE_PATH),
  })

  _RESPONSE_REGEX = immutabledict.immutabledict({
      # Example matched pattern:
      # [1653012222.679309][1030572:1030577] [DMG]        Data = 1, 2
      "DESCRIPTOR_ATTRIBUTE_RESPONSE": r".DMG.\s+Data = (\w+)",
      "DEVICE_TYPE_LIST_RESPONSE": r".TOO.\s+(?:Device)?Type: (\d+)",
  })

  def __init__(self, *args, **kwargs) -> None:
    super().__init__(*args, **kwargs)
    self._chip_tool_path = ""
    self._regexes.update(_REGEXES)
    self._timeouts.update(_TIMEOUTS)

  @decorators.LogDecorator(_logger)
  def factory_reset(self) -> None:
    """Factory resets the device."""
    self.matter_controller.factory_reset()

  @decorators.CapabilityDecorator(
      matter_controller_chip_tool.MatterControllerChipTool
  )
  def matter_controller(
      self,
  ) -> matter_controller_chip_tool.MatterControllerChipTool:
    """Matter controller capability to send chip-tool commands to the device."""
    return self.lazy_init(
        matter_controller_chip_tool.MatterControllerChipTool,
        device_name=self.name,
        regex_shell_fn=self.shell_with_regex,
        shell_fn=self.shell,
        send_file_to_device=_raise_not_implemented_error,
        get_property_fn=self.get_property,
        set_property_fn=self.set_property,
    )

  @decorators.OptionalProperty
  def matter_node_id(self) -> Optional[int]:
    """Matter Node ID assigned to the currently commissioned end device."""
    return self.props["optional"].get("matter_node_id")

  @decorators.CapabilityDecorator(
      matter_endpoints_accessor_chip_tool.MatterEndpointsAccessorChipTool
  )
  def matter_endpoints(
      self,
  ) -> matter_endpoints_accessor_chip_tool.MatterEndpointsAccessorChipTool:
    """Matter capability to access commissioned device's endpoint instances."""
    if self.matter_node_id is None:
      raise errors.DeviceError(
          "matter_endpoints requires a commissioned end device. "
          "Commission a device via matter_controller.commission."
      )

    return self.lazy_init(
        matter_endpoints_accessor_chip_tool.MatterEndpointsAccessorChipTool,
        device_name=self.name,
        node_id_getter=lambda: self.matter_node_id,
        shell_fn=self.shell,
        shell_with_regex=self.shell_with_regex,
        matter_controller=self.matter_controller,
        device_type=self.DEVICE_TYPE,
        response_regex=self._RESPONSE_REGEX,
    )

  @decorators.health_check
  def check_chip_tool_available(self):
    """Sets self._chip_tool_path to the chip-tool binary path from $PATH.

    Raises:
      DependencyUnavailableError: if chip-tool is not found in $PATH.
    """
    chip_tool_path = host_utils.get_command_path(_CHIP_TOOL)
    if not chip_tool_path:
      host_path_env = os.getenv("PATH", "")
      raise errors.DependencyUnavailableError(
          f"Did not find {_CHIP_TOOL} in the host's $PATH: {host_path_env}"
      )
    self._chip_tool_path = chip_tool_path

  @decorators.health_check
  def check_chip_tool_executable(self):
    """Checks that the chip-tool binary is executable.

    Raises:
      DependencyUnavailableError: if chip-tool is not executable.
    """
    response, return_code = self.shell(
        self._chip_tool_path, include_return_code=True
    )
    if return_code != 0:
      raise errors.DependencyUnavailableError(
          f"{self._chip_tool_path} is not executable. "
          f"Didn't find {_REGEXES['USAGE']} in {response}. "
          f"Return code: {return_code}. "
      )

  @decorators.PersistentProperty
  def platform(self) -> str:
    """Returns the platform type of the device."""
    return platform.platform()

  def get_console_configuration(self) -> console_config.ConsoleConfiguration:
    """Returns the interactive console configuration."""
    return console_config.get_log_response_separate_port_configuration(
        self.switchboard.get_line_identifier()
    )

  @decorators.PersistentProperty
  def health_checks(self) -> List[Callable[[], None]]:
    """Returns list of methods to execute as health checks."""
    return [
        self.check_device_connected,
        self.check_create_switchboard,
        self.check_chip_tool_available,
        self.check_chip_tool_executable,
    ]

  @decorators.LogDecorator(_logger)
  def recover(self, error: errors.CheckDeviceReadyError) -> None:
    """Recovers the device from an error detected by check_device_ready()."""
    if isinstance(error, errors.DependencyUnavailableError):
      # TODO(gdm-authors): something can be called here to (re)install the
      # chip-tool binary if it's not working. This is an example of a health
      # check and recovery. The DependencyUnavailableError would be coming from
      # either check_chip_tool_available or check_chip_tool_executable failures.
      pass
    else:
      super().recover(error)

  @decorators.LogDecorator(_logger)
  def get_detection_info(
      self,
  ) -> Tuple[
      custom_types.PersistentConfigsDict, custom_types.OptionalConfigsDict
  ]:
    """Gets the persistent and optional attributes of a device during setup.

    Returns:
      Dictionaries of persistent attributes, and optional attributes.
    """
    self.props["optional"]["matter_node_id"] = None
    # Stubs for required persistent properties.
    self.props["persistent_identifiers"]["model"] = "N/A"
    self.props["persistent_identifiers"]["serial_number"] = "00000000"
    return self.props["persistent_identifiers"], self.props["optional"]

  @classmethod
  def is_connected(
      cls, device_config: custom_types.ManagerDeviceConfigDict
  ) -> bool:
    """Determines if the device is connected (reachable).

    Args:
      device_config: Dictionary containing "persistent" properties.

    Returns:
      True if the device is connected, False otherwise.
    """
    return host_utils.has_command(_CHIP_TOOL)

  # TODO(gdm-authors): this is hacky. This should work as 'ShellSSH' doesn't
  # actually assume the underlying communication is going over SSH (it just uses
  # switchboard.send_and_expect, which is a communication abstraction; in this
  # case it's using a subprocess.Popen to execute host shell commands), but
  # the 'ShellSSH' naming suggests otherwise. Perhaps rename the capability or
  # reimplement shell() here without using ShellSSH.
  @decorators.CapabilityDecorator(shell_ssh.ShellSSH)
  def shell_capability(self) -> shell_ssh.ShellSSH:
    """An SSH shell command execution capability."""
    return self.lazy_init(
        shell_ssh.ShellSSH,
        self.switchboard.send_and_expect,
        self.name,
        timeout=self.timeouts["SHELL"],
        tries=1,
    )

  def shell(
      self,
      command: str,
      command_name: str = "shell",
      timeout: Optional[float] = None,
      port: int = 0,
      include_return_code: bool = False,
      searchwindowsize: int = config.SEARCHWINDOWSIZE,
  ) -> Union[str, Tuple[str, int]]:
    """Sends command and returns response and optionally return code.

    Args:
      command: Shell command to execute.
      command_name: Identifier for command.
      timeout: Time in seconds to wait for device to respond.
      port: Which port to send on. Port 0 is typically used for commands.
      include_return_code: Whether to also return the command return code.
      searchwindowsize: Number of the response bytes to look at.

    Raises:
      DeviceError: if communication fails.

    Returns:
      The device response and optionally (if include_return_code is True) the
      return code.
    """
    return self.shell_capability.shell(
        command=command,
        command_name=command_name,
        timeout=timeout or self.timeouts["SHELL"],
        port=port,
        include_return_code=include_return_code,
        searchwindowsize=searchwindowsize,
    )

  def shell_with_regex(
      self,
      command: str,
      regex: str,
      regex_group: int = 1,
      command_name: str = "shell",
      raise_error: bool = False,
      tries: int = 1,
      port: int = 0,
      timeout: Optional[float] = None,
      searchwindowsize: int = config.SEARCHWINDOWSIZE,
  ) -> str:
    """Sends a command, searches for a regex in the response, and returns a match group.

    Args:
      command: Shell command to issue.
      regex: Regular expression with one or more capturing groups.
      regex_group: Number of regex group to return.
      command_name: Command name to appear in log messages.
      raise_error: whether or not to raise error if unable to find a match.
      tries: how many times to try executing the command before failing.
      port: which port to send the shell command to.
      timeout: Time in seconds to wait for device to respond.
      searchwindowsize: Number of the response bytes to look at.

    Returns:
      Value of the capturing group with index 'regex_group' in the match.

    Raises:
      DeviceError: if command execution fails OR
                   couldn't find the requested group in any of the responses.
    """
    return self.command_with_regex(
        command=command,
        regex=regex,
        command_fn=self.shell,
        regex_group=regex_group,
        raise_error=raise_error,
        tries=tries,
        command_name=command_name,
        port=port,
        timeout=timeout,
    )

  @decorators.CapabilityDecorator(switchboard.SwitchboardDefault)
  def switchboard(self) -> switchboard.SwitchboardDefault:
    """Switchboard capability instance for communicating with the device."""
    switchboard_name = self._get_private_capability_name(
        switchboard.SwitchboardDefault
    )
    if not hasattr(self, switchboard_name):
      switchboard_kwargs = {
          **self._COMMUNICATION_KWARGS,
          "communication_address": self.communication_address,
          "communication_type": self.COMMUNICATION_TYPE.__name__,
          "log_path": self.log_file_name,
          "device_name": self.name,
          "event_parser": None,
      }
      setattr(
          self,
          switchboard_name,
          self.get_manager().create_switchboard(**switchboard_kwargs),
      )

    return getattr(self, switchboard_name)


_DeviceClass = ChipTool
_COMMUNICATION_TYPE = _DeviceClass.COMMUNICATION_TYPE.__name__
# For Mobly controller integration.
MOBLY_CONTROLLER_CONFIG_NAME = (
    mobly_controller.get_mobly_controller_config_name(_DeviceClass.DEVICE_TYPE))
create = mobly_controller.create
destroy = mobly_controller.destroy
get_info = mobly_controller.get_info
get_manager = mobly_controller.get_manager


def export_extensions() -> dict[str, Any]:
  """Exports device class and capabilities to act as a GDM extension package."""
  return {
      "auxiliary_devices": [_DeviceClass],
      "detect_criteria": immutabledict.immutabledict({
          _COMMUNICATION_TYPE: host_shell_detect_criteria.HOST_SHELL_QUERY_DICT,
      }),
  }

__version__ = version.VERSION
