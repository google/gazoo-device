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

"""Matter cluster capability unit test for level_control_pw_rpc module."""
from unittest import mock

import gazoo_device
from gazoo_device import errors
from gazoo_device.capabilities import matter_endpoints_accessor_pw_rpc
from gazoo_device.capabilities.matter_clusters import level_control_pw_rpc
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_LEVEL_CONTROL_RPC_MODULE = (
    gazoo_device.capabilities.matter_clusters.level_control_pw_rpc.
    LevelControlClusterPwRpc)
_FAKE_DEVICE_NAME = "fake-device-name"
_FAKE_ENDPOINT_ID = 1
_FAKE_LEVEL = 100


class LevelControlClusterPwRpcTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for LevelControlClusterPwRpc."""

  def setUp(self):
    super().setUp()
    self.fake_read = mock.Mock(spec=matter_endpoints_accessor_pw_rpc
                               .MatterEndpointsAccessorPwRpc.read)
    self.fake_read.return_value = mock.Mock(data_uint8=_FAKE_LEVEL)
    self.fake_write = mock.Mock(spec=matter_endpoints_accessor_pw_rpc
                                .MatterEndpointsAccessorPwRpc.write)
    self.uut = level_control_pw_rpc.LevelControlClusterPwRpc(
        device_name=_FAKE_DEVICE_NAME,
        endpoint_id=_FAKE_ENDPOINT_ID,
        read=self.fake_read,
        write=self.fake_write)

  @mock.patch.object(
      _LEVEL_CONTROL_RPC_MODULE,
      "current_level",
      new_callable=mock.PropertyMock(return_value=_FAKE_LEVEL))
  def test_move_to_level_on_success(self, mock_current_level):
    """Verifies move_to_level on success."""
    self.uut.move_to_level(level=_FAKE_LEVEL)

    self.fake_write.assert_called_once()

  @mock.patch.object(
      _LEVEL_CONTROL_RPC_MODULE,
      "current_level",
      new_callable=mock.PropertyMock(return_value=0))
  def test_move_to_level_on_failure_incorrect_level(self, mock_current_level):
    """Verifies move_to_level on failure with incorrect level."""
    error_regex = (f"Device {_FAKE_DEVICE_NAME} current level didn't change to"
                   f" {_FAKE_LEVEL} from 0")
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.move_to_level(level=_FAKE_LEVEL)

  def test_current_level_method(self):
    """Verifies current_level method on success."""
    self.assertEqual(_FAKE_LEVEL, self.uut.current_level)

  def test_min_level_method(self):
    """Verifies min_level method on success."""
    self.assertEqual(_FAKE_LEVEL, self.uut.min_level)

  def test_max_level_method(self):
    """Verifies max_level method on success."""
    self.assertEqual(_FAKE_LEVEL, self.uut.max_level)
