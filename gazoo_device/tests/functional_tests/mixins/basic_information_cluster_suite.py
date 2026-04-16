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

"""Mixin for Matter Basic Information cluster test suite."""
from mobly import asserts


class BasicInformationClusterTestSuite:
  """Mixin for Matter Basic Information cluster test suite.

  The mixin assumes self.endpoint is set.
  """

  def test_model_revision_attribute(self):
    """Tests the model revision attribute."""
    asserts.assert_is_instance(
        self.endpoint.basic_information.data_model_revision, int)

  def test_vendor_name_attribute(self):
    """Tests the vendor name attribute."""
    asserts.assert_is_instance(self.endpoint.basic_information.vendor_name, str)

  def test_vendor_id_attribute(self):
    """Tests the vendor ID attribute."""
    asserts.assert_is_instance(self.endpoint.basic_information.vendor_id, int)

  def test_product_name_attribute(self):
    """Tests the product name attribute."""
    asserts.assert_is_instance(
        self.endpoint.basic_information.product_name, str)

  def test_product_id_attribute(self):
    """Tests the product ID attribute."""
    asserts.assert_is_instance(self.endpoint.basic_information.product_id, int)

  def test_node_label_attribute(self):
    """Tests the nodel label attribute."""
    asserts.assert_is_instance(self.endpoint.basic_information.node_label, str)

  def test_location_attribute(self):
    """Tests the location attribute."""
    asserts.assert_is_instance(self.endpoint.basic_information.location, str)

  def test_hardware_version_attribute(self):
    """Tests the hardware version attribute."""
    asserts.assert_is_instance(
        self.endpoint.basic_information.hardware_version, int)

  def test_hardware_version_string_attribute(self):
    """Tests the hardware version string attribute."""
    asserts.assert_is_instance(
        self.endpoint.basic_information.hardware_version_string, str)

  def test_software_version_attribute(self):
    """Tests the software version attribute."""
    asserts.assert_is_instance(
        self.endpoint.basic_information.software_version, int)

  def test_software_version_string_attribute(self):
    """Tests the software version string attribute."""
    asserts.assert_is_instance(
        self.endpoint.basic_information.software_version_string, str)

  def test_manufacturing_date(self):
    """Tests the manufacturing_date attribute."""
    asserts.assert_is_instance(
        self.endpoint.basic_information.manufacturing_date, str)

  def test_part_number_attribute(self):
    """Tests the part_number attribute."""
    asserts.assert_is_instance(self.endpoint.basic_information.part_number, str)

  def test_product_url_attribute(self):
    """Tests the product_url attribute."""
    asserts.assert_is_instance(self.endpoint.basic_information.product_url, str)

  def test_product_label_attribute(self):
    """Tests the product_label attribute."""
    asserts.assert_is_instance(
        self.endpoint.basic_information.product_label, str)

  def test_serial_number_attribute(self):
    """Tests the serial_number attribute."""
    asserts.assert_is_instance(
        self.endpoint.basic_information.serial_number, str)

  def test_unique_id_attribute(self):
    """Tests the unique_id attribute."""
    asserts.assert_is_instance(self.endpoint.basic_information.unique_id, str)
