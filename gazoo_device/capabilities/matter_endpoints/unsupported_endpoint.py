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

"""Matter unsupported endpoint placeholder class."""
from gazoo_device import decorators
from gazoo_device import gdm_logger
from gazoo_device.capabilities.matter_endpoints.interfaces import unsupported_endpoint_base

logger = gdm_logger.get_logger()


class UnsupportedEndpoint(unsupported_endpoint_base.UnsupportedBase):
  """Matter unsupported endpoint placeholder class."""

  @decorators.DynamicProperty
  def name(self) -> str:
    """The name of the endpoint on the device."""
    return f"Unsupported endpoint (device type: {self.device_type_id})"

  @decorators.DynamicProperty
  def device_type_id(self) -> int:
    """The name of the endpoint on the device."""
    return self._device_type_id
