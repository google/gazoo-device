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

"""Pigweed RPC implementation of the Matter Color Control cluster capability.
"""
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters.interfaces import color_control_base
from gazoo_device.protos import attributes_service_pb2

logger = gdm_logger.get_logger()
ColorControlCluster = matter_enums.ColorControlCluster
INT8U_ATTRIBUTE_TYPE = attributes_service_pb2.AttributeType.ZCL_INT8U_ATTRIBUTE_TYPE


class ColorControlClusterPwRpc(color_control_base.ColorControlClusterBase):
  """Matter Color Control cluster capability."""

  @decorators.CapabilityLogDecorator(logger)
  def move_to_hue(self, hue: int, verify: bool = True) -> None:
    """The MoveToHue command.

    On receipt of this command, a device should move from its current hue
    to the given hue value.

    Args:
      hue: The hue that the device should move to.
      verify: If true, verifies the hue changes before returning.
    """
    previous_hue = self.current_hue

    self._write(
        endpoint_id=self._endpoint_id,
        cluster_id=ColorControlCluster.ID,
        attribute_id=ColorControlCluster.ATTRIBUTE_CURRENT_HUE,
        attribute_type=INT8U_ATTRIBUTE_TYPE,
        data_uint8=hue)

    if verify:
      if self.current_hue != hue:  # pylint: disable=comparison-with-callable
        raise errors.DeviceError(
            f"Device {self._device_name} current hue didn't change to {hue} "
            f"from {previous_hue}.")

  @decorators.CapabilityLogDecorator(logger)
  def move_to_saturation(self, saturation: int, verify: bool = True) -> None:
    """The MoveToSaturation command.

    On receipt of this command, a device should move from its current saturation
    to the given saturation value.

    Args:
      saturation: The saturation that the device should move to.
      verify: If true, verifies the hue changes before returning.
    """
    previous_saturation = self.current_saturation

    self._write(
        endpoint_id=self._endpoint_id,
        cluster_id=ColorControlCluster.ID,
        attribute_id=ColorControlCluster.ATTRIBUTE_CURRENT_SATURATION,
        attribute_type=INT8U_ATTRIBUTE_TYPE,
        data_uint8=saturation)

    if verify:
      if self.current_saturation != saturation:  # pylint: disable=comparison-with-callable
        raise errors.DeviceError(
            f"Device {self._device_name} current saturation didn't change to "
            f"{saturation} from {previous_saturation}.")

  @decorators.DynamicProperty
  def current_hue(self) -> int:
    """The CurrentHue attribute.

    The CurrentHue attribute contains the current hue value of the light.

    Returns:
      The current hue.
    """
    color_data = self._read(
        endpoint_id=self._endpoint_id,
        cluster_id=matter_enums.ColorControlCluster.ID,
        attribute_id=ColorControlCluster.ATTRIBUTE_CURRENT_HUE,
        attribute_type=INT8U_ATTRIBUTE_TYPE)
    return color_data.data_uint8

  @decorators.DynamicProperty
  def current_saturation(self) -> int:
    """The CurrentSaturation attribute.

    The CurrentSaturation attribute contains the current saturation value of
    the light.

    Returns:
      The current saturation.
    """
    color_data = self._read(
        endpoint_id=self._endpoint_id,
        cluster_id=matter_enums.ColorControlCluster.ID,
        attribute_id=ColorControlCluster.ATTRIBUTE_CURRENT_SATURATION,
        attribute_type=INT8U_ATTRIBUTE_TYPE)
    return color_data.data_uint8
