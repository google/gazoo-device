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

"""Matter cluster unit test for temperature_measurement_pw_rpc module."""
from unittest import mock

from gazoo_device.capabilities import matter_endpoints_accessor
from gazoo_device.capabilities.matter_clusters import temperature_measurement_pw_rpc
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_FAKE_DEVICE_NAME = "fake-device-name"
_FAKE_ENDPOINT_ID = 1
_FAKE_DATA = 1


class TemperatureMeasurementClusterPwRpcTest(
    fake_device_test_case.FakeDeviceTestCase):
  """Unit test for TemperatureMeasurementClusterPwRpc."""

  def setUp(self):
    super().setUp()
    fake_read = mock.Mock(
        spec=matter_endpoints_accessor.MatterEndpointsAccessor.read)
    self.uut = (
        temperature_measurement_pw_rpc.TemperatureMeasurementClusterPwRpc(
            device_name=_FAKE_DEVICE_NAME,
            endpoint_id=_FAKE_ENDPOINT_ID,
            read=fake_read,
            write=None))

  def test_measured_value_attribute(self):
    """Verifies the measured_value attribute on success."""
    self.uut._read.return_value = mock.Mock(data_int16=_FAKE_DATA)

    self.assertEqual(_FAKE_DATA, self.uut.measured_value)

  def test_min_measured_value_attribute(self):
    """Verifies the min_measured_value attribute on success."""
    fake_min_measured_value = (
        temperature_measurement_pw_rpc._MIN_MEASURED_UPPERBOUND+_FAKE_DATA)
    expected_value = (
        fake_min_measured_value - temperature_measurement_pw_rpc._ATTR_VAL_MAX)
    self.uut._read.return_value = mock.Mock(data_int16=fake_min_measured_value)

    self.assertEqual(expected_value, self.uut.min_measured_value)

  def test_max_measured_value_bitmap_attribute(self):
    """Verifies the max_measured_value attribute on success."""
    self.uut._read.return_value = mock.Mock(data_int16=_FAKE_DATA)

    self.assertEqual(_FAKE_DATA, self.uut.max_measured_value)


if __name__ == "__main__":
  fake_device_test_case.main()
