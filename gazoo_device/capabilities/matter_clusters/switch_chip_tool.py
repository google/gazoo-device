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

"""chip-tool implementation of Matter Switch cluster capability.
"""
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.matter_clusters.interfaces import switch_base

_LOGGER = gdm_logger.get_logger()

_CLUSTER_NAME = "switch"


class SwitchClusterChipTool(switch_base.SwitchClusterBase):
  """Matter Switch cluster capability."""

  @decorators.DynamicProperty
  def current_position(self) -> int:
    """The CurrentPosition attribute."""
    return self._read(self._endpoint_id, _CLUSTER_NAME, "current-position")

  @decorators.CapabilityLogDecorator(_LOGGER)
  def set_current_position(self, position: int, verify: bool = True) -> None:
    """The CurrentPosition attribute."""

    self._write(
        endpoint_id=self._endpoint_id,
        cluster=_CLUSTER_NAME,
        attribute="current-position",
        data_uint8=position,
    )

    if verify:
      current_position_attribute = self._read(
          endpoint_id=self._endpoint_id,
          cluster=_CLUSTER_NAME,
          attribute="current-position",
      )
      if current_position_attribute.data_uint8 != position:
        raise errors.DeviceError(
            f"Device {self._device_name} current position attribute did not "
            f"change from {current_position_attribute.data_uint8}."
        )
