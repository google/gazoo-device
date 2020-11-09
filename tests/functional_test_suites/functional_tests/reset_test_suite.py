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

"""Functional test suite for the reset() method."""
import datetime
import time
import traceback

from mobly import asserts
from functional_tests import gdm_test_base


LOG_CATCH_UP_DELAY = 3


class ResetTestSuite(gdm_test_base.GDMTestBase):
    """Functional tests for the "reset" method."""

    @classmethod
    def is_applicable_to(cls, device_type, device_class, device_name):
        """Determine if this test suite can run on the given device."""
        return hasattr(device_class, "reset")

    @classmethod
    def requires_pairing(cls):
        """Returns True if the device in the testbed must be paired to run this test suite."""
        return False

    def test_1009_reset(self):
        time.sleep(LOG_CATCH_UP_DELAY)
        start_time = datetime.datetime.now()

        try:
            self.device.reset()
        except Exception:
            traceback_message = traceback.format_exc()
            asserts.fail("Error happened during reset: " + traceback_message)
        self._verify_no_unexpected_reboots(start_time)

    def _verify_no_unexpected_reboots(self, start_time):
        """Verify no unexpected reboots after start time."""
        bootups = self.device.event_parser.get_unexpected_reboots()
        unexpected_timestamps = [event["system_timestamp"] for event in bootups if event[
            "system_timestamp"] > start_time]
        asserts.assert_false(unexpected_timestamps,
                             "There were {} unexpected bootups after {} at {}".format(
                                 len(unexpected_timestamps), start_time, unexpected_timestamps))


if __name__ == "__main__":
    gdm_test_base.main()
