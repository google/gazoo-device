# Copyright 2020 Google LLC
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

"""Test suite for devices using the shell_ssh  capability."""
import traceback

from mobly import asserts
from functional_tests import gdm_test_base

SUCCESS_RETURN_CODE = 0


class ShellSshTestSuite(gdm_test_base.GDMTestBase):
    """Tests for the shell_ssh capability."""

    @classmethod
    def is_applicable_to(cls, device_type, device_class, device_name):
        """Determine if this test suite can run on the given device."""
        return device_class.has_capabilities(["shell_ssh"])

    @classmethod
    def requires_pairing(cls):
        """Returns True if the device in the testbed must be paired to run this test suite."""
        return False

    def test_3301_shell_ssh_capability_with_return_code(self):
        """Test case for shell_ssh capability to verify command completes successfully."""
        try:
            response, code = self.device.shell_capability.shell(self.test_config["shell_cmd"],
                                                                include_return_code=True)
            asserts.assert_equal(code, SUCCESS_RETURN_CODE)
        except Exception:
            traceback_message = traceback.format_exc()
            asserts.fail("Error happened during call to shell_ssh capability shell method "
                         + traceback_message)


if __name__ == "__main__":
    gdm_test_base.main()
