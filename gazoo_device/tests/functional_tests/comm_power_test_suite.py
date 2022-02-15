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

"""This test suite verifies comm_power capability."""
import logging
from typing import Type
from gazoo_device.tests.functional_tests.utils import gdm_test_base
from mobly import asserts

_ON = "on"
_OFF = "off"


class FakeManagerEthernetSwitch():
  """Mock of ManagedEthernetSwitch."""

  def __init__(self):
    self.port_modes = {}

  def get_port_status(self, port):
    """Returns the status of the ethernet port."""
    return self.port_modes.setdefault(port, _OFF)

  def turn_on_port(self, port):
    """Turns the ethernet port on."""
    self.port_modes[port] = _ON

  def turn_off_port(self, port):
    """Turns the ethernet port off."""
    self.port_modes[port] = _OFF


class CommPowerTestSuite(gdm_test_base.GDMTestBase):
  """Functional test suite for the comm_power capability."""

  @classmethod
  def is_applicable_to(cls, device_type: str,
                       device_class: Type[gdm_test_base.DeviceType],
                       device_name: str) -> bool:
    """Determine if this test suite can run on the given device."""
    if not device_class.has_capabilities(["comm_power"]):
      return False
    props = ["comm_power.hub_name", "comm_power.port_number"]
    return cls.check_properties_set(device_name, props)

  @classmethod
  def requires_pairing(cls) -> bool:
    """Returns True if the device must be paired to run this test suite."""
    return False

  def setup_test(self):
    """Called at the beginning of each test."""
    super().setup_test()
    if self.device.comm_power.hub_type == "ethernet_switch":
      self.device.ethernet_switch = FakeManagerEthernetSwitch()

  def test_comm_power_on_and_off(self):
    """Verifies comm_power methods on and off work."""
    original_mode = self.device.comm_power.port_mode
    # pylint: disable=protected-access
    if self.device.comm_power._power_and_data_share_cable:
      expected_mode_off = "charge"
    else:
      expected_mode_off = "off"
    # pylint: enable=protected-access

    try:
      self.device.comm_power.off()
      asserts.assert_equal(
          self.device.comm_power.port_mode, expected_mode_off,
          f"{self.device.name} port {self.device.comm_power.port_number} "
          f"should have been set to {expected_mode_off}")

      self.device.comm_power.on()
      asserts.assert_in(
          self.device.comm_power.port_mode, ["sync", "on"],
          f"{self.device.name} port {self.device.comm_power.port_number} "
          "should have been set to 'on' or 'sync' but is "
          f"{self.device.comm_power.port_mode}")

    finally:
      if self.device.comm_power.port_mode != original_mode:
        logging.info(
            "Restoring device communication power back to its "
            "original mode %r", original_mode)
        if original_mode in ["off", "charge"]:
          self.device.comm_power.off()
        else:
          self.device.comm_power.on()


if __name__ == "__main__":
  gdm_test_base.main()
