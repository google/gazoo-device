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

"""Example reboot device test with GDM + Mobly.

Usage:
  python3 mobly_example_test.py -c ~/gazoo/testbeds/One-Raspberrypi.yml

See README.md for more details.
"""
import os
import sys

from gazoo_device import device_types
from gazoo_device import package_registrar
# Use Raspberry Pi as an example. This can be any GDM device module.
from gazoo_device.auxiliary_devices import raspberry_pi
from mobly import asserts
from mobly import base_test
from mobly import test_runner


class MoblyExampleRebootTest(base_test.BaseTestClass):
  """Example reboot device test with GDM + Mobly."""
  devices: list[device_types.Device]

  def setup_class(self):
    """Creates a Manager instance."""
    super().setup_class()
    # Register the device class under test.
    package_registrar.register(raspberry_pi)
    self.devices = self.register_controller(raspberry_pi)

  def test_reboot(self):
    """Reboots all devices in the testbed."""
    for device in self.devices:
      device.reboot()
      asserts.assert_true(
          device.connected,
          f"Device {device.name} did not come back online after reboot")


if __name__ == "__main__":
  test_runner.main()
