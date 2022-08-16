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
"""Matter cluster capability unit test for thermostat_chip_tool module."""

import functools
from unittest import mock

from absl.testing import parameterized
from gazoo_device.capabilities import matter_controller_chip_tool
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters import thermostat_chip_tool
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_MATTER_NODE_ID = 1234
_ENDPOINT_ID = 1

_WRITE_ATTRIBUTE_TESTS = (
    ("occupied_heating_setpoint", "occupied-heating-setpoint", 2700, 2700),
    ("occupied_cooling_setpoint", "occupied-cooling-setpoint", 2500, 2500),
    ("control_sequence_of_operation", "control-sequence-of-operation",
     matter_enums.ThermostatControlSequence.COOLING_ONLY.value,
     matter_enums.ThermostatControlSequence.COOLING_ONLY),
    ("system_mode", "system-mode", matter_enums.ThermostatSystemMode.HEAT.value,
     matter_enums.ThermostatSystemMode.HEAT),
)
_READ_ATTRIBUTE_TESTS = _WRITE_ATTRIBUTE_TESTS + (
    ("local_temperature", "local-temperature", 2300, 2300),)


class ThermostatClusterChipToolTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for ThermostatClusterChipTool."""

  def setUp(self):
    super().setUp()
    self._node_id = _MATTER_NODE_ID
    self._endpoint_id = _ENDPOINT_ID

    self.fake_read = mock.Mock(
        spec=functools.partial(
            matter_controller_chip_tool.MatterControllerChipTool.read,
            self._node_id))
    self.fake_write = mock.Mock(
        spec=functools.partial(
            matter_controller_chip_tool.MatterControllerChipTool.write,
            self._node_id))
    self.fake_send = mock.Mock(
        spec=functools.partial(
            matter_controller_chip_tool.MatterControllerChipTool.send,
            self._node_id))
    self.uut = thermostat_chip_tool.ThermostatClusterChipTool(
        device_name="rpi_matter_controller-1234",
        endpoint_id=self._endpoint_id,
        read=self.fake_read,
        write=self.fake_write,
        send=self.fake_send)

  @parameterized.named_parameters(*_READ_ATTRIBUTE_TESTS)
  def test_read_attribute(self, attribute_name, raw_value, value):
    self.fake_read.return_value = raw_value
    self.assertEqual(getattr(self.uut, attribute_name.replace("-", "_")), value)
    self.fake_read.assert_called_once_with(self._endpoint_id, "thermostat",
                                           attribute_name)

  @parameterized.named_parameters(*_WRITE_ATTRIBUTE_TESTS)
  def test_write_attribute(self, attribute_name, raw_value, value):
    setattr(self.uut, attribute_name.replace("-", "_"), value)
    self.fake_write.assert_called_once_with(self._endpoint_id, "thermostat",
                                            attribute_name, raw_value)

  def test_setpoint_raise_lower_command(self):
    self.uut.setpoint_raise_lower(matter_enums.ThermostatSystemMode.HEAT, 10)
    self.fake_send.assert_called_once_with(
        self._endpoint_id, "thermostat", "setpoint-raise-lower",
        [matter_enums.ThermostatSystemMode.HEAT.value, 10])


if __name__ == "__main__":
  fake_device_test_case.main()
