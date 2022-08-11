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

"""Unit tests for MatterEndpointsAliasesMixin."""
from unittest import mock

from gazoo_device.base_classes import matter_endpoints_mixin
from gazoo_device.capabilities.interfaces import matter_endpoints_base
from gazoo_device.capabilities.matter_endpoints import color_temperature_light
from gazoo_device.capabilities.matter_endpoints import contact_sensor
from gazoo_device.capabilities.matter_endpoints import dimmable_light
from gazoo_device.capabilities.matter_endpoints import door_lock
from gazoo_device.capabilities.matter_endpoints import extended_color_light
from gazoo_device.capabilities.matter_endpoints import flow_sensor
from gazoo_device.capabilities.matter_endpoints import humidity_sensor
from gazoo_device.capabilities.matter_endpoints import light_sensor
from gazoo_device.capabilities.matter_endpoints import occupancy_sensor
from gazoo_device.capabilities.matter_endpoints import on_off_light
from gazoo_device.capabilities.matter_endpoints import on_off_light_switch
from gazoo_device.capabilities.matter_endpoints import pressure_sensor
from gazoo_device.capabilities.matter_endpoints import root_node
from gazoo_device.capabilities.matter_endpoints import temperature_sensor
from gazoo_device.tests.unit_tests.utils import fake_device_test_case


class MatterDeviceStub(matter_endpoints_mixin.MatterEndpointAliasesMixin):
  """Dummy implementation of a Matter controller."""

  def __init__(self):
    self.fake_endpoint = mock.Mock(
        spec=matter_endpoints_base.MatterEndpointsBase)
    self.fake_get_endpoint_call = (
        self.fake_endpoint.get_endpoint_instance_by_class)

  @property
  def matter_endpoints(self):
    return self.fake_endpoint

  def close(self):
    pass


class MatterEndpointsAliasesMixinTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit tests for MatterEndpointAliasesMixin."""

  def setUp(self):
    super().setUp()
    self.uut = MatterDeviceStub()

  def test_color_temperature_light_alias(self):
    """Verifies color_temperature_light endpoint alias on success."""
    self.assertIsNotNone(self.uut.color_temperature_light)
    self.uut.fake_get_endpoint_call.assert_called_once_with(
        color_temperature_light.ColorTemperatureLightEndpoint)

  def test_contact_sensor_alias(self):
    """Verifies contact_sensor endpoint alias on success."""
    self.assertIsNotNone(self.uut.contact_sensor)
    self.uut.fake_get_endpoint_call.assert_called_once_with(
        contact_sensor.ContactSensorEndpoint)

  def test_dimmable_light_alias(self):
    """Verifies dimmable_light endpoint alias on success."""
    self.assertIsNotNone(self.uut.dimmable_light)
    self.uut.fake_get_endpoint_call.assert_called_once_with(
        dimmable_light.DimmableLightEndpoint)

  def test_door_lock_alias(self):
    """Verifies door_lock endpoint alias on success."""
    self.assertIsNotNone(self.uut.door_lock)
    self.uut.fake_get_endpoint_call.assert_called_once_with(
        door_lock.DoorLockEndpoint)

  def test_extended_color_light_alias(self):
    """Verifies extended_color_light endpoint alias on success."""
    self.assertIsNotNone(self.uut.extended_color_light)
    self.uut.fake_get_endpoint_call.assert_called_once_with(
        extended_color_light.ExtendedColorLightEndpoint)

  def test_flow_sensor_alias(self):
    """Verifies flow_sensor endpoint alias on success."""
    self.assertIsNotNone(self.uut.flow_sensor)
    self.uut.fake_get_endpoint_call.assert_called_once_with(
        flow_sensor.FlowSensorEndpoint)

  def test_humidity_sensor_alias(self):
    """Verifies humidity_sensor endpoint alias on success."""
    self.assertIsNotNone(self.uut.humidity_sensor)
    self.uut.fake_get_endpoint_call.assert_called_once_with(
        humidity_sensor.HumiditySensorEndpoint)

  def test_light_sensor_alias(self):
    """Verifies light_sensor endpoint alias on success."""
    self.assertIsNotNone(self.uut.light_sensor)
    self.uut.fake_get_endpoint_call.assert_called_once_with(
        light_sensor.LightSensorEndpoint)

  def test_occupancy_sensor_alias(self):
    """Verifies occupancy_sensor endpoint alias on success."""
    self.assertIsNotNone(self.uut.occupancy_sensor)
    self.uut.fake_get_endpoint_call.assert_called_once_with(
        occupancy_sensor.OccupancySensorEndpoint)

  def test_on_off_light_alias(self):
    """Verifies on_off_light endpoint alias on success."""
    self.assertIsNotNone(self.uut.on_off_light)
    self.uut.fake_get_endpoint_call.assert_called_once_with(
        on_off_light.OnOffLightEndpoint)

  def test_on_off_light_switch_alias(self):
    """Verifies on_off_light_switch endpoint alias on success."""
    self.assertIsNotNone(self.uut.on_off_light_switch)
    self.uut.fake_get_endpoint_call.assert_called_once_with(
        on_off_light_switch.OnOffLightSwitchEndpoint)

  def test_pressure_sensor_alias(self):
    """Verifies pressure_sensor endpoint alias on success."""
    self.assertIsNotNone(self.uut.pressure_sensor)
    self.uut.fake_get_endpoint_call.assert_called_once_with(
        pressure_sensor.PressureSensorEndpoint)

  def test_root_node_alias(self):
    """Verifies root_node endpoint alias on success."""
    self.assertIsNotNone(self.uut.root_node)
    self.uut.fake_get_endpoint_call.assert_called_once_with(
        root_node.RootNodeEndpoint)

  def test_temperature_sensor_alias(self):
    """Verifies temperature_sensor endpoint alias on success."""
    self.assertIsNotNone(self.uut.temperature_sensor)
    self.uut.fake_get_endpoint_call.assert_called_once_with(
        temperature_sensor.TemperatureSensorEndpoint)


if __name__ == "__main__":
  fake_device_test_case.main()
