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

"""Stub concrete subclass of abstract AuxiliaryDevice for unit testing.

This module is a GDM extension package (as it defines export_extensions).
"""
from typing import Any, NoReturn

from gazoo_device import custom_types
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.base_classes import auxiliary_device
from gazoo_device.detect_criteria import generic_detect_criteria
from gazoo_device.switchboard import switchboard
from gazoo_device.switchboard.communication_types import ssh_comms
import immutabledict

_LOGGER = gdm_logger.get_logger()


class AuxiliaryDeviceStub(auxiliary_device.AuxiliaryDevice):
  """Stub class that implements abstract methods and properties."""
  COMMUNICATION_TYPE = ssh_comms.SshComms
  _COMMUNICATION_KWARGS = immutabledict.immutabledict()
  DEVICE_TYPE = "aux"
  DETECT_MATCH_CRITERIA = immutabledict.immutabledict({
      # Dummy detection query.
      generic_detect_criteria.GenericQuery.ALWAYS_TRUE: True,
  })
  logger = _LOGGER  # Mocked by device_base_class_test.py.

  @decorators.LogDecorator(_LOGGER)
  def get_console_configuration(self) -> None:
    del self  # Unused.
    return None

  @decorators.PersistentProperty
  def some_property(self) -> str:
    return "something"

  @decorators.DynamicProperty
  def bad_property(self) -> NoReturn:
    raise errors.DeviceError("x")

  @decorators.LogDecorator(_LOGGER)
  def get_detection_info(self) -> NoReturn:
    raise errors.DeviceError(
        f"get_detection_info is not implemented by {type(self).__name__}.")

  @classmethod
  def is_connected(
      cls, device_config: custom_types.ManagerDeviceConfigDict) -> bool:
    return True

  @decorators.LogDecorator(_LOGGER)
  def reboot(self, no_wait: bool = False, method: str = "shell") -> None:
    del no_wait, method  # Unused.

  @decorators.health_check
  def check_3(self) -> NoReturn:
    """Fake health check 3.

    Raises:
      DeviceError: for testing.
    """
    raise errors.DeviceError("health check failed")

  def shell(self,
            command: str,
            command_name: str = "shell",
            timeout: float = 1,
            port: int = 0,
            include_return_code: bool = False) -> str:
    """Mock shell methods.

    Args:
      command: Unused.
      command_name: Name of the shell command.
      timeout: If 0, raises an error.
      port: Unused.
      include_return_code: Unused.

    Raises:
      DeviceError: if timeout is 0.

    Returns:
      Mock shell return value.
    """
    del command, port, include_return_code  # Unused.
    if timeout == 0:
      raise errors.DeviceError(
          f"command_name: {command_name}. Test timeout error.")
    return "NCC-1701"

  @decorators.CapabilityDecorator(switchboard.SwitchboardDefault)
  def switchboard(self) -> switchboard.SwitchboardDefault:
    """Instance for communicating with the device."""
    switchboard_name = self._get_private_capability_name(
        switchboard.SwitchboardDefault)
    if not hasattr(self, switchboard_name):
      switchboard_kwargs = {
          **self._COMMUNICATION_KWARGS,
          "communication_address": self.communication_address,
          "communication_type": self.COMMUNICATION_TYPE.__name__,
          "log_path": self.log_file_name,
          "device_name": self.name,
          "event_parser": None
      }
      setattr(self, switchboard_name,
              self.get_manager().create_switchboard(**switchboard_kwargs))

    return getattr(self, switchboard_name)


def export_extensions() -> dict[str, Any]:
  """Exports device class and capabilities to act as a GDM extension package."""
  return {"auxiliary_devices": [AuxiliaryDeviceStub]}

__version__ = "0.0.1"
