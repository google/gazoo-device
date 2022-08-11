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
"""Matter cluster unit test for thermostat_pw_rpc module."""
from unittest import mock

from absl.testing import parameterized
from gazoo_device.capabilities import matter_endpoints_accessor_pw_rpc
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters import thermostat_pw_rpc
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

ThermostatCluster = matter_enums.ThermostatCluster

_FAKE_DEVICE_NAME = "fake-device-name"
_FAKE_ENDPOINT_ID = 1
_FAKE_TEMPERATURE = 2330


class ThermostatClusterPwRpcTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for ThermostatClusterPwRpc."""

  def setUp(self):
    super().setUp()
    self.fake_read = mock.Mock(
        spec=matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc.read)
    self.fake_write = mock.Mock(spec=matter_endpoints_accessor_pw_rpc
                                .MatterEndpointsAccessorPwRpc.write)
    self.uut = thermostat_pw_rpc.ThermostatClusterPwRpc(
        device_name=_FAKE_DEVICE_NAME,
        endpoint_id=_FAKE_ENDPOINT_ID,
        read=self.fake_read,
        write=self.fake_write)

  def test_cluster_instance_is_not_none(self):
    """Verifies the cluster instance is not none."""
    self.assertIsNotNone(self.uut)

  def test_read_local_temperature_attribute(self):
    """Tests reading the LocalTemperature attribute."""
    self.fake_read.return_value = mock.Mock(data_int16=_FAKE_TEMPERATURE)
    self.assertEqual(self.uut.local_temperature, _FAKE_TEMPERATURE)

  def test_read_occupied_heating_setpoint_attribute(self):
    """Tests reading the OccupiedHeatingSetpoint attribute."""
    self.fake_read.return_value = mock.Mock(data_int16=_FAKE_TEMPERATURE)
    self.assertEqual(self.uut.occupied_heating_setpoint, _FAKE_TEMPERATURE)

  def test_write_occupied_heating_setpoint_attribute(self):
    """Tests writing the OccupiedHeatingSetpoint attribute."""
    self.uut.occupied_heating_setpoint = _FAKE_TEMPERATURE
    self.fake_write.assert_called_once()

  def test_read_occupied_cooling_setpoint_attribute(self):
    """Tests reading the OccupiedCoolingSetpoint attribute."""
    self.fake_read.return_value = mock.Mock(data_int16=_FAKE_TEMPERATURE)
    self.assertEqual(self.uut.occupied_cooling_setpoint, _FAKE_TEMPERATURE)

  def test_write_occupied_cooling_setpoint_attribute(self):
    """Tests writing the OccupiedCoolingSetpoint attribute."""
    self.uut.occupied_cooling_setpoint = _FAKE_TEMPERATURE
    self.fake_write.assert_called_once()

  def test_read_control_sequence_of_operation_attribute(self):
    """Tests reading the ControlSequenceOfOperation attribute."""
    self.fake_read.return_value = mock.Mock(
        data_uint8=matter_enums.ThermostatControlSequence.HEATING_ONLY.value)
    self.assertEqual(self.uut.control_sequence_of_operation,
                     matter_enums.ThermostatControlSequence.HEATING_ONLY)

  def test_write_control_sequence_of_operation_attribute(self):
    """Tests writing the ControlSequenceOfOperation attribute."""
    self.uut.control_sequence_of_operation = matter_enums.ThermostatControlSequence.HEATING_ONLY
    self.fake_write.assert_called_once()

  def test_read_system_mode_attribute(self):
    """Tests reading the SystemMode attribute."""
    self.fake_read.return_value = mock.Mock(
        data_uint8=matter_enums.ThermostatSystemMode.HEAT.value)
    self.assertEqual(self.uut.system_mode,
                     matter_enums.ThermostatSystemMode.HEAT)

  def test_write_system_mode_attribute(self):
    """Tests writing the SystemMode attribute."""
    self.uut.system_mode = matter_enums.ThermostatSystemMode.HEAT
    self.fake_write.assert_called_once()

  @parameterized.named_parameters(
      ("raise_heat", matter_enums.ThermostatSetpointMode.HEAT, 10, 2400, None),
      ("lower_heat", matter_enums.ThermostatSetpointMode.HEAT, -10, 2200, None),
      ("raise_cool", matter_enums.ThermostatSetpointMode.COOL, 10, None, 2800),
      ("lower_cool", matter_enums.ThermostatSetpointMode.COOL, -10, None, 2600),
      ("raise_both", matter_enums.ThermostatSetpointMode.BOTH, 10, 2400, 2800),
      ("lower_both", matter_enums.ThermostatSetpointMode.BOTH, -10, 2200, 2600),
  )
  def test_command_setpoint(self, mode, amount, expected_heating_setpoint,
                            expected_cooling_setpoint):
    """Tests issuing the SetpointRaiseLower command."""
    def _fake_read_setpoint(*_, **kwargs):
      return (mock.Mock(data_int16=2300) if kwargs["attribute_id"]
              == ThermostatCluster.ATTRIBUTE_OCCUPIED_HEATING_SETPOINT else
              mock.Mock(data_int16=2700))
    self.fake_read.side_effect = _fake_read_setpoint

    self.uut.setpoint_raise_lower(mode, amount)
    call_args = self.fake_write.call_args_list
    new_setpoints = {
        call_args[i][1]["attribute_id"]: call_args[i][1]["data_int16"]
        for i in range(len(call_args))
    }

    if expected_heating_setpoint is not None:
      self.assertEqual(
          new_setpoints[ThermostatCluster.ATTRIBUTE_OCCUPIED_HEATING_SETPOINT],
          expected_heating_setpoint)
    if expected_cooling_setpoint is not None:
      self.assertEqual(
          new_setpoints[ThermostatCluster.ATTRIBUTE_OCCUPIED_COOLING_SETPOINT],
          expected_cooling_setpoint)


if __name__ == "__main__":
  fake_device_test_case.main()
