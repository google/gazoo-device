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

"""Capability unit test for pwrpc_light_default module."""
from unittest import mock

import gazoo_device
from gazoo_device import errors
from gazoo_device.capabilities import pwrpc_light_default
from gazoo_device.protos import lighting_service_pb2
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_PWRPC_LIGHT_MODULE = (
    gazoo_device.capabilities.pwrpc_light_default.PwRPCLightDefault)
_FAKE_DEVICE_NAME = "light_device"
_FAKE_BRIGHTNESS_LEVEL = 10
_FAKE_HUE = 1
_FAKE_SATURATION = 1
_FAKE_TIMEOUT = 1


class PwRPCLightDefaultTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for PwRPCLightDefault."""

  def setUp(self):
    super().setUp()
    self.switchboard_call_mock = mock.Mock()
    self.switchboard_call_expect_mock = mock.Mock()
    fake_expect_regexes = {
        pwrpc_light_default.LightingAction.ON: "on",
        pwrpc_light_default.LightingAction.OFF: "off"}
    self.uut = pwrpc_light_default.PwRPCLightDefault(
        device_name=_FAKE_DEVICE_NAME,
        expect_lighting_regexes=fake_expect_regexes,
        expect_timeout=_FAKE_TIMEOUT,
        switchboard_call=self.switchboard_call_mock,
        switchboard_call_expect=self.switchboard_call_expect_mock)

  @mock.patch.object(pwrpc_light_default.PwRPCLightDefault, "_on_off")
  def test_001_light_on(self, mock_on_off):
    """Verifies turning light on."""
    self.uut.on()
    mock_on_off.assert_called_once_with(True, False)

  @mock.patch.object(pwrpc_light_default.PwRPCLightDefault, "_on_off")
  def test_002_light_off(self, mock_on_off):
    """Verifies turning light off."""
    self.uut.off()
    mock_on_off.assert_called_once_with(False, False)

  @mock.patch.object(pwrpc_light_default.PwRPCLightDefault, "_get_state")
  def test_003_get_light_state(self, mock_get_state):
    """Verifies getting light state."""
    mock_get_state.return_value.on = True
    self.assertTrue(self.uut.state)
    mock_get_state.assert_called_once()

  @mock.patch.object(pwrpc_light_default.PwRPCLightDefault, "_get_state")
  def test_004_get_light_brightness(self, mock_get_state):
    """Verifies getting lighting brightness."""
    mock_get_state.return_value.level = _FAKE_BRIGHTNESS_LEVEL
    self.assertEqual(_FAKE_BRIGHTNESS_LEVEL, self.uut.brightness)
    mock_get_state.assert_called_once()

  @mock.patch.object(pwrpc_light_default.PwRPCLightDefault, "_get_state")
  def test_005_get_light_color(self, mock_get_state):
    """Verifies getting lighting color."""
    fake_color = mock.Mock(hue=_FAKE_HUE, saturation=_FAKE_SATURATION)
    mock_get_state.return_value.color = fake_color
    self.assertEqual(_FAKE_HUE, self.uut.color.hue)
    self.assertEqual(_FAKE_SATURATION, self.uut.color.saturation)

  @mock.patch.object(_PWRPC_LIGHT_MODULE,
                     "state", new_callable=mock.PropertyMock)
  def test_006_on_off_with_success(self, mock_state):
    """Verifies _on_off method on success."""
    self.switchboard_call_expect_mock.return_value = None, (True, None)
    mock_state.return_value = True

    self.uut._on_off(on=True, no_wait=False)

    self.switchboard_call_expect_mock.assert_called_once()
    mock_state.assert_called_once()

  def test_006_on_off_failure_false_ack(self):
    """Verifies _on_off method on failure with false ack value."""
    self.switchboard_call_expect_mock.return_value = None, (False, None)
    error_regex = f"Device {_FAKE_DEVICE_NAME} turning light on failed."

    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.on()

    self.switchboard_call_expect_mock.assert_called_once()

  @mock.patch.object(_PWRPC_LIGHT_MODULE,
                     "state", new_callable=mock.PropertyMock)
  def test_006_on_off_failure_incorrect_state(self, mock_state):
    """Verifies _on_off method on failure with incorrect state."""
    self.switchboard_call_expect_mock.return_value = None, (True, None)
    mock_state.return_value = False
    error_regex = f"Device {_FAKE_DEVICE_NAME} light didn't turn on."

    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.on()

    self.switchboard_call_expect_mock.assert_called_once()
    mock_state.assert_called_once()

  def test_007_get_state_with_success(self):
    """Verifies _get_state method on success."""
    fake_on_state = lighting_service_pb2.LightingState(on=True)
    fake_on_state_in_bytes = fake_on_state.SerializeToString()
    self.switchboard_call_mock.return_value = (True, fake_on_state_in_bytes)

    state = self.uut._get_state()

    self.assertTrue(state.on)

  def test_007_get_state_failure_false_ack(self):
    """Verifies _get_state method on failure with false ack value."""
    self.switchboard_call_mock.return_value = (False, "")
    error_regex = f"Device {_FAKE_DEVICE_NAME} getting light state failed."

    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut._get_state()

    self.switchboard_call_mock.assert_called_once()


if __name__ == "__main__":
  fake_device_test_case.main()
