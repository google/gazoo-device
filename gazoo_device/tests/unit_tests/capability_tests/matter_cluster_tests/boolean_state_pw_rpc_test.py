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

"""Matter cluster unit test for boolean_state_pw_rpc module."""
from unittest import mock

import gazoo_device
from gazoo_device import errors
from gazoo_device.capabilities import matter_endpoints_accessor_pw_rpc
from gazoo_device.capabilities.matter_clusters import boolean_state_pw_rpc
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_BOOLEAN_STATE_RPC_MODULE = (
    gazoo_device.capabilities.matter_clusters.boolean_state_pw_rpc
    .BooleanStateClusterPwRpc)
_FAKE_DEVICE_NAME = "fake-device-name"
_FAKE_ENDPOINT_ID = 1
_FAKE_DATA = True


class BooleanStateClusterPwRpcTest(
    fake_device_test_case.FakeDeviceTestCase):
  """Unit test for BooleanStateClusterPwRpc."""

  def setUp(self):
    super().setUp()
    self.fake_read = mock.Mock(
        spec=matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc.read)
    self.fake_write = mock.Mock(spec=matter_endpoints_accessor_pw_rpc
                                .MatterEndpointsAccessorPwRpc.write)
    self.uut = boolean_state_pw_rpc.BooleanStateClusterPwRpc(
        device_name=_FAKE_DEVICE_NAME,
        endpoint_id=_FAKE_ENDPOINT_ID,
        read=self.fake_read,
        write=self.fake_write)

  def test_state_value(self):
    """Verifies the state_value attribute on success."""
    self.fake_read.return_value = mock.Mock(data_bool=_FAKE_DATA)
    self.assertEqual(_FAKE_DATA, self.uut.state_value)

  def test_set_state_value_success(self):
    """Verifies update state_value on success."""
    self.fake_read.return_value = mock.Mock(data_bool=_FAKE_DATA)
    self.uut.state_value = _FAKE_DATA
    self.fake_write.assert_called_once()

  def test_set_state_value_failure_incorrect_state(self):
    """Verifies update state_value method on failure."""
    error_regex = (
        f"Device {_FAKE_DEVICE_NAME} state_value didn't change to "
        f"False from True.")
    self.fake_read.return_value = mock.Mock(data_bool=_FAKE_DATA)
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.state_value = False


if __name__ == "__main__":
  fake_device_test_case.main()
