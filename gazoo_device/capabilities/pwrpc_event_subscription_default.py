# Copyright 2024 Google LLC
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

"""Pigweed RPC Event Subscription capability."""

from typing import Any, Callable

from gazoo_device import decorators
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import pwrpc_event_subscription_base
from gazoo_device.protos import boolean_state_service_pb2
from gazoo_device.utility import pwrpc_utils


logger = gdm_logger.get_logger()


class PwRpcEventSubscriptionDefault(
    pwrpc_event_subscription_base.PwRpcEventSubscriptionBase):
  """Pigweed RPC Event Subscription capability."""

  def __init__(self,
               device_name: str,
               switchboard_call: Callable[..., Any],
               rpc_timeout_s: int):
    """Creates an instance of the PwRpcEventSubscriptionDefault capability.

    Args:
      device_name: Device name used for logging.
      switchboard_call: The switchboard.call method.
      rpc_timeout_s: Timeout (s) for RPC call.
    """
    super().__init__(device_name=device_name)
    self._switchboard_call = switchboard_call
    self._rpc_timeout_s = rpc_timeout_s

  @decorators.CapabilityLogDecorator(logger)
  def set_boolean_state(self, state_value: bool) -> None:
    """Sets the boolean state for event subscription.

    Assume only one endpoint on the device so endpoint_id=1 is used.

    Args:
      state_value: Boolean state to set.
    """
    self._switchboard_call(
        method_name=pwrpc_utils.RPC_METHOD_NAME,
        method_args=("BooleanState", "Set"),
        method_kwargs={"endpoint_id": 1,
                       "state_value": state_value,
                       "pw_rpc_timeout_s": self._rpc_timeout_s})

  @decorators.CapabilityLogDecorator(logger)
  def get_boolean_state(self) -> bool:
    """Gets the boolean state for event subscription.

    Assume only one endpoint on the device so endpoint_id=1 is used.

    Returns:
      The boolean state.
    """
    payload = self._switchboard_call(
        method_name=pwrpc_utils.RPC_METHOD_NAME,
        method_args=("BooleanState", "Get"),
        method_kwargs={"endpoint_id": 1,
                       "pw_rpc_timeout_s": self._rpc_timeout_s})
    response = boolean_state_service_pb2.BooleanStateGetResponse.FromString(
        payload)
    return response.state.state_value
