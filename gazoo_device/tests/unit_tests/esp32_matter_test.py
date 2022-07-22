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

"""Unit tests for device class Esp32Matter."""
import unittest
from gazoo_device.capabilities import flash_build_esptool
from gazoo_device.primary_devices import esp32_matter
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_FAKE_DEVICE_ID = "esp32matter-1234"
_FAKE_DEVICE_ADDRESS = "fake-device-address"


class Esp32MatterTests(fake_device_test_case.FakeDeviceTestCase):
  """Unit tests for device class Esp32Matter."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements(_FAKE_DEVICE_ID)
    self.device_config["persistent"]["console_port_name"] = _FAKE_DEVICE_ADDRESS
    self.uut = esp32_matter.Esp32Matter(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory)

  def test_os_attribute(self):
    """Verifies the os attribute."""
    self.assertEqual("FreeRTOS", self.uut.os)

  def test_platform_attribute(self):
    """Verfies the platform attribute."""
    self.assertEqual("ESP32", self.uut.platform)

  def test_pw_rpc_wifi_capability(self):
    """Verifies the initialization of pw_rpc_wifi capability."""
    self.assertIsNotNone(self.uut.pw_rpc_wifi)

  @unittest.skipIf(not flash_build_esptool._ESPTOOL_AVAILABLE,
                   "esptool is not installed")
  def test_flash_build_capability(self):
    """Verifies the initialization of flash_build capability."""
    self.assertIsNotNone(self.uut.flash_build)


if __name__ == "__main__":
  fake_device_test_case.main()
