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
"""chip-tool implementation of the Matter Thermostat cluster capability.
"""
from gazoo_device import decorators
from gazoo_device import gdm_logger
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters.interfaces import thermostat_base

logger = gdm_logger.get_logger()

_CLUSTER_NAME = "thermostat"


class ThermostatClusterChipTool(thermostat_base.ThermostatClusterBase):
  """Matter Thermostat cluster capability."""

  @decorators.DynamicProperty
  def local_temperature(self) -> int:
    """The LocalTemperature attribute.

    Returns:
      The temperature, as measured locally or remotely (over the network),
      on the Celsius scale with a resolution of 0.01°C.
    """
    return self._read(self._endpoint_id, _CLUSTER_NAME, "local-temperature")

  @decorators.DynamicProperty
  def occupied_cooling_setpoint(self) -> int:
    """The OccupiedCoolingSetpoint attribute.

    Returns:
      The cooling mode setpoint when the room is occupied, on the Celsius scale
      with a resolution of 0.01°C.
    """
    return self._read(self._endpoint_id, _CLUSTER_NAME,
                      "occupied-cooling-setpoint")

  @occupied_cooling_setpoint.setter
  def occupied_cooling_setpoint(self, value: int) -> None:
    """Updates the OccupiedCoolingSetpoint attribute with new value."""
    self._write(self._endpoint_id, _CLUSTER_NAME, "occupied-cooling-setpoint",
                value)

  @decorators.DynamicProperty
  def occupied_heating_setpoint(self) -> int:
    """The OccupiedHeatingSetpoint attribute.

    Returns:
      The heating mode setpoint when the room is occupied, on the Celsius scale
      with a resolution of 0.01°C.
    """
    return self._read(self._endpoint_id, _CLUSTER_NAME,
                      "occupied-heating-setpoint")

  @occupied_heating_setpoint.setter
  def occupied_heating_setpoint(self, value: int) -> None:
    """Updates the OccupiedHeatingSetpoint attribute with new value."""
    self._write(self._endpoint_id, _CLUSTER_NAME, "occupied-heating-setpoint",
                value)

  @decorators.DynamicProperty
  def control_sequence_of_operation(
      self) -> matter_enums.ThermostatControlSequence:
    """The ControlSequenceOfOperation attribute.

    Returns:
      The overall operating environment of the thermostat, and the possible
      system modes that the thermostat can operate in.
    """
    operation_data = self._read(self._endpoint_id, _CLUSTER_NAME,
                                "control-sequence-of-operation")
    return matter_enums.ThermostatControlSequence(operation_data)

  @control_sequence_of_operation.setter
  def control_sequence_of_operation(
      self, value: matter_enums.ThermostatControlSequence) -> None:
    """Updates the ControlSequenceOfOperation attribute with new value."""
    self._write(self._endpoint_id, _CLUSTER_NAME,
                "control-sequence-of-operation", value.value)

  @decorators.DynamicProperty
  def system_mode(self) -> matter_enums.ThermostatSystemMode:
    """The SystemMode attribute.

    Returns:
      The current operating mode of the thermostat.
    """
    mode_data = self._read(self._endpoint_id, _CLUSTER_NAME, "system-mode")
    return matter_enums.ThermostatSystemMode(mode_data)

  @system_mode.setter
  def system_mode(self, value: matter_enums.ThermostatSystemMode) -> None:
    """Updates the SystemMode attribute with new value."""
    self._write(self._endpoint_id, _CLUSTER_NAME, "system-mode", value.value)

  @decorators.CapabilityLogDecorator(logger)
  def setpoint_raise_lower(self, mode: matter_enums.ThermostatSetpointMode,
                           amount: int) -> None:
    """The SetpointRaiseLower command to add specified amount to setpoint.

    Args:
      mode: The mode for which the sepoints are to be adjusted.
      amount: The amount (possibly negative) that should be added to the
        setpoint(s), in steps of 0.1°C
    """
    self._send(self._endpoint_id, _CLUSTER_NAME, "setpoint-raise-lower",
               [mode.value, amount])
