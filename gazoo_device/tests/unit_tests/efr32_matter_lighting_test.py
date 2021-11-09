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

"""Unit tests for device class Efr32MatterLighting."""
from gazoo_device.primary_devices import efr32_matter_lighting
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_FAKE_DEVICE_ID = "efr32matterlighting-1234"
_FAKE_DEVICE_ADDRESS = "fake-device-address"


class Efr32MatterLightingTests(fake_device_test_case.FakeDeviceTestCase):
  """Unit tests for device class Efr32MatterLighting."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements(_FAKE_DEVICE_ID)
    self.device_config["persistent"]["console_port_name"] = _FAKE_DEVICE_ADDRESS
    self.uut = efr32_matter_lighting.Efr32MatterLighting(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory)

  def test_001_create_nrfmatterlighting_device(self):
    """Verifies create_device works as expected."""
    self.assertIsNotNone(self.uut)

  def test_002_button_rpc_capability(self):
    """Verifies the initialization of pw_rpc_button capability."""
    self.assertIsNotNone(self.uut.pw_rpc_button)

  def test_003_lighting_rpc_capability(self):
    """Verifies the initialization of pw_rpc_light capability."""
    self.assertIsNotNone(self.uut.pw_rpc_light)


if __name__ == "__main__":
  fake_device_test_case.main()
