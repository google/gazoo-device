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

"""Test suite for Switchboard capability."""
import os.path
import time
from typing import Tuple, Type

from gazoo_device.switchboard import log_process
from gazoo_device.tests.functional_tests.utils import gdm_test_base
from mobly import asserts


class MockPowerSwitch:

  def __init__(self):
    self._is_on = False

  def turn_on_power(self):
    self._is_on = True

  def power_is_on(self):
    return self._is_on


class SwitchboardTestSuite(gdm_test_base.GDMTestBase):
  """Test suite for Switchboard capability."""

  @classmethod
  def is_applicable_to(cls, device_type: str,
                       device_class: Type[gdm_test_base.DeviceType],
                       device_name: str) -> bool:
    """Determine if this test suite can run on the given device."""
    return device_class.has_capabilities(["switchboard"])

  @classmethod
  def requires_pairing(cls) -> bool:
    """Returns True if the device must be paired to run this test suite."""
    return False

  @classmethod
  def required_test_config_variables(cls) -> Tuple[str, ...]:
    """Returns keys required to be present in the functional test config."""
    return ("shell_cmd", "expect")

  def test_send_and_expect(self):
    """Tests send_and_expect() method."""
    timeout = 10  # In seconds.
    response = self.device.switchboard.send_and_expect(
        self.test_config["shell_cmd"],
        self.test_config["expect"],
        timeout=timeout)
    asserts.assert_false(
        response.timedout,
        "{} switchboard.send_and_expect failed for command {!r}. "
        "Did not find regex {!r} in {}s. Device output: {!r}"
        .format(self.device.name, self.test_config["shell_cmd"],
                self.test_config["expect"], timeout, response.before))

  def test_do_and_expect(self):
    """Tests switchboard.do_and_expect() method."""
    switch = MockPowerSwitch()
    expect_result = self.device.switchboard.do_and_expect(
        switch.turn_on_power, (), {},
        ["fake_string, won't match anything"],
        timeout=.1)
    asserts.assert_true(
        expect_result.timedout,
        "Expected do_and_expect to time out, but timedout was False")
    asserts.assert_true(
        switch.power_is_on, "switch.turn_on_power() did not execute. "
        "The power state is still off for switch.")

  def test_expect_with_bogus_logline(self):
    """Tests switchboard.expect() method for a log line that doesn't exist."""
    phrase = "garblygookand more"
    response = self.device.switchboard.expect([phrase], timeout=2)
    asserts.assert_true(
        response.timedout, "Response should have timed out, but it didn't. "
        f"Requested log line regex: {phrase!r}. "
        f"Device output: {response.before!r}")

  def test_rotate_log(self):
    """Tests max_log_size and auto log rotation features."""
    old_log_file_name = self.device.log_file_name
    expected_log_filename = log_process.get_next_log_filename(old_log_file_name)
    expected_message = "Special message to trigger at least one log rotation"
    max_log_size = len(expected_message) * 10
    self.device.switchboard.set_max_log_size(max_log_size)
    time.sleep(.5)  # Allow time for set_max_log_size to complete.

    try:
      for _ in range(20):
        self.device.switchboard.add_log_note(expected_message)
      end_time = time.time() + 3
      while (old_log_file_name == self.device.log_file_name
             and time.time() < end_time):
        time.sleep(0.1)
      asserts.assert_true(
          os.path.exists(old_log_file_name),
          f"Expected old log file name {old_log_file_name} to exist")
      asserts.assert_true(
          os.path.exists(expected_log_filename),
          f"Expected new log file name {expected_log_filename} to exist")
      asserts.assert_not_equal(
          old_log_file_name, self.device.log_file_name,
          f"Expected log file name to change from {old_log_file_name}")
    finally:
      # Disable log rotation (the default) after the test.
      self.device.switchboard.set_max_log_size(0)


if __name__ == "__main__":
  gdm_test_base.main()

