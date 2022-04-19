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
import unittest
from unittest import mock

from gazoo_device import errors
from gazoo_device.capabilities.matter_clusters.interfaces import cluster_base
from gazoo_device.capabilities.matter_endpoints.interfaces import endpoint_base
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_FAKE_CLUSTER_NAME = "fake-cluster-name"
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
        switchboard_call=None,
        rpc_timeout_s=_FAKE_RPC_TIMEOUT_S)

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

  @mock.patch.object(
      endpoint_base.EndpointBase, "get_supported_cluster_flavors")
  def test_cluster_lazy_init_on_success(self, mock_get_supported_clusters):
    """Verifies cluster_lazy_init method on success."""
    fake_cluster_inst = mock.Mock(spec=cluster_base.ClusterBase)
    fake_cluster_cls = mock.Mock(__name__=_FAKE_CLUSTER_NAME,
                                 return_value=fake_cluster_inst)
    mock_get_supported_clusters.return_value = {fake_cluster_cls,}

    self.assertEqual(fake_cluster_inst,
                     self.uut.cluster_lazy_init(fake_cluster_cls))

  # TODO(gdm-authors) Unblock the check once b/228923824 is resolved
  @unittest.skip("Temporarily skip due to firmware issue.")
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


if __name__ == "__main__":
  fake_device_test_case.main()
