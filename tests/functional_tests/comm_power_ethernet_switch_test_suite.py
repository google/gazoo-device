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

"""This test suite verifies comm_power_ethernet_switch capability."""
from managed_ethernet_switch import managed_ethernet_switch
from mobly import asserts
from functional_tests import gdm_test_base

REQUIRED_OPTIONAL_PROPERTIES = ["ethernet_switch_ip", "ethernet_switch_port"]

class CommPowerEthernetSwitchTestSuite(gdm_test_base.GDMTestBase):
    """Functional test suite for the EthernetSwitch flavor of comm_power capability."""

    @classmethod
    def is_applicable_to(cls, device_type, device_class, device_name):
        """Determine if this test suite can run on the given device."""
        if device_class.has_capabilities(["comm_power"]):
            flavor = str(device_class.comm_power.capability_classes).split(".")[-2]
            if flavor == 'comm_power_ethernet_switch':
                return cls.check_properties_set(device_name, REQUIRED_OPTIONAL_PROPERTIES)
            else:
                return False
        else:
            return False

    @classmethod
    def requires_pairing(cls):
        """Returns True if the device in the testbed must be paired to run this test suite."""
        return False

    def setup_test(self):
        """Called at the beginning of each test"""
        super().setup_test()

        if not self.device.ethernet_switch:
            self.mes = managed_ethernet_switch.ManagedEthernetSwitch(
                switch_ip=self.device.ethernet_switch_ip)
            self.device.ethernet_switch = self.mes

    def test_comm_power_on_and_off(self):
        """Verifies comm_power methods on and off work."""
        self.test_port = self._get_port()
        original_mode = self._get_port_state()

        try:
            self.device.comm_power.off()
            asserts.assert_equal(self._get_port_state(), "off",
                                 f'{self.device.name} port {self.test_port} should have been '
                                 'set to off')
            self.device.comm_power.on()
            asserts.assert_equal(self._get_port_state(), "on",
                                 f'{self.device.name} port {self.test_port} should have been '
                                 'set to on')
        finally:
            if self._get_port_state() != original_mode:
                if original_mode == "off":
                    self.logger.info('Restoring device communication power back to its '
                                     f'original mode of {original_mode}.')
                else:
                    self.device.comm_power.on()

    def _get_port(self):
        """Returns device port."""
        return self.device.ethernet_switch_api.port

    def _get_port_state(self):
        """Returns port state."""
        return self.device.ethernet_switch_api.status


if __name__ == "__main__":
    gdm_test_base.main()
