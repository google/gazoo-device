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

"""Unit tests for esp32 module."""
from gazoo_device import errors
from gazoo_device.auxiliary_devices import esp32
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
import immutabledict


_MOCK_ESP32_ADDRESS = "/dev/bus/usb/001/002"
_ESP32_PERSISTENT_PROPERTIES = immutabledict.immutabledict({
    "os": "FreeRTOS",
    "platform": "ESP32",
    "serial_number": "FT2BSR6O",
    "name": "esp32_detect",
    "device_type": "esp32",
})


class ESP32DeviceTests(fake_device_test_case.FakeDeviceTestCase):
  """Unit tests for base class ESP32."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements("esp32-detect")
    self.device_config["persistent"]["console_port_name"] = _MOCK_ESP32_ADDRESS
    self.uut = esp32.ESP32(self.mock_manager,
                           self.device_config,
                           log_directory=self.artifacts_directory)

  def test_001_esp32_attributes(self):
    """Verify esp32 attributes."""
    self._test_get_detection_info(_MOCK_ESP32_ADDRESS,
                                  esp32.ESP32,
                                  _ESP32_PERSISTENT_PROPERTIES)

  def test_002_recover(self):
    """Verify recover method."""
    with self.assertRaises(errors.DeviceError):
      self.uut.recover(errors.CheckDeviceReadyError(self.uut.name, "error"))

  def test_003_switchboard(self):
    """Verify the inactive switchboard in esp32."""
    with self.assertRaises(errors.DeviceError):
      self.uut.switchboard.send()


if __name__ == "__main__":
  fake_device_test_case.main()
