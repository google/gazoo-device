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
"""Unit tests for m5stick module."""

from gazoo_device.auxiliary_devices import m5stick
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.tests.unit_tests.utils import fake_responder
import immutabledict

_FAKE_DEVICE_ID = "m5stick-detect"
_FAKE_DEVICE_ADDRESS = (
    "/dev/serial/by-id/usb-Hades2001_M5stack_FT2BSR6O-if00-port0")
_M5STICK_PERSISTENT_PROPERTIES = immutabledict.immutabledict({
    "os": "FreeRTOS",
    "platform": "ESP32",
    "serial_number": "FT2BSR6O",
    "name": "m5stick_detect",
    "device_type": "m5stick",
})


class M5StickDeviceTests(fake_device_test_case.FakeDeviceTestCase):
  """Unit tests for M5stick dev board."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements(_FAKE_DEVICE_ID)
    self.device_config["persistent"]["console_port_name"] = _FAKE_DEVICE_ADDRESS
    self.uut = m5stick.M5Stick(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory)

  def test_get_console_configuration(self):
    """Verifies m5stick get_console_configuration."""
    self.assertIsNotNone(self.uut.get_console_configuration())

  def test_m5stick_attributes(self):
    """Verifies m5stick attributes."""
    self._test_get_detection_info(_FAKE_DEVICE_ADDRESS, m5stick.M5Stick,
                                  _M5STICK_PERSISTENT_PROPERTIES)

  def test_switchboard_returns_valid_object(self):
    """Verifies a switchboard object is returned without error."""
    self.assertIsNotNone(self.uut.switchboard)

  def test_switchboard_send_and_expect(self):
    """Verifies send_and_expect method works on a switchboard."""
    expected_response = ("m5stick start pairing\n"
                         "m5stick enter discoverable mode\n"
                         "started")
    fake_responder_inst = fake_responder.FakeResponder(behavior_dict={
        "startFP\n": expected_response,
    })
    self.uut.switchboard.send_and_expect = fake_responder_inst.send_and_expect

    response = self.uut.switchboard.send_and_expect("startFP", ["(.*)"])

    self.assertEqual(response.match.group(1), expected_response)


if __name__ == "__main__":
  fake_device_test_case.main()
