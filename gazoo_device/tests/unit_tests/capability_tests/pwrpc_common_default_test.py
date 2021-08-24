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
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
try:
  # pylint: disable=g-import-not-at-top
  from device_service import device_service_pb2
except ImportError:
  device_service_pb2 = None


_DEVICE_SERVICE_PATH = (
    "gazoo_device.capabilities.pwrpc_common_default.device_service_pb2")
_FAKE_DEVICE_NAME = "matter_device"
_FAKE_VENDOR_ID = 1234
_FAKE_PRODUCT_ID = 5678
_FAKE_SOFTWARE_VERSION = 0
_FAKE_TIMEOUT = 5


class PwRPCCommonDefaultTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for PwRPCCommonDefault."""

  def setUp(self):
    super().setUp()
    self.switchboard_call_mock = mock.Mock()
    self.switchboard_call_expect_mock = mock.Mock()
    self.uut = pwrpc_common_default.PwRPCCommonDefault(
        device_name=_FAKE_DEVICE_NAME,
        switchboard_call=self.switchboard_call_mock,
        switchboard_call_expect=self.switchboard_call_expect_mock)
    if device_service_pb2 is not None:
      fake_device_info = device_service_pb2.DeviceInfo(
          vendor_id=_FAKE_VENDOR_ID,
          product_id=_FAKE_PRODUCT_ID,
          software_version=_FAKE_SOFTWARE_VERSION)
      self.fake_device_info_in_bytes = fake_device_info.SerializeToString()
    else:
      self.fake_device_info_in_bytes = None
      info_patcher = mock.patch(_DEVICE_SERVICE_PATH)
      self.device_service = info_patcher.start()
      self.addCleanup(info_patcher.stop)
      self.device_service.DeviceInfo.FromString().vendor_id = _FAKE_VENDOR_ID
      self.device_service.DeviceInfo.FromString().product_id = _FAKE_PRODUCT_ID
      self.device_service.DeviceInfo.FromString().software_version = (
          _FAKE_SOFTWARE_VERSION)
      self.device_service.DeviceInfo.FromString().not_exist = None

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
      self.uut._get_static_info("not_exist")  # pylint: disable=protected-access
    self.switchboard_call_mock.assert_called_once()

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault, "_get_static_info")
  def test_004_reboot_pass(self, mock_version):
    """Verifies reboot passes with no_wait=False."""
    self.switchboard_call_expect_mock.return_value = (None, (True, None))
    self.uut.reboot(no_wait=False,
                    rpc_timeout_s=_FAKE_TIMEOUT,
                    bootup_logline_regex="logs",
                    bootup_timeout=_FAKE_TIMEOUT)
    self.switchboard_call_expect_mock.assert_called_once()
    self.assertEqual(1, mock_version.call_count)

  def test_005_reboot_no_wait_pass(self):
    """Verifies reboot passes with no_wait=True."""
    self.switchboard_call_mock.return_value = (True, None)
    self.uut.reboot(no_wait=True, rpc_timeout_s=_FAKE_TIMEOUT)
    self.switchboard_call_mock.assert_called_once()

  def test_006_reboot_ack_failed(self):
    """Verifies reboot fails with false ack value."""
    self.switchboard_call_expect_mock.return_value = (None, (False, None))
    error_regex = r"triggering Reboot failed: The action did not succeed"
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.reboot(no_wait=False,
                      rpc_timeout_s=_FAKE_TIMEOUT,
                      bootup_logline_regex="logs",
                      bootup_timeout=_FAKE_TIMEOUT)
    self.switchboard_call_expect_mock.assert_called_once()

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault,
      "_get_static_info",
      side_effect=errors.DeviceError(""))
  def test_007_reboot_bootup_failed(self, mock_version):
    """Verifies reboot fails with bootup failure."""
    self.switchboard_call_expect_mock.return_value = (None, (True, None))
    error_regex = f"Failed to boot up within {_FAKE_TIMEOUT}s"
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.reboot(no_wait=False,
                      rpc_timeout_s=_FAKE_TIMEOUT,
                      bootup_logline_regex="logs",
                      bootup_timeout=_FAKE_TIMEOUT)
    self.switchboard_call_expect_mock.assert_called_once()
    self.assertEqual(10, mock_version.call_count)

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault, "_get_static_info")
  def test_008_factory_reset_pass(self, mock_version):
    """Verifies factory reset passes with no_wait=False."""
    self.switchboard_call_expect_mock.return_value = (None, (True, None))
    self.uut.factory_reset(no_wait=False,
                           rpc_timeout_s=_FAKE_TIMEOUT,
                           bootup_logline_regex="logs",
                           bootup_timeout=_FAKE_TIMEOUT)
    self.switchboard_call_expect_mock.assert_called_once()
    self.assertEqual(1, mock_version.call_count)

  def test_009_factory_reset_no_wait_pass(self):
    """Verifies factory reset passes with no_wait=True."""
    self.switchboard_call_mock.return_value = (True, None)
    self.uut.factory_reset(no_wait=True, rpc_timeout_s=_FAKE_TIMEOUT)
    self.switchboard_call_mock.assert_called_once()

  def test_010_factory_reset_ack_failed(self):
    """Verifies factory reset fails with false ack value."""
    self.switchboard_call_expect_mock.return_value = (None, (False, None))
    error_regex = r"triggering FactoryReset failed: The action did not succeed"
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.factory_reset(no_wait=False,
                             rpc_timeout_s=_FAKE_TIMEOUT,
                             bootup_logline_regex="logs",
                             bootup_timeout=_FAKE_TIMEOUT)
    self.switchboard_call_expect_mock.assert_called_once()

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault,
      "_get_static_info",
      side_effect=errors.DeviceError(""))
  def test_010_factory_reset_bootup_failed(self, mock_version):
    """Verifies factory reset fails with bootup failure."""
    self.switchboard_call_expect_mock.return_value = (None, (True, None))
    error_regex = f"Failed to boot up within {_FAKE_TIMEOUT}s"
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.factory_reset(no_wait=False,
                             rpc_timeout_s=_FAKE_TIMEOUT,
                             bootup_logline_regex="",
                             bootup_timeout=_FAKE_TIMEOUT)
    self.switchboard_call_expect_mock.assert_called_once()
    self.assertEqual(10, mock_version.call_count)

  def test_012_ota_pass(self):
    """Verifies OTA passes."""
    self.switchboard_call_mock.return_value = (True, None)
    self.uut.ota()
    self.switchboard_call_mock.assert_called_once()

  def test_013_invalid_argument_of_trigger_device_action(self):
    """Verifies failure for passing invalid argument."""
    error_regex = "Both or neither should be provided"
    with self.assertRaisesRegex(ValueError, error_regex):
      # pylint: disable=protected-access
      self.uut._trigger_device_action(action="SomeAction",
                                      rpc_timeout_s=0,
                                      expect_regex="SomeRegex")

if __name__ == "__main__":
  fake_device_test_case.main()
