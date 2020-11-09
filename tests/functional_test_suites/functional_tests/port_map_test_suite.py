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

"""Test suite that verifies that PortMap is able to discover the device.

Warning: This test suite assumes that all devices with usb_hub capability are indeed attached
to a usb_hub.
"""
from __future__ import absolute_import
from mobly import asserts
from functional_tests import gdm_test_base


class PortMapTestSuite(gdm_test_base.GDMTestBase):
    """Functional tests for PortMap."""

    @classmethod
    def is_applicable_to(cls, device_type, device_class, device_name):
        """Determine if this test suite can run on the given device."""
        return device_class.has_capabilities(["usb_hub"])

    @classmethod
    def requires_pairing(cls):
        """Returns True if the device in the testbed must be paired to run this test suite."""
        return False

    def test_4500_port_map_finds_device(self):
        """Verifies the device is in the port map."""
        device_name = self.device.name
        port_map = self.manager.port_map()
        device_found = False
        for device_or_hub in port_map:
            if device_or_hub['hub_device']:
                for device in device_or_hub['port_list']:
                    if device and device_name in device['Discovered']:
                        device_found = True
            else:
                if device_name in device_or_hub['Discovered']:
                    device_found = True

        asserts.assert_true(device_found,
                            "device {} was not found by port-map.".format(device_name))


if __name__ == "__main__":
    gdm_test_base.main()
