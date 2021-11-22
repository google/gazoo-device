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

"""Capability unit test for pwrpc_common_default module."""
from unittest import mock
from gazoo_device import errors
from gazoo_device.capabilities import pwrpc_common_default
from gazoo_device.protos import device_service_pb2
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_FAKE_ACTION = "fake-action"
_FAKE_DEVICE_NAME = "matter_device"
_FAKE_VENDOR_ID = 1234
_FAKE_PRODUCT_ID = 5678
_FAKE_SOFTWARE_VERSION = 0
_FAKE_TIMEOUT = 5


class PwRPCCommonDefaultTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for PwRPCCommonDefault."""

  def setUp(self):
    super().setUp()
    self.add_time_mocks()
    self.switchboard_call_mock = mock.Mock()
    self.uut = pwrpc_common_default.PwRPCCommonDefault(
        device_name=_FAKE_DEVICE_NAME,
        switchboard_call=self.switchboard_call_mock,
        rpc_timeout_s=_FAKE_TIMEOUT)
    fake_device_info = device_service_pb2.DeviceInfo(
        vendor_id=_FAKE_VENDOR_ID,
        product_id=_FAKE_PRODUCT_ID,
        software_version=_FAKE_SOFTWARE_VERSION)
    self.fake_device_info_in_bytes = fake_device_info.SerializeToString()

  def test_001_get_static_info(self):
    """Verifies getting device static info successfully."""
    self.switchboard_call_mock.return_value = (True,
                                               self.fake_device_info_in_bytes)
    self.assertEqual(self.uut.vendor_id, _FAKE_VENDOR_ID)
    self.assertEqual(self.uut.product_id, _FAKE_PRODUCT_ID)
    self.assertEqual(self.uut.software_version, _FAKE_SOFTWARE_VERSION)
    self.assertEqual(3, self.switchboard_call_mock.call_count)

  def test_002_get_static_info_failed_false_ack(self):
    """Verifies getting device static info with failure of false ack."""
    self.switchboard_call_mock.return_value = (False, None)
    with self.assertRaises(errors.DeviceError):
      self.uut.vendor_id  # pylint: disable=pointless-statement
    self.switchboard_call_mock.assert_called_once()

  def test_003_get_static_info_failed_invalid_key(self):
    """Verifies getting device static info with failure of invalid key."""
    self.switchboard_call_mock.return_value = (True,
                                               self.fake_device_info_in_bytes)
    error_regex = "not_exist doesn't exist in static info."
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut._get_static_info("not_exist")
    self.switchboard_call_mock.assert_called_once()

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault, "wait_for_bootup_complete")
  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault, "_trigger_device_action")
  def test_004_reboot_on_success(self, mock_trigger, mock_wait):
    """Verifies reboot on success with verify=True."""
    self.uut.reboot()

    mock_trigger.assert_called_once_with(action="Reboot")
    mock_wait.assert_called_once()

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault, "wait_for_bootup_complete")
  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault, "_trigger_device_action")
  def test_005_factory_reset_on_success(self, mock_trigger, mock_wait):
    """Verifies factory-reset on success with verify=True."""
    self.uut.factory_reset()

    mock_trigger.assert_called_once_with(action="FactoryReset")
    mock_wait.assert_called_once()

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault, "_trigger_device_action")
  def test_006_ota_on_success(self, mock_trigger):
    """Verifies OTA on success."""
    self.uut.ota()

    mock_trigger.assert_called_once_with(action="TriggerOta")

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault, "_get_static_info")
  def test_007_wait_for_bootup_complete_on_success(self, mock_get_info):
    """Verifies wait_for_bootup_complete on success."""
    self.uut.wait_for_bootup_complete(bootup_timeout=_FAKE_TIMEOUT)

    mock_get_info.assert_called_once()

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault,
      "_get_static_info",
      side_effect=errors.DeviceError(""))
  def test_007_wait_for_bootup_complete_on_failure(self, mock_get_info):
    """Verifies wait_for_bootup_complete on failure."""
    fake_timeout_sec = 1
    error_regex = f"Failed to boot up within {fake_timeout_sec}s"
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.wait_for_bootup_complete(bootup_timeout=fake_timeout_sec)

  def test_008_trigger_device_actio_on_success(self):
    """Verifies _trigger_device_action on success."""
    self.switchboard_call_mock.return_value = True, None

    self.uut._trigger_device_action(action=_FAKE_ACTION)

    self.switchboard_call_mock.assert_called_once()

  def test_009_trigger_device_action_on_failure(self):
    """Verifies _trigger_device_action on failure."""
    self.switchboard_call_mock.return_value = False, None
    error_regex = f"triggering {_FAKE_ACTION} failed"

    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut._trigger_device_action(action=_FAKE_ACTION)


if __name__ == "__main__":
  fake_device_test_case.main()
