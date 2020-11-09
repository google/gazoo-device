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

"""Test suite for ethernet_switch_api capability.

Requires a testbed with a device with an "ethernet_switch_api" capability and a managed Ethernet
Switch.
"""
from __future__ import absolute_import
import traceback
from mobly import asserts
from functional_tests import gdm_test_base
from managed_ethernet_switch import managed_ethernet_switch
from gazoo_device import manager

REQUIRED_OPTIONAL_PROPERTIES = ["ethernet_switch_ip", "ethernet_switch_port"]


class EthernetSwitchApiCapabilityTests(gdm_test_base.GDMTestBase):
    """Test suite for ethernet_switch_api capability."""

    @classmethod
    def is_applicable_to(cls, device_type, device_class, device_name):
        """Determine if this test suite can run on the given device."""
        return (device_class.has_capabilities(["ethernet_switch_api"])
                and cls.check_properties_set(device_name, REQUIRED_OPTIONAL_PROPERTIES))

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

    def test_100_ethernet_switch_api(self):
        """test case for enable(), disable() and status"""
        if self.device.ethernet_switch_api.status:
            self._test_100_disable()
            self._test_100_enable()
        else:
            self._test_100_enable()

    def _test_100_enable(self):
        """Test case for enable()"""
        try:
            self.device.ethernet_switch_api.enable()
            asserts.assert_true(self.device.ethernet_switch_api.status, "status should be True")
        except Exception:
            traceback_message = traceback.format_exc()
            asserts.fail("Error happened during lock: " + traceback_message)

    def _test_100_disable(self):
        """Test case for disable()"""
        try:
            self.device.ethernet_switch_api.disable()
            asserts.assert_false(self.device.ethernet_switch_api.status, "status should be False")
        except Exception:
            traceback_message = traceback.format_exc()
            asserts.fail("Error happened during unlock: " + traceback_message)


if __name__ == "__main__":
    gdm_test_base.main()
