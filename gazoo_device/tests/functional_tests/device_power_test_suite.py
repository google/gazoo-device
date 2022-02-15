# Copyright 2022 Google LLC
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
import logging
from typing import Type
from gazoo_device.tests.functional_tests.utils import gdm_test_base
from mobly import asserts


class DevicePowerTestSuite(gdm_test_base.GDMTestBase):
  """Test suite for the device_power capability."""

  @classmethod
  def is_applicable_to(cls, device_type: str,
                       device_class: Type[gdm_test_base.DeviceType],
                       device_name: str) -> bool:
    """Determine if this test suite can run on the given device."""
    if not device_class.has_capabilities(["device_power"]):
      return False
    props = ["device_power.hub_name", "device_power.port_number"]
    return cls.check_properties_set(device_name, props)

  @classmethod
  def requires_pairing(cls) -> bool:
    """Returns True if the device must be paired to run this test suite."""
    return False

  def test_device_power_on_off(self):
    """Verifies on() and off() methods work."""
    original_mode = self.device.device_power.port_mode

    try:
      self.device.device_power.off()
      asserts.assert_equal(
          self.device.device_power.port_mode, "off",
          f"{self.device.name} port {self.device.device_power.port_number} "
          "should have been set to off")
      self.device.device_power.on()
      on_modes = ["on", "charge", "sync"]
      asserts.assert_in(
          self.device.device_power.port_mode, on_modes,
          f"{self.device.name} port {self.device.device_power.port_number} "
          f"should have been set to one of {on_modes}")

    finally:
      if original_mode == "off":
        logging.info(
            "Restoring device power back to its original mode 'off'")
        self.device.device_power.off()


if __name__ == "__main__":
  gdm_test_base.main()
