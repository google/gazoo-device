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

"""This test suite verifies the switch_power capability."""
import logging
from typing import Type

from gazoo_device.capabilities import switch_power_dli_powerswitch
from gazoo_device.tests.functional_tests.utils import gdm_test_base
from mobly import asserts


class SwitchPowerTestSuite(gdm_test_base.GDMTestBase):
  """Functional test suite for the switch_power capability."""

  @classmethod
  def is_applicable_to(cls, device_type: str,
                       device_class: Type[gdm_test_base.DeviceType],
                       device_name: str) -> bool:
    """Determine if this test suite can run on the given device."""
    return (device_class.has_capabilities(["switch_power"])
            and not device_class.has_capabilities(["switch_power_ethernet"]))

  @classmethod
  def requires_pairing(cls) -> bool:
    """Returns True if the device must be paired to run this test suite."""
    return False

  def setup_test(self):
    """Determines the switch 'on' state: 'sync' or 'on'."""
    super().setup_test()
    if "sync" in self.device.switch_power.supported_modes:
      self.on_state = "sync"
    else:
      self.on_state = "on"

  def test_switch_power_on_and_off(self):
    """Tests switch_power.power_on() and switch_power.power_off()."""
    original_mode = self.device.switch_power.get_mode(port=1)
    try:
      self.device.switch_power.power_off(port=1)
      asserts.assert_equal(
          self.device.switch_power.get_mode(port=1), "off",
          f"{self.device.name} port 1 should have been set to 'off'")
      self.device.switch_power.power_on(port=1)
      asserts.assert_equal(
          self.device.switch_power.get_mode(port=1), self.on_state,
          f"{self.device.name} port 1 should have been set to "
          f"{self.on_state!r}")

    finally:
      logging.info("Setting device power back to its original mode: %r",
                   original_mode)
      self.device.switch_power.set_mode(mode=original_mode, port=1)

  def test_switch_power_set_all_ports_mode(self):
    """Tests set_all_ports_mode() method."""
    original_mode = self.device.switch_power.get_all_ports_mode()
    try:
      expected_value = [self.on_state] * self.device.switch_power.total_ports
      self.device.switch_power.set_all_ports_mode(self.on_state)
      all_ports_mode = self.device.switch_power.get_all_ports_mode()
      asserts.assert_equal(
          all_ports_mode,
          expected_value,
          f"{self.device.name} expected to set port values to {expected_value} "
          f"but got {all_ports_mode}")

    finally:
      logging.info("Setting device power back to its original mode: %r",
                   original_mode)
      if isinstance(self.device.switch_power,
                    switch_power_dli_powerswitch.SwitchPowerDliPowerswitch):
        offset = 0
      else:
        offset = 1
      for index, mode in enumerate(original_mode):
        self.device.switch_power.set_mode(mode=mode, port=index+offset)

  def test_switch_power_set_mode(self):
    """Tests set_mode() method."""
    original_mode = self.device.switch_power.get_mode(port=1)
    try:
      self.device.switch_power.set_mode(mode="off", port=1)
      asserts.assert_equal(
          self.device.switch_power.get_mode(port=1), "off",
          f"{self.device.name} port 1 should have been set to off")
      self.device.switch_power.set_mode(mode=self.on_state, port=1)
      asserts.assert_equal(
          self.device.switch_power.get_mode(port=1), self.on_state,
          f"{self.device.name} port 1 should have been set to "
          f"{self.on_state!r}")
    finally:
      logging.info("Setting device power back to its original mode: %r",
                   original_mode)
      self.device.switch_power.set_mode(mode=original_mode, port=1)


if __name__ == "__main__":
  gdm_test_base.main()
