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

"""Unit tests for device class NrfMatter."""
from gazoo_device.primary_devices import nrf_matter
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_FAKE_DEVICE_ID = "nrfmatter-1234"
_FAKE_DEVICE_ADDRESS = "fake-device-address"


class NrfMatterTests(fake_device_test_case.FakeDeviceTestCase):
  """Unit tests for device class NrfMatter."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements(_FAKE_DEVICE_ID)
    self.device_config["persistent"]["console_port_name"] = _FAKE_DEVICE_ADDRESS
    self.uut = nrf_matter.NrfMatter(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory)

  def test_os_attribute(self):
    """Verifies the os attribute."""
    self.assertEqual("Zephyr RTOS", self.uut.os)

  def test_platform_attribute(self):
    """Verfies the platform attribute."""
    self.assertEqual("nRF Connect", self.uut.platform)

  def test_flash_build_capability(self):
    """Verifies the initialization of flash_build capability."""
    self.assertIsNotNone(self.uut.flash_build)


if __name__ == "__main__":
  fake_device_test_case.main()
