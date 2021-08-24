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
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
try:
  # pylint: disable=g-import-not-at-top
  from lighting_service import lighting_service_pb2
except ImportError:
  lighting_service_pb2 = None


_LIGHTING_SERVICE_PATH = (
    "gazoo_device.capabilities.pwrpc_light_default.lighting_service_pb2")
_PWRPC_LIGHT_MODULE = (
    gazoo_device.capabilities.pwrpc_light_default.PwRPCLightDefault)
_FAKE_DEVICE_NAME = "light_device"
_FAKE_CURRENT_LEVEL = 10
_FAKE_MAX_LEVEL = 100


class PwRPCLightDefaultTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for PwRPCLightDefault."""

  def setUp(self):
    super().setUp()
    self.switchboard_call_mock = mock.Mock()
    self.uut = pwrpc_light_default.PwRPCLightDefault(
        device_name=_FAKE_DEVICE_NAME,
        switchboard_call=self.switchboard_call_mock)
    if lighting_service_pb2 is not None:
      fake_on_state = lighting_service_pb2.LightingState(on=True)
      self.fake_on_state_in_bytes = fake_on_state.SerializeToString()
      fake_off_state = lighting_service_pb2.LightingState(on=False)
      self.fake_off_state_in_bytes = fake_off_state.SerializeToString()
      fake_brightness = lighting_service_pb2.LightingBrightness(
          level=_FAKE_CURRENT_LEVEL, max_level=_FAKE_MAX_LEVEL)
      self.fake_brightness_in_bytes = fake_brightness.SerializeToString()
    else:  # Mock data if Pigweed packages are not available
      self.fake_on_state_in_bytes = None
      self.fake_off_state_in_bytes = None
      self.fake_brightness_in_bytes = None
      lighting_patcher = mock.patch(_LIGHTING_SERVICE_PATH)
      self.lighting_service = lighting_patcher.start()
      self.addCleanup(lighting_patcher.stop)
      self.lighting_service.LightingBrightness.FromString().level = (
          _FAKE_CURRENT_LEVEL)
      self.lighting_service.LightingBrightness.FromString().max_level = (
          _FAKE_MAX_LEVEL)

  @mock.patch.object(_PWRPC_LIGHT_MODULE,
                     "state", new_callable=mock.PropertyMock)
  def test_001_light_on_pass(self, mock_state):
    """Verifies turning light on successfully."""
    self.switchboard_call_mock.return_value = (True, None)
    mock_state.return_value = True
    self.uut.on()
    self.switchboard_call_mock.assert_called_once()
    self.assertEqual(1, mock_state.call_count)

  def test_002_light_on_fail_false_ack(self):
    """Verifies turning light on fails with false ack value."""
    self.switchboard_call_mock.return_value = (False, None)
    error_regex = f"Device {_FAKE_DEVICE_NAME} turning light on failed."
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.on()
    self.switchboard_call_mock.assert_called_once()

  @mock.patch.object(_PWRPC_LIGHT_MODULE,
                     "state", new_callable=mock.PropertyMock)
  def test_002_light_on_fail_incorrect_state(self, mock_state):
    """Verifies turning light on fails with incorrect state."""
    self.switchboard_call_mock.return_value = (True, None)
    mock_state.return_value = False
    error_regex = f"Device {_FAKE_DEVICE_NAME} light didn't turn on."
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.on()
    self.switchboard_call_mock.assert_called_once()
    mock_state.assert_called_once()

  @mock.patch.object(_PWRPC_LIGHT_MODULE,
                     "state", new_callable=mock.PropertyMock)
  def test_003_light_off_pass(self, mock_state):
    """Verifies turning light off successfully."""
    self.switchboard_call_mock.return_value = (True, None)
    mock_state.return_value = False
    self.uut.off()
    self.switchboard_call_mock.assert_called_once()

  def test_004_light_off_fail_false_ack(self):
    """Verifies turning light off fails with false ack value."""
    self.switchboard_call_mock.return_value = (False, None)
    error_regex = f"Device {_FAKE_DEVICE_NAME} turning light off failed."
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.off()
    self.switchboard_call_mock.assert_called_once()

  def test_005_light_state_on_pass(self):
    """Verifies getting light state on successfully."""
    if self.fake_off_state_in_bytes is None:
      self.lighting_service.LightingState.FromString().on = True
    self.switchboard_call_mock.return_value = (True,
                                               self.fake_on_state_in_bytes)
    self.assertTrue(self.uut.state)
    self.switchboard_call_mock.assert_called_once()

  def test_006_light_state_off_pass(self):
    """Verifies getting light state off successfully."""
    if self.fake_off_state_in_bytes is None:
      self.lighting_service.LightingState.FromString().on = False
    self.switchboard_call_mock.return_value = (True,
                                               self.fake_off_state_in_bytes)
    self.assertFalse(self.uut.state)
    self.switchboard_call_mock.assert_called_once()

  def test_007_light_state_fail_false_ack(self):
    """Verifies getting light state fails with false ack value."""
    self.switchboard_call_mock.return_value = (False, None)
    error_regex = f"Device {_FAKE_DEVICE_NAME} getting light state failed."
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.state  # pylint: disable=pointless-statement
    self.switchboard_call_mock.assert_called_once()

  def test_008_light_brightness_pass(self):
    """Verifies getting light brightness successfully."""
    self.switchboard_call_mock.return_value = (True,
                                               self.fake_brightness_in_bytes)
    level, max_level = self.uut.brightness
    self.assertEqual(_FAKE_CURRENT_LEVEL, level)
    self.assertEqual(_FAKE_MAX_LEVEL, max_level)
    self.switchboard_call_mock.assert_called_once()

  def test_009_light_brightness_fail_false_ack(self):
    """Verifies getting light brightness fails with false ack value."""
    self.switchboard_call_mock.return_value = (False, None)
    error_regex = f"Device {_FAKE_DEVICE_NAME} getting light state failed."
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.brightness  # pylint: disable=pointless-statement
    self.switchboard_call_mock.assert_called_once()


if __name__ == "__main__":
  fake_device_test_case.main()
