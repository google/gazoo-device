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

"""Matter Door Lock endpoint.

This endpoint module corresponds to the
"Door Lock" Matter device type which defines required and optional clusters
in the Matter spec 1.0.

A Door Lock endpoint houses an instance of Door Lock Matter device type with
the following defined clusters on this endpoint:

The required clusters for this endpoint: Door Lock.
The optional clusters for this endpoint: Groups, Scenes, Alarms, Time,
TimeSync and Poll Control.
"""
from gazoo_device import decorators
from gazoo_device.capabilities.matter_clusters import door_lock_pw_rpc
from gazoo_device.capabilities.matter_endpoints.interfaces import door_lock_base


class DoorLockEndpoint(door_lock_base.DoorLockBase):
  """Matter Door Lock endpoint."""

  @decorators.CapabilityDecorator(door_lock_pw_rpc.DoorLockClusterPwRpc)
  def door_lock(self) -> door_lock_pw_rpc.DoorLockClusterPwRpc:
    """Matter Door Lock cluster instance."""
    return self.cluster_lazy_init(door_lock_pw_rpc.DoorLockClusterPwRpc)

  # TODO(b/209362086) Add the below clusters

  # def scenes(self):
  #   """Matter Scenes cluster instance."""
  #   raise NotImplementedError("Scenes cluster isn't implemented.")

  # def groups(self):
  #   """Matter Groups cluster instance."""
  #   raise NotImplementedError("Groups cluster isn't implemented.")

  # def alarms(self):
  #   """Matter Alarms cluster instance."""
  #   raise NotImplementedError("Alarms cluster isn't implemented.")

  # def time(self):
  #   """Matter Time cluster instance."""
  #   raise NotImplementedError("Time cluster isn't implemented.")

  # def time_sync(self):
  #   """Matter TimeSync cluster instance."""
  #   raise NotImplementedError("TimeSync cluster isn't implemented.")

  # def poll_control(self):
  #   """Matter Poll Control cluster instance."""
  #   raise NotImplementedError("Poll Control cluster isn't implemented.")
