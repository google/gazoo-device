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

"""Defines all functional test suites and their run order."""
from gazoo_device.tests.functional_tests import auxiliary_device_common_test_suite
from gazoo_device.tests.functional_tests import color_temperature_light_test_suite
from gazoo_device.tests.functional_tests import comm_power_test_suite
from gazoo_device.tests.functional_tests import common_test_suite
from gazoo_device.tests.functional_tests import contact_sensor_test_suite
from gazoo_device.tests.functional_tests import device_power_test_suite
from gazoo_device.tests.functional_tests import dimmable_light_test_suite
from gazoo_device.tests.functional_tests import door_lock_test_suite
from gazoo_device.tests.functional_tests import embedded_script_test_suite
from gazoo_device.tests.functional_tests import extended_color_light_test_suite
from gazoo_device.tests.functional_tests import file_transfer_test_suite
from gazoo_device.tests.functional_tests import flow_sensor_test_suite
from gazoo_device.tests.functional_tests import humidity_sensor_test_suite
from gazoo_device.tests.functional_tests import light_sensor_test_suite
from gazoo_device.tests.functional_tests import matter_endpoints_test_suite
from gazoo_device.tests.functional_tests import occupancy_sensor_test_suite
from gazoo_device.tests.functional_tests import on_off_light_switch_test_suite
from gazoo_device.tests.functional_tests import on_off_light_test_suite
from gazoo_device.tests.functional_tests import on_off_plugin_unit_test_suite
from gazoo_device.tests.functional_tests import optional_properties_test_suite
from gazoo_device.tests.functional_tests import package_management_test_suite
from gazoo_device.tests.functional_tests import pressure_sensor_test_suite
from gazoo_device.tests.functional_tests import pw_rpc_button_test_suite
from gazoo_device.tests.functional_tests import pw_rpc_common_test_suite
from gazoo_device.tests.functional_tests import pw_rpc_wifi_test_suite
from gazoo_device.tests.functional_tests import shell_ssh_test_suite
from gazoo_device.tests.functional_tests import speaker_test_suite
from gazoo_device.tests.functional_tests import switch_power_test_suite
from gazoo_device.tests.functional_tests import switchboard_test_suite
from gazoo_device.tests.functional_tests import temperature_sensor_test_suite
from gazoo_device.tests.functional_tests import thermostat_test_suite
from gazoo_device.tests.functional_tests import window_covering_test_suite
from gazoo_device.tests.functional_tests.utils import suite_filter

TEST_SUITES = (
    auxiliary_device_common_test_suite.AuxiliaryDeviceCommonTestSuite,
    color_temperature_light_test_suite.ColorTemperatureTestSuite,
    comm_power_test_suite.CommPowerTestSuite,
    common_test_suite.CommonTestSuite,
    contact_sensor_test_suite.ContactSensorTestSuite,
    device_power_test_suite.DevicePowerTestSuite,
    dimmable_light_test_suite.DimmableLightTestSuite,
    door_lock_test_suite.DoorLockTestSuite,
    embedded_script_test_suite.EmbeddedScriptTestSuite,
    extended_color_light_test_suite.ExtendedColorLightTestSuite,
    file_transfer_test_suite.FileTransferTestSuite,
    flow_sensor_test_suite.FlowSensorTestSuite,
    humidity_sensor_test_suite.HumiditySensorTestSuite,
    light_sensor_test_suite.LightSensorTestSuite,
    matter_endpoints_test_suite.MatterEndpointsPwRpcTestSuite,
    occupancy_sensor_test_suite.OccupancySensorTestSuite,
    on_off_light_switch_test_suite.OnOffLightSwitchTestSuite,
    on_off_light_test_suite.OnOffLightTestSuite,
    on_off_plugin_unit_test_suite.OnOffPluginUnitTestSuite,
    optional_properties_test_suite.OptionalPropertiesTestSuite,
    package_management_test_suite.PackageManagementTestSuite,
    pressure_sensor_test_suite.PressureSensorTestSuite,
    pw_rpc_button_test_suite.PwRPCButtonTestSuite,
    pw_rpc_common_test_suite.PwRPCCommonTestSuite,
    pw_rpc_wifi_test_suite.PwRPCWifiTestSuite,
    shell_ssh_test_suite.ShellSshTestSuite,
    speaker_test_suite.SpeakerTestSuite,
    switch_power_test_suite.SwitchPowerTestSuite,
    switchboard_test_suite.SwitchboardTestSuite,
    temperature_sensor_test_suite.TemperatureSensorTestSuite,
    thermostat_test_suite.ThermostatTestSuite,
    window_covering_test_suite.WindowCoveringTestSuite,
)


def get_suite_index(suite: suite_filter.SuiteType) -> int:
  """Returns the key used for test suite sorting."""
  aux_common_test_suite = (
      auxiliary_device_common_test_suite.AuxiliaryDeviceCommonTestSuite)
  if suite in [common_test_suite.CommonTestSuite, aux_common_test_suite]:
    # CommonTestSuite runs first as it does a factory reset of the device.
    return 0
  else:
    return 1  # Other test suites run in any order.
