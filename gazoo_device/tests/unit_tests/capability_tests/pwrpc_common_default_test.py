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

"""Capability unit test for pwrpc_common_default module."""
from unittest import mock

from absl.testing import parameterized
from gazoo_device import errors
from gazoo_device.capabilities import pwrpc_common_default
from gazoo_device.protos import device_service_pb2
from gazoo_device.switchboard import switchboard
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.utility import retry

_FAKE_ACTION = "fake-action"
_FAKE_DEVICE_NAME = "matter_device"
_FAKE_SOFTWARE_VERSION = "fake-software_version"
_FAKE_QR_CODE = "fake-qr-code"
_FAKE_QR_CODE_URL = "fake-qr-code-url"
_FAKE_PAIRING_INFO = "fake-pairing-info"
_FAKE_FABRIC_INFO = "fake-fabric-info"
_FAKE_PAYLOAD_BYTES = b"fake-payload-bytes"
_FAKE_PAYLOAD = "fake-payload"
_FAKE_PAIRING_CODE = 0
_FAKE_PAIRING_DISCRIMINATOR = 0
_FAKE_TIMEOUT = 5
_FAKE_ERROR_MESSAGE = "fake-error-message"
_FAKE_FABRIC_INFO_INST = mock.Mock(spec=device_service_pb2.FabricInfo,
                                   node_id="fake-node-id")
_FAKE_VERIFIER = b"fake-verifier"
_FAKE_SALT = b"fake-salt"
_FAKE_ITERATION_COUNT = 10


class PwRPCCommonDefaultTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for PwRPCCommonDefault."""

  def setUp(self):
    super().setUp()
    self.add_time_mocks()
    self.switchboard_call_mock = mock.Mock(
        spec=switchboard.SwitchboardDefault.call)
    self.uut = pwrpc_common_default.PwRPCCommonDefault(
        device_name=_FAKE_DEVICE_NAME,
        switchboard_call=self.switchboard_call_mock,
        rpc_timeout_s=_FAKE_TIMEOUT)

  @mock.patch.object(pwrpc_common_default.PwRPCCommonDefault, "get_device_info")
  def test_get_software_version_on_success(self, mock_get_device_info):
    """Verifies getting software version on success."""
    mock_get_device_info.return_value.software_version_string = (
        _FAKE_SOFTWARE_VERSION)
    self.assertEqual(self.uut.software_version, _FAKE_SOFTWARE_VERSION)

  @mock.patch.object(pwrpc_common_default.PwRPCCommonDefault, "pairing_info")
  def test_get_qr_code_on_success(self, mock_get_pairing_info):
    """Verifies getting QR code on success."""
    mock_get_pairing_info.qr_code = _FAKE_QR_CODE
    self.assertEqual(self.uut.qr_code, _FAKE_QR_CODE)

  @mock.patch.object(pwrpc_common_default.PwRPCCommonDefault, "pairing_info")
  def test_get_qr_code_url_on_success(self, mock_get_pairing_info):
    """Verifies getting QR code URL on success."""
    mock_get_pairing_info.qr_code_url = _FAKE_QR_CODE_URL
    self.assertEqual(self.uut.qr_code_url, _FAKE_QR_CODE_URL)

  @mock.patch.object(pwrpc_common_default.PwRPCCommonDefault, "get_device_info")
  def test_get_pairing_info_on_success(self, mock_get_device_info):
    """Verifies getting pairing info on success."""
    mock_get_device_info.return_value.pairing_info = _FAKE_PAIRING_INFO
    self.assertEqual(self.uut.pairing_info, _FAKE_PAIRING_INFO)

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault, "get_device_state")
  def test_get_fabric_info_on_success(self, mock_get_device_state):
    """Verifies getting fabric info on success."""
    mock_get_device_state.return_value.fabric_info = _FAKE_FABRIC_INFO
    self.assertEqual(self.uut.fabric_info, list(_FAKE_FABRIC_INFO))

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault, "wait_for_bootup_complete")
  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault, "_trigger_device_action")
  def test_reboot_on_success(self, mock_trigger, mock_wait):
    """Verifies reboot on success with verify=True."""
    self.uut.reboot()

    mock_trigger.assert_called_once_with(action="Reboot")
    mock_wait.assert_called_once()

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault, "wait_for_bootup_complete")
  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault, "_trigger_device_action")
  def test_factory_reset_on_success(self, mock_trigger, mock_wait):
    """Verifies factory-reset on success with verify=True."""
    self.uut.factory_reset()

    mock_trigger.assert_called_once_with(action="FactoryReset")
    mock_wait.assert_called_once()

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault, "_trigger_device_action")
  def test_ota_on_success(self, mock_trigger):
    """Verifies OTA on success."""
    self.uut.ota()

    mock_trigger.assert_called_once_with(action="TriggerOta")

  @mock.patch.object(retry, "retry")
  def test_wait_for_bootup_complete_on_success(self, mock_retry):
    """Verifies wait_for_bootup_complete on success."""
    self.uut.wait_for_bootup_complete(bootup_timeout=_FAKE_TIMEOUT)

    mock_retry.assert_called_once()

  @mock.patch.object(
      retry,
      "retry",
      side_effect=errors.CommunicationTimeoutError(_FAKE_ERROR_MESSAGE))
  def test_wait_for_bootup_complete_on_failure(self, mock_retry):
    """Verifies wait_for_bootup_complete on failure."""
    error_regex = (
        f"{_FAKE_DEVICE_NAME} failed to boot up within {_FAKE_TIMEOUT}s")
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.wait_for_bootup_complete(bootup_timeout=_FAKE_TIMEOUT)

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault, "_trigger_device_action")
  def test_get_device_info_on_success(self, mock_trigger_device_action):
    """Verifies get_device_info on success."""
    fake_device_info = device_service_pb2.DeviceInfo(
        software_version_string=_FAKE_SOFTWARE_VERSION)
    mock_trigger_device_action.return_value = (
        fake_device_info.SerializeToString())

    self.assertEqual(fake_device_info, self.uut.get_device_info())
    mock_trigger_device_action.assert_called_once_with(action="GetDeviceInfo")

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault, "_trigger_device_action")
  def test_get_device_state_on_success(self, mock_trigger_device_action):
    """Verifies get_device_state on success."""
    fake_device_state = device_service_pb2.DeviceState(time_since_boot_millis=0)
    mock_trigger_device_action.return_value = (
        fake_device_state.SerializeToString())

    self.assertEqual(fake_device_state, self.uut.get_device_state())
    mock_trigger_device_action.assert_called_once_with(action="GetDeviceState")

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault, "_trigger_device_action")
  def test_set_pairing_info(self, mock_trigger_device_action):
    """Verifies set_pairing_info on success."""
    self.uut.set_pairing_info(code=_FAKE_PAIRING_CODE,
                              discriminator=_FAKE_PAIRING_DISCRIMINATOR)

    mock_trigger_device_action.assert_called_once_with(
        action="SetPairingInfo",
        code=_FAKE_PAIRING_CODE,
        discriminator=_FAKE_PAIRING_DISCRIMINATOR)

  @parameterized.parameters(([_FAKE_FABRIC_INFO_INST], True), ([], False))
  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault, "get_device_state")
  def test_pairing_state(
      self, ret_fabric_info, expected_pairing_state, fake_get_device_state):
    """Verifies pairing_state on success."""
    fake_get_device_state.return_value.fabric_info = ret_fabric_info

    self.assertEqual(expected_pairing_state, self.uut.pairing_state)

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault, "_trigger_device_action")
  def test_get_spake_info_on_success(self, mock_trigger_device_action):
    """Verifies get_spake_info on success."""
    fake_spake_info = device_service_pb2.SpakeInfo(
        verifier=_FAKE_VERIFIER, salt=_FAKE_SALT)
    mock_trigger_device_action.return_value = (
        fake_spake_info.SerializeToString())

    self.assertEqual(fake_spake_info, self.uut.get_spake_info())
    mock_trigger_device_action.assert_called_once_with(action="GetSpakeInfo")

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault, "_trigger_device_action")
  @mock.patch.object(pwrpc_common_default.PwRPCCommonDefault, "get_spake_info")
  def test_set_spake_info_on_success(
      self, mock_get_spake_info, mock_trigger_device_action):
    """Verifies set_spake_info on success."""
    mock_get_spake_info.return_value = mock.Mock(
        verifier=_FAKE_VERIFIER,
        salt=_FAKE_SALT,
        iteration_count=_FAKE_ITERATION_COUNT)

    self.uut.set_spake_info()

    mock_trigger_device_action.assert_called_once_with(
        action="SetSpakeInfo",
        verifier=_FAKE_VERIFIER,
        salt=_FAKE_SALT,
        iteration_count=_FAKE_ITERATION_COUNT)

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault, "_trigger_device_action")
  def test_is_advertising(self, mock_trigger_device_action):
    """Verifies is_advertising on success."""
    fake_advertising_state = device_service_pb2.PairingState(
        pairing_enabled=True)
    mock_trigger_device_action.return_value = (
        fake_advertising_state.SerializeToString())

    self.assertTrue(self.uut.is_advertising)

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault, "_trigger_device_action")
  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault,
      "pairing_state", new_callable=mock.PropertyMock(return_value=True))
  def test_start_advertising_noop(
      self, mock_pairing_state, mock_trigger_device_action):
    """Verifies start_advertising noop."""
    self.uut.start_advertising()

    self.assertEqual(0, mock_trigger_device_action.call_count)

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault, "_trigger_device_action")
  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault,
      "pairing_state", new_callable=mock.PropertyMock(return_value=False))
  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault,
      "is_advertising", new_callable=mock.PropertyMock(return_value=False))
  def test_start_advertising_on_success(
      self,
      mock_is_advertising,
      mock_pairing_state,
      mock_trigger_device_action):
    """Verifies start_advertising on success."""
    self.uut.start_advertising()

    mock_trigger_device_action.assert_called_once_with(
        action="SetPairingState", pairing_enabled=True)

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault, "_trigger_device_action")
  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault,
      "is_advertising", new_callable=mock.PropertyMock(return_value=False))
  def test_stop_advertising_noop(
      self, mock_is_advertising, mock_trigger_device_action):
    """Verifies stop_advertising noop."""
    self.uut.stop_advertising()

    self.assertEqual(0, mock_trigger_device_action.call_count)

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault, "_trigger_device_action")
  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault,
      "is_advertising", new_callable=mock.PropertyMock(return_value=True))
  def test_stop_advertising_on_success(
      self, mock_is_advertising, mock_trigger_device_action):
    """Verifies stop_advertising on success."""
    self.uut.stop_advertising()

    mock_trigger_device_action.assert_called_once_with(
        action="SetPairingState", pairing_enabled=False)

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault, "_trigger_device_action")
  def test_set_ota_metadata(self, mock_trigger_device_action):
    """Verifies set_ota_metadata method on success."""
    self.uut.set_ota_metadata(tlv_metadata=b"tlv_metadata")

    mock_trigger_device_action.assert_called_once_with(
        action="SetOtaMetadataForProvider", tlv=b"tlv_metadata")

  def test_trigger_device_action(self):
    """Verifies _trigger_device_action on success."""
    self.switchboard_call_mock.return_value = _FAKE_PAYLOAD_BYTES

    self.assertEqual(
        _FAKE_PAYLOAD_BYTES,
        self.uut._trigger_device_action(action=_FAKE_ACTION))

    self.switchboard_call_mock.assert_called_once()


if __name__ == "__main__":
  fake_device_test_case.main()
