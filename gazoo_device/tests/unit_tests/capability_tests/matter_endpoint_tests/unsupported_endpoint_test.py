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

"""Matter endpoint capability unit test for unsupported_endpoint module."""
from gazoo_device.capabilities.matter_endpoints import unsupported_endpoint
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_FAKE_DEVICE_NAME = "fake-device-name"
_FAKE_ENDPOINT_ID = 1
_FAKE_DEVICE_TYPE_ID = 1


class UnsupportedEndpointTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for UnsupportedEndpoint."""

  def setUp(self):
    super().setUp()
    self.uut = unsupported_endpoint.UnsupportedEndpoint(
        device_name=_FAKE_DEVICE_NAME,
        identifier=_FAKE_ENDPOINT_ID,
        device_type_id=_FAKE_DEVICE_TYPE_ID,
        supported_clusters=set(),
        read=None,
        write=None)

  def test_name_property(self):
    """Verifies the name property on success."""
    expected_name = f"Unsupported endpoint (device type: {_FAKE_DEVICE_TYPE_ID})"
    self.assertEqual(expected_name, self.uut.name)


if __name__ == "__main__":
  fake_device_test_case.main()
