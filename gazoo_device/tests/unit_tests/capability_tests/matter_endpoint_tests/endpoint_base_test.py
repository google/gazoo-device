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

"""Matter endpoint capability unit test for endpoint_base module."""
from unittest import mock

from gazoo_device import errors
from gazoo_device.capabilities.matter_clusters.interfaces import cluster_base
from gazoo_device.capabilities.matter_endpoints.interfaces import endpoint_base
from gazoo_device.protos import attributes_service_pb2
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_FAKE_CLUSTER_NAME = "on_off_cluster"
_FAKE_DEVICE_NAME = "fake-device-name"
_FAKE_ENDPOINT_ID = 1
_FAKE_ENDPOINT_NAME = "fake-endpoint-name"
_FAKE_RPC_TIMEOUT_S = 0


class EndpointBaseTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for EndpointBase."""

  def setUp(self):
    super().setUp()
    self.fake_cluster_cls = mock.Mock(spec=cluster_base.ClusterBase)
    self.fake_cluster_cls.get_capability_name.return_value = _FAKE_CLUSTER_NAME
    self.uut = endpoint_base.EndpointBase(
        device_name=_FAKE_DEVICE_NAME,
        identifier=_FAKE_ENDPOINT_ID,
        supported_clusters={self.fake_cluster_cls,},
        read=None,
        write=None)

  def test_endpoint_id(self):
    """Verifies endpoint ID property."""
    self.assertEqual(_FAKE_ENDPOINT_ID, self.uut.id)

  @mock.patch.object(
      endpoint_base.EndpointBase,
      "get_capability_name",
      return_value=_FAKE_ENDPOINT_NAME)
  def test_endpoint_name(self, mock_get_capability_name):
    """Verifies endpoint name property."""
    self.assertEqual(_FAKE_ENDPOINT_NAME, self.uut.name)

  def test_device_type_id(self):
    """Verifies device_type_id property."""
    self.assertIsNone(self.uut.device_type_id)

  @mock.patch.object(
      endpoint_base.EndpointBase, "get_supported_cluster_flavors")
  def test_cluster_lazy_init_on_success(self, mock_get_supported_clusters):
    """Verifies cluster_lazy_init method on success."""
    cluster_id = attributes_service_pb2.ClusterType.ZCL_COLOR_CONTROL_CLUSTER_ID
    fake_cluster_inst = mock.Mock(spec=cluster_base.ClusterBase)
    fake_cluster_cls = mock.Mock(__name__=_FAKE_CLUSTER_NAME,
                                 return_value=fake_cluster_inst)
    fake_cluster_cls.CLUSTER_ID = cluster_id
    mock_get_supported_clusters.return_value = {fake_cluster_cls,}

    self.assertEqual(fake_cluster_inst, self.uut.cluster_lazy_init(cluster_id))

  @mock.patch.object(
      endpoint_base.EndpointBase,
      "get_capability_name",
      return_value=_FAKE_ENDPOINT_NAME)
  @mock.patch.object(
      endpoint_base.EndpointBase, "get_supported_cluster_flavors")
  def test_cluster_lazy_init_on_failure(
      self, mock_get_supported_clusters, mock_get_capability_name):
    """Verifies cluster_lazy_init method on failure."""
    mock_get_supported_clusters.return_value = set()
    fake_cluster_cls = mock.Mock(spec=cluster_base.ClusterBase)
    error_message = (f"{_FAKE_DEVICE_NAME} does not support cluster "
                     f"{fake_cluster_cls} on endpoint {_FAKE_ENDPOINT_NAME}")

    with self.assertRaisesRegex(errors.DeviceError, error_message):
      self.uut.cluster_lazy_init(fake_cluster_cls)

  def test_get_supported_clusters(self):
    """Verifies get_supported_clusters on success."""
    self.assertEqual([_FAKE_CLUSTER_NAME], self.uut.get_supported_clusters())

  def test_get_supported_cluster_flavors(self):
    """Verifies get_supported_cluster_flavors on success."""
    self.assertEqual(
        {self.fake_cluster_cls,}, self.uut.get_supported_cluster_flavors())

  def test_has_clusters_on_success(self):
    """Verifies has_clusters on success."""
    self.assertTrue(self.uut.has_clusters(["on_off"]))
    self.assertFalse(self.uut.has_clusters(["door_lock"]))

  def test_has_clusters_on_failure(self):
    """Verifies has_clusters on failure."""
    error_message = "Cluster invalid_cluster is not recognized"
    with self.assertRaisesRegex(errors.DeviceError, error_message):
      self.uut.has_clusters(["invalid_cluster"])

  @mock.patch.object(
      endpoint_base.EndpointBase,
      "get_capability_name",
      return_value=_FAKE_ENDPOINT_NAME)
  def test_str_representation(self, mock_get_capability_name):
    """Verifies __str__ representation on success."""
    expected_str = (f"{_FAKE_ENDPOINT_NAME} (endpoint ID: {_FAKE_ENDPOINT_ID})"
                    f" on {_FAKE_DEVICE_NAME}")
    self.assertEqual(expected_str, str(self.uut))


if __name__ == "__main__":
  fake_device_test_case.main()
