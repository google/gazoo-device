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

"""Matter endpoint capability wrapper."""
from typing import Any, Mapping, Type

from gazoo_device import decorators
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import matter_endpoints_base
from gazoo_device.capabilities.matter_endpoints.interfaces import endpoint_base

import immutabledict

logger = gdm_logger.get_logger()


class MatterEndpointsAccessor(matter_endpoints_base.MatterEndpointsBase):
  """Capability wrapper for accessing the Matter endpoint instances."""

  def __init__(
      self,
      endpoint_id_to_class: Mapping[int, Type[endpoint_base.EndpointBase]],
      device_name: str,
      **endpoint_kwargs: Any):
    super().__init__(device_name=device_name)
    self._endpoint_id_to_class = immutabledict.immutabledict(
        endpoint_id_to_class)
    self._endpoint_kwargs = endpoint_kwargs
    self._endpoints = {}

  @decorators.CapabilityLogDecorator(logger)
  def get(self, endpoint_id: int) -> endpoint_base.EndpointBase:
    """Gets the specific endpoint instance by ID."""
    if endpoint_id not in self._endpoints:
      endpoint_cls = self._endpoint_id_to_class[endpoint_id]
      self._endpoints[endpoint_id] = endpoint_cls(
          device_name=self._device_name, **self._endpoint_kwargs)
    return self._endpoints[endpoint_id]

  @decorators.CapabilityLogDecorator(logger)
  def list(self) -> Mapping[int, Type[endpoint_base.EndpointBase]]:
    """Lists all supported endpoint classes."""
    return self._endpoint_id_to_class
