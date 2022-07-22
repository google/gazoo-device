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

"""Unit tests for the raspberry_pi_matter module."""
from unittest import mock
from gazoo_device.primary_devices import raspberry_pi_matter
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.tests.unit_tests.utils import raspberry_pi_matter_controller_device_logs
import immutabledict

_FAKE_DEVICE_IP = "123.45.67.89"
_FAKE_SERIAL_NUMBER = "fake-serial-number"
_CONNECT_PERSISTENT_PROPERTIES = immutabledict.immutabledict({
    "console_port_name": _FAKE_DEVICE_IP,
    "serial_number": _FAKE_SERIAL_NUMBER,
    "name": "rpimatter-1234",
    "device_type": "rpimatter",
    "model": "PROTO",
    "wpan_mac_address": "123456"
})


class RaspberryPiMatterTests(fake_device_test_case.FakeDeviceTestCase):
  """Test for RaspberryPiMatter device controller."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements("rpimatter-1234")
    self.device_config["persistent"]["console_port_name"] = _FAKE_DEVICE_IP
    self.fake_responder.behavior_dict = (
        raspberry_pi_matter_controller_device_logs.DEFAULT_BEHAVIOR.copy())

    self.uut = raspberry_pi_matter.RaspberryPiMatter(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory)

  def test_os_attribute(self):
    """Verifies the os attribute."""
    self.assertEqual("Ubuntu", self.uut.os)

  def test_platform_attribute(self):
    """Verfies the platform attribute."""
    self.assertEqual("Raspberry Pi 4", self.uut.platform)

  @mock.patch.object(
      raspberry_pi_matter.RaspberryPiMatter,
      "shell_with_regex",
      return_value=_FAKE_SERIAL_NUMBER)
  def test_get_detection_info_on_success(self, mock_shell):
    """Verifies persistent properties are set correctly."""
    persistent_dict, _ = self.uut.get_detection_info()
    self.assertEqual(_CONNECT_PERSISTENT_PROPERTIES, persistent_dict)


if __name__ == "__main__":
  fake_device_test_case.main()
