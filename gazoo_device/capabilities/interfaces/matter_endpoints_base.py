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

"""Interface for Matter endpoint capability wrapper."""
import abc
from typing import Mapping, Type
from gazoo_device.capabilities.interfaces import capability_base
from gazoo_device.capabilities.matter_endpoints.interfaces import endpoint_base

ROOT_NODE_ENDPOINT_ID = 0


class MatterEndpointsBase(capability_base.CapabilityBase):
  """Capability wrapper for accessing the Matter endpoint instances."""

  @abc.abstractmethod
  def get(self, endpoint_id: int) -> endpoint_base.EndpointBase:
    """Gets the specific endpoint instance by endpoint ID."""

  @abc.abstractmethod
  def list(self) -> Mapping[int, Type[endpoint_base.EndpointBase]]:
    """Lists all supported endpoints."""
