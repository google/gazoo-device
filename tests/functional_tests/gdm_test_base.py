# Copyright 2020 Google LLC
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

"""Base class for Gazoo Device Manager on-device tests.

Uses Mobly framework: https://github.com/google/mobly.
"""
import abc
import inspect
import logging
import os
import subprocess
import time
import traceback
import json
from mobly import asserts
from mobly import signals
from mobly import test_runner
from mobly import base_test
from gazoo_device import errors
from gazoo_device import manager

CUR_LOCATION = os.path.dirname(os.path.abspath(__file__))
CONFIGS_PATH = os.path.abspath(os.path.join(CUR_LOCATION, "../functional_test_configs"))
GAZOO_DEVICE_CONTROLLER = "GazooDevice"
RECONNECT_TIMEOUT = 60  # Max wait time for the device to reconnect after a test


class GDMTestBase(abc.ABC, base_test.BaseTestClass):
    """Base class for all functional test suites."""

    def __init__(self, configs):
        super().__init__(configs)
        self._abort_in_setup_class = False
        self.logger = logging.getLogger()
        self.gazoo_device_configs = self.get_gazoo_device_configs()
        self.load_test_config()
        self.filter_tests()

    @classmethod
    @abc.abstractmethod
    def is_applicable_to(cls, device_type, device_class, device_name):
        """Determine if this test suite is applicable to (can run on) the given device type.

        Args:
            device_type (str): one of the device types supported by GDM.
            device_class (type): device controller class object.
            device_name (str): GDM device name.

        Returns:
            bool: True if this test suite can run on the given device type, False otherwise.

        Note:
            This allows to dynamically determine the set of test suites to run for a device.
            device_class argument is provided for convenience.
            device_name is provided in case you need to communicate to the device. Most
            implementations won't need to create the device. Since device creation is slower,
            prefer using device_type and/or device_class instead (unless you have to).
        """

    @classmethod
    @abc.abstractmethod
    def requires_pairing(cls):
        """Returns True if the device in the testbed must be paired to run this test suite.

        Returns:
            bool: True if this test suite requires a paired device, False otherwise.

        Note:
            All devices on GDM regression servers are unpaired. Test suites which require
            paired devices do not run in automated regression tests.
        """

    @classmethod
    def required_test_config_variables(cls):
        """Returns a list of keys required to be present in the functional test config.

        Returns:
            list[str]: functional test config keys which are used by the test suite.
        """
        return []

    def setup_class(self):
        """Aborts the test suite if all tests have been filtered out by self.filter_tests()."""
        super().setup_class()
        self.manager = manager.Manager(log_directory=self.log_path,
                                       gdm_log_file=os.path.join(self.log_path, "gdm.log"),
                                       stdout_logging=False)
        self.check_test_config_keys()
        if self._abort_in_setup_class:
            asserts.abort_class("All tests in test suite {} have been skipped. "
                                "Aborting the test suite.".format(type(self).__name__))

    def teardown_class(self):
        self.manager.close()

    def setup_test(self):
        """Creates the first Gazoo device listed in testbed config.

        Raises:
            Fails test if unable to create each device.
        """
        super().setup_test()
        here = os.path.dirname(os.path.abspath(__file__))
        filters_dir_path = os.path.join(here, 'filters')
        if not os.path.exists(filters_dir_path):
            here = os.path.join(here, 'functional_tests')
        full_path_filter_list = []
        for filter_path in self.test_config["custom_filters"]:
            full_path_filter_list.append(os.path.join(here, filter_path))
        for i in range(2):
            try:
                self.devices = [self.manager.create_device(self.gazoo_device_configs[0]["id"],
                                                           log_name_prefix=self._get_log_suffix(),
                                                           filters=full_path_filter_list)]
                break
            except signals.TestFailure as err:
                if "DeviceNotConnectedError" in str(err):
                    if i == 0:
                        self.logger.warning(
                            "Device creation failed attempt 1/2. "
                            "Sleeping 30 seconds to allow device to fully boot up.")
                        time.sleep(30)
                    else:
                        msg = "Device creation failed in two tries. Aborting all tests."
                        self.logger.error(msg)
                        asserts.abort_all(msg)
                else:
                    raise err

        if not self.devices:
            asserts.fail(
                "Infrastructure Issue. No devices created for functional test. Is testbed empty?")
        self.device = self.devices[0]
        if self.device is None:
            asserts.fail("Infrastructure Issue. Device creation returned None.")
        try:
            if hasattr(self.device, "firmware_version"):
                version = self.device.firmware_version
                self.logger.info("DUT: {} Firmware version: {}".format(self.device.name, version))
            else:
                # Auxiliary devices may not have support for firmware_version.
                self.device.device_is_connected()
                self.logger.info("DUT: {} device is connected.".format(self.device.name))
        except (errors.GazooDeviceError, errors.DeviceNotConnectedError) as e:
            asserts.fail("Infrastructure Issue. Failed to communicate with device {}. "
                         "Error: {!r}.\n{}"
                         .format(self.device.name, e, traceback.format_exc()))

    def teardown_test(self):
        """Closes each device."""
        if hasattr(self, 'devices'):
            self.wait_for_device()
            time.sleep(3)
            for device in self.devices:
                device.close()

    def wait_for_device(self):  # wait for devices that use adb to reconnect
        deadline = time.time() + RECONNECT_TIMEOUT
        while time.time() < deadline:
            if self.device.name in self.manager.get_connected_devices(category="all"):
                break
            self.logger.info("{} is not connected. Waiting for it to reconnect..."
                             .format(self.device.name))
            time.sleep(1)
        else:
            asserts.fail("{} failed to reconnect in {}s"
                         .format(self.device.name, RECONNECT_TIMEOUT))

    def get_gazoo_device_configs(self):
        """Extracts Gazoo devices from the testbed."""
        gazoo_device_configs = []
        for controller, device_name_list in self.controller_configs.items():
            if controller == GAZOO_DEVICE_CONTROLLER:
                for device_name in device_name_list:
                    gazoo_device_configs.append({"id": device_name})
        if not gazoo_device_configs:
            raise RuntimeError("The testbed config does not have any {} controller entries"
                               .format(GAZOO_DEVICE_CONTROLLER))
        return gazoo_device_configs

    def load_test_config(self):
        """Loads device specific test_config.json."""
        test_config_file = self._get_default_json(self.gazoo_device_configs[0]["id"])
        self.logger.info("Test_config_file: {}".format(test_config_file))
        test_config_path = os.path.join(CONFIGS_PATH, test_config_file)

        if not os.path.exists(test_config_path):
            if not os.path.exists(test_config_path):
                raise ValueError("Test config file {} does not exist".format(test_config_path))
        try:
            with open(test_config_path, "r") as test_config_file:
                self.test_config = json.load(test_config_file)
        except Exception as err:
            raise ValueError("Test_config_file '{}' not parseable as json. Fix file. Err: {!r}.".
                             format(test_config_path, err))

    @classmethod
    def check_properties_set(cls, device_name, property_list):
        mgr = manager.Manager()
        for property_name in property_list:
            value = mgr.get_device_prop(device_name, property_name)
            if value is None or str(value).startswith("Exception"):
                return False
        return True

    def check_test_config_keys(self):
        """Checks that all keys used by this test suite are present in the functional test config.

        Raises:
            KeyError: one or more of the required keys are missing from the functional test config.
        """
        missing_keys = [key for key in self.required_test_config_variables()
                        if key not in self.test_config]
        if missing_keys:
            raise KeyError("The following keys are missing from the functional test "
                           "config: {}.".format(missing_keys))

    def filter_tests(self):
        """Removes tests found in "do_not_run_tests" of the test config from tests to run.

        Note:
            If specific tests are given through --tests,
            this is ignored and just those tests are run.
        """
        filtered_tests = self.get_test_filter_list("do_not_run_tests")
        test_list = [name for name, _ in inspect.getmembers(self, inspect.ismethod)
                     if name.startswith("test_")]

        tests_to_run = [test for test in test_list if test not in filtered_tests]
        if not tests_to_run:
            self._abort_in_setup_class = True

        # self.tests overwrites running all the tests (but runs all tests if it's empty)
        self.tests = tests_to_run
        self.logger.info("Filtered out tests: {}".format(", ".join(filtered_tests)))

    def get_test_filter_list(self, filter_name):
        """Returns the list of test names in the current test suite found in the filter."""
        test_or_suite_names = self.test_config.get(filter_name, [])
        test_list = [name for name, _ in inspect.getmembers(self, inspect.ismethod)
                     if name.startswith("test_")]

        filtered_tests = []
        for full_name in test_or_suite_names:
            if "." in full_name:  # name is SuiteName.test_name
                suite_name, test_name = full_name.split(".")
                if suite_name == type(self).__name__ and test_name in test_list:
                    filtered_tests.append(test_name)
            elif full_name == type(self).__name__:  # name is SuiteName
                filtered_tests = test_list
                break
        return filtered_tests

    def _execute_subprocess(self, cmd):
        """Executes a subprocess command.

        Args:
            cmd: A string that is the command to execute.

        Returns:
            The output of the command run if exit code is 0.
        """
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        (out, err) = proc.communicate()
        return out, err

    def _get_default_json(self, devname):
        """Returns name of json file based on device name. Used when json file is not specified."""
        return devname.split('-')[0] + "_test_config.json"

    def _get_log_suffix(self):
        """Returns the log suffix to be used for test log files."""
        return self.current_test_info.name


def main():
    """Runs the current test suite."""
    test_runner.main()


if __name__ == '__main__':
    main()
