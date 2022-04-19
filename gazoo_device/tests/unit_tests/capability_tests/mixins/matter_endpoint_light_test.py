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

"""Mixin for Matter lighting endpoint unit test."""
from unittest import mock

from gazoo_device.capabilities.matter_endpoints.interfaces import endpoint_base

FAKE_DEVICE_NAME = "fake-device-name"
FAKE_ENDPOINT_ID = 1
FAKE_RPC_TIMEOUT_S = 10


class LightEndpointTest:
  """Mixin for Matter Lighting category endpoint unit tests.

  Assumes self.uut is set.
  """

  @mock.patch.object(endpoint_base.EndpointBase, "cluster_lazy_init")
  def test_cluster_on_off_cluster(self, mock_cluster_lazy_init):
    """Verifies creating on_off cluster on success."""
    fake_on_off_cluster_inst = mock.Mock()
    mock_cluster_lazy_init.return_value = fake_on_off_cluster_inst

    self.assertEqual(fake_on_off_cluster_inst, self.uut.on_off)

  @mock.patch.object(endpoint_base.EndpointBase, "cluster_lazy_init")
  def test_cluster_level_control_cluster(self, mock_cluster_lazy_init):
    """Verifies creating level control cluster on success."""
    fake_level_cluster_inst = mock.Mock()
    mock_cluster_lazy_init.return_value = fake_level_cluster_inst

    self.assertEqual(fake_level_cluster_inst, self.uut.level)

  @mock.patch.object(endpoint_base.EndpointBase, "cluster_lazy_init")
  def test_cluster_color_control_cluster(self, mock_cluster_lazy_init):
    """Verifies creating color control cluster on success."""
    fake_color_cluster_inst = mock.Mock()
    mock_cluster_lazy_init.return_value = fake_color_cluster_inst

    self.assertEqual(fake_color_cluster_inst, self.uut.color)
