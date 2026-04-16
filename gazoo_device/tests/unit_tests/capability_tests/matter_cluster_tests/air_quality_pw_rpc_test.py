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

"""Matter cluster capability unit test for air_quality_pw_rpc module."""
from unittest import mock

from absl.testing import parameterized
from gazoo_device.capabilities import matter_endpoints_accessor_pw_rpc
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters import air_quality_pw_rpc
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_FAKE_DEVICE_NAME = "fake-device-name"
_FAKE_ENDPOINT_ID = 1


class AirQualityClusterPwRpcTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for AirQualityClusterPwRpc."""

  def setUp(self):
    super().setUp()
    self.fake_read = mock.Mock(spec=matter_endpoints_accessor_pw_rpc
                               .MatterEndpointsAccessorPwRpc.read)
    self.fake_write = mock.Mock(spec=matter_endpoints_accessor_pw_rpc
                                .MatterEndpointsAccessorPwRpc.write)
    self.uut = air_quality_pw_rpc.AirQualityClusterPwRpc(
        device_name=_FAKE_DEVICE_NAME,
        endpoint_id=_FAKE_ENDPOINT_ID,
        read=self.fake_read,
        write=self.fake_write)

  @parameterized.named_parameters(
      ("unknown_air_quality", 0, matter_enums.AirQualityEnum.UNKNOWN),
      ("good_air_quality", 1, matter_enums.AirQualityEnum.GOOD),
      ("fair_air_quality", 2, matter_enums.AirQualityEnum.FAIR),
      ("moderate_air_quality", 3, matter_enums.AirQualityEnum.MODERATE),
      ("poor_air_quality", 4, matter_enums.AirQualityEnum.POOR),
      ("very_poor_air_quality", 5, matter_enums.AirQualityEnum.VERY_POOR),
      ("extremely_poor_air_quality", 6,
       matter_enums.AirQualityEnum.EXTREMELY_POOR))
  def test_air_quality_attribute(self, air_quality_type, expected_type):
    """Verifies the air_quality attribute on success."""
    self.fake_read.return_value = mock.Mock(data_uint8=air_quality_type)
    self.assertEqual(expected_type, self.uut.air_quality)

  @parameterized.named_parameters(
      ("unknown_air_quality", matter_enums.AirQualityEnum.UNKNOWN),
      ("good_air_quality", matter_enums.AirQualityEnum.GOOD),
      ("fair_air_quality", matter_enums.AirQualityEnum.FAIR),
      ("moderate_air_quality", matter_enums.AirQualityEnum.MODERATE),
      ("poor_air_quality", matter_enums.AirQualityEnum.POOR),
      ("very_poor_air_quality", matter_enums.AirQualityEnum.VERY_POOR),
      ("extremely_poor_air_quality",
       matter_enums.AirQualityEnum.EXTREMELY_POOR))
  def test_write_air_quality_attribute_success(self, air_quality_type):
    """Verifies write the air_quality attribute on success."""
    self.uut.air_quality = air_quality_type
    self.fake_write.assert_called_once()


if __name__ == "__main__":
  fake_device_test_case.main()
