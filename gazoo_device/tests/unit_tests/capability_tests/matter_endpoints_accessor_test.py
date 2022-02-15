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

"""Capability unit test for matter_endpoints_accessor module."""
from unittest import mock

from gazoo_device.capabilities import matter_endpoints_accessor
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

import immutabledict

_FAKE_ENDPOINT_ID = 0
_FAKE_DEVICE_NAME = "fake-device-name"


class MatterEndpointsAccessorTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for MatterEndpointsAccessor."""

  def setUp(self):
    super().setUp()
    self.fake_endpoint_inst = mock.Mock()
    fake_endpoint_cls = mock.Mock(return_value=self.fake_endpoint_inst)
    self.fake_endpoint_id_to_cls = immutabledict.immutabledict({
        _FAKE_ENDPOINT_ID: fake_endpoint_cls
    })
    self.uut = matter_endpoints_accessor.MatterEndpointsAccessor(
        endpoint_id_to_class=self.fake_endpoint_id_to_cls,
        device_name=_FAKE_DEVICE_NAME)

  def test_get_endpoint(self):
    """Verifies the get endpoint method on success."""
    self.assertEqual(self.fake_endpoint_inst,
                     self.uut.get(endpoint_id=_FAKE_ENDPOINT_ID))

  def test_list_endpoints(self):
    """Verifies the list endpoints method on success."""
    self.assertEqual(self.fake_endpoint_id_to_cls,
                     self.uut.list())


if __name__ == "__main__":
  fake_device_test_case.main()
