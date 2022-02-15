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

"""Tests for example_extension_package."""
from absl.testing import absltest
import gazoo_device

import example_extension_package

_EXAMPLE_CONTROLLER_DEVICE_TYPE = (
    example_extension_package.example_linux_device.ExampleLinuxDevice
    .DEVICE_TYPE)


class ExampleExtensionPackageTest(absltest.TestCase):
  """Unit tests for the example extension package."""

  def test_registration(self):
    """Test that the extension package can be registered with gazoo_device."""
    self.assertNotIn(
        _EXAMPLE_CONTROLLER_DEVICE_TYPE,
        gazoo_device.Manager.get_supported_device_types(),
        f"{_EXAMPLE_CONTROLLER_DEVICE_TYPE!r} should not be known by Manager "
        "before the package is registered")

    gazoo_device.register(example_extension_package)

    self.assertIn(
        _EXAMPLE_CONTROLLER_DEVICE_TYPE,
        gazoo_device.Manager.get_supported_device_types(),
        f"{_EXAMPLE_CONTROLLER_DEVICE_TYPE!r} should be known by Manager "
        "after the package is registered")


if __name__ == "__main__":
  absltest.main()
