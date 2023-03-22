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

"""Interface for the Matter Fan Control cluster capability."""
import abc
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters.interfaces import cluster_base


class FanControlClusterBase(cluster_base.ClusterBase, metaclass=abc.ABCMeta):
  """Matter Fan Control cluster capability."""

  CLUSTER_ID = matter_enums.FanControlCluster.ID

  @property
  @abc.abstractmethod
  def fan_mode(self) -> int:
    """The FanMode attribute."""

  @property
  @abc.abstractmethod
  def fan_mode_sequence(self) -> int:
    """The FanModeSequence attribute."""

  @property
  @abc.abstractmethod
  def percent_setting(self) -> int:
    """The PercentSetting attribute."""

  @property
  @abc.abstractmethod
  def percent_current(self) -> int:
    """The PercentCurrent attribute."""

  @property
  @abc.abstractmethod
  def speed_max(self) -> int:
    """The SpeedMax attribute."""

  @property
  @abc.abstractmethod
  def speed_setting(self) -> int:
    """The SpeedSetting attribute."""

  @property
  @abc.abstractmethod
  def speed_current(self) -> int:
    """The SpeedCurrent attribute."""
