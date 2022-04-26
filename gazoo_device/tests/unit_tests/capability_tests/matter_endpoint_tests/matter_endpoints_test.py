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

_FAKE_DEVICE_NAME = "fake-device-name"
_FAKE_ENDPOINT_ID = 1
_FAKE_RPC_TIMEOUT_S = 10


CLUSTER_NAMES = ("color", "door_lock", "level", "on_off")

ENDPOINT_AND_CLUSTER_PAIR = [
    dict(endpoint_class=endpoint_class, cluster_name=cluster_name)
    for endpoint_class, cluster_name in itertools.product(
        matter_endpoints_and_clusters.SUPPORTED_ENDPOINTS, CLUSTER_NAMES)]


class MatterEndpointsTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit tests for Matter endpoints.

  Cluster instance is only tested if it's supported on the endpoint.
  """

  @parameterized.parameters(ENDPOINT_AND_CLUSTER_PAIR)
  @mock.patch.object(endpoint_base.EndpointBase, "cluster_lazy_init")
  def test_endpoint_and_cluster(
      self, mock_cluster_lazy_init, endpoint_class, cluster_name):
    """Verifies the endpoint and cluster instance initialization."""
    uut = endpoint_class(
        device_name=_FAKE_DEVICE_NAME,
        identifier=_FAKE_ENDPOINT_ID,
        supported_clusters=set(),
        switchboard_call=None,
        rpc_timeout_s=_FAKE_RPC_TIMEOUT_S)
    if hasattr(uut, cluster_name):
      fake_cluster_instance = mock.Mock(spec=cluster_base.ClusterBase)
      mock_cluster_lazy_init.return_value = fake_cluster_instance
      cluster = getattr(uut, cluster_name)
      self.assertEqual(fake_cluster_instance, cluster)
    else:
      self.skipTest(f"{cluster_name} is not supported on {uut}.")
