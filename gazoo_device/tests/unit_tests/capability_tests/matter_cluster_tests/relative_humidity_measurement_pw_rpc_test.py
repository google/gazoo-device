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

"""Matter cluster unit test for relative_humidity_measurement_pw_rpc module."""
from gazoo_device.capabilities.matter_clusters import relative_humidity_measurement_pw_rpc
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_FAKE_DEVICE_NAME = "fake-device-name"
_FAKE_ENDPOINT_ID = 1


class RelativeHumidityMeasurementClusterPwRpcTest(
    fake_device_test_case.FakeDeviceTestCase):
  """Unit test for RelativeHumidityMeasurementClusterPwRpc."""

  def setUp(self):
    super().setUp()
    self.uut = (
        relative_humidity_measurement_pw_rpc.
        RelativeHumidityMeasurementClusterPwRpc(
            device_name=_FAKE_DEVICE_NAME,
            endpoint_id=_FAKE_ENDPOINT_ID,
            read=None,
            write=None))

  def test_cluster_instance_is_not_none(self):
    """Verifies the cluster instance is not none."""
    self.assertIsNotNone(self.uut)


if __name__ == "__main__":
  fake_device_test_case.main()
