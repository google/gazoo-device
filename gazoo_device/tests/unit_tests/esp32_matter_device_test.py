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

"""Unit tests for base class Esp32MatterDevice."""
from unittest import mock

from gazoo_device import console_config
from gazoo_device import errors
from gazoo_device.base_classes import esp32_matter_device
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
import immutabledict


_FAKE_DEVICE_ID = "esp32matterdevicestub-detect"
_FAKE_DEVICE_ADDRESS = "fake-device-address"
_FAKE_FIRMWARE_VERSION = "fake-firmware-version"
_FAKE_COMMAND = "fake-command"
_ESP32_CONNECT_PERSISTENT_PROPERTIES = immutabledict.immutabledict({
    "os": "FreeRTOS",
    "platform": "ESP32",
    "serial_number": "FT2BSR6O",
    "name": "esp32matterdevicestub_detect",
    "device_type": "esp32matterdevicestub",
})


class Esp32MatterDeviceStub(esp32_matter_device.Esp32MatterDevice):
  """Dummy implementation for instantiation of Esp32MatterDevice."""
  DEVICE_TYPE = "esp32matterdevicestub"


class Esp32MatterDeviceTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit tests for base class Esp32MatterDevice."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements(_FAKE_DEVICE_ID)
    self.device_config["persistent"]["console_port_name"] = _FAKE_DEVICE_ADDRESS
    self.uut = Esp32MatterDeviceStub(self.mock_manager,
                                     self.device_config,
                                     log_directory=self.artifacts_directory)

  @mock.patch.object(console_config, "get_log_only_configuration")
  def test_001_get_console_configuration_on_success(self, mock_console_config):
    """Verifies get_console_configuration on success."""
    config = self.uut.get_console_configuration()
    self.assertIsNotNone(config)

  def test_002_get_detection_info_on_success(self):
    """Verifies persistent properties are set correctly."""
    self._test_get_detection_info(
        console_port_name=_FAKE_DEVICE_ADDRESS,
        device_class=Esp32MatterDeviceStub,
        persistent_properties=_ESP32_CONNECT_PERSISTENT_PROPERTIES)

  @mock.patch.object(esp32_matter_device.os.path, "exists", return_value=True)
  def test_003_is_connected_true(self, mock_exists):
    """Verifies is_connected returns true when console port exists."""
    self.assertTrue(
        esp32_matter_device.Esp32MatterDevice.is_connected(self.device_config))
    mock_exists.assert_called_once()

  @mock.patch.object(
      esp32_matter_device.Esp32MatterDevice, "pw_rpc_common")
  def test_004_get_firmware_version_on_success(self, mock_rpc_common):
    """Verifies get firmware_version on success."""
    mock_rpc_common.software_version = _FAKE_FIRMWARE_VERSION
    self.assertEqual(self.uut.firmware_version, _FAKE_FIRMWARE_VERSION)

  @mock.patch.object(
      esp32_matter_device.Esp32MatterDevice, "pw_rpc_common")
  def test_005_reboot_on_success(self, mock_rpc_common):
    """Verifies reboot on success."""
    self.uut.reboot()
    mock_rpc_common.reboot.assert_called_once()

  @mock.patch.object(
      esp32_matter_device.Esp32MatterDevice, "pw_rpc_common")
  def test_006_factory_reset_on_success(self, mock_rpc_common):
    """Verifies factory reset on success."""
    self.uut.factory_reset()
    mock_rpc_common.factory_reset.assert_called_once()

  def test_007_common_rpc_capability(self):
    """Verifies the initialization of pw_rpc_common capability."""
    self.assertTrue(self.uut.pw_rpc_common)

  def test_008_shell_not_implemented(self):
    """Verifies the shell method not implemented."""
    error_regex = "shell not implemented for ESP32 Matter device."
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.shell(command=_FAKE_COMMAND)

  @mock.patch.object(
      esp32_matter_device.Esp32MatterDevice, "pw_rpc_common")
  def test_009_wait_for_bootup_complete_not_implemented(self, mock_rpc_common):
    """Verifies the wait_for_bootup_complete not implemented."""
    self.uut.wait_for_bootup_complete()
    mock_rpc_common.wait_for_bootup_complete.assert_called_once()


if __name__ == "__main__":
  fake_device_test_case.main()
