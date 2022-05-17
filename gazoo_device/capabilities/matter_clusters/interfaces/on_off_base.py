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

"""Interface for the Matter On/Off cluster capability."""
import abc
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters.interfaces import cluster_base


class OnOffClusterBase(cluster_base.ClusterBase, metaclass=abc.ABCMeta):
  """Matter On/Off cluster capability."""

  CLUSTER_ID = matter_enums.OnOffCluster.ID

  @abc.abstractmethod
  def on(self, verify: bool = True) -> None:
    """The On command to turn on the Matter device.

    Args:
      verify: If true, verifies the state change before returning.
    """

  @abc.abstractmethod
  def off(self, verify: bool = True) -> None:
    """The Off command to turn off the Matter device.

    Args:
      verify: If true, verifies the state change before returning.
    """

  @abc.abstractmethod
  def toggle(self, verify: bool = True) -> None:
    """The Toggle command to toggle the OnOff state of the Matter device.

    Args:
      verify: If true, verifies the state change before returning.
    """

  @property
  @abc.abstractmethod
  def onoff(self) -> bool:
    """The OnOff attribute.

    Returns:
      True if the device is in on state, false if it's in off state.
    """
