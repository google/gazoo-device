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

"""Test suite that verifies that optional properties are retrievable."""
from __future__ import absolute_import
import traceback

from mobly import asserts
from functional_tests import gdm_test_base

TESTED_PROPERTIES = ["ftdi_serial_number", "build_date"]


class OptionalPropertiesTestSuite(gdm_test_base.GDMTestBase):
    """Test suite that verifies that optional properties are retrievable."""

    @classmethod
    def is_applicable_to(cls, device_type, device_class, device_name):
        """Determine if this test suite can run on the given device."""
        return any(hasattr(device_class, attr) for attr in TESTED_PROPERTIES)

    @classmethod
    def requires_pairing(cls):
        """Returns True if the device in the testbed must be paired to run this test suite."""
        return False

    def test_1003_get_ftdi_serial_number(self):
        if hasattr(type(self.device), "ftdi_serial_number"):
            try:
                asserts.assert_true(self.device.ftdi_serial_number is not None,
                                    "ftdi serial number should not be None")
            except Exception:
                traceback_message = traceback.format_exc()
                asserts.fail("Error happened during get ftdi serial number: " +
                             traceback_message)

    def test_1005_get_build_date(self):
        if hasattr(type(self.device), "build_date"):
            try:
                asserts.assert_true(self.device.build_date is not None,
                                    "build date should not be None")
            except Exception:
                traceback_message = traceback.format_exc()
                asserts.fail("Error happened during get build date: " +
                             traceback_message)


if __name__ == "__main__":
    gdm_test_base.main()
