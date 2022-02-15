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

"""Matter cluster capability unit test for color_control_pw_rpc module."""
from unittest import mock

import gazoo_device
from gazoo_device import errors
from gazoo_device.capabilities.matter_clusters import color_control_pw_rpc
from gazoo_device.protos import lighting_service_pb2
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_COLOR_CONTROL_RPC_MODULE = (
    gazoo_device.capabilities.matter_clusters.color_control_pw_rpc.
    ColorControlClusterPwRpc)
_FAKE_DEVICE_NAME = "fake-device-name"
_FAKE_TIMEOUT_S = 10
_FAKE_HUE_VAULE = 108
_FAKE_SATURATION_VAULE = 180
_FAKE_COLOR = "fake-color"


class ColorControlClusterPwRpcTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for ColorControlClusterPwRpc."""

  def setUp(self):
    super().setUp()
    self.fake_switchboard_call = mock.Mock()
    self.uut = color_control_pw_rpc.ColorControlClusterPwRpc(
        device_name=_FAKE_DEVICE_NAME,
        switchboard_call=self.fake_switchboard_call,
        rpc_timeout_s=_FAKE_TIMEOUT_S)

  @mock.patch.object(
      _COLOR_CONTROL_RPC_MODULE, "current_hue",
      new_callable=mock.PropertyMock(return_value=_FAKE_HUE_VAULE))
  @mock.patch.object(
      _COLOR_CONTROL_RPC_MODULE, "current_saturation",
      new_callable=mock.PropertyMock(return_value=_FAKE_SATURATION_VAULE))
  @mock.patch.object(
      color_control_pw_rpc.ColorControlClusterPwRpc, "_set_light_color")
  def test_move_to_hue_on_success(
      self, mock_set_light_color, mock_saturation, mock_hue):
    """Verifies move_to_hue method on success."""
    self.uut.move_to_hue(hue=_FAKE_HUE_VAULE)

    mock_set_light_color.assert_called_once_with(
        hue=_FAKE_HUE_VAULE, saturation=_FAKE_SATURATION_VAULE)

  @mock.patch.object(
      _COLOR_CONTROL_RPC_MODULE, "current_hue",
      new_callable=mock.PropertyMock(return_value=0))
  @mock.patch.object(
      _COLOR_CONTROL_RPC_MODULE, "current_saturation",
      new_callable=mock.PropertyMock(return_value=_FAKE_SATURATION_VAULE))
  @mock.patch.object(
      color_control_pw_rpc.ColorControlClusterPwRpc, "_set_light_color")
  def test_move_to_hue_on_failure_incorrect_hue(
      self, mock_set_light_color, mock_saturation, mock_hue):
    """Verifies move_to_hue method on failure with incorrect hue."""
    error_msg = f"Device {_FAKE_DEVICE_NAME} current hue didn't change"
    with self.assertRaisesRegex(errors.DeviceError, error_msg):
      self.uut.move_to_hue(hue=_FAKE_HUE_VAULE)

  @mock.patch.object(
      _COLOR_CONTROL_RPC_MODULE, "current_hue",
      new_callable=mock.PropertyMock(return_value=_FAKE_HUE_VAULE))
  @mock.patch.object(
      _COLOR_CONTROL_RPC_MODULE, "current_saturation",
      new_callable=mock.PropertyMock(return_value=_FAKE_SATURATION_VAULE))
  @mock.patch.object(
      color_control_pw_rpc.ColorControlClusterPwRpc, "_set_light_color")
  def test_move_to_saturation_on_success(
      self, mock_set_light_color, mock_saturation, mock_hue):
    """Verifies move_to_hue method on success."""
    self.uut.move_to_saturation(saturation=_FAKE_SATURATION_VAULE)

    mock_set_light_color.assert_called_once_with(
        hue=_FAKE_HUE_VAULE, saturation=_FAKE_SATURATION_VAULE)

  @mock.patch.object(
      _COLOR_CONTROL_RPC_MODULE, "current_hue",
      new_callable=mock.PropertyMock(return_value=_FAKE_SATURATION_VAULE))
  @mock.patch.object(
      _COLOR_CONTROL_RPC_MODULE, "current_saturation",
      new_callable=mock.PropertyMock(return_value=0))
  @mock.patch.object(
      color_control_pw_rpc.ColorControlClusterPwRpc, "_set_light_color")
  def test_move_to_saturation_on_failure_incorrect_hue(
      self, mock_set_light_color, mock_saturation, mock_hue):
    """Verifies move_to_saturation on failure with incorrect saturation."""
    error_msg = f"Device {_FAKE_DEVICE_NAME} current saturation didn't change"
    with self.assertRaisesRegex(errors.DeviceError, error_msg):
      self.uut.move_to_saturation(saturation=_FAKE_HUE_VAULE)

  @mock.patch.object(
      color_control_pw_rpc.ColorControlClusterPwRpc, "_get_light_color")
  def test_current_hue_on_success(self, mock_get_light_color):
    """Verifies current_hue on success."""
    mock_get_light_color.return_value = mock.Mock(hue=_FAKE_HUE_VAULE)

    self.assertEqual(_FAKE_HUE_VAULE, self.uut.current_hue)

  @mock.patch.object(
      color_control_pw_rpc.ColorControlClusterPwRpc, "_get_light_color")
  def test_current_saturation_on_success(self, mock_get_light_color):
    """Verifies current_saturation on success."""
    mock_get_light_color.return_value = mock.Mock(
        saturation=_FAKE_SATURATION_VAULE)

    self.assertEqual(_FAKE_SATURATION_VAULE, self.uut.current_saturation)

  @mock.patch.object(lighting_service_pb2.LightingState, "FromString")
  def test_get_light_color_on_success(self, mock_from_string):
    """Verifies _get_light_color on success."""
    mock_from_string.return_value = mock.Mock(color=_FAKE_COLOR)
    self.fake_switchboard_call.return_value = True, None

    self.assertEqual(_FAKE_COLOR, self.uut._get_light_color())

  def test_get_light_color_on_failure(self):
    """Verifies _get_light_color on failure with false ack."""
    self.fake_switchboard_call.return_value = False, None
    error_msg = f"Device {_FAKE_DEVICE_NAME} getting lighting state failed."

    with self.assertRaisesRegex(errors.DeviceError, error_msg):
      self.uut._get_light_color()

  def test_set_light_color_on_success(self):
    """Verifies _set_light_color on success."""
    self.fake_switchboard_call.return_value = True, None

    self.uut._set_light_color(
        hue=_FAKE_HUE_VAULE, saturation=_FAKE_SATURATION_VAULE)

    self.fake_switchboard_call.assert_called_once()

  def test_set_light_color_on_failure_with_false_ack(self):
    """Verifies _set_light_color on failure with false ack."""
    self.fake_switchboard_call.return_value = False, None
    error_msg = f"Device {_FAKE_DEVICE_NAME} setting lighting color failed"

    with self.assertRaisesRegex(errors.DeviceError, error_msg):
      self.uut._set_light_color(
          hue=_FAKE_HUE_VAULE, saturation=_FAKE_SATURATION_VAULE)


if __name__ == "__main__":
  fake_device_test_case.main()
