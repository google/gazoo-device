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

"""This test suite verifies switch_power_dli_powerswitch capability."""

from mobly import asserts
from functional_tests import gdm_test_base


class SwitchPowerDliPowerswitchTestSuite(gdm_test_base.GDMTestBase):
    """Functional tests for the powerswitch_power capability."""

    @classmethod
    def is_applicable_to(cls, device_type, device_class, device_name):
        """Determine if this test suite can run on the given device."""
        if not device_class.has_capabilities(["switch_power"]):
            return False
        flavor = str(device_class.switch_power.capability_classes).split(".")[-2]
        return flavor == 'switch_power_dli_powerswitch'

    @classmethod
    def requires_pairing(cls):
        """Returns True if the device in the testbed must be paired to run this test suite."""
        return False

    def test_3112_verify_power_on_power_off(self):
        """Verifies power_on and power_off works."""
        original_mode = self.device.switch_power.get_mode(port=0)
        try:
            self.device.switch_power.power_off(port=0)
            asserts.assert_equal(self.device.switch_power.get_mode(port=0), "off",
                                 '{} port {} should have been set to {}'.format(
                                     self.device.name, '0', 'off'))
            self.device.switch_power.power_on(port=0)
            asserts.assert_equal(self.device.switch_power.get_mode(port=0), "on",
                                 '{} port {} should have been set to {}'.format(
                                     self.device.name, '0', 'on'))

        finally:
            self.logger.info("set the powerswitch power back to the "
                             "original mode: {}".format(original_mode))
            if original_mode == "on":
                self.device.switch_power.power_on(port=0)
            else:
                self.device.switch_power.power_off(port=0)

    def test_3113_verify_set_all_port_mode(self):
        """Verifies set_all_ports_mode works."""
        original_mode = self.device.switch_power.get_all_ports_mode()
        try:
            expectant_value = ['on', 'on', 'on', 'on', 'on', 'on', 'on', 'on']
            self.device.switch_power.set_all_ports_mode("on")
            asserts.assert_equal(self.device.switch_power.get_all_ports_mode(),
                                 expectant_value,
                                 '{} expected to set port values to {} but got {}'.format(
                                     self.device.name,
                                     expectant_value,
                                     self.device.switch_power.get_all_ports_mode()))

        finally:
            self.logger.info("set the powerswitch power back to the "
                             "original mode: {}".format(original_mode))
            for indx, mode in enumerate(original_mode):
                if "on" in mode:
                    self.device.switch_power.power_on(port=indx)
                else:
                    self.device.switch_power.power_off(port=indx)

    def test_3114_verify_set_mode(self):
        """Verifies set_mode works."""
        original_mode = self.device.switch_power.get_mode(port=0)
        try:
            self.device.switch_power.set_mode(mode="off", port=0)
            asserts.assert_equal(self.device.switch_power.get_mode(port=0), "off",
                                 '{} port {} should have been set to {}'.format(
                                     self.device.name, '0', 'off'))
            self.device.switch_power.set_mode(mode="on", port=0)
            asserts.assert_equal(self.device.switch_power.get_mode(port=0), "on",
                                 '{} port {} should have been set to {}'.format(
                                     self.device.name, '0', 'on'))

        finally:
            self.logger.info("set the powerswitch power back to the "
                             "original mode: {}".format(original_mode))
            if original_mode == "on":
                self.device.switch_power.power_on(port=0)
            else:
                self.device.switch_power.power_off(port=0)


if __name__ == "__main__":
    gdm_test_base.main()
