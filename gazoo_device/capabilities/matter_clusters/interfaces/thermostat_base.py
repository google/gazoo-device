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

"""Interface for the Matter Thermostat cluster capability."""
import abc
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters.interfaces import cluster_base


class ThermostatClusterBase(cluster_base.ClusterBase, metaclass=abc.ABCMeta):
  """Matter Thermostat cluster capability."""

  CLUSTER_ID = matter_enums.ThermostatCluster.ID

  @property
  @abc.abstractmethod
  def local_temperature(self) -> int:
    """The LocalTemperature attribute.

    Returns:
      The temperature, as measured locally or remotely (over the network),
      on the Celsius scale with a resolution of 0.01°C.
    """

  @property
  @abc.abstractmethod
  def occupied_cooling_setpoint(self) -> int:
    """The OccupiedCoolingSetpoint attribute.

    Returns:
      The cooling mode setpoint when the room is occupied, on the Celsius scale
      with a resolution of 0.01°C.
    """

  @property
  @abc.abstractmethod
  def occupied_heating_setpoint(self) -> int:
    """The OccupiedHeatingSetpoint attribute.

    Returns:
      The heating mode setpoint when the room is occupied, on the Celsius scale
      with a resolution of 0.01°C.
    """

  @property
  @abc.abstractmethod
  def control_sequence_of_operation(
      self) -> matter_enums.ThermostatControlSequence:
    """The ControlSequenceOfOperation attribute.

    Returns:
      The overall operating environment of the thermostat, and the possible
      system modes that the thermostat can operate in.
    """

  @property
  @abc.abstractmethod
  def system_mode(self) -> matter_enums.ThermostatSystemMode:
    """The SystemMode attribute.

    Returns:
      The current operating mode of the thermostat.
    """

  @abc.abstractmethod
  def setpoint_raise_lower(self, mode: matter_enums.ThermostatSetpointMode,
                           amount: int) -> None:
    """The SetpointRaiseLower command to add specified amount to setpoint.

    Args:
      mode: The mode for which the sepoints are to be adjusted.
      amount: The amount (possibly negative) that should be added to the
        setpoint(s), in steps of 0.1°C
    """
