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

"""This test suite verifies comm_power_cambrionix capability."""
from mobly import asserts
from functional_tests import gdm_test_base


class CommPowerCambrionixTestSuite(gdm_test_base.GDMTestBase):
    """Functional test suite for the Cambrionix flavor of comm_power capability."""

    @classmethod
    def is_applicable_to(cls, device_type, device_class, device_name):
        """Determine if this test suite can run on the given device."""
        return device_class.has_capabilities(["comm_power_cambrionix"])

    @classmethod
    def requires_pairing(cls):
        """Returns True if the device in the testbed must be paired to run this test suite."""
        return False

    def test_comm_power_on_and_off(self):
        """Verifies comm_power methods on and off work."""
        self.test_port = self._get_port()
        original_mode = self._get_port_state()

        try:
            self.device.comm_power.off()
            if self.device.comm_power._power_and_data_share_cable:
                asserts.assert_equal(self._get_port_state(), "charge",
                                     f'{self.device.name} port {self.test_port} should have been '
                                     'set to charge')
            else:
                asserts.assert_equal(self._get_port_state(), "off",
                                     f'{self.device.name} port {self.test_port} should have been '
                                     'set to off')
            self.device.comm_power.on()
            asserts.assert_equal(self._get_port_state(), "on",
                                 f'{self.device.name} port {self.test_port} should have been '
                                 'set to on')
        finally:
            if self._get_port_state() != original_mode:
                if original_mode == "off" or original_mode == "charge":
                    self.logger.info('Restoring device communication power back to its '
                                     f'original mode of {original_mode}.')
                    self.device.comm_power.off()
                else:
                    self.device.comm_power.on()

    def _get_port(self):
        """Returns device port."""
        return self.device.comm_power._data_usb_port

    def _get_port_state(self):
        """Returns port state."""
        port_mode = self.device.comm_power._cambrionix.switch_power.get_mode(self.test_port)
        if port_mode == 'sync':
            port_mode = 'on'
        return port_mode


if __name__ == "__main__":
    gdm_test_base.main()
