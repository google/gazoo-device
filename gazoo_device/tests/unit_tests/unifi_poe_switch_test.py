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

"""Unit tests for unifi_poe_switch module."""
from unittest import mock

from gazoo_device import errors
from gazoo_device.auxiliary_devices import unifi_poe_switch
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.tests.unit_tests.utils import unifi_poe_switch_device_logs
from gazoo_device.utility import host_utils
import immutabledict


_PERSISTENT_PROPERTIES = immutabledict.immutabledict({
    "ip_address": "123.45.67.89",
    "total_ports": 8,
    "serial_number": "1234567890ab",
    "communication_address": "123.45.67.89",
    "model": "USW-8P-150",
})

_DYNAMIC_PROPERTIES = immutabledict.immutabledict({
    "firmware_version": "4.3.13.11253",
})


class UnifiPoeSwitchTests(fake_device_test_case.FakeDeviceTestCase):
  """Tests for unifi_poe_switch auxiliary device class."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements("unifi_switch-1234")
    self.device_config["persistent"]["console_port_name"] = "123.45.67.89"
    self.fake_responder.behavior_dict = (
        unifi_poe_switch_device_logs.DEFAULT_BEHAVIOR.copy())
    is_pingable_patcher = mock.patch.object(
        host_utils, "is_pingable", return_value=True)
    is_pingable_patcher.start()
    self.addCleanup(is_pingable_patcher.stop)
    self.uut = unifi_poe_switch.UnifiPoeSwitch(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory)

  def test_001_get_dynamic_properties(self):
    self.validate_dynamic_properties(_DYNAMIC_PROPERTIES)

  def test_002_get_detection_info_for_unifi_switch_device(self):

    self._test_get_detection_info(
        self.device_config["persistent"]["console_port_name"],
        device_class=unifi_poe_switch.UnifiPoeSwitch,
        persistent_properties=_PERSISTENT_PROPERTIES.copy())

  def test_004_is_connected_true(self):
    self.assertTrue(
        unifi_poe_switch.UnifiPoeSwitch.is_connected(self.device_config))

  @mock.patch.object(host_utils, "is_pingable", return_value=False)
  def test_005_is_connected_false(self, mock_is_pingable):
    self.assertFalse(
        unifi_poe_switch.UnifiPoeSwitch.is_connected(self.device_config))

  @mock.patch.object(
      host_utils, "is_pingable", side_effect=iter([True, False, False, True]))
  def test_007_reboot(self, mock_is_pingable):
    self.uut.reboot()
    self.assertEqual(mock_is_pingable.call_count, 4)

  @mock.patch.object(
      host_utils, "is_pingable", side_effect=iter([False, False, True]))
  def test_008_recover(self, mock_is_pingable):
    self.uut.recover(errors.DeviceNotResponsiveError(self.uut.name, ""))
    self.assertEqual(mock_is_pingable.call_count, 3)

  def test_008_recover_called_with_not_recoverable_exception(self):
    with self.assertRaisesRegex(errors.DeviceError, "Raise the test message"):
      self.uut.recover(errors.DeviceError("Raise the test message"))

  def test_009_check_telnet_connect_success(self):
    self.uut.check_device_ready()

  def test_009_check_telnet_connect_non_zero_return_code(self):
    self.fake_responder.behavior_dict = (
        unifi_poe_switch_device_logs.HEALTH_CHECK_FAILURE.copy())
    with self.assertRaisesRegex(errors.DeviceNotResponsiveError,
                                "failed to establish telnet connection"):
      self.uut.check_device_ready()


if __name__ == "__main__":
  fake_device_test_case.main()
