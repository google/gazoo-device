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

"""Mixin for testing pwrpc_common_default capability."""
from unittest import mock

from gazoo_device import console_config
from gazoo_device import errors
from gazoo_device.capabilities import pwrpc_common_default

_FAKE_FIRMWARE_VERSION = "fake-firmware-version"
_FAKE_COMMAND = "fake-command"
_FAKE_PAIRING_CODE = 0
_FAKE_PAIRING_DISCRIMINATOR = 0


class PigweedRpcCommonTestMixin:
  """Mixin for Matter device unit tests of Pigweed RPC common capability..

  Assumes self.uut is set.
  """

  @mock.patch.object(console_config, "get_log_only_configuration")
  def test_get_console_configuration_on_success(
      self, unused_mock_console_config):
    """Verifies get_console_configuration on success."""
    config = self.uut.get_console_configuration()
    self.assertIsNotNone(config)

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault,
      "software_version",
      new_callable=mock.PropertyMock,
      return_value=_FAKE_FIRMWARE_VERSION)
  def test_get_firmware_version_on_success(self, unused_mock_sw_version):
    """Verifies get firmware_version on success."""
    self.assertEqual(self.uut.firmware_version, _FAKE_FIRMWARE_VERSION)

  @mock.patch.object(pwrpc_common_default.PwRPCCommonDefault, "reboot")
  def test_reboot_on_success(self, mock_reboot):
    """Verifies reboot on success."""
    self.uut.reboot()
    mock_reboot.assert_called_once()

  @mock.patch.object(pwrpc_common_default.PwRPCCommonDefault, "factory_reset")
  def test_factory_reset_on_success(self, mock_factory_reset):
    """Verifies factory reset on success."""
    self.uut.factory_reset()
    mock_factory_reset.assert_called_once()

  def test_common_rpc_capability_initialization_success(self):
    """Verifies the initialization of pw_rpc_common capability."""
    self.assertIsNotNone(self.uut.pw_rpc_common)

  def test_shell_not_implemented(self):
    """Verifies the shell method not implemented."""
    error_regex = "shell not implemented."
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.shell(command=_FAKE_COMMAND)

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault, "wait_for_bootup_complete")
  def test_wait_for_bootup_complete_on_success(
      self, mock_wait_for_bootup_complete):
    """Verifies the wait_for_bootup_complete on success."""
    self.uut.wait_for_bootup_complete()
    mock_wait_for_bootup_complete.assert_called_once()

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault,
      "pairing_info",
      new_callable=mock.PropertyMock)
  def test_get_pairing_code_on_success(self, mock_pairing_info):
    """Verifies get pairing_code on success."""
    fake_pairing_code = mock.Mock(code=_FAKE_PAIRING_CODE)
    mock_pairing_info.return_value = fake_pairing_code
    self.assertEqual(self.uut.pairing_code, _FAKE_PAIRING_CODE)

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault,
      "pairing_info",
      new_callable=mock.PropertyMock)
  def test_get_pairing_discriminator_on_success(self, mock_pairing_info):
    """Verifies get pairing_discriminator on success."""
    fake_discriminator = mock.Mock(discriminator=_FAKE_PAIRING_DISCRIMINATOR)
    mock_pairing_info.return_value = fake_discriminator
    self.assertEqual(
        self.uut.pairing_discriminator, _FAKE_PAIRING_DISCRIMINATOR)
