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

"""Matter Dimmable Light endpoint.

A Dimmable Light is a lighting device that is capable of being switched on or
off and the intensity of its light adjusted by means of a bound controller
device such as a Dimmer Switch or a Color Dimmer Switch.

This endpoint module corresponds to the
"Dimmable Light" Matter device type which defines required and optional clusters
in the Matter spec 1.0.

A Dimmable light endpoint houses an instance of Dimmable Light Matter device
type with the following defined clusters on this endpoint:

The required clusters for this endpoint: Scenes, OnOff, Level and Groups.
The optional clusters for this endpoint: Occupancy.
"""
from typing import Any, Callable

from gazoo_device import decorators
from gazoo_device.capabilities.matter_clusters import level_control_pw_rpc
from gazoo_device.capabilities.matter_clusters import on_off_pw_rpc
from gazoo_device.capabilities.matter_endpoints.interfaces import dimmable_light_base


class DimmableLightEndpoint(dimmable_light_base.DimmableLightBase):
  """Matter Dimmable light endpoint."""

  def __init__(self,
               device_name: str,
               switchboard_call: Callable[..., Any],
               rpc_timeout_s: int):
    """Initializes Matter Dimmable light endpoint instance.

    Args:
      device_name: Device name used for logging.
      switchboard_call: The switchboard.call method.
      rpc_timeout_s: Timeout (s) for RPC call.
    """
    super().__init__(device_name=device_name)
    self._switchboard_call = switchboard_call
    self._rpc_timeout_s = rpc_timeout_s

  @decorators.CapabilityDecorator(on_off_pw_rpc.OnOffClusterPwRpc)
  def on_off(self) -> on_off_pw_rpc.OnOffClusterPwRpc:
    """Matter OnOff cluster instance."""
    return self.cluster_lazy_init(
        on_off_pw_rpc.OnOffClusterPwRpc,
        device_name=self._device_name,
        switchboard_call=self._switchboard_call,
        rpc_timeout_s=self._rpc_timeout_s)

  @decorators.CapabilityDecorator(level_control_pw_rpc.LevelControlClusterPwRpc)
  def level(self) -> level_control_pw_rpc.LevelControlClusterPwRpc:
    """Matter Level Control cluster instance."""
    return self.cluster_lazy_init(
        level_control_pw_rpc.LevelControlClusterPwRpc,
        device_name=self._device_name,
        switchboard_call=self._switchboard_call,
        rpc_timeout_s=self._rpc_timeout_s)

  # TODO(b/209362086) Add the below clusters
  # def scenes(self):
  #   """Matter Scenes cluster instance."""
  #   # TODO(b/206741536): Implement Scenes cluster.
  #   raise NotImplementedError("Scenes cluster isn't implemented.")

  # def groups(self):
  #   """Matter Groups cluster instance."""
  #   # TODO(b/206741536): Implement Groups cluster.
  #   raise NotImplementedError("Groups cluster isn't implemented.")

  # def occupancy(self):
  #   """Matter Occupancy cluster instance."""
  #   # TODO(b/206741536): Implement Occupancy cluster.
  #   raise NotImplementedError("Occupancy cluster isn't implemented.")