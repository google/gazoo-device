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

"""Functional Test Runner.

Runs the on-device regression test suites for a particular testbed model.
See README.md for more information.
"""
from typing import Optional, Sequence

from absl import app
from absl import flags
import gazoo_device
from gazoo_device.tests.functional_tests import auxiliary_device_common_test_suite
from gazoo_device.tests.functional_tests import color_temperature_light_test_suite
from gazoo_device.tests.functional_tests import comm_power_test_suite
from gazoo_device.tests.functional_tests import common_test_suite
from gazoo_device.tests.functional_tests import device_power_test_suite
from gazoo_device.tests.functional_tests import dimmable_light_test_suite
from gazoo_device.tests.functional_tests import door_lock_test_suite
from gazoo_device.tests.functional_tests import embedded_script_test_suite
from gazoo_device.tests.functional_tests import file_transfer_test_suite
from gazoo_device.tests.functional_tests import matter_endpoints_test_suite
from gazoo_device.tests.functional_tests import on_off_light_test_suite
from gazoo_device.tests.functional_tests import optional_properties_test_suite
from gazoo_device.tests.functional_tests import package_management_test_suite
from gazoo_device.tests.functional_tests import pressure_sensor_test_suite
from gazoo_device.tests.functional_tests import pw_rpc_button_test_suite
from gazoo_device.tests.functional_tests import pw_rpc_common_test_suite
from gazoo_device.tests.functional_tests import pw_rpc_wifi_test_suite
from gazoo_device.tests.functional_tests import shell_ssh_test_suite
from gazoo_device.tests.functional_tests import switch_power_test_suite
from gazoo_device.tests.functional_tests import switchboard_test_suite
from gazoo_device.tests.functional_tests import temperature_sensor_test_suite
from gazoo_device.tests.functional_tests.utils import suite_filter
from mobly import config_parser
from mobly import suite_runner

_CONFIG_FLAG = flags.DEFINE_string(
    name="config",
    default=None,
    help="Path to the Mobly .yml testbed config file",
    required=True,
    short_name="c")

SuiteCollectionType = suite_filter.SuiteCollectionType

TEST_SUITES = (
    auxiliary_device_common_test_suite.AuxiliaryDeviceCommonTestSuite,
    color_temperature_light_test_suite.ColorTemperatureTestSuite,
    comm_power_test_suite.CommPowerTestSuite,
    common_test_suite.CommonTestSuite,
    device_power_test_suite.DevicePowerTestSuite,
    embedded_script_test_suite.EmbeddedScriptTestSuite,
    file_transfer_test_suite.FileTransferTestSuite,
    dimmable_light_test_suite.DimmableLightTestSuite,
    door_lock_test_suite.DoorLockTestSuite,
    matter_endpoints_test_suite.MatterEndpointsPwRpcTestSuite,
    on_off_light_test_suite.OnOffLightTestSuite,
    optional_properties_test_suite.OptionalPropertiesTestSuite,
    package_management_test_suite.PackageManagementTestSuite,
    pressure_sensor_test_suite.PressureSensorTestSuite,
    pw_rpc_button_test_suite.PwRPCButtonTestSuite,
    pw_rpc_common_test_suite.PwRPCCommonTestSuite,
    pw_rpc_wifi_test_suite.PwRPCWifiTestSuite,
    shell_ssh_test_suite.ShellSshTestSuite,
    switch_power_test_suite.SwitchPowerTestSuite,
    switchboard_test_suite.SwitchboardTestSuite,
    temperature_sensor_test_suite.TemperatureSensorTestSuite,
)


def _get_suite_index(suite: suite_filter.SuiteType) -> int:
  """Returns the key used for test suite sorting."""
  aux_common_test_suite = (
      auxiliary_device_common_test_suite.AuxiliaryDeviceCommonTestSuite)
  if suite == aux_common_test_suite:
    # CommonTestSuite runs first as it does a factory reset of the device.
    return 0
  else:
    return 1  # Other test suites run in any order.


def _reorder_test_suites(
    test_suites: SuiteCollectionType) -> SuiteCollectionType:
  """Reorders test suites to ensure factory reset run first."""
  test_suites.sort(key=_get_suite_index)
  return test_suites


def _get_device_name(config_path: str) -> str:
  """Extracts the device name from the Mobly config."""
  config = config_parser.load_test_config_file(config_path)[0]
  controller_name = gazoo_device.MOBLY_CONTROLLER_CONFIG_NAME
  return config.controller_configs[controller_name][0]["id"]


def _run_tests(argv: Optional[Sequence[str]] = None) -> None:
  """Identifies tests to run and runs them via the Mobly test runner."""
  del argv  # Unused.
  device_name = _get_device_name(_CONFIG_FLAG.value)
  test_suite_dict = suite_filter.identify_tests_to_run(
      all_test_suites=TEST_SUITES,
      reorder_test_suites=_reorder_test_suites,
      device_name=device_name)
  all_test_names = []
  for suite_class, test_names in test_suite_dict.items():
    for test_name in test_names:
      all_test_names.append(f"{suite_class.__name__}.{test_name}")
  suite_runner.run_suite(
      test_classes=test_suite_dict.keys(),
      argv=["--tests"] + all_test_names + ["--config", _CONFIG_FLAG.value])


def main(argv: Optional[Sequence[str]] = None) -> None:
  app.run(main=_run_tests, argv=argv)


if __name__ == "__main__":
  main()
