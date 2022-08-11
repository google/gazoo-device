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

"""Mixin for Matter Thermostat cluster test suite."""
from gazoo_device.capabilities import matter_enums
from mobly import asserts

_FAKE_DATA1 = 2330
_FAKE_DATA2 = 2750


class ThermostatClusterTestSuite:
  """Mixin for Matter Thermostat cluster test suite.

  The mixin assumes self.endpoint is set.
  """

  def test_local_temperature_attribute(self):
    """Tests the LocalTemperature attribute."""
    asserts.assert_is_instance(
        self.endpoint.thermostat.local_temperature, int,
        "LocalTemperature attribute must be the int type.")

  def test_occupied_cooling_setpoint_attribute(self):
    """Tests the OccupiedCoolingSetpoint attribute."""
    self.endpoint.thermostat.occupied_cooling_setpoint = _FAKE_DATA1
    asserts.assert_equal(
        _FAKE_DATA1,
        self.endpoint.thermostat.occupied_cooling_setpoint)

  # TODO(b/241020267): enable the test once sample app supports writing setpoint
  # def test_occupied_heating_setpoint_attribute(self):
  #   """Tests the OccupiedHeatingSetpoint attribute."""
  #   self.endpoint.thermostat.occupied_heating_setpoint = _FAKE_DATA2
  #   asserts.assert_equal(
  #       _FAKE_DATA2,
  #       self.endpoint.thermostat.occupied_heating_setpoint)

  def test_control_sequence_of_operation_attribute(self):
    """Tests the ControlSequenceOfOperation attribute."""
    self.endpoint.thermostat.control_sequence_of_operation = matter_enums.ThermostatControlSequence.HEATING_ONLY
    asserts.assert_equal(
        matter_enums.ThermostatControlSequence.HEATING_ONLY,
        self.endpoint.thermostat.control_sequence_of_operation)

  def test_system_mode_attribute(self):
    """Tests the SystemMode attribute."""
    self.endpoint.thermostat.system_mode = matter_enums.ThermostatSystemMode.HEAT
    asserts.assert_equal(
        matter_enums.ThermostatSystemMode.HEAT,
        self.endpoint.thermostat.system_mode)

  def test_setpoint_raise_lower_command(self):
    """Tests raising the temperature setpoint via SetpointRaiseLower command."""
    self.endpoint.thermostat.occupied_cooling_setpoint = 2300
    self.endpoint.thermostat.setpoint_raise_lower(
        matter_enums.ThermostatSetpointMode.COOL, 10)
    asserts.assert_equal(
        self.endpoint.thermostat.occupied_cooling_setpoint, 2400)
