# Copyright 2021 Google LLC
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

"""Unit tests for device class ESP32PigweedLocking."""
from gazoo_device.auxiliary_devices import esp32_pigweed_locking
from gazoo_device.tests.unit_tests.utils import fake_device_test_case


class ESP32PigweedLockingTests(fake_device_test_case.FakeDeviceTestCase):
  """Test module for device class ESP32PigweedLocking."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements("esp32pigweedlocking-1234")
    self.device_config["persistent"]["console_port_name"] = "/dev/bus/usb/01/02"
    self.uut = esp32_pigweed_locking.ESP32PigweedLocking(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory)

  def test_001_firmware_version(self):
    """Verifies the initialization of pw_rpc_lock capability."""
    self.assertEqual("NOT_IMPLEMENTED", self.uut.firmware_version)

  def test_002_locking_rpc_capability(self):
    """Verifies the initialization of pw_rpc_lock capability."""
    self.assertTrue(self.uut.pw_rpc_lock)


if __name__ == "__main__":
  fake_device_test_case.main()
