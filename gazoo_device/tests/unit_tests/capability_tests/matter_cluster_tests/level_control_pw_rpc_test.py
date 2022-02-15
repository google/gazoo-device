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
from gazoo_device.capabilities.matter_clusters import level_control_pw_rpc
from gazoo_device.protos import lighting_service_pb2
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_LEVEL_CONTROL_RPC_MODULE = (
    gazoo_device.capabilities.matter_clusters.level_control_pw_rpc.
    LevelControlClusterPwRpc)
_FAKE_DEVICE_NAME = "fake-device-name"
_FAKE_TIMEOUT_S = 10
_FAKE_LEVEL = 100


class LevelControlClusterPwRpcTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for LevelControlClusterPwRpc."""

  def setUp(self):
    super().setUp()
    self.fake_switchboard_call = mock.Mock()
    self.uut = level_control_pw_rpc.LevelControlClusterPwRpc(
        device_name=_FAKE_DEVICE_NAME,
        switchboard_call=self.fake_switchboard_call,
        rpc_timeout_s=_FAKE_TIMEOUT_S)

  @mock.patch.object(
      _LEVEL_CONTROL_RPC_MODULE,
      "current_level",
      new_callable=mock.PropertyMock(return_value=_FAKE_LEVEL))
  def test_move_to_level_on_success(self, mock_current_level):
    """Verifies move_to_level on success."""
    self.fake_switchboard_call.return_value = True, None

    self.uut.move_to_level(level=_FAKE_LEVEL)

    self.fake_switchboard_call.assert_called_once()

  @mock.patch.object(
      _LEVEL_CONTROL_RPC_MODULE,
      "current_level",
      new_callable=mock.PropertyMock(return_value=0))
  def test_move_to_level_on_failure_false_ack(self, mock_current_level):
    """Verifies move_to_level on failure with false ack."""
    self.fake_switchboard_call.return_value = False, None
    error_regex = (f"Device {_FAKE_DEVICE_NAME} moving current level to "
                   f"{_FAKE_LEVEL} failed")
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.move_to_level(level=_FAKE_LEVEL)

  @mock.patch.object(
      _LEVEL_CONTROL_RPC_MODULE,
      "current_level",
      new_callable=mock.PropertyMock(return_value=0))
  def test_move_to_level_on_failure_incorrect_level(self, mock_current_level):
    """Verifies move_to_level on failure with incorrect level."""
    self.fake_switchboard_call.return_value = True, None
    error_regex = (f"Device {_FAKE_DEVICE_NAME} current level didn't change to"
                   f" {_FAKE_LEVEL} from 0")
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.move_to_level(level=_FAKE_LEVEL)

  def test_current_level_on_success(self):
    """Verifies current_level on success."""
    fake_level = lighting_service_pb2.LightingState(level=_FAKE_LEVEL)
    fake_level_in_bytes = fake_level.SerializeToString()
    self.fake_switchboard_call.return_value = True, fake_level_in_bytes

    self.assertEqual(_FAKE_LEVEL, self.uut.current_level)
    self.fake_switchboard_call.assert_called_once()

  def test_current_level_on_failure_false_ack(self):
    """Verifies current_level on failure with false ack."""
    self.fake_switchboard_call.return_value = False, None
    error_regex = (f"Device {_FAKE_DEVICE_NAME} getting CurrentLevel attribute "
                   "failed.")
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.current_level  # pylint: disable=pointless-statement
