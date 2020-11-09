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

"""Test suite for devices using the switch_power_usb capabilities."""
import time

from mobly import asserts
from functional_tests import gdm_test_base

REQUIRED_MODES = ['sync', 'off']


class SwitchPowerUsbTestSuite(gdm_test_base.GDMTestBase):
    """Tests for the usb_hub_power capability.

    Warning: This test will change the power mode for ports on the hub, so the hub should not
    be used for connecting other devices.
    """

    @classmethod
    def is_applicable_to(cls, device_type, device_class, device_name):
        """Determine if this test suite can run on the given device."""
        if not device_class.has_capabilities(["switch_power"]):
            return False
        flavor = str(device_class.switch_power.capability_classes).split(".")[-2]
        return flavor == 'switch_power_usb_with_charge'

    @classmethod
    def requires_pairing(cls):
        """Returns True if the device in the testbed must be paired to run this test suite."""
        return False

    def test_5800_sync_and_off_modes_supported(self):
        """Verify that the required modes are supported."""
        supported_modes = self.device.switch_power.supported_modes
        result = all(mode in supported_modes for mode in REQUIRED_MODES)
        if not result:
            asserts.fail("{} Required switch_power modes not found. Required: {}, found: {}".
                         format(self.device.name, REQUIRED_MODES, supported_modes))

    def test_5801_set_and_get_mode(self):
        """Verify that setting and getting a single port works as expected"""
        self.device.switch_power.set_mode("off", 1)
        time.sleep(5)
        mode = self.device.switch_power.get_mode(1)
        asserts.assert_equal(mode, "off", "{} expected usb_hub mode to be 'off' found: {}".
                             format(self.device.name, mode))
        self.device.switch_power.set_mode("sync", 1)
        time.sleep(5)
        mode = self.device.switch_power.get_mode(1)
        asserts.assert_equal(mode, "sync", "{} expected usb_hub mode to be 'sync' found: {}".
                             format(self.device.name, mode))

    def test_5805_set_and_get_all_ports_mode(self):
        """Verify that setting and getting all ports works as expected."""
        self.device.switch_power.set_all_ports_mode("off")
        time.sleep(5)
        mode_list = self.device.switch_power.get_all_ports_mode()
        valid_result = ['', 'off']
        result = all(mode in valid_result for mode in mode_list)
        if not result:
            asserts.fail("{} All ports were expected to be 'off', found: {}".
                         format(self.device.name, mode_list))
        self.device.switch_power.set_all_ports_mode("sync")
        time.sleep(5)
        mode_list = self.device.switch_power.get_all_ports_mode()
        valid_result = ['', 'sync']
        result = all(mode in valid_result for mode in mode_list)
        if not result:
            asserts.fail("{} All ports were expected to be 'sync', found: {}".
                         format(self.device.name, mode_list))

    def test_5805_power_off_and_on(self):
        """Verify that setting the power mode with power_on and Power_off works as expected."""
        self.device.switch_power.power_off(1)
        time.sleep(5)
        mode = self.device.switch_power.get_mode(1)
        asserts.assert_equal(mode, "off", "{} expected usb_hub mode to be 'off' found: {}".
                             format(self.device.name, mode))
        self.device.switch_power.power_on(1)
        time.sleep(5)
        mode = self.device.switch_power.get_mode(1)
        asserts.assert_equal(mode, "sync", "{} expected usb_hub mode to be 'sync' found: {}".
                             format(self.device.name, mode))


if __name__ == "__main__":
    gdm_test_base.main()
