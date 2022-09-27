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

from absl.testing import parameterized
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
from gazoo_device.capabilities.matter_endpoints import on_off_plugin_unit
from gazoo_device.capabilities.matter_endpoints import pressure_sensor
from gazoo_device.capabilities.matter_endpoints import root_node
from gazoo_device.capabilities.matter_endpoints import speaker
from gazoo_device.capabilities.matter_endpoints import temperature_sensor
from gazoo_device.capabilities.matter_endpoints import thermostat
from gazoo_device.capabilities.matter_endpoints import window_covering
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

  @parameterized.parameters(
      ("color_temperature_light",
       color_temperature_light.ColorTemperatureLightEndpoint),
      ("contact_sensor", contact_sensor.ContactSensorEndpoint),
      ("dimmable_light", dimmable_light.DimmableLightEndpoint),
      ("door_lock", door_lock.DoorLockEndpoint),
      ("extended_color_light", extended_color_light.ExtendedColorLightEndpoint),
      ("flow_sensor", flow_sensor.FlowSensorEndpoint),
      ("humidity_sensor", humidity_sensor.HumiditySensorEndpoint),
      ("light_sensor", light_sensor.LightSensorEndpoint),
      ("occupancy_sensor", occupancy_sensor.OccupancySensorEndpoint),
      ("on_off_light", on_off_light.OnOffLightEndpoint),
      ("on_off_light_switch", on_off_light_switch.OnOffLightSwitchEndpoint),
      ("on_off_plugin_unit", on_off_plugin_unit.OnOffPluginUnitEndpoint),
      ("pressure_sensor", pressure_sensor.PressureSensorEndpoint),
      ("root_node", root_node.RootNodeEndpoint),
      ("speaker", speaker.SpeakerEndpoint),
      ("temperature_sensor", temperature_sensor.TemperatureSensorEndpoint),
      ("thermostat", thermostat.ThermostatEndpoint),
      ("window_covering", window_covering.WindowCoveringEndpoint),
  )
  def test_endpoint_alias(self, attribute_name, endpoint_class):
    """Verifies endpoint alias on success."""
    self.assertIsNotNone(getattr(self.uut, attribute_name))
    self.uut.fake_get_endpoint_call.assert_called_once_with(endpoint_class)


if __name__ == "__main__":
  fake_device_test_case.main()
