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

"""Interface for the Matter Switch State cluster capability."""

import abc

from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters.interfaces import cluster_base


class SwitchClusterBase(cluster_base.ClusterBase, metaclass=abc.ABCMeta):
  """Matter Switch State cluster capability."""

  # Spec:
  # https://project-chip.github.io/connectedhomeip-spec/appclusters.html#ref_SwitchCluster
  CLUSTER_ID = matter_enums.SwitchCluster.ID

  @property
  @abc.abstractmethod
  def current_position(self) -> int:
    """The CurrentPosition attribute."""

  @abc.abstractmethod
  def set_current_position(self, position: int, verify: bool = True) -> None:
    """Sets the CurrentPosition attribute."""
