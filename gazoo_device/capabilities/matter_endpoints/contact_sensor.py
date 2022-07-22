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

"""Matter Contact Sensor endpoint.

This endpoint module corresponds to the
"Contact Sensor" Matter device type which defines required and optional
clusters in the Matter spec 1.0.

The required clusters for this endpoint: Boolean State
"""
from gazoo_device import decorators
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters import boolean_state_pw_rpc
from gazoo_device.capabilities.matter_endpoints.interfaces import contact_sensor_base


class ContactSensorEndpoint(contact_sensor_base.ContactSensorBase):
  """Matter Contact Sensor endpoint."""

  @decorators.CapabilityDecorator(boolean_state_pw_rpc.BooleanStateClusterPwRpc)
  def boolean_state(self) -> boolean_state_pw_rpc.BooleanStateClusterPwRpc:
    """Matter Boolean State cluster instance."""
    return self.cluster_lazy_init(matter_enums.BooleanStateCluster.ID)
