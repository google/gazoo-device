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
  python3 mobly_example_test.py -c ~/gazoo/testbeds/One-Somedevice.yml

See README.md for more details.
"""
import logging
import os
import sys
from typing import List

import gazoo_device
from mobly import asserts
from mobly import base_test
from mobly import test_runner

# If using a device controller from an extension package:
# import my_extension_package
# gazoo_device.register(my_extension_package)

_GAZOO_DEVICE_CONTROLLER = "GazooDevice"


class MoblyExampleRebootTest(base_test.BaseTestClass):
  """Example reboot device test with GDM + Mobly."""

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.manager = None
    self.devices = []

  def setup_class(self):
    """Creates a Manager instance."""
    super().setup_class()
    self.manager = gazoo_device.Manager(
        log_directory=self.log_path,
        gdm_log_file=os.path.join(self.log_path, "gdm.log"),
        # Avoid log duplication with Mobly's stdout log handler
        stdout_logging=False)

  def teardown_class(self):
    """Closes the Manager instance."""
    self.manager.close()
    self.manager = None
    super().teardown_class()

  def setup_test(self):
    """Creates device controllers for all devices in the testbed."""
    super().setup_test()
    gazoo_device_names = self._get_gazoo_device_names()
    self.devices = [self.manager.create_device(device_name)
                    for device_name in gazoo_device_names]
    logging.info("Created devices for test: %s",
                 [device.name for device in self.devices])

  def teardown_test(self):
    """Closes all device controllers."""
    for device in self.devices:
      device.close()
    self.devices = []
    super().teardown_test()

  def _get_gazoo_device_names(self) -> List[str]:
    """Extracts names of Gazoo devices from the testbed.

    Raises:
      RuntimeError: If the testbed config does not contain any "GazooDevice"
        controller entries.

    Returns:
      Names of all GazooDevices in the testbed.
    """
    gazoo_device_configs = self.controller_configs.get(
        _GAZOO_DEVICE_CONTROLLER, [])
    gazoo_device_names = [config["id"] for config in gazoo_device_configs]
    if not gazoo_device_names:
      raise RuntimeError(
          f"The testbed config does not have any {_GAZOO_DEVICE_CONTROLLER} "
          "controller entries")
    return gazoo_device_names

  def test_reboot(self):
    """Reboots all devices in the testbed."""
    for device in self.devices:
      device.reboot()
      asserts.assert_true(
          device.connected,
          f"Device {device.name} did not come back online after reboot")


if __name__ == "__main__":
  test_runner.main()
