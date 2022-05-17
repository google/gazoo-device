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

"""Pigweed RPC implementation of the Matter On/Off cluster capability.
"""
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters.interfaces import on_off_base
from gazoo_device.protos import attributes_service_pb2

logger = gdm_logger.get_logger()
OnOffCluster = matter_enums.OnOffCluster
BOOLEAN_ATTRIBUTE_TYPE = attributes_service_pb2.AttributeType.ZCL_BOOLEAN_ATTRIBUTE_TYPE


class OnOffClusterPwRpc(on_off_base.OnOffClusterBase):
  """Matter On/Off cluster capability."""

  @decorators.CapabilityLogDecorator(logger)
  def on(self, verify: bool = True) -> None:
    """The On command to turn on the Matter device.

    Args:
      verify: If true, verifies the state change before returning.
    """
    self._onoff_command(on=True, verify=verify)

  @decorators.CapabilityLogDecorator(logger)
  def off(self, verify: bool = True) -> None:
    """The Off command to turn off the Matter device.

    Args:
      verify: If true, verifies the state change before returning.
    """
    self._onoff_command(on=False, verify=verify)

  @decorators.CapabilityLogDecorator(logger)
  def toggle(self, verify: bool = True) -> None:
    """The Toggle command to toggle the OnOff state of the Matter device.

    On receipt of this command, if a device is in its "Off" state it should
    enter its "On" state. Otherwise, if it is in its "On" state it should
    enter its "Off" state.

    Args:
      verify: If true, verifies the state change before returning.
    """
    self._onoff_command(on=not self.onoff, verify=verify)

  @decorators.DynamicProperty
  def onoff(self) -> bool:
    """The OnOff attribute.

    The OnOff attribute indicates the state of the device and has the following
    values: FALSE = "Off" state, TRUE = "On" state.

    Returns:
      True if the device is in on state, false if it's in off state.

    Raises:
      DeviceError: when the ack value is false.
    """
    onoff_data = self._read(
        endpoint_id=self._endpoint_id,
        cluster_id=OnOffCluster.ID,
        attribute_id=OnOffCluster.ATTRIBUTE_ON_OFF,
        attribute_type=BOOLEAN_ATTRIBUTE_TYPE)
    return onoff_data.data_bool

  def _onoff_command(self, on: bool, verify: bool = True) -> None:
    """Turn on/off the device.

    Args:
      on: Turns on the device if true, turn off the device otherwise.
      verify: If true, verifies the device configurations before returning.

    Raises:
      DeviceError: when the ack value if false or the device does not transition
      to the appropriate OnOff state.
    """
    self._write(
        endpoint_id=self._endpoint_id,
        cluster_id=OnOffCluster.ID,
        attribute_id=OnOffCluster.ATTRIBUTE_ON_OFF,
        attribute_type=BOOLEAN_ATTRIBUTE_TYPE,
        data_bool=on)

    if verify:
      if on != self.onoff:  # pylint: disable=comparison-with-callable
        action = "on" if on else "off"
        raise errors.DeviceError(
            f"Device {self._device_name} didn't turn {action}.")
