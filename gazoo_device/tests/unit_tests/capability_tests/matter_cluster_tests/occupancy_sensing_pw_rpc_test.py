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

"""Matter cluster capability unit test for occupancy_sensing_pw_rpc module."""
from unittest import mock

from gazoo_device import errors
from gazoo_device.capabilities import matter_endpoints_accessor_pw_rpc
from gazoo_device.capabilities.matter_clusters import occupancy_sensing_pw_rpc
from gazoo_device.protos import attributes_service_pb2
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_FAKE_DEVICE_NAME = "fake-device-name"
_FAKE_ENDPOINT_ID = 1
_FAKE_DATA = 1
_FAKE_DATA2 = 2


class OccupancySensingClusterPwRpcTest(fake_device_test_case.FakeDeviceTestCase
                                      ):
  """Unit test for OccupancySensingClusterPwRpc."""

  def setUp(self):
    super().setUp()
    self.fake_read = mock.Mock(
        spec=matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc.read)
    self.fake_write = mock.Mock(spec=matter_endpoints_accessor_pw_rpc
                                .MatterEndpointsAccessorPwRpc.write)
    self.fake_read.return_value = mock.Mock(data_uint8=_FAKE_DATA)
    self.uut = occupancy_sensing_pw_rpc.OccupancySensingClusterPwRpc(
        device_name=_FAKE_DEVICE_NAME,
        endpoint_id=_FAKE_ENDPOINT_ID,
        read=self.fake_read,
        write=self.fake_write)

  def test_occupancy_attribute(self):
    """Verifies the occupancy attribute on success."""
    self.assertEqual(_FAKE_DATA, self.uut.occupancy)

  def test_writing_occupancy_attribute_success(self):
    """Verifies writing the occupancy attribute on success."""
    self.uut.occupancy = _FAKE_DATA
    self.fake_write.assert_called_once()

  def test_writing_occupancy_attribute_failure(self):
    """Verifies writing the occupancy attribute on failure."""
    self.fake_read.return_value = attributes_service_pb2.AttributeData(
        data_uint8=_FAKE_DATA2)
    with self.assertRaisesRegex(errors.DeviceError, "didn't change"):
      self.uut.occupancy = _FAKE_DATA

  def test_occupancy_sensor_type_attribute(self):
    """Verifies the occupancy_sensor_type attribute on success."""
    self.assertEqual(_FAKE_DATA, self.uut.occupancy_sensor_type)

  def test_occupancy_sensor_type_bitmap_attribute(self):
    """Verifies the occupancy_sensor_type_bitmap attribute on success."""
    self.assertEqual(_FAKE_DATA, self.uut.occupancy_sensor_type_bitmap)


if __name__ == "__main__":
  fake_device_test_case.main()
