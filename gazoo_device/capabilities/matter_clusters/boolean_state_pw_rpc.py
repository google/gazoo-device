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

"""RPC implementation of Matter Boolean State cluster capability.
"""

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters.interfaces import boolean_state_base
from gazoo_device.protos import attributes_service_pb2


logger = gdm_logger.get_logger()
_BooleanStateCluster = matter_enums.BooleanStateCluster
BOOLEAN_ATTRIBUTE_TYPE = attributes_service_pb2.AttributeType.ZCL_BOOLEAN_ATTRIBUTE_TYPE


class BooleanStateClusterPwRpc(
    boolean_state_base.BooleanStateClusterBase):
  """Matter Boolean State cluster capability."""

  @decorators.DynamicProperty
  def state_value(self) -> bool:
    """The StateValue attribute.

    The semantics of this boolean state are defined by the device type using
    this cluster. For example, in a Contact Sensor device type, FALSE=open or
    no contact, TRUE=closed or contact.

    Returns:
      The StateValue attribute.
    """
    measured_value_data = self._read(
        endpoint_id=self._endpoint_id,
        cluster_id=_BooleanStateCluster.ID,
        attribute_id=_BooleanStateCluster.ATTRIBUTE_STATE_VALUE,
        attribute_type=BOOLEAN_ATTRIBUTE_TYPE)
    return measured_value_data.data_bool

  @state_value.setter
  def state_value(self, state: bool) -> None:
    """Updates the StateValue attribute.

    The semantics of this boolean state are defined by the device type using
    this cluster. For example, in a Contact Sensor device type, FALSE=open or
    no contact, TRUE=closed or contact.

    Args:
      state: The state BooleanState should update to.
    """
    previous_state = self.state_value

    self._write(
        endpoint_id=self._endpoint_id,
        cluster_id=_BooleanStateCluster.ID,
        attribute_id=_BooleanStateCluster.ATTRIBUTE_STATE_VALUE,
        attribute_type=BOOLEAN_ATTRIBUTE_TYPE,
        data_bool=state)

    if self.state_value != state:  # pylint: disable=comparison-with-callable
      raise errors.DeviceError(
          f"Device {self._device_name} state_value didn't change to "
          f"{state} from {previous_state}.")

