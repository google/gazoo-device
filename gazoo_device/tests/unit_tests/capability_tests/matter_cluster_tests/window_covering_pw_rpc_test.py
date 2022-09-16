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

"""Matter cluster unit test for widow_covering_pw_rpc module."""
from unittest import mock

import gazoo_device
from gazoo_device import errors
from gazoo_device.capabilities import matter_endpoints_accessor_pw_rpc
from gazoo_device.capabilities.matter_clusters import window_covering_pw_rpc
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_WINDOW_COVERING_RPC_MODULE = (
    gazoo_device.capabilities.matter_clusters.window_covering_pw_rpc
    .WindowCoveringClusterPwRpc)
_FAKE_DEVICE_NAME = "fake-device-name"
_FAKE_ENDPOINT_ID = 1
_FAKE_DATA = 10


class WindowCoveringPwRpcTest(
    fake_device_test_case.FakeDeviceTestCase):
  """Unit test for WindowCoveringPwRpc."""

  def setUp(self):
    super().setUp()
    self.fake_read = mock.Mock(
        spec=matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc.read,
        return_value=mock.Mock(data_uint8=_FAKE_DATA))
    self.fake_write = mock.Mock(spec=matter_endpoints_accessor_pw_rpc
                                .MatterEndpointsAccessorPwRpc.write)
    self.uut = window_covering_pw_rpc.WindowCoveringClusterPwRpc(
        device_name=_FAKE_DEVICE_NAME,
        endpoint_id=_FAKE_ENDPOINT_ID,
        read=self.fake_read,
        write=self.fake_write)

  @mock.patch.object(
      window_covering_pw_rpc.WindowCoveringClusterPwRpc,
      "_read_percent_attribute",
      return_value=_FAKE_DATA,
      autospec=True)
  def test_get_current_position_lift_percentage(self, mock_read_percent):
    """Verifies the current_position_lift_percentage attribute read on success."""
    self.assertEqual(_FAKE_DATA, self.uut.current_position_lift_percentage)
    mock_read_percent.assert_called_once()

  @mock.patch.object(
      window_covering_pw_rpc.WindowCoveringClusterPwRpc,
      "_read_percent_attribute",
      return_value=_FAKE_DATA,
      autospec=True)
  @mock.patch.object(
      window_covering_pw_rpc.WindowCoveringClusterPwRpc,
      "_write_percent_attribute",
      return_value=_FAKE_DATA,
      autospec=True)
  def test_set_current_position_lift_percentage_success(self,
                                                        mock_write_percent,
                                                        mock_read_percent):
    """Verifies update current_position_lift_percentage attribute on success."""
    self.uut.current_position_lift_percentage = _FAKE_DATA
    mock_write_percent.assert_called_once()
    mock_read_percent.assert_called_once()

  def test_set_current_position_lift_percentage_failure(self):
    """Verifies update current_position_lift_percentage method on failure."""
    error_data = 50
    error_regex = (
        f"Device {_FAKE_DEVICE_NAME} current_position_lift_percentage didn't "
        f"change to {error_data}.")
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.current_position_lift_percentage = error_data

  @mock.patch.object(
      window_covering_pw_rpc.WindowCoveringClusterPwRpc,
      "_read_percent_attribute",
      return_value=_FAKE_DATA,
      autospec=True)
  def test_get_current_position_tilt_percentage(self, mock_read_percent):
    """Verifies the current_position_tilt_percentage attribute read on success."""
    self.assertEqual(_FAKE_DATA, self.uut.current_position_tilt_percentage)
    mock_read_percent.assert_called_once()

  @mock.patch.object(
      window_covering_pw_rpc.WindowCoveringClusterPwRpc,
      "_read_percent_attribute",
      return_value=_FAKE_DATA,
      autospec=True)
  @mock.patch.object(
      window_covering_pw_rpc.WindowCoveringClusterPwRpc,
      "_write_percent_attribute",
      return_value=_FAKE_DATA,
      autospec=True)
  def test_set_current_position_tilt_percentage_success(self,
                                                        mock_write_percent,
                                                        mock_read_percent):
    """Verifies update current_position_tilt_percentage attribute on success."""
    self.uut.current_position_tilt_percentage = _FAKE_DATA
    mock_write_percent.assert_called_once()
    mock_read_percent.assert_called_once()

  def test_set_current_position_tilt_percentage_failure(self):
    """Verifies update current_position_tilt_percentage method on failure."""
    error_data = 50
    error_regex = (
        f"Device {_FAKE_DEVICE_NAME} current_position_tilt_percentage didn't "
        f"change to {error_data}.")
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.current_position_tilt_percentage = error_data

  def test_read_percent_attribute_type(self):
    """Verifies the read_percent_attribute_type on success."""
    percent = self.uut.current_position_lift_percentage
    self.fake_read.assert_called_once()
    self.assertEqual(_FAKE_DATA, percent)

  def test_write_percent_attribute_type(self):
    """Verifies the write_percent_attribute_type on success."""
    self.uut.current_position_lift_percentage = _FAKE_DATA
    self.fake_write.assert_called_once()

if __name__ == "__main__":
  fake_device_test_case.main()
