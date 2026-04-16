# Copyright 2023 Google LLC
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

"""Matter cluster capability unit test for basic_information_pw_rpc module."""
from unittest import mock

from absl.testing import parameterized
from gazoo_device.capabilities import matter_endpoints_accessor_pw_rpc
from gazoo_device.capabilities.matter_clusters import basic_information_pw_rpc
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

from gazoo_device.utility import tlv_utils


class BasicInformationClusterPwRpcTest(
    fake_device_test_case.FakeDeviceTestCase):
  """Unit test for BasicInformationClusterPwRpc."""

  def setUp(self):
    super().setUp()
    self.fake_read = mock.Mock(spec=matter_endpoints_accessor_pw_rpc
                               .MatterEndpointsAccessorPwRpc.read)
    self.uut = basic_information_pw_rpc.BasicInformationClusterPwRpc(
        device_name="fake-device-name",
        endpoint_id=1,
        read=self.fake_read,
        write=None)

  @parameterized.parameters(
      ("data_model_revision",),
      ("vendor_name",),
      ("vendor_id",),
      ("product_name",),
      ("product_id",),
      ("node_label",),
      ("location",),
      ("hardware_version",),
      ("hardware_version_string",),
      ("software_version",),
      ("software_version_string"),
      ("manufacturing_date",),
      ("part_number",),
      ("product_url",),
      ("product_label",),
      ("serial_number",),
      ("unique_id",),)
  @mock.patch.object(
      basic_information_pw_rpc.BasicInformationClusterPwRpc,
      "_get_attribute_value", return_value="mock_value")
  def test_basic_information_attribute(
      self, attribute_name, mock_get_attribute_value):
    """Verifies the basic information attribute."""
    self.assertEqual("mock_value", getattr(self.uut, attribute_name))
    mock_get_attribute_value.assert_called_once()

  def test_get_attribute_value_has_field(self):
    """Verifies _get_attribute_value method on success with data field."""
    mock_data = mock.Mock(data_uint16=0)
    mock_data.HasField.return_value = True
    self.fake_read.return_value = mock_data
    self.assertEqual(0, self.uut._get_attribute_value(
        attribute_id=0, attribute_type=basic_information_pw_rpc.UINT16_TYPE))

  @parameterized.parameters(
      ({"Any": {1: [{1: {0: 1982833481, 1: [0, 40, 1], 2: "TEST_VENDOR"}}]}},
       "TEST_VENDOR"),
      ({"data": "data"}, "{'data': 'data'}"))
  @mock.patch.object(tlv_utils, "TLVReader")
  def test_get_attribute_value(
      self, mock_tlv_value, expected_output, mock_tlv_reader):
    """Verifies _get_attribute_value method on success with TLV data."""
    mock_tlv_reader.return_value.get.return_value = mock_tlv_value
    mock_data = mock.Mock(tlv_data=0)
    mock_data.HasField.return_value = False
    self.fake_read.return_value = mock_data
    self.assertEqual(expected_output, self.uut._get_attribute_value(0, 0))


if __name__ == "__main__":
  fake_device_test_case.main()
