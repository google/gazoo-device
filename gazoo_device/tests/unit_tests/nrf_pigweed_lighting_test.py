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

"""Unit tests for device class NRFPigweedLighting."""
from unittest import mock

from gazoo_device.auxiliary_devices import nrf_pigweed_lighting
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_FAKE_DEVICE_ID = "efr32pigweedlighting-1234"
_FAKE_DEVICE_ADDRESS = "/dev/bus/usb/01/02"
_FAKE_FIRMWARE_VERSION = "0"


class NRFPigweedLightingTests(fake_device_test_case.FakeDeviceTestCase):
  """Test module for device class NRFPigweedLighting."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements(_FAKE_DEVICE_ID)
    self.device_config["persistent"]["console_port_name"] = _FAKE_DEVICE_ADDRESS
    self.uut = nrf_pigweed_lighting.NRFPigweedLighting(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory)

  def test_001_create_nrfpigweedlighting_device(self):
    """Verifies create_device works as expected."""
    self.assertIsNotNone(self.uut)

  def test_002_lighting_rpc_capability(self):
    """Verifies the initialization of pw_rpc_light capability."""
    self.assertTrue(self.uut.pw_rpc_light)

  def test_003_common_rpc_capability(self):
    """Verifies the initialization of pw_rpc_common capability."""
    self.assertTrue(self.uut.pw_rpc_common)

  def test_004_button_rpc_capability(self):
    """Verifies the initialization of pw_rpc_button capability."""
    self.assertTrue(self.uut.pw_rpc_button)

  @mock.patch.object(
      nrf_pigweed_lighting.NRFPigweedLighting, "pw_rpc_common")
  def test_005_firmware_version(self, mock_rpc_common):
    """Verifies the firmware_version method."""
    mock_rpc_common.software_version = _FAKE_FIRMWARE_VERSION
    self.assertEqual(self.uut.firmware_version, _FAKE_FIRMWARE_VERSION)

  @mock.patch.object(
      nrf_pigweed_lighting.NRFPigweedLighting, "pw_rpc_common")
  def test_006_reboot(self, mock_rpc_common):
    """Verifies the reboot method."""
    self.uut.reboot()
    self.assertEqual(1, mock_rpc_common.reboot.call_count)

  @mock.patch.object(
      nrf_pigweed_lighting.NRFPigweedLighting, "pw_rpc_common")
  def test_007_factory_reset(self, mock_rpc_common):
    """Verifies the factory_reset method."""
    self.uut.factory_reset()
    self.assertEqual(1, mock_rpc_common.factory_reset.call_count)


if __name__ == "__main__":
  fake_device_test_case.main()
