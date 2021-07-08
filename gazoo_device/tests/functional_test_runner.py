# Copyright 2021 Google LLC
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
import unittest

from gazoo_device.tests.functional_tests import auxiliary_device_common_test_suite
from gazoo_device.tests.functional_tests import comm_power_test_suite
from gazoo_device.tests.functional_tests import common_test_suite
from gazoo_device.tests.functional_tests import device_power_test_suite
from gazoo_device.tests.functional_tests import file_transfer_test_suite
from gazoo_device.tests.functional_tests import optional_properties_test_suite
from gazoo_device.tests.functional_tests import package_management_test_suite
from gazoo_device.tests.functional_tests import pw_rpc_light_test_suite
from gazoo_device.tests.functional_tests import shell_ssh_test_suite
from gazoo_device.tests.functional_tests import switch_power_test_suite
from gazoo_device.tests.functional_tests import switchboard_test_suite
from gazoo_device.tests.functional_tests.utils import gazoo_input
from gazoo_device.tests.functional_tests.utils import gazootest
from gazoo_device.tests.functional_tests.utils import runner_lib

SuiteCollectionType = runner_lib.SuiteCollectionType

# TODO(artorl): Open-source the remainder of functional test suites.
TEST_SUITES = (
    auxiliary_device_common_test_suite.AuxiliaryDeviceCommonTestSuite,
    comm_power_test_suite.CommPowerTestSuite,
    common_test_suite.CommonTestSuite,
    device_power_test_suite.DevicePowerTestSuite,
    file_transfer_test_suite.FileTransferTestSuite,
    optional_properties_test_suite.OptionalPropertiesTestSuite,
    package_management_test_suite.PackageManagementTestSuite,
    pw_rpc_light_test_suite.PwRPCLightTestSuite,
    shell_ssh_test_suite.ShellSshTestSuite,
    switch_power_test_suite.SwitchPowerTestSuite,
    switchboard_test_suite.SwitchboardTestSuite,
)


def load_tests(loader: unittest.TestLoader,
               standard_tests: unittest.TestSuite,
               pattern: str) -> unittest.TestSuite:
  """Called by unittest framework to load tests."""
  del loader  # We use our own test loader.
  del pattern  # Not used since we don't use the default discovery mechanism.
  testbed_config = gazoo_input.get_testbed_config()
  device_name = testbed_config.devices[0].name

  standard_tests.addTests(
      runner_lib.identify_tests_to_run(
          TEST_SUITES, _reorder_test_suites, device_name))
  return standard_tests


def _reorder_test_suites(
    test_suites: SuiteCollectionType) -> SuiteCollectionType:
  """Reorders test suites to ensure factory reset run first."""
  test_suites.sort(key=_get_suite_index)
  return test_suites


def _get_suite_index(suite: runner_lib.SuiteType) -> int:
  """Returns the key used for test suite sorting."""
  aux_common_test_suite = (
      auxiliary_device_common_test_suite.AuxiliaryDeviceCommonTestSuite)
  if suite == aux_common_test_suite:
    # CommonTestSuite runs first as it does a factory reset of the device.
    return 0
  else:
    return 1  # Other test suites run in any order.


if __name__ == "__main__":
  gazootest.main()
