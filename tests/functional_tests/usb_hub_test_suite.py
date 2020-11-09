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

"""This test suite verifies usb hub related changes work as expected."""
from mobly import asserts
from functional_tests import gdm_test_base


class UsbHubTestSuite(gdm_test_base.GDMTestBase):
    """Functional tests for the usb_hub capability."""

    @classmethod
    def is_applicable_to(cls, device_type, device_class, device_name):
        """Determine if this test suite can run on the given device."""
        return (device_class.has_capabilities(["usb_hub"])
                and cls.check_properties_set(device_name, ["device_usb_hub_name"]))

    @classmethod
    def requires_pairing(cls):
        """Returns True if the device in the testbed must be paired to run this test suite."""
        return False

    def test_3110_verify_usb_state_after_close(self):
        """Verify that close does not change the usb port power mode."""
        current_state = self.device.usb_hub.get_device_power()
        self.device.close()
        asserts.assert_equal(
            self.device.usb_hub.get_device_power(), current_state,
            "Device USB hub port should be left in the same power state after the device is "
            "closed")


if __name__ == "__main__":
    gdm_test_base.main()
