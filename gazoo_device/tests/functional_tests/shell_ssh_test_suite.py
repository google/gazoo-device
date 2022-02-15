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

"""Test suite for devices using the shell_ssh capability."""
from typing import Tuple, Type
from gazoo_device.tests.functional_tests.utils import gdm_test_base
from mobly import asserts

_SUCCESS_RETURN_CODE = 0


class ShellSshTestSuite(gdm_test_base.GDMTestBase):
  """Functional tests for the shell_ssh capability."""

  @classmethod
  def is_applicable_to(cls, device_type: str,
                       device_class: Type[gdm_test_base.DeviceType],
                       device_name: str) -> bool:
    """Determine if this test suite can run on the given device."""
    return device_class.has_capabilities(["shell_ssh"])

  @classmethod
  def requires_pairing(cls) -> bool:
    """Returns True if the device must be paired to run this test suite."""
    return False

  @classmethod
  def required_test_config_variables(cls) -> Tuple[str, ...]:
    """Returns keys required to be present in the functional test config."""
    return ("shell_cmd",)

  def test_shell_with_return_code(self):
    """Tests shell() command execution with return code."""
    response, code = self.device.shell_capability.shell(
        self.test_config["shell_cmd"], include_return_code=True)
    asserts.assert_true(response, "response should contain characters")
    asserts.assert_is_instance(response, str)
    asserts.assert_equal(code, _SUCCESS_RETURN_CODE)


if __name__ == "__main__":
  gdm_test_base.main()
