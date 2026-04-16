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

from absl.testing import parameterized
from gazoo_device.capabilities import matter_endpoints_accessor_pw_rpc
from gazoo_device.capabilities.matter_clusters import boolean_state_pw_rpc
from gazoo_device.tests.unit_tests.utils import unit_test_case

_FAKE_DEVICE_NAME = "fake-device-name"
_FAKE_ENDPOINT_ID = 1
_FAKE_DATA = True


class BooleanStateClusterPwRpcTest(unit_test_case.UnitTestCase):
  """Unit test for BooleanStateClusterPwRpc."""

  def setUp(self):
    super().setUp()
    self.mock_endpoint_accessor = mock.create_autospec(
        matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc,
        instance=True,
    )
    self.uut = boolean_state_pw_rpc.BooleanStateClusterPwRpc(
        device_name=_FAKE_DEVICE_NAME,
        endpoint_id=_FAKE_ENDPOINT_ID,
        read=self.mock_endpoint_accessor.read,
        write=self.mock_endpoint_accessor.write,
        send=self.mock_endpoint_accessor.send,
    )

  def test_state_value(self):
    """Verifies the state_value attribute on success."""
    self.mock_endpoint_accessor.read.return_value = mock.Mock(
        data_bool=_FAKE_DATA
    )
    self.assertEqual(_FAKE_DATA, self.uut.state_value)

  @parameterized.named_parameters(
      dict(
          testcase_name="when_set_to_true",
          target_state_value=True,
      ),
      dict(
          testcase_name="when_set_to_false",
          target_state_value=False,
      ),
  )
  def test_set_state_value_success(self, target_state_value):
    """Verifies update state_value on success."""
    self.uut.state_value = target_state_value
    self.mock_endpoint_accessor.send.assert_called_once_with(
        service_name="BooleanState",
        rpc_name="Set",
        endpoint_id=1,
        state_value=target_state_value,
    )


if __name__ == "__main__":
  unit_test_case.main()
