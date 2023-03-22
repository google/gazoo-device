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
"""Matter endpoints unit test."""
import itertools
from unittest import mock

from absl.testing import parameterized
from gazoo_device.capabilities import matter_endpoints_and_clusters
from gazoo_device.capabilities.matter_clusters.interfaces import cluster_base
from gazoo_device.capabilities.matter_endpoints.interfaces import endpoint_base
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.utility import common_utils

_FAKE_DEVICE_NAME = "fake-device-name"
_FAKE_ENDPOINT_ID = 1
_FAKE_RPC_TIMEOUT_S = 10

# Trim the PwRpc cluster capability names into alias names.
_CLUSTER_NAMES_PW_RPC = tuple(
    common_utils.title_to_snake_case(cluster.__name__).replace(
        "_cluster_pw_rpc", "")
    for cluster in matter_endpoints_and_clusters.SUPPORTED_CLUSTERS_PW_RPC)
_ENDPOINT_AND_CLUSTER_PRODUCT_PW_RPC = tuple(
    itertools.product(
        matter_endpoints_and_clusters.SUPPORTED_ENDPOINTS,
        _CLUSTER_NAMES_PW_RPC))
_ENDPOINT_AND_SUPPORTED_CLUSTER_PRODUCT_PW_RPC = tuple(
    (endpoint_class, cluster_name)
    for endpoint_class, cluster_name in _ENDPOINT_AND_CLUSTER_PRODUCT_PW_RPC
    if hasattr(endpoint_class, cluster_name))

# Trim the chip-tool cluster capability names into alias names.
_CLUSTER_NAMES_CHIP_TOOL = tuple(
    common_utils.title_to_snake_case(cluster.__name__).replace(
        "_cluster_chip_tool", "")
    for cluster in matter_endpoints_and_clusters.SUPPORTED_CLUSTERS_CHIP_TOOL)
_ENDPOINT_AND_CLUSTER_PRODUCT_CHIP_TOOL = tuple(
    itertools.product(
        matter_endpoints_and_clusters.SUPPORTED_ENDPOINTS,
        _CLUSTER_NAMES_CHIP_TOOL))
_ENDPOINT_AND_SUPPORTED_CLUSTER_PRODUCT_CHIP_TOOL = tuple(
    (endpoint_class, cluster_name)
    for endpoint_class, cluster_name in _ENDPOINT_AND_CLUSTER_PRODUCT_CHIP_TOOL
    if hasattr(endpoint_class, cluster_name))


class MatterEndpointsTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit tests for Matter endpoints.

  Cluster instance is only tested if it's supported on the endpoint.
  """

  @parameterized.parameters(*_ENDPOINT_AND_SUPPORTED_CLUSTER_PRODUCT_PW_RPC)
  @mock.patch.object(endpoint_base.EndpointBase, "cluster_lazy_init",
                     return_value=mock.Mock(spec=cluster_base.ClusterBase))
  def test_endpoint_and_cluster_pw_rpc(
      self, endpoint_class, cluster_name, mock_cluster_lazy_init):
    """Tests endpoint and cluster instance initialization for PigweedRPC."""
    uut = endpoint_class(
        device_name=_FAKE_DEVICE_NAME,
        identifier=_FAKE_ENDPOINT_ID,
        supported_clusters=(
            matter_endpoints_and_clusters.SUPPORTED_CLUSTERS_PW_RPC),
        read=None,
        write=None)
    self.assertEqual(
        getattr(uut, cluster_name), mock_cluster_lazy_init.return_value)

  @parameterized.parameters(*_ENDPOINT_AND_SUPPORTED_CLUSTER_PRODUCT_CHIP_TOOL)
  @mock.patch.object(endpoint_base.EndpointBase, "cluster_lazy_init",
                     return_value=mock.Mock(spec=cluster_base.ClusterBase))
  def test_endpoint_and_cluster_chip_tool(
      self, endpoint_class, cluster_name, mock_cluster_lazy_init):
    """Tests endpoint and cluster instance initialization for chip-tool."""
    uut = endpoint_class(
        device_name=_FAKE_DEVICE_NAME,
        identifier=_FAKE_ENDPOINT_ID,
        supported_clusters=(
            matter_endpoints_and_clusters.SUPPORTED_CLUSTERS_CHIP_TOOL),
        read=None,
        write=None)
    self.assertEqual(
        getattr(uut, cluster_name), mock_cluster_lazy_init.return_value)
