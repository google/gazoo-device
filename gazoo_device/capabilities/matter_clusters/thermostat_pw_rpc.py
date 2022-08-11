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

"""Pigweed RPC implementation of the Matter Thermostat cluster capability.
"""
from gazoo_device import decorators
from gazoo_device import gdm_logger
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters.interfaces import thermostat_base
from gazoo_device.protos import attributes_service_pb2

logger = gdm_logger.get_logger()
ThermostatCluster = matter_enums.ThermostatCluster
ENUM8_ATTRIBUTE_TYPE = attributes_service_pb2.AttributeType.ZCL_ENUM8_ATTRIBUTE_TYPE
INT16S_ATTRIBUTE_TYPE = attributes_service_pb2.AttributeType.ZCL_INT16S_ATTRIBUTE_TYPE


class ThermostatClusterPwRpc(thermostat_base.ThermostatClusterBase):
  """Matter Thermostat cluster capability."""

  @decorators.DynamicProperty
  def local_temperature(self) -> int:
    """The LocalTemperature attribute.

    Returns:
      The temperature, as measured locally or remotely (over the network),
      on the Celsius scale with a resolution of 0.01°C.
    """
    temperature_data = self._read(
        endpoint_id=self._endpoint_id,
        cluster_id=ThermostatCluster.ID,
        attribute_id=ThermostatCluster.ATTRIBUTE_LOCAL_TEMPERATURE,
        attribute_type=INT16S_ATTRIBUTE_TYPE)
    return temperature_data.data_int16

  @decorators.DynamicProperty
  def occupied_cooling_setpoint(self) -> int:
    """The OccupiedCoolingSetpoint attribute.

    Returns:
      The cooling mode setpoint when the room is occupied, on the Celsius scale
      with a resolution of 0.01°C.
    """
    setpoint_data = self._read(
        endpoint_id=self._endpoint_id,
        cluster_id=ThermostatCluster.ID,
        attribute_id=ThermostatCluster.ATTRIBUTE_OCCUPIED_COOLING_SETPOINT,
        attribute_type=INT16S_ATTRIBUTE_TYPE)
    return setpoint_data.data_int16

  @occupied_cooling_setpoint.setter
  def occupied_cooling_setpoint(self, value: int) -> None:
    """Updates the OccupiedCoolingSetpoint attribute with new value."""
    self._write(
        endpoint_id=self._endpoint_id,
        cluster_id=ThermostatCluster.ID,
        attribute_id=ThermostatCluster.ATTRIBUTE_OCCUPIED_COOLING_SETPOINT,
        attribute_type=INT16S_ATTRIBUTE_TYPE,
        data_int16=value)

  @decorators.DynamicProperty
  def occupied_heating_setpoint(self) -> int:
    """The OccupiedHeatingSetpoint attribute.

    Returns:
      The heating mode setpoint when the room is occupied, on the Celsius scale
      with a resolution of 0.01°C.
    """
    setpoint_data = self._read(
        endpoint_id=self._endpoint_id,
        cluster_id=ThermostatCluster.ID,
        attribute_id=ThermostatCluster.ATTRIBUTE_OCCUPIED_HEATING_SETPOINT,
        attribute_type=INT16S_ATTRIBUTE_TYPE)
    return setpoint_data.data_int16

  @occupied_heating_setpoint.setter
  def occupied_heating_setpoint(self, value: int) -> None:
    """Updates the OccupiedHeatingSetpoint attribute with new value."""
    self._write(
        endpoint_id=self._endpoint_id,
        cluster_id=ThermostatCluster.ID,
        attribute_id=ThermostatCluster.ATTRIBUTE_OCCUPIED_HEATING_SETPOINT,
        attribute_type=INT16S_ATTRIBUTE_TYPE,
        data_int16=value)

  @decorators.DynamicProperty
  def control_sequence_of_operation(
      self) -> matter_enums.ThermostatControlSequence:
    """The ControlSequenceOfOperation attribute.

    Returns:
      The overall operating environment of the thermostat, and the possible
      system modes that the thermostat can operate in.
    """
    operation_data = self._read(
        endpoint_id=self._endpoint_id,
        cluster_id=ThermostatCluster.ID,
        attribute_id=ThermostatCluster.ATTRIBUTE_CONTROL_SEQUENCE_OF_OPERATION,
        attribute_type=ENUM8_ATTRIBUTE_TYPE)
    return matter_enums.ThermostatControlSequence(operation_data.data_uint8)

  @control_sequence_of_operation.setter
  def control_sequence_of_operation(
      self, value: matter_enums.ThermostatControlSequence) -> None:
    """Updates the ControlSequenceOfOperation attribute with new value."""
    self._write(
        endpoint_id=self._endpoint_id,
        cluster_id=ThermostatCluster.ID,
        attribute_id=ThermostatCluster.ATTRIBUTE_CONTROL_SEQUENCE_OF_OPERATION,
        attribute_type=ENUM8_ATTRIBUTE_TYPE,
        data_uint8=value.value)

  @decorators.DynamicProperty
  def system_mode(self) -> matter_enums.ThermostatSystemMode:
    """The SystemMode attribute.

    Returns:
      The current operating mode of the thermostat.
    """
    mode_data = self._read(
        endpoint_id=self._endpoint_id,
        cluster_id=ThermostatCluster.ID,
        attribute_id=ThermostatCluster.ATTRIBUTE_SYSTEM_MODE,
        attribute_type=ENUM8_ATTRIBUTE_TYPE)
    return matter_enums.ThermostatSystemMode(mode_data.data_uint8)

  @system_mode.setter
  def system_mode(self, value: matter_enums.ThermostatSystemMode) -> None:
    """Updates the SystemMode attribute with new value."""
    self._write(
        endpoint_id=self._endpoint_id,
        cluster_id=ThermostatCluster.ID,
        attribute_id=ThermostatCluster.ATTRIBUTE_SYSTEM_MODE,
        attribute_type=ENUM8_ATTRIBUTE_TYPE,
        data_uint8=value.value)

  @decorators.CapabilityLogDecorator(logger)
  def setpoint_raise_lower(self, mode: matter_enums.ThermostatSetpointMode,
                           amount: int) -> None:
    """The SetpointRaiseLower command to add specified amount to setpoint.

    As Ember API does not support cluster commands yet, this method reads the
    current occupied setpoint and updates them accordingly with setters.

    Args:
      mode: The mode for which the sepoints are to be adjusted.
      amount: The amount (possibly negative) that should be added to the
        setpoint(s), in steps of 0.1°C
    """
    delta = amount * 10
    if mode == matter_enums.ThermostatSetpointMode.HEAT:
      self.occupied_heating_setpoint = self.occupied_heating_setpoint + delta
    elif mode == matter_enums.ThermostatSetpointMode.COOL:
      self.occupied_cooling_setpoint = self.occupied_cooling_setpoint + delta
    else:
      self.occupied_heating_setpoint = self.occupied_heating_setpoint + delta
      self.occupied_cooling_setpoint = self.occupied_cooling_setpoint + delta
