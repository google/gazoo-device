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
from unittest import mock

import gazoo_device
from gazoo_device.auxiliary_devices import esp32_pigweed_locking
from gazoo_device.tests.unit_tests.utils import fake_device_test_case


_PWRPC_COMMON_CLASS = (
    gazoo_device.capabilities.pwrpc_common_default.PwRPCCommonDefault)
_FAKE_FW_VERSION = "0"


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

  @mock.patch.object(
      _PWRPC_COMMON_CLASS, "software_version", new_callable=mock.PropertyMock)
  def test_001_firmware_version(self, mock_fw_version):
    """Verifies the firmware_version."""
    mock_fw_version.return_value = _FAKE_FW_VERSION
    self.assertEqual(_FAKE_FW_VERSION, self.uut.firmware_version)
    self.assertEqual(1, mock_fw_version.call_count)

  @mock.patch.object(_PWRPC_COMMON_CLASS, "reboot")
  def test_002_reboot(self, mock_reboot):
    """Verifies the reboot method."""
    self.uut.reboot()
    self.assertEqual(1, mock_reboot.call_count)

  @mock.patch.object(_PWRPC_COMMON_CLASS, "factory_reset")
  def test_003_factory_reset(self, mock_factory_reset):
    """Verifies the factory_reset method."""
    self.uut.factory_reset()
    self.assertEqual(1, mock_factory_reset.call_count)

  def test_004_common_rpc_capability(self):
    """Verify the initialization of pw_rpc_common capability."""
    self.assertTrue(self.uut.pw_rpc_common)

  def test_005_locking_rpc_capability(self):
    """Verifies the initialization of pw_rpc_lock capability."""
    self.assertTrue(self.uut.pw_rpc_lock)


if __name__ == "__main__":
  fake_device_test_case.main()
