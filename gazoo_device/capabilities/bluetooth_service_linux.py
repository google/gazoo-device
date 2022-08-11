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
"""The bluetooth service controls capability for linux platform."""
import enum
from typing import Callable

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import bluetooth_service_base

logger = gdm_logger.get_logger()


class _Commands(str, enum.Enum):
  """System service control commands for bluetooth service."""
  STATUS = "sudo systemctl status bluetooth"
  START = "sudo systemctl start bluetooth"
  STOP = "sudo systemctl stop bluetooth"
  RESTART = "sudo systemctl restart bluetooth"


class _Regexes(str, enum.Enum):
  """Regexes for the shell output of bluetooth service."""
  STATUS = r"Active: (\w+) \(\w+\)(.*)"


class BluetoothServiceLinux(bluetooth_service_base.BluetoothServiceBase):
  """The bluetooth service controls capability for linux platform."""

  def __init__(
      self,
      device_name: str,
      shell_fn: Callable[..., str],
      shell_with_regex_fn: Callable[..., str]):
    """Initializes an instance of BluetoothServiceLinux capability.

    Args:
      device_name: Name of device using this capability.
      shell_fn: The shell method of the device.
      shell_with_regex_fn: The shell_with_regex method of the device.
    """
    super().__init__(device_name=device_name)
    self._shell = shell_fn
    self._shell_with_regex = shell_with_regex_fn

  @decorators.DynamicProperty
  def status(self) -> bool:
    """Returns whether the bluetooth service is active or not."""
    return self._shell_with_regex(
        command=_Commands.STATUS,
        regex=_Regexes.STATUS,
        raise_error=True) == "active"

  @decorators.CapabilityLogDecorator(logger)
  def start(self) -> None:
    """Starts the bluetooth service."""
    self._shell(_Commands.START)
    if not self.status:
      raise errors.DeviceError(
          f"{self._device_name} failed to start bluetooth.")

  @decorators.CapabilityLogDecorator(logger)
  def stop(self) -> None:
    """Stops the bluetooth service."""
    self._shell(_Commands.STOP)
    if self.status:  # pylint: disable=using-constant-test
      raise errors.DeviceError(
          f"{self._device_name} failed to stop bluetooth.")

  @decorators.CapabilityLogDecorator(logger)
  def restart(self) -> None:
    """Retarts the bluetooth service."""
    self._shell(_Commands.RESTART)
    if not self.status:
      raise errors.DeviceError(
          f"{self._device_name} failed to restart bluetooth.")
