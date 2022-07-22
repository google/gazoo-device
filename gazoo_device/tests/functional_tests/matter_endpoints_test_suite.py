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

"""Test suite for devices using the matter_endpoints capability."""
import logging
from typing import Type
from gazoo_device.tests.functional_tests.utils import gdm_test_base
from mobly import asserts


class MatterEndpointsPwRpcTestSuite(gdm_test_base.GDMTestBase):
  """Tests for the matter_endpoints capability."""

  @classmethod
  def is_applicable_to(cls, device_type: str,
                       device_class: Type[gdm_test_base.DeviceType],
                       device_name: str) -> bool:
    """Determines if this test suite can run on the given device."""
    return device_class.has_capabilities(["matter_endpoints"])

  @classmethod
  def requires_pairing(cls) -> bool:
    """Returns True if the device must be paired to run this test suite."""
    return False

  def test_list_method(self):
    """Tests if list method returns non-empty mapping."""
    asserts.assert_true(bool(self.device.matter_endpoints.list()),
                        "The returned endpoint list should not be empty.")

  def test_get_method(self):
    """Tests get method on success."""
    endpoint_ids = self.device.matter_endpoints.get_supported_endpoint_ids()
    asserts.assert_true(bool(endpoint_ids),
                        "The supported endpoint IDs should not be empty.")

    # Every endpoint ID works, so pick the first one.
    endpoint = self.device.matter_endpoints.get(endpoint_ids[0])
    asserts.assert_is_instance(endpoint.device_type_id, int)

  def test_get_supported_endpoints(self):
    """Tests get_supported_endpoints on success."""
    endpoints = self.device.matter_endpoints.get_supported_endpoints()
    asserts.assert_true(bool(endpoints),
                        "get_supported_endpoints should not return empty list.")

  def test_get_supported_endpoint_flavors(self):
    """Tests get_supported_endpoint_flavors on success."""
    endpoint_flavors = (
        self.device.matter_endpoints.get_supported_endpoint_flavors())
    asserts.assert_true(
        bool(endpoint_flavors),
        "get_supported_endpoint_flavors should not return empty list.")

  def test_get_supported_endpoints_and_clusters(self):
    """Tests get_supported_endpoints_and_clusters on success."""
    endpoints_and_clusters = (
        self.device.matter_endpoints.get_supported_endpoints_and_clusters())
    asserts.assert_true(
        bool(endpoints_and_clusters),
        "get_supported_endpoints_and_clusters should not return empty mapping.")

  def test_get_supported_endpoint_instances_and_cluster_flavors(self):
    """Tests get_supported_endpoint_instances_and_cluster_flavors on success."""
    endpoint_instances_and_cluster_flavors = (
        self.device.matter_endpoints.
        get_supported_endpoint_instances_and_cluster_flavors())
    asserts.assert_true(
        bool(endpoint_instances_and_cluster_flavors),
        "get_supported_endpoint_instances_and_cluster_flavors should not "
        "return empty mapping.")

  def test_log_endpoints_and_supported_clusters(self):
    """Logs endpoints and supported clusters for debugging purposes."""
    logging.info("%s endpoint to clusters supported by GDM:", self.device.name)
    for endpoint_id in self.device.matter_endpoints.list():
      endpoint_instance = self.device.matter_endpoints.get(endpoint_id)
      supported_cluster_names = endpoint_instance.get_supported_clusters()
      logging.info("\t%s: %s", endpoint_instance, supported_cluster_names)


if __name__ == "__main__":
  gdm_test_base.main()
