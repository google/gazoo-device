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

"""Test suite for devices performing a parallel upgrade.

Usage:
   Example: python parallel_test_suite.py -t One-<DEVICE>

Requirements:
   The "<DEVICE>_test_config.json" file should have the following entry
       "<DEVICE>_forced_upgrade": true
"""

from __future__ import absolute_import
from mobly import asserts
from functional_tests import gdm_test_base
import parallel_funcs


class ParallelTestSuite(gdm_test_base.GDMTestBase):
    """Functional tests for parallel_funcs.py."""

    @classmethod
    def is_applicable_to(cls, device_type, device_class, device_name):
        """Determine if this test suite can run on the given device."""
        return hasattr(device_class, "upgrade")

    @classmethod
    def requires_pairing(cls):
        """Returns True if the device in the testbed must be paired to run this test suite."""
        # Doesn't actually require pairing, but don't run this test suite in regression testing
        return True

    def test_100_parallel_upgrade(self):
        """Upgrade devices in parallel.
        """
        upgrade_params_dicts = parallel_funcs.get_parameter_dicts(
            self.devices, self.user_settings, 'upgrade')
        try:
            parallel_funcs.upgrade(self.devices, upgrade_params_dicts, self.logger)
        except Exception as err:
            asserts.fail("Error(s): {!r}".format(err.message))

if __name__ == "__main__":
    gdm_test_base.main()
