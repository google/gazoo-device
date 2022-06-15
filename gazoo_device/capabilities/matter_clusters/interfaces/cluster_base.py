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

"""Interface for the Matter cluster capability."""
import inspect
from typing import Any, Callable, Optional
from gazoo_device.capabilities.interfaces import capability_base


class ClusterBase(capability_base.CapabilityBase):
  """Matter cluster capability interface."""

  # Cluster ID defined in the Matter spec.
  CLUSTER_ID = None

  def __init__(self,
               device_name: str,
               endpoint_id: int,
               read: Callable[..., Any],
               write: Callable[..., Any],
               send: Optional[Callable[..., Any]] = None):
    """Initializes an instance of the Matter cluster capability.

    Args:
      device_name: Device name used for logging.
      endpoint_id: Endpoint ID of endpoint which hosts this cluster.
      read: The Ember API or MatterController read method.
      write: The Ember API or MatterController write method.
      send: The MatterController command send method.
    """
    super().__init__(device_name=device_name)
    self._endpoint_id = endpoint_id
    self._read = read
    self._write = write
    self._send = send

  def __setattr__(self, name: str, value: Any) -> None:
    """Overrides the __setattr__ to check if setting to the valid attribute."""
    def is_setter_property(member):
      return isinstance(member, property) and member.fset is not None

    valid_attributes = {
        name for name, _ in inspect.getmembers(
            self.__class__, is_setter_property)}

    # Skip the private attribute: _device_name, _healthy, _endpoint_id etc.
    if name not in valid_attributes and not name.startswith("_"):
      raise AttributeError(
          f"Invalid attribute '{name}' to set. Valid attributes are "
          f"{valid_attributes}.")

    super().__setattr__(name, value)
