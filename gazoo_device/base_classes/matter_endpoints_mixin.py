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
"""Mixin for Matter endpoint aliases."""
from gazoo_device import decorators
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
from gazoo_device.capabilities.matter_endpoints import temperature_sensor
from gazoo_device.capabilities.matter_endpoints import thermostat


class MatterEndpointAliasesMixin:
  """Mixin for Matter endpoint aliases.

  The mixin assumes self.matter_endpoints capability is set.
  """

  @decorators.CapabilityDecorator(
      color_temperature_light.ColorTemperatureLightEndpoint)
  def color_temperature_light(
      self) -> color_temperature_light.ColorTemperatureLightEndpoint:
    """Matter Color Temperature Light endpoint instance.

    Returns:
      Color Temperature Light endpoint instance.

    Raises:
      DeviceError when Color Temperate Light endpoint is not supported on the
      device.
    """
    return self.matter_endpoints.get_endpoint_instance_by_class(
        color_temperature_light.ColorTemperatureLightEndpoint)

  @decorators.CapabilityDecorator(contact_sensor.ContactSensorEndpoint)
  def contact_sensor(self) -> contact_sensor.ContactSensorEndpoint:
    """Matter Contact Sensor endpoint instance.

    Returns:
      Contact Sensor endpoint instance.

    Raises:
      DeviceError when Contact Sensor endpoint is not supported on the
      device.
    """
    return self.matter_endpoints.get_endpoint_instance_by_class(
        contact_sensor.ContactSensorEndpoint)

  @decorators.CapabilityDecorator(dimmable_light.DimmableLightEndpoint)
  def dimmable_light(self) -> dimmable_light.DimmableLightEndpoint:
    """Matter Dimmable Light endpoint instance.

    Returns:
      Dimmable Light endpoint instance.

    Raises:
      DeviceError when Dimmable Light endpoint is not supported on the
      device.
    """
    return self.matter_endpoints.get_endpoint_instance_by_class(
        dimmable_light.DimmableLightEndpoint)

  @decorators.CapabilityDecorator(door_lock.DoorLockEndpoint)
  def door_lock(self) -> door_lock.DoorLockEndpoint:
    """Matter Door Lock endpoint instance.

    Returns:
      Door Lock endpoint instance.

    Raises:
      DeviceError when Door Lock endpoint is not supported on the
      device.
    """
    return self.matter_endpoints.get_endpoint_instance_by_class(
        door_lock.DoorLockEndpoint)

  @decorators.CapabilityDecorator(
      extended_color_light.ExtendedColorLightEndpoint)
  def extended_color_light(
      self) -> extended_color_light.ExtendedColorLightEndpoint:
    """Matter Extended color light endpoint instance.

    Returns:
      Extended color light endpoint instance.

    Raises:
      DeviceError when Extended color light endpoint is not supported on the
      device.
    """
    return self.matter_endpoints.get_endpoint_instance_by_class(
        extended_color_light.ExtendedColorLightEndpoint)

  @decorators.CapabilityDecorator(flow_sensor.FlowSensorEndpoint)
  def flow_sensor(self) -> flow_sensor.FlowSensorEndpoint:
    """Matter Flow sensor endpoint instance.

    Returns:
      Flow sensor endpoint instance.

    Raises:
      DeviceError when flow sensor endpoint is not supported on the
      device.
    """
    return self.matter_endpoints.get_endpoint_instance_by_class(
        flow_sensor.FlowSensorEndpoint)

  @decorators.CapabilityDecorator(humidity_sensor.HumiditySensorEndpoint)
  def humidity_sensor(self) -> humidity_sensor.HumiditySensorEndpoint:
    """Matter Humidity Sensor endpoint instance.

    Returns:
      Humidity Sensor endpoint instance.

    Raises:
      DeviceError when Humidity Sensor endpoint is not supported on the
      device.
    """
    return self.matter_endpoints.get_endpoint_instance_by_class(
        humidity_sensor.HumiditySensorEndpoint)

  @decorators.CapabilityDecorator(light_sensor.LightSensorEndpoint)
  def light_sensor(self) -> light_sensor.LightSensorEndpoint:
    """Matter Light sensor endpoint instance.

    Returns:
      Light sensor endpoint instance.

    Raises:
      DeviceError when light sensor endpoint is not supported on the
      device.
    """
    return self.matter_endpoints.get_endpoint_instance_by_class(
        light_sensor.LightSensorEndpoint)

  @decorators.CapabilityDecorator(occupancy_sensor.OccupancySensorEndpoint)
  def occupancy_sensor(self) -> occupancy_sensor.OccupancySensorEndpoint:
    """Matter Occupancy Sensor endpoint instance.

    Returns:
      Occupancy Sensor endpoint instance.

    Raises:
      DeviceError when Occupancy Sensor endpoint is not supported on the
      device.
    """
    return self.matter_endpoints.get_endpoint_instance_by_class(
        occupancy_sensor.OccupancySensorEndpoint)

  @decorators.CapabilityDecorator(on_off_light.OnOffLightEndpoint)
  def on_off_light(self) -> on_off_light.OnOffLightEndpoint:
    """Matter OnOff Light endpoint instance.

    Returns:
      OnOff Light endpoint instance.

    Raises:
      DeviceError when OnOff Light endpoint is not supported on the
      device.
    """
    return self.matter_endpoints.get_endpoint_instance_by_class(
        on_off_light.OnOffLightEndpoint)

  @decorators.CapabilityDecorator(on_off_light_switch.OnOffLightSwitchEndpoint)
  def on_off_light_switch(self) -> on_off_light_switch.OnOffLightSwitchEndpoint:
    """Matter OnOff Light Switch endpoint instance.

    Returns:
      OnOff Light Switch endpoint instance.

    Raises:
      DeviceError when OnOff Light Switch endpoint is not supported on the
      device.
    """
    return self.matter_endpoints.get_endpoint_instance_by_class(
        on_off_light_switch.OnOffLightSwitchEndpoint)

  @decorators.CapabilityDecorator(on_off_plugin_unit.OnOffPluginUnitEndpoint)
  def on_off_plugin_unit(self) -> on_off_plugin_unit.OnOffPluginUnitEndpoint:
    """Matter On/Off Plug-in Unit endpoint instance.

    Returns:
      On/Off Plug-in Unit endpoint instance.

    Raises:
      DeviceError when On/Off Plug-in Unit endpoint is not supported on the
      device.
    """
    return self.matter_endpoints.get_endpoint_instance_by_class(
        on_off_plugin_unit.OnOffPluginUnitEndpoint)

  @decorators.CapabilityDecorator(pressure_sensor.PressureSensorEndpoint)
  def pressure_sensor(self) -> pressure_sensor.PressureSensorEndpoint:
    """Matter Pressure Sensor endpoint instance.

    Returns:
      Pressure Sensor endpoint instance.

    Raises:
      DeviceError when Pressure Sensor endpoint is not supported on the
      device.
    """
    return self.matter_endpoints.get_endpoint_instance_by_class(
        pressure_sensor.PressureSensorEndpoint)

  @decorators.CapabilityDecorator(root_node.RootNodeEndpoint)
  def root_node(self) -> root_node.RootNodeEndpoint:
    """Matter Root Node endpoint instance.

    Returns:
      Root Node endpoint instance.

    Raises:
      DeviceError when Root Node endpoint is not supported on the
      device.
    """
    return self.matter_endpoints.get_endpoint_instance_by_class(
        root_node.RootNodeEndpoint)

  @decorators.CapabilityDecorator(temperature_sensor.TemperatureSensorEndpoint)
  def temperature_sensor(self) -> temperature_sensor.TemperatureSensorEndpoint:
    """Matter Temperature Sensor endpoint instance.

    Returns:
      Temperature Sensor endpoint instance.

    Raises:
      DeviceError when Temperature Sensor endpoint is not supported on the
      device.
    """
    return self.matter_endpoints.get_endpoint_instance_by_class(
        temperature_sensor.TemperatureSensorEndpoint)

  @decorators.CapabilityDecorator(thermostat.ThermostatEndpoint)
  def thermostat(self) -> thermostat.ThermostatEndpoint:
    """Matter Thermostat endpoint instance.

    Returns:
      Thermostat endpoint instance.

    Raises:
      DeviceError when Thermostat endpoint is not supported on the
      device.
    """
    return self.matter_endpoints.get_endpoint_instance_by_class(
        thermostat.ThermostatEndpoint)

