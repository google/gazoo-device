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
"""chip-tool implementation of the Matter On/Off cluster capability.
"""
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.matter_clusters.interfaces import on_off_base

logger = gdm_logger.get_logger()

_CLUSTER_NAME = 'onoff'


class OnOffClusterChipTool(on_off_base.OnOffClusterBase):
  """chip-tool based Matter On/Off cluster capability."""

  @decorators.CapabilityLogDecorator(logger)
  def on(self, verify: bool = True) -> None:
    """The On command to turn on the Matter device."""
    self._onoff_command('on', True, verify)

  @decorators.CapabilityLogDecorator(logger)
  def off(self, verify: bool = True) -> None:
    """The Off command to turn off the Matter device."""
    self._onoff_command('off', False, verify)

  @decorators.CapabilityLogDecorator(logger)
  def toggle(self, verify: bool = True) -> None:
    """The Toggle command to toggle the OnOff state of the Matter device."""
    self._onoff_command('toggle', not self.onoff, verify)

  @decorators.DynamicProperty
  def onoff(self) -> bool:
    """The OnOff attribute."""
    return self._read(self._endpoint_id, _CLUSTER_NAME, 'on-off')

  def _onoff_command(self, command: str, on: bool, verify: bool = True) -> None:
    """Turn on/off the device.

    Args:
      command: Name of the command to send to the device via chip-tool.
      on: Turns on the device if true, turn off the device otherwise.
      verify: If true, verifies the device configurations before returning.

    Raises:
      DeviceError: when the device does not transition to the appropriate
      OnOff state.
    """
    self._send(self._endpoint_id, _CLUSTER_NAME, command, [])

    if verify and on is not self.onoff:
      action = 'on' if on else 'off'
      raise errors.DeviceError(
          f'Device {self._device_name} did not turn {action}.')
