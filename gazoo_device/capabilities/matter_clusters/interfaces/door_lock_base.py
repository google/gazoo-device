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

"""Interface for the Matter Door Lock cluster capability."""
import abc
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters.interfaces import cluster_base


class DoorLockClusterBase(cluster_base.ClusterBase, metaclass=abc.ABCMeta):
  """Matter Door Lock cluster capability."""

  CLUSTER_ID = matter_enums.DoorLockCluster.ID

  @abc.abstractmethod
  def lock_door(self, verify: bool = True) -> None:
    """The Lock Door command to lock the Matter device.

    Args:
      verify: If true, verifies the state configurations before returning.
    """

  @abc.abstractmethod
  def unlock_door(self, verify: bool = True) -> None:
    """The Unlock Door command to unlock the Matter device.

    Args:
      verify: If true, verifies the state configurations before returning.
    """

  @property
  @abc.abstractmethod
  def lock_state(self) -> int:
    """The LockState attribute.

    Returns:
      The enum value of the current locked state:
      0: Not fully locked.
      1: Locked.
      2: Unlocked.
    """
