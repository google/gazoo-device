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
"""Unit tests for the MatterControllerChipTool capability."""

from gazoo_device import errors
from gazoo_device.auxiliary_devices import raspberry_pi_matter_controller
from gazoo_device.capabilities.matter_clusters import basic_information_chip_tool
from gazoo_device.capabilities.matter_clusters import on_off_chip_tool
from gazoo_device.capabilities.matter_endpoints import on_off_light
from gazoo_device.capabilities.matter_endpoints.interfaces import endpoint_base
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.tests.unit_tests.utils import raspberry_pi_matter_controller_device_logs


class MatterEndpointsAccessorChipToolCapabilityTests(
    fake_device_test_case.FakeDeviceTestCase):
  """Unit test for MatterEndpointsAccessorChipTool capability implementation."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements("rpi_matter_controller-1234")
    self.device_config["persistent"]["console_port_name"] = "123.45.67.89"
    self.fake_responder.behavior_dict = (
        raspberry_pi_matter_controller_device_logs.DEFAULT_BEHAVIOR.copy())

    self.uut = raspberry_pi_matter_controller.RaspberryPiMatterController(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory)
    self._node_id = 1234
    self._endpoint = 1
    self.device_config["options"]["matter_node_id"] = self._node_id

  def test_get_endpoint(self):
    """Tests get_endpoint."""
    self.assertIsInstance(
        self.uut.matter_endpoints.get(self._endpoint),
        on_off_light.OnOffLightEndpoint)

  def test_list_endpoints(self):
    """Tests list."""
    endpoints = self.uut.matter_endpoints.list()
    self.assertLen(endpoints, 2)
    self.assertEqual(endpoints[self._endpoint], on_off_light.OnOffLightEndpoint)

  def test_get_endpoint_instance_by_class(self):
    """Tests get_endpoint_instance_by_class."""
    self.assertEqual(
        self.uut.matter_endpoints.get_endpoint_instance_by_class(
            on_off_light.OnOffLightEndpoint),
        self.uut.matter_endpoints.get(self._endpoint))

  def test_get_invalid_endpoint(self):
    """Tests get with invalid endpoint id."""
    with self.assertRaises(errors.DeviceError):
      self.uut.matter_endpoints.get(42)

  def test_get_invalid_endpoint_instance_by_class(self):
    """Tests get_endpoint_instance_by_class with invalid endpoint class."""
    with self.assertRaises(errors.DeviceError):
      self.uut.matter_endpoints.get_endpoint_instance_by_class(
          endpoint_base.EndpointBase)

  def test_reset(self):
    """Tests reset."""
    self.uut.matter_endpoints.list()
    self.assertNotEmpty(self.uut.matter_endpoints._endpoint_id_to_class)

    self.uut.matter_endpoints.get(self._endpoint)
    self.assertNotEmpty(self.uut.matter_endpoints._endpoints)

    self.uut.matter_endpoints.reset()
    self.assertEmpty(self.uut.matter_endpoints._endpoints)
    self.assertEmpty(self.uut.matter_endpoints._endpoint_id_to_class)
    self.assertEmpty(self.uut.matter_endpoints._endpoint_class_to_id)
    self.assertEmpty(self.uut.matter_endpoints._endpoint_id_to_clusters)
    self.assertEmpty(self.uut.matter_endpoints._endpoint_id_to_device_type_id)

  def test_has_endpoints(self):
    """Tests has_endpoints."""
    self.assertTrue(self.uut.matter_endpoints.has_endpoints(["on_off_light"]))

  def test_has_endpoints_invalid(self):
    """Tests has_endpoints with invalid endpoint name."""
    self.assertFalse(self.uut.matter_endpoints.has_endpoints(["fake_endpoint"]))

  def test_get_supported_endpoints(self):
    """Tests get_supported_endpoints."""
    supported_endpoints = self.uut.matter_endpoints.get_supported_endpoints()
    self.assertNotEmpty(supported_endpoints)
    self.assertIn("on_off_light", supported_endpoints)

  def test_get_supported_endpoints_and_clusters(self):
    """Tests get_supported_endpoints_and_clusters."""
    self.assertDictEqual(
        self.uut.matter_endpoints.get_supported_endpoints_and_clusters(),
        {0: ["basic_information_cluster"], 1: ["on_off_cluster"]})

  def test_get_supported_endpoint_instances_and_cluster_flavors(self):
    """Tests get_supported_endpoint_instances_and_cluster_flavors."""
    endpoints = self.uut.matter_endpoints.get_supported_endpoint_instances_and_cluster_flavors(
    )
    self.assertNotEmpty(endpoints)
    endpoint_clusters = list(endpoints.values())
    self.assertSetEqual(
        endpoint_clusters[0],
        set([basic_information_chip_tool.BasicInformationClusterChipTool]))
    self.assertSetEqual(
        endpoint_clusters[1],
        set([on_off_chip_tool.OnOffClusterChipTool]))

  def test_endpoint_id_to_clusters(self):
    """Tests endpoint_id_to_clusters property."""
    self.assertEmpty(self.uut.matter_endpoints._endpoint_id_to_clusters)
    self.assertNotEmpty(self.uut.matter_endpoints.endpoint_id_to_clusters)

  def test_endpoint_id_to_device_type_id(self):
    """Tests endpoint_id_to_device_type_id property."""
    self.assertEmpty(self.uut.matter_endpoints._endpoint_id_to_device_type_id)
    self.assertNotEmpty(self.uut.matter_endpoints.endpoint_id_to_device_type_id)
