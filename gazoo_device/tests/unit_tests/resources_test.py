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

"""Unit tests for resources.py."""
import os.path
from unittest import mock

from absl.testing import parameterized
from gazoo_device import resources
from gazoo_device.tests.unit_tests.utils import unit_test_case


class ResourcesTests(unit_test_case.UnitTestCase):
  """Unit tests for resources.py."""

  def test_extract_external(self):
    """Tests extract() in the open-source pip distribution."""
    resource_path = "bin/some_binary"
    self.assertEqual(
        resources.extract(resource_path),
        os.path.join(resources._PACKAGE_PATH, resource_path))


if __name__ == "__main__":
  unit_test_case.main()
