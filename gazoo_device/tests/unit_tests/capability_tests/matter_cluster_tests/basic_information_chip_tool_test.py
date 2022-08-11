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
"""Matter cluster capability unit test for basic_information_chip_tool module."""

import functools
from unittest import mock

from absl.testing import parameterized
from gazoo_device.capabilities import matter_controller_chip_tool
from gazoo_device.capabilities.matter_clusters import basic_information_chip_tool
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_MATTER_NODE_ID = 1234
_BASIC_INFORMATION_ENDPOINT_ID = 0


class BasicInformationClusterChipToolTest(
    fake_device_test_case.FakeDeviceTestCase):
  """Unit test for BasicInformationClusterChipTool."""

  def setUp(self):
    super().setUp()
    self._node_id = _MATTER_NODE_ID
    self._endpoint_id = _BASIC_INFORMATION_ENDPOINT_ID

    self.fake_read = mock.Mock(
        spec=functools.partial(
            matter_controller_chip_tool.MatterControllerChipTool.read,
            self._node_id))
    self.fake_write = mock.Mock(
        spec=functools.partial(
            matter_controller_chip_tool.MatterControllerChipTool.write,
            self._node_id))
    self.fake_send = mock.Mock(
        spec=functools.partial(
            matter_controller_chip_tool.MatterControllerChipTool.send,
            self._node_id))
    self.uut = basic_information_chip_tool.BasicInformationClusterChipTool(
        device_name="rpi_matter_controller-1234",
        endpoint_id=self._endpoint_id,
        read=self.fake_read,
        write=self.fake_write,
        send=self.fake_send)

  @parameterized.named_parameters([
      ("data_model_revision", "data-model-revision", 1),
      ("vendor_name", "vendor-name", "TEST_VENDOR"),
      ("vendor_id", "vendor-id", 1234),
      ("product_name", "product-name", "TEST_PRODUCT"),
      ("product_id", "product-id", 4),
      ("node_label", "node-label", ""),
      ("location", "location", "US"),
      ("hardware_version", "hardware-version", 5),
      ("hardware_version_string", "hardware-version-string", "TEST_VERSION"),
      ("software_version", "software-version", 7),
      ("software_version_string", "software-version-string", "TEST_VERSION"),
      ("capability_minima", "capability-minima", 0),
  ])
  def test_read_attribute(self, attribute_name, value):
    """Tests reading attribute."""
    self.fake_read.return_value = value
    self.assertEqual(
        getattr(self.uut, attribute_name.replace("-", "_")),
        self.fake_read.return_value)
    self.fake_read.assert_called_once_with(
        self._endpoint_id, "basic", attribute_name)


if __name__ == "__main__":
  fake_device_test_case.main()
