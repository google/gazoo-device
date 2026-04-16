# Copyright 2024 Google LLC
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

"""Capability unit test for pwrpc_event_subscription module."""

from unittest import mock

from absl.testing import parameterized

from gazoo_device.capabilities import pwrpc_event_subscription_default
from gazoo_device.protos import boolean_state_service_pb2
from gazoo_device.switchboard import switchboard
from gazoo_device.tests.unit_tests.utils import unit_test_case


class PwRpcEventSubscriptionTest(parameterized.TestCase):
  """Unit test for PwRpcEventSubscriptionDefault."""

  def setUp(self):
    super().setUp()
    self.switchboard_call_mock = mock.Mock(
        spec=switchboard.SwitchboardDefault.call)
    self.uut = pwrpc_event_subscription_default.PwRpcEventSubscriptionDefault(
        device_name="fake_device_name",
        switchboard_call=self.switchboard_call_mock,
        rpc_timeout_s=3)

  @parameterized.parameters((True,), (False,))
  def test_set_boolean_state(self, state_value):
    """Verifies set_boolean_state on success."""
    self.uut.set_boolean_state(state_value=state_value)

    self.switchboard_call_mock.assert_called_once()

  @parameterized.parameters((True,), (False,))
  def test_get_boolean_state(self, state_value):
    """Verifies get_boolean_state on success."""
    fake_boolean_state = boolean_state_service_pb2.BooleanStateState(
        state_value=state_value)
    response_byte = boolean_state_service_pb2.BooleanStateGetResponse(
        state=fake_boolean_state).SerializeToString()
    self.switchboard_call_mock.return_value = response_byte

    self.assertEqual(state_value, self.uut.get_boolean_state())


if __name__ == "__main__":
  unit_test_case.main()
