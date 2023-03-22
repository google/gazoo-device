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

"""Matter cluster unit test for illuminance_measurement_pw_rpc module."""
from unittest import mock

from gazoo_device.capabilities import matter_endpoints_accessor_pw_rpc
from gazoo_device.capabilities.matter_clusters import illuminance_measurement_pw_rpc
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_FAKE_DEVICE_NAME = "fake-device-name"
_FAKE_ENDPOINT_ID = 1
_FAKE_DATA = 0


class IlluminanceMeasurementClusterPwRpcTest(
    fake_device_test_case.FakeDeviceTestCase):
  """Unit test for IlluminanceMeasurementClusterPwRpc."""

  def setUp(self):
    super().setUp()
    self.fake_read = mock.Mock(spec=matter_endpoints_accessor_pw_rpc
                               .MatterEndpointsAccessorPwRpc.read)
    self.fake_read.return_value = mock.Mock(data_uint8=_FAKE_DATA)
    self.fake_write = mock.Mock(spec=matter_endpoints_accessor_pw_rpc
                                .MatterEndpointsAccessorPwRpc.write)
    self.uut = (
        illuminance_measurement_pw_rpc.IlluminanceMeasurementClusterPwRpc(
            device_name=_FAKE_DEVICE_NAME,
            endpoint_id=_FAKE_ENDPOINT_ID,
            read=self.fake_read,
            write=self.fake_write))

  def test_cluster_instance_is_not_none(self):
    """Verifies the cluster instance is not none."""
    self.assertIsNotNone(self.uut)

  def test_light_sensor_type(self):
    """Verifies the light sensor type property."""
    self.assertEqual(_FAKE_DATA, self.uut.light_sensor_type)

  def test_light_sensor_type_setter(self):
    """Verifies the light sensor type setter."""
    self.uut.light_sensor_type = _FAKE_DATA
    self.uut._write.assert_called_once()


if __name__ == "__main__":
  fake_device_test_case.main()
