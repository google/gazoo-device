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

"""Matter endpoint capability unit test for matter_door_lock module."""
from unittest import mock
from gazoo_device.capabilities.matter_endpoints import door_lock
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_FAKE_DEVICE_NAME = "fake-device-name"
_FAKE_RPC_TIMEOUT_S = 10


class DoorLockEndpointTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for DoorLockEndpoint."""

  def setUp(self):
    super().setUp()
    self.uut = door_lock.DoorLockEndpoint(
        device_name=_FAKE_DEVICE_NAME,
        switchboard_call=None,
        rpc_timeout_s=_FAKE_RPC_TIMEOUT_S)

  @mock.patch.object(door_lock.DoorLockEndpoint, "cluster_lazy_init")
  def test_cluster_door_lock_cluster(self, mock_cluster_lazy_init):
    """Verifies creating door lock cluster on success."""
    fake_door_lock_cluster_inst = mock.Mock()
    mock_cluster_lazy_init.return_value = fake_door_lock_cluster_inst

    self.assertEqual(fake_door_lock_cluster_inst, self.uut.door_lock)


if __name__ == "__main__":
  fake_device_test_case.main()
