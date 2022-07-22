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

"""Interface for the Matter Level Control cluster capability."""
import abc
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters.interfaces import cluster_base


class LevelControlClusterBase(cluster_base.ClusterBase, metaclass=abc.ABCMeta):
  """Matter Level Control cluster capability."""

  CLUSTER_ID = matter_enums.LevelControlCluster.ID

  @abc.abstractmethod
  def move_to_level(self, level: int, verify: bool = True) -> None:
    """The MoveToLevel command.

    Args:
      level: The level that the device should move to.
      verify: If true, verifies the level changes before returning.
    """

  @property
  @abc.abstractmethod
  def current_level(self) -> int:
    """The CurrentLevel attribute.

    Returns:
      The current level.
    """

  @property
  @abc.abstractmethod
  def min_level(self) -> int:
    """The MinLevel attribute.

    The MinLevel attribute indicates the minimum value of CurrentLevel that is
    capable of being assigned.

    Returns:
      The min level.
    """

  @property
  @abc.abstractmethod
  def max_level(self) -> int:
    """The MaxLevel attribute.

    The MaxLevel attribute indicates the maximum value of CurrentLevel that is
    capable of being assigned.

    Returns:
      The max level.
    """

  # TODO(b/212193200)
  # Add additional attributes / commands for level control cluster
