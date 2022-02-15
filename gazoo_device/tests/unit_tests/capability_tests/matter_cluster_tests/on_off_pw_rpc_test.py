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

"""Matter cluster capability unit test for on_off_pw_rpc module."""
from unittest import mock

import gazoo_device
from gazoo_device import errors
from gazoo_device.capabilities.matter_clusters import on_off_pw_rpc
from gazoo_device.protos import lighting_service_pb2
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_ON_OFF_RPC_MODULE = (
    gazoo_device.capabilities.matter_clusters.on_off_pw_rpc.OnOffClusterPwRpc)
_FAKE_DEVICE_NAME = "fake-device-name"
_FAKE_TIMEOUT_S = 10


class OnOffClusterPwRpcTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for OnOffClusterPwRpc."""

  def setUp(self):
    super().setUp()
    self.fake_switchboard_call = mock.Mock()
    self.uut = on_off_pw_rpc.OnOffClusterPwRpc(
        device_name=_FAKE_DEVICE_NAME,
        switchboard_call=self.fake_switchboard_call,
        rpc_timeout_s=_FAKE_TIMEOUT_S)

  @mock.patch.object(on_off_pw_rpc.OnOffClusterPwRpc, "_onoff_command")
  def test_on_command(self, mock_on_off):
    """Verifies the on command."""
    self.uut.on()
    mock_on_off.assert_called_once_with(on=True, verify=True)

  @mock.patch.object(on_off_pw_rpc.OnOffClusterPwRpc, "_onoff_command")
  def test_off_command(self, mock_on_off):
    """Verifies the off command."""
    self.uut.off()
    mock_on_off.assert_called_once_with(on=False, verify=True)

  @mock.patch.object(on_off_pw_rpc.OnOffClusterPwRpc, "_onoff_command")
  @mock.patch.object(
      _ON_OFF_RPC_MODULE,
      "onoff",
      new_callable=mock.PropertyMock(return_value=True))
  def test_toggle_command(self, mock_state, mock_on_off):
    """Verifies the toggle command."""
    self.uut.toggle()

    mock_on_off.assert_called_once_with(on=False, verify=True)

  def test_onoff_attribute_on_success(self):
    """Verifies the onoff attribute on success."""
    fake_on_state = lighting_service_pb2.LightingState(on=True)
    fake_on_state_in_bytes = fake_on_state.SerializeToString()
    self.fake_switchboard_call.return_value = (True, fake_on_state_in_bytes)

    self.assertTrue(self.uut.onoff)

  def test_onoff_attribute_failure_false_ack(self):
    """Verifies the onoff attribute on failure with false ack value."""
    self.fake_switchboard_call.return_value = (False, "")
    error_regex = f"Device {_FAKE_DEVICE_NAME} getting OnOff state failed."

    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.onoff  # pylint: disable=pointless-statement

    self.fake_switchboard_call.assert_called_once()

  @mock.patch.object(
      _ON_OFF_RPC_MODULE,
      "onoff",
      new_callable=mock.PropertyMock(return_value=True))
  def test_on_off_method_success(self, mock_state):
    """Verifies _on_off method on success."""
    self.fake_switchboard_call.return_value = (True, None)

    self.uut._onoff_command(on=True, verify=True)

    self.fake_switchboard_call.assert_called_once()

  def test_on_off_method_failure_false_ack(self):
    """Verifies _on_off method on failure with false ack value."""
    self.fake_switchboard_call.return_value = (False, None)
    error_regex = f"Device {_FAKE_DEVICE_NAME} turning off failed."

    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut._onoff_command(on=False)

  @mock.patch.object(
      _ON_OFF_RPC_MODULE,
      "onoff",
      new_callable=mock.PropertyMock(return_value=True))
  def test_on_off_method_failure_incorrect_state(self, mock_state):
    """Verifies _on_off method on failure with incorrect state."""
    self.fake_switchboard_call.return_value = (True, None)
    error_regex = f"Device {_FAKE_DEVICE_NAME} didn't turn off."

    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut._onoff_command(on=False)


if __name__ == "__main__":
  fake_device_test_case.main()
