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

"""Matter cluster capability unit test for cluster_base module."""
from gazoo_device.capabilities.matter_clusters.interfaces import cluster_base
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_FAKE_DEVICE_NAME = "fake-device-name"
_FAKE_ENDPOINT_ID = 1
_FAKE_ATTRIBUTE = "fake_attribute"


class ClusterBaseTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for ClusterBase."""

  def setUp(self):
    super().setUp()
    self.uut = cluster_base.ClusterBase(
        device_name=_FAKE_DEVICE_NAME,
        endpoint_id=_FAKE_ENDPOINT_ID,
        read=None,
        write=None)

  def test_setattr_method_on_failure(self):
    """Verifies the overridden __setattr__ on failure.

    The on success scenarios are covered by the other cluster unit tests.
    """
    with self.assertRaisesRegex(
        AttributeError, f"Invalid attribute '{_FAKE_ATTRIBUTE}' to set"):
      self.uut.fake_attribute = 0


if __name__ == "__main__":
  fake_device_test_case.main()
