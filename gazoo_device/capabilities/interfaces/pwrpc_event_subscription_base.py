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

"""Interface for a Pigweed RPC Event Subscription capability."""

import abc

from gazoo_device.capabilities.interfaces import capability_base


class PwRpcEventSubscriptionBase(capability_base.CapabilityBase):
  """PwRpcEventSubscription capability base class."""

  @abc.abstractmethod
  def set_boolean_state(self, state_value: bool) -> None:
    """Sets the boolean state for event subscription.

    Assume only one endpoint on the device so endpoint_id=1 is used.

    Args:
      state_value: Boolean state to set.
    """

  @abc.abstractmethod
  def get_boolean_state(self) -> bool:
    """Gets the boolean state for event subscription.

    Assume only one endpoint on the device so endpoint_id=1 is used.

    Returns:
      The boolean state.
    """
