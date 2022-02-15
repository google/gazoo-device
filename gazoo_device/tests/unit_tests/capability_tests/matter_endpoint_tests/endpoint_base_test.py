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

from gazoo_device.capabilities.matter_endpoints.interfaces import endpoint_base
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_FAKE_CLUSTER_NAME = "fake-cluster-name"
_FAKE_DEVICE_NAME = "fake-device-name"


class EndpointBaseTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for EndpointBase."""

  def setUp(self):
    super().setUp()
    self.uut = endpoint_base.EndpointBase(device_name=_FAKE_DEVICE_NAME)

  def test_cluster_lazy_init_on_success(self):
    """Verifies cluster_lazy_init method on success."""
    fake_cluster_inst = mock.Mock()
    fake_cluster_cls = mock.Mock(__name__=_FAKE_CLUSTER_NAME,
                                 return_value=fake_cluster_inst)

    self.assertEqual(fake_cluster_inst,
                     self.uut.cluster_lazy_init(fake_cluster_cls))


if __name__ == "__main__":
  fake_device_test_case.main()
