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

"""Interface for the Matter Color Control cluster capability."""

import abc
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters.interfaces import cluster_base


class ColorControlClusterBase(cluster_base.ClusterBase, metaclass=abc.ABCMeta):
  """Matter Color Control cluster capability."""

  CLUSTER_ID = matter_enums.ColorControlCluster.ID

  @abc.abstractmethod
  def move_to_hue(self, hue: int, verify: bool = True) -> None:
    """The MoveToHue command.

    Args:
      hue: The hue that the device should move to.
      verify: If true, verifies the hue changes before returning.
    """

  @abc.abstractmethod
  def move_to_saturation(self, saturation: int, verify: bool = True) -> None:
    """The MoveToSaturation command.

    Args:
      saturation: The saturation that the device should move to.
      verify: If true, verifies the saturation changes before returning.
    """

  @property
  @abc.abstractmethod
  def current_hue(self) -> int:
    """The CurrentHue attribute.

    Returns:
      The current hue.
    """

  @property
  @abc.abstractmethod
  def current_saturation(self) -> int:
    """The CurrentSaturation attribute.

    Returns:
      The current saturation.
    """

  # TODO(b/212193200)
  # Add additional attributes / commands for color control cluster
