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
from gazoo_device.capabilities import matter_endpoints_accessor_pw_rpc
from gazoo_device.capabilities.matter_clusters import color_control_pw_rpc
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_COLOR_CONTROL_RPC_MODULE = (
    gazoo_device.capabilities.matter_clusters.color_control_pw_rpc.
    ColorControlClusterPwRpc)
_FAKE_DEVICE_NAME = "fake-device-name"
_FAKE_VAULE = 108
_FAKE_ENDPOINT_ID = 1


class ColorControlClusterPwRpcTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for ColorControlClusterPwRpc."""

  def setUp(self):
    super().setUp()
    self.fake_read = mock.Mock(spec=matter_endpoints_accessor_pw_rpc
                               .MatterEndpointsAccessorPwRpc.read)
    self.fake_write = mock.Mock(spec=matter_endpoints_accessor_pw_rpc
                                .MatterEndpointsAccessorPwRpc.write)
    self.uut = color_control_pw_rpc.ColorControlClusterPwRpc(
        device_name=_FAKE_DEVICE_NAME,
        endpoint_id=_FAKE_ENDPOINT_ID,
        read=self.fake_read,
        write=self.fake_write)

  @mock.patch.object(
      _COLOR_CONTROL_RPC_MODULE, "current_hue",
      new_callable=mock.PropertyMock(return_value=_FAKE_VAULE))
  def test_move_to_hue_on_success(self, mock_hue):
    """Verifies move_to_hue method on success."""
    self.uut.move_to_hue(hue=_FAKE_VAULE)

    self.fake_write.assert_called_once()

  @mock.patch.object(
      _COLOR_CONTROL_RPC_MODULE, "current_hue",
      new_callable=mock.PropertyMock(return_value=0))
  def test_move_to_hue_on_failure_incorrect_hue(self, mock_hue):
    """Verifies move_to_hue method on failure with incorrect hue."""
    error_msg = f"Device {_FAKE_DEVICE_NAME} current hue didn't change"
    with self.assertRaisesRegex(errors.DeviceError, error_msg):
      self.uut.move_to_hue(hue=_FAKE_VAULE)

  @mock.patch.object(
      _COLOR_CONTROL_RPC_MODULE, "current_saturation",
      new_callable=mock.PropertyMock(return_value=_FAKE_VAULE))
  def test_move_to_saturation_on_success(self, mock_saturation):
    """Verifies move_to_hue method on success."""
    self.uut.move_to_saturation(saturation=_FAKE_VAULE)

    self.fake_write.assert_called_once()

  @mock.patch.object(
      _COLOR_CONTROL_RPC_MODULE, "current_saturation",
      new_callable=mock.PropertyMock(return_value=0))
  def test_move_to_saturation_on_failure_incorrect_hue(self, mock_saturation):
    """Verifies move_to_saturation on failure with incorrect saturation."""
    error_msg = f"Device {_FAKE_DEVICE_NAME} current saturation didn't change"
    with self.assertRaisesRegex(errors.DeviceError, error_msg):
      self.uut.move_to_saturation(saturation=_FAKE_VAULE)

  def test_current_hue_method(self):
    """Verifies current_hue method on success."""
    self.fake_read.return_value = mock.Mock(data_uint8=_FAKE_VAULE)

    self.assertEqual(_FAKE_VAULE, self.uut.current_hue)

  def test_current_saturation_method(self):
    """Verifies current_saturation method on success."""
    self.fake_read.return_value = mock.Mock(data_uint8=_FAKE_VAULE)

    self.assertEqual(_FAKE_VAULE, self.uut.current_saturation)

  def test_color_temperature_mireds(self):
    """Verifies color_temperature_mireds method on success."""
    self.fake_read.return_value = mock.Mock(data_uint16=_FAKE_VAULE)

    self.assertEqual(_FAKE_VAULE, self.uut.color_temperature_mireds)

  @mock.patch.object(
      _COLOR_CONTROL_RPC_MODULE, "color_temperature_mireds",
      new_callable=mock.PropertyMock(return_value=_FAKE_VAULE))
  def test_move_to_color_temperature_on_success(self, mock_color_temp):
    """Verifies move_to_color_temperature method on success."""
    self.uut.move_to_color_temperature(color_temperature_mireds=_FAKE_VAULE)

    self.fake_write.assert_called_once()

  @mock.patch.object(
      _COLOR_CONTROL_RPC_MODULE, "color_temperature_mireds",
      new_callable=mock.PropertyMock(return_value=0))
  def test_move_to_color_temperature_on_failure(self, mock_color_temp):
    """Verifies move_to_color_temperature method on failure."""
    error_msg = "current color temperature didn't change"
    with self.assertRaisesRegex(errors.DeviceError, error_msg):
      self.uut.move_to_color_temperature(color_temperature_mireds=_FAKE_VAULE)


if __name__ == "__main__":
  fake_device_test_case.main()
