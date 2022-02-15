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

"""Unit test for device class Esp32MatterAllclusters."""
from gazoo_device.primary_devices import esp32_matter_allclusters
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_FAKE_DEVICE_ID = "esp32matterallclusters-1234"
_FAKE_DEVICE_ADDRESS = "/dev/bus/usb/01/02"


class Esp32MatterAllclustersTests(fake_device_test_case.FakeDeviceTestCase):
  """Unit tests for device class Esp32MatterAllclusters."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements(_FAKE_DEVICE_ID)
    self.device_config["persistent"]["console_port_name"] = _FAKE_DEVICE_ADDRESS
    self.uut = esp32_matter_allclusters.Esp32MatterAllclusters(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory)

  def test_button_rpc_capability(self):
    """Verifies the initialization of pw_rpc_button capability."""
    self.assertIsNotNone(self.uut.pw_rpc_button)

  def test_wifi_rpc_capability(self):
    """Verifies the initialization of pw_rpc_wifi capability."""
    self.assertIsNotNone(self.uut.pw_rpc_wifi)

  def test_on_off_light_endpoint(self):
    """Verifies the initialization of on_off_light endpoint."""
    self.assertIsNotNone(self.uut.on_off_light)

  def test_color_temperature_light_endpoint(self):
    """Verifies the initialization of color_temperature_light endpoint."""
    self.assertIsNotNone(self.uut.color_temperature_light)


if __name__ == "__main__":
  fake_device_test_case.main()
