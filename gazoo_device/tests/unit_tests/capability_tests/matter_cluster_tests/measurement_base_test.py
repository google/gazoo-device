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

"""Matter cluster unit test for measurement_base module."""
from unittest import mock
from gazoo_device import errors
from gazoo_device.capabilities import matter_endpoints_accessor_pw_rpc
from gazoo_device.capabilities.matter_clusters.interfaces import measurement_base
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_FAKE_DEVICE_NAME = "fake-device-name"
_FAKE_ENDPOINT_ID = 1
_FAKE_ATTRIBUTE_ID = 0
_FAKE_DATA = 1
_FAKE_DATA2 = 2
_FAKE_CLUSTER_ID = 0


class FakeMeasurementCluster(measurement_base.MeasurementClusterBase):
  """Fake Measurement cluster."""
  CLUSTER_ID = _FAKE_CLUSTER_ID
  MATTER_CLUSTER = mock.Mock(ID=_FAKE_CLUSTER_ID)


class MeasurementClusterBaseTest(
    fake_device_test_case.FakeDeviceTestCase):
  """Unit test for MeasurementClusterBase."""

  def setUp(self):
    super().setUp()
    fake_read = mock.Mock(spec=matter_endpoints_accessor_pw_rpc
                          .MatterEndpointsAccessorPwRpc.read)
    fake_read.return_value = mock.Mock(data_int16=_FAKE_DATA)
    fake_write = mock.Mock(spec=matter_endpoints_accessor_pw_rpc
                           .MatterEndpointsAccessorPwRpc.write)
    self.uut = FakeMeasurementCluster(
        device_name=_FAKE_DEVICE_NAME,
        endpoint_id=_FAKE_ENDPOINT_ID,
        read=fake_read,
        write=fake_write)

  @mock.patch.object(measurement_base.MeasurementClusterBase,
                     "_read_value",
                     return_value=_FAKE_DATA)
  def test_read_measured_value_attribute(self, mock_read):
    """Verifies reading measured_value attribute on success."""
    self.assertEqual(_FAKE_DATA, self.uut.measured_value)
    mock_read.assert_called_once()

  @mock.patch.object(measurement_base.MeasurementClusterBase, "_write_value")
  def test_write_measured_value_attribute(self, mock_write):
    """Verifies writing measured_value attribute on success."""
    self.uut.measured_value = _FAKE_DATA
    mock_write.assert_called_once()

  @mock.patch.object(measurement_base.MeasurementClusterBase,
                     "_read_value",
                     return_value=_FAKE_DATA)
  def test_read_min_measured_value_attribute(self, mock_read):
    """Verifies reading min_measured_value attribute on success."""
    self.assertEqual(_FAKE_DATA, self.uut.min_measured_value)
    mock_read.assert_called_once()

  @mock.patch.object(measurement_base.MeasurementClusterBase, "_write_value")
  def test_write_min_measured_value_attribute(self, mock_write):
    """Verifies writing min_measured_value attribute on success."""
    self.uut.min_measured_value = _FAKE_DATA
    mock_write.assert_called_once()

  @mock.patch.object(measurement_base.MeasurementClusterBase,
                     "_read_value",
                     return_value=_FAKE_DATA)
  def test_read_max_measured_value_attribute(self, mock_read):
    """Verifies reading max_measured_value attribute on success."""
    self.assertEqual(_FAKE_DATA, self.uut.max_measured_value)
    mock_read.assert_called_once()

  @mock.patch.object(measurement_base.MeasurementClusterBase, "_write_value")
  def test_write_max_measured_value_attribute(self, mock_write):
    """Verifies writing max_measured_value attribute on success."""
    self.uut.max_measured_value = _FAKE_DATA
    mock_write.assert_called_once()

  def test_read_value_method_on_success(self):
    """Verifies _read_value method on success."""
    self.assertEqual(_FAKE_DATA, self.uut._read_value(_FAKE_ATTRIBUTE_ID))

  def test_write_value_method_on_success(self):
    """Verifies _write_value method on success."""
    self.uut._write_value(_FAKE_ATTRIBUTE_ID, _FAKE_DATA)

  def test_write_value_method_on_failure(self):
    """Verifies _write_value method on failure."""
    with self.assertRaisesRegex(errors.DeviceError, "didn't change"):
      self.uut._write_value(_FAKE_ATTRIBUTE_ID, _FAKE_DATA2)


if __name__ == "__main__":
  fake_device_test_case.main()
