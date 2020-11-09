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

"""This test suite verifies device_power capability."""
from gazoo_device import manager
from mobly import asserts
from functional_tests import gdm_test_base


class DevicePowerTestSuite(gdm_test_base.GDMTestBase):
    """Test suite for the device_power capability."""

    @classmethod
    def is_applicable_to(cls, device_type, device_class, device_name):
        """Determine if this test suite can run on the given device."""
        if not device_class.has_capabilities(["device_power"]):
            return False
        props = ['device_power.hub_name', 'device_power.port_number']
        return cls.check_properties_set(device_name, props)

    @classmethod
    def requires_pairing(cls):
        """Returns True if the device in the testbed must be paired to run this test suite."""
        return False

    def test_device_power_on_off(self):
        """Verifies on and off works."""
        original_mode = self.device.device_power.port_mode

        try:
            self.device.device_power.off()
            asserts.assert_equal(self.device.device_power.port_mode, "off",
                                 f'{self.device.name} port {self.device.device_power.port_number} should have been set to off')
            self.device.device_power.on()
            asserts.assert_true(self.device.device_power.port_mode in ["on", "charge", "sync"],
                                f'{self.device.name} port {self.device.device_power.port_number} should have been set to on')
        finally:
            if original_mode == "off":
                self.logger.info("restoring device power back to its original mode of off")
                self.device.device_power.off()


if __name__ == "__main__":
    gdm_test_base.main()
