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
"""dli_powerswitch.py unit tests."""
from unittest import mock

from gazoo_device.auxiliary_devices import dli_powerswitch
from gazoo_device.tests.unit_tests.utils import dli_powerswitch_logs
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.utility import host_utils
from gazoo_device.utility import http_utils
import immutabledict

_PERSISTENT_PROPERTIES = immutabledict.immutabledict({
    "console_port_name": "123.45.67.89",
    "device_type": "powerswitch",
    "model": "LPC9",
    "serial_number": "ABCD1234",
})


def _mock_command(*args, **kwargs):
  """Returns a http response object retrieved from dli_powerswitch device."""
  del kwargs  # Unused by the mock.
  data = dli_powerswitch_logs.DEFAULT_BEHAVIOR[args[0]]
  return _ResponseObject(data["text"], data["status_code"])


class _ResponseObject:
  """HTTP response container."""

  def __init__(self, text, status_code):
    self.text = text
    self.status_code = status_code


class PowerswitchTest(fake_device_test_case.FakeDeviceTestCase):
  """Powerswitch unit test class."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements("powerswitch-1234")
    self.device_config["persistent"]["console_port_name"] = "123.45.67.89"
    self.uut = dli_powerswitch.DliPowerSwitch(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory,
        log_file_name=None)

  def test_001_powerswitch_init(self):
    """Testing the creation of the powerswitch_device object."""
    self.assertTrue(
        self.uut,
        "The {} object failed to be created.".format("powerswitch_device"))

  @mock.patch.object(host_utils, "is_pingable", return_value=True)
  def test_002_is_connected_true(self, mock_ping):
    """Verify is_connected works as expected."""
    self.assertTrue(
        dli_powerswitch.DliPowerSwitch.is_connected(self.device_config))

  @mock.patch.object(http_utils, "send_http_get", side_effect=_mock_command)
  def test_003_get_detection_info(self, mock_http_get):
    """Verify get detection info works correctly."""
    self._test_get_detection_info(
        self.device_config["persistent"]["console_port_name"],
        dli_powerswitch.DliPowerSwitch, _PERSISTENT_PROPERTIES)

  @mock.patch.object(
      http_utils,
      "send_http_post",
      side_effect=RuntimeError("Failure calling HTTP post"))
  def test_006_write_command_failed_response(self, mock_http_post):
    """Verify exception raised when HTTP POST command returns an error."""
    with self.assertRaisesRegexp(RuntimeError, "Failure calling HTTP post"):
      self.uut._write_command("POST", "RAISE_EXCEPTION", headers={})

  @mock.patch.object(http_utils, "send_http_get", side_effect=_mock_command)
  def test_007_get_firmware(self, mock_http_get):
    """Verify the successful retrieval of device firmware version."""
    self.assertTrue(self.uut.firmware_version)

  @mock.patch.object(http_utils, "send_http_get", side_effect=_mock_command)
  def test_009_powerswitch_power_get_mode(self, mock_http_get):
    """Verify the powerswitch_power capability is initialized properly."""
    self.assertEqual(self.uut.powerswitch_power.get_mode(1), "on")

  @mock.patch.object(http_utils, "send_http_get", side_effect=_mock_command)
  def test_010_switch_power_get_mode(self, mock_http_get):
    """Verify the switch_power capability is initialized properly."""
    self.assertEqual(self.uut.switch_power.get_mode(1), "on")

  @mock.patch.object(host_utils, "is_pingable", return_value=True)
  def test_011_check_device_ready_success(self, mock_is_pingable):
    """Test check_device_ready() when all health checks pass."""
    self.uut.check_device_ready()


if __name__ == "__main__":
  fake_device_test_case.main()
