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

"""Unit test for device class EFR32PigweedLighting."""
from gazoo_device.auxiliary_devices import efr32_pigweed_lighting
from gazoo_device.tests.unit_tests.utils import fake_device_test_case


class EFR32PigweedLightingTests(fake_device_test_case.FakeDeviceTestCase):
  """Test module for device class EFR32PigweedLighting."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements("efr32pigweedlighting-1234")
    self.device_config["persistent"]["console_port_name"] = "/dev/bus/usb/01/02"
    self.uut = efr32_pigweed_lighting.EFR32PigweedLighting(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory)

  def test_001_create_nrfpigweedlighting_device(self):
    """Verify create_device works as expected."""
    self.assertIsNotNone(self.uut)

  def test_002_lighting_rpc_capability(self):
    """Verify the initialization of pw_rpc_light capability."""
    self.assertTrue(self.uut.pw_rpc_light)

  def test_003_common_rpc_capability(self):
    """Verify the initialization of pw_rpc_common capability."""
    self.assertTrue(self.uut.pw_rpc_common)

  def test_004_button_rpc_capability(self):
    """Verify the initialization of pw_rpc_button capability."""
    self.assertTrue(self.uut.pw_rpc_button)


if __name__ == "__main__":
  fake_device_test_case.main()
