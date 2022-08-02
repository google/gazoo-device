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
"""Interface for Matter sample app controls capability.

See more details in the CHIP Linux Lighting Example document:
https://github.com/project-chip/connectedhomeip/tree/master/examples/lighting-app/linux
"""
import abc
from typing import List

from gazoo_device.capabilities.interfaces import capability_base


class MatterSampleAppBase(capability_base.CapabilityBase):
  """Abstract base class for Matter controller capability."""

  @abc.abstractmethod
  def is_present(self) -> bool:
    """Returns if the app binary is present."""

  @abc.abstractmethod
  def is_running(self) -> bool:
    """Returns if the app process is running."""

  @abc.abstractmethod
  def get_process_ids(self) -> List[str]:
    """Gets all currently active app process IDs."""

  @abc.abstractmethod
  def restart(self) -> None:
    """Restarts the app process.

    Raises:
      DeviceError if the app didn't restart successfully.
    """

  @abc.abstractmethod
  def upgrade(self, app_file: str) -> None:
    """Upgrades to a new app file.

    Args:
      app_file: Local path to app file.
    """
