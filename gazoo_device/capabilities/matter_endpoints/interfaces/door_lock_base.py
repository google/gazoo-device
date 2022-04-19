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

"""Interface for a Matter Door Lock endpoint."""
import abc
from gazoo_device.capabilities.matter_endpoints.interfaces import endpoint_base


class DoorLockBase(endpoint_base.EndpointBase, metaclass=abc.ABCMeta):
  """Matter Door Lock endpoint interface."""

  DEVICE_TYPE_ID = 0x000A

  @property
  @abc.abstractmethod
  def door_lock(self):
    """Required cluster: Door Lock cluster."""

  # TODO(b/209362086) Add the below optional clusters
  # @abc.abstractproperty
  # def scenes(self):
  #   """Optional cluster: ZCL Scenes cluster."""

  # @abc.abstractproperty
  # def groups(self):
  #   """Optional cluster: ZCL Groups cluster."""

  # @abc.abstractproperty
  # def alarms(self):
  #   """Optional cluster: ZCL Alarms cluster."""

  # @abc.abstractproperty
  # def time(self):
  #   """Optional cluster: ZCL Time cluster."""

  # @abc.abstractproperty
  # def time_sync(self):
  #   """Optional cluster: ZCL TimeSync cluster."""

  # @abc.abstractproperty
  # def poll_control(self):
  #   """Optional cluster: ZCL Poll Control cluster."""
