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

"""RPC implementation of Matter Switch cluster capability.
"""
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters.interfaces import switch_base
from gazoo_device.protos import attributes_service_pb2

_LOGGER = gdm_logger.get_logger()
SwitchCluster = matter_enums.SwitchCluster

INT8U_ATTRIBUTE_TYPE = (
    attributes_service_pb2.AttributeType.ZCL_INT8U_ATTRIBUTE_TYPE
)


# TODO(gdm-authors): Add support for NumberOfPositions,
# MultiPressMax attributes to SwitchClusterPwRpc with switch_base
class SwitchClusterPwRpc(switch_base.SwitchClusterBase):
  """Matter Switch cluster capability."""

  @decorators.DynamicProperty
  def current_position(self) -> int:
    """The CurrentPosition attribute."""
    return self._get_position(
        attribute_id=SwitchCluster.ATTRIBUTE_CURRENT_POSITION
    )

  @decorators.CapabilityLogDecorator(_LOGGER)
  def set_current_position(self, position: int, verify: bool = True) -> None:
    """Sets the CurrentPosition attribute.

    Args:
      position: The position to set.
      verify: Whether to verify the position after setting it.
    """
    self._write(
        endpoint_id=self._endpoint_id,
        cluster_id=SwitchCluster.ID,
        attribute_id=SwitchCluster.ATTRIBUTE_CURRENT_POSITION,
        attribute_type=INT8U_ATTRIBUTE_TYPE,
        data_uint8=position,
    )

    current_position_attribute = self._get_position(
        attribute_id=SwitchCluster.ATTRIBUTE_CURRENT_POSITION
    )
    if verify:
      if current_position_attribute != position:
        raise errors.DeviceError(
            f"Expected current position to be {position}, but got"
            f" {current_position_attribute}"
        )

  @decorators.CapabilityLogDecorator(_LOGGER)
  def generate_initial_press_event(self) -> None:
    """Generates an initial press event."""
    self._write(
        endpoint_id=self._endpoint_id,
        cluster_id=SwitchCluster.ID,
        attribute_id=SwitchCluster.ATTRIBUTE_CURRENT_POSITION,
        attribute_type=INT8U_ATTRIBUTE_TYPE,
        data_uint8=1,
    )

  def _get_position(self, attribute_id: int) -> int:
    """Get position value by attribute ID."""
    position_data = self._read(
        endpoint_id=self._endpoint_id,
        cluster_id=SwitchCluster.ID,
        attribute_id=attribute_id,
        attribute_type=INT8U_ATTRIBUTE_TYPE,
    )
    return position_data.data_uint8
