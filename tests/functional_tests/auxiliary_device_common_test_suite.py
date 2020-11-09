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

"""Test suite for all auxiliary devices, covers basic functionality."""
import os
import json
import shutil
import time
import traceback
import sys
import subprocess

from mobly import asserts

import gazoo_device
from gazoo_device.base_classes import auxiliary_device
from functional_tests import gdm_test_base

# nlmodel does exist but nl_model is a typo, control_port_name never used
# qr_code has been deprecated for some devices.
DEPRECATED_PROPERTIES = ["nl_model", "mac_address", "control_port_name", "wireless_reg_dom",
                         "adb_serial", "qr_code", "default_device_name"]

# Allows the log process to catch up after device creation by using a time.sleep().
# Prevents having old device bootup events in the logs checked by _verify_no_unexpected_bootups().
LOG_CATCH_UP_DELAY = 3


class PowerSwitch:

    def __init__(self):
        self._is_on = False

    def turn_on_power(self):
        self._is_on = True

    def power_is_on(self):
        return self._is_on


def turn_everything_on(switch_list):
    for sw in switch_list:
        sw.turn_on_power()


class AuxiliaryDeviceCommonTestSuite(gdm_test_base.GDMTestBase):
    """Common test suite for all auxiliary devices."""

    @classmethod
    def is_applicable_to(cls, device_type, device_class, device_name):
        """Determine if this test suite can run on the given device."""
        return issubclass(device_class, auxiliary_device.AuxiliaryDevice)

    @classmethod
    def requires_pairing(cls):
        """Returns True if the device in the testbed must be paired to run this test suite."""
        return False

    @classmethod
    def required_test_config_variables(cls):
        """Returns a list of keys required to be present in the functional test config.

        Returns:
            list[str]: functional test config keys which are used by the test suite.
        """
        return ["shell_cmd", "expect", "known_logline", "custom_filters"]

    def test_1000_close_device(self):
        self.logger.info("Testing close device stops logging")
        log_file = self.device.log_file_name
        asserts.assert_true(os.path.exists(log_file),
                            "Cannot test close as device is not logging")
        self.device.close()
        time.sleep(1)
        size = os.stat(log_file).st_size
        time.sleep(.1)
        asserts.assert_true(size == os.stat(log_file).st_size,
                            "Log has updated after device is closed")

    def test_1001_logging(self):
        self._verify_logging()

    def test_1002_get_serial_number(self):
        try:
            asserts.assert_true(self.device.serial_number is not None,
                                "serial number should not be None")
        except Exception:
            traceback_message = traceback.format_exc()
            asserts.fail("Error happened during get serial number: " +
                         traceback_message)

    def test_1004_get_firmware_version(self):
        self._verify_firmware_version()

    def test_1008_reboot(self):
        """Reboot automatically verifies the reboot happens correctly.

        Note:
         Verifies device is_connected afer reboot.
        """
        time.sleep(LOG_CATCH_UP_DELAY)

        try:
            self.device.reboot()
        except Exception:
            traceback_message = traceback.format_exc()
            asserts.fail("Error happened during reboot: " + traceback_message)
        self.device.device_is_connected()

    def test_1011_send_and_expect(self):
        try:
            self.device.switchboard.send_and_expect(self.test_config["shell_cmd"],
                                                    self.test_config["expect"],
                                                    timeout=10)
        except Exception:
            traceback_message = traceback.format_exc()
            asserts.fail("Error happened during send and expect: " + traceback_message)

    def test_1012_shell(self):
        try:
            self.device.shell(self.test_config["shell_cmd"])
        except Exception:
            traceback_message = traceback.format_exc()
            asserts.fail("Error happened during shell command: " + traceback_message)

    def test_1016_do_and_expect_some_func_is_called(self):
        switch = PowerSwitch()
        expect_result = self.device.switchboard.do_and_expect(
            turn_everything_on,
            [[switch]],
            {},
            ["fake_string, won't match anything"],
            timeout=.1)
        asserts.assert_true(expect_result.timedout,
                            "Expected do_and_expect to timeout, but timedout was False")
        asserts.assert_true(switch.power_is_on,
                            "turn_everything_on function did not execute, "
                            "the power state is still off for switch.")

    def test_1115_test_expect_with_bogus_logline(self):
        self.logger.info("testing expect with bogus log line")
        phrase = "garblygookand more"
        try:
            response = self.device.switchboard.expect([phrase], timeout=2)
            if not response.timedout:
                asserts.fail("Response should time out. Instead got: {}".format(response))
        except Exception:
            traceback_message = traceback.format_exc()
            asserts.fail("Error happened during expect with bogus logline: " +
                         traceback_message)

    def test_2002_get_device_prop_can_execute(self):
        """Check get_device_prop can execute."""
        self.device.close()
        try:
            self.manager.get_device_prop(self.device.name)
        except Exception as err:
            asserts.fail("manager.get_device_prop failed, Err: {!r}. Check gdm.log for more info"
                         .format(err))

    def test_2003_redetect(self):
        """Executes the code in the device class that supports device detection."""
        self.device.close()
        time.sleep(.2)
        new_file_devices_name = os.path.join(self.log_path, "test_2003_devices.json")
        new_file_options_name = os.path.join(self.log_path, "test_2003_device_options.json")

        shutil.copy(self.manager.device_file_name, new_file_devices_name)
        shutil.copy(self.manager.device_options_file_name, new_file_options_name)
        # self.manager._devices
        new_manager = gazoo_device.Manager(device_file_name=new_file_devices_name,
                                           device_options_file_name=new_file_options_name,
                                           log_directory=self.log_path,
                                           gdm_log_file=os.path.join(
                                               self.log_path,
                                               "test_2003_gdm.txt"))
        new_manager.redetect(self.device.name, self.log_path)
        new_manager.close()
        asserts.assert_true(
            (self.device.name in new_manager._devices or self.device.name in new_manager.
             other_devices),
            "Device was not successfully detected. "
            "See test_2003_gdm.txt and {}_detext.txt for more info".format(
                self.device.device_type))
        if self.device.name in new_manager._devices:
            old_dict = self.manager._devices[self.device.name]["persistent"]
            new_dict = new_manager._devices[self.device.name]["persistent"]
        else:
            old_dict = self.manager.other_devices[self.device.name]["persistent"]
            new_dict = new_manager.other_devices[self.device.name]["persistent"]
        for name, a_dict in [("Old", old_dict), ("Detected", new_dict)]:
            self.logger.info("{} configuration: ".format(name))
            for key, value in a_dict.items():
                self.logger.info("\t{}:{}".format(key, value))

        missing_props = []
        bad_values = []

        for prop, old_value in old_dict.items():
            if prop in new_dict:
                new_value = new_dict[prop]
                if old_value != new_value:
                    bad_values.append(
                        "{}: {!r} was previously {!r}".format(
                            prop, new_value, old_value))

            elif prop not in DEPRECATED_PROPERTIES:
                missing_props.append(prop)
        msg = ""
        if missing_props:
            msg += "{} is missing the following previous props: {}.\n".format(
                self.device.name,
                missing_props)
        if bad_values:
            msg += "{} has the following mismatched values: {}.".format(
                self.device.name,
                ", ".join(bad_values))

        self.logger.info(msg)
        asserts.assert_false(missing_props or bad_values, msg)

    def test_3000_make_devices_ready_json_only(self):
        """Ensure only json is logged by the make-devices-ready command for this device."""
        self.device.close()
        cmd = "{gdm} make-devices-ready --devices={device_name}".format(
            gdm=os.path.join(os.path.dirname(sys.executable), "gdm"),
            device_name=self.device.name)
        output = subprocess.check_output(cmd, shell=True).decode("utf-8", "replace")

        try:
            json.loads(output)
        except json.decoder.JSONDecodeError:
            self.fail("make_devices_ready for {} logged non-json. Output: {!r}".format(
                self.device.name, output))

    def _verify_firmware_version(self):
        try:
            asserts.assert_true(self.device.firmware_version is not None,
                                "firmware version should not be None")
        except Exception:
            traceback_message = traceback.format_exc()
            asserts.fail("Error happened during get firmware version: " +
                         traceback_message)

    def _verify_logging(self):
        log_file = self.device.log_file_name
        asserts.assert_true(
            os.path.exists(log_file), "Failed to initiate the log file")
        asserts.assert_true(os.stat(log_file).st_size > 0,
                            "{} is not logging".format(self.device.name))

    def _verify_expect_log(self):
        self.logger.info("Expecting logline {!r}".format(self.test_config["known_logline"]))
        try:
            res = self.device.switchboard.expect([self.test_config["known_logline"]], timeout=30)
        except Exception:
            traceback_message = traceback.format_exc()
            asserts.fail("Error happened during expect: " + traceback_message)
        asserts.assert_true(res.index is not None, "Expect returned None")
        asserts.assert_true(
            res.index == 0,
            "Phrase {} should have been found in the log lines"
            .format(self.test_config["known_logline"]))


if __name__ == "__main__":
    gdm_test_base.main()
