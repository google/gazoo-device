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

# TODO(gdm-authors): Add link to setup documentation.
"""This test suite verifies the embedded_script capability.

Test suite requires LUA 'test_script' to be deployed on testing DUT.
"""
import time

from typing import Type
from gazoo_device.tests.functional_tests.utils import gdm_test_base
from mobly import asserts


class EmbeddedScriptTestSuite(gdm_test_base.GDMTestBase):
  """Functional test suite for the embedded_script capability."""

  @classmethod
  def is_applicable_to(cls, device_type: str,
                       device_class: Type[gdm_test_base.DeviceType],
                       device_name: str) -> bool:
    """Determine if this test suite can run on the given device."""
    return (device_class.has_capabilities(["switch_power"]) and
            device_class.has_capabilities(["embedded_script"]))

  @classmethod
  def requires_pairing(cls) -> bool:
    """Returns True if the device must be paired to run this test suite."""
    return True

  def setup_test(self):
    """Set states and script name for running tests."""
    super().setup_test()
    self.on_state = "on"
    self.script_name = "test_script"
    self.port = 1

  def test_run_script(self):
    """Tests if script is executed over powerswitch."""
    self.device.switch_power.power_off(port=(self.port-1))
    self.device.embedded_script.run(script_name=self.script_name,
                                    script_args=[str(self.port)])
    time.sleep(10)
    current_state = self.device.switch_power.get_mode(self.port-1)
    asserts.assert_equal(
        current_state, self.on_state,
        "{port} for device {device_name} should have been set to on state.".
        format(port=self.port, device_name=self.device.name))

  def test_terminate_script(self):
    """Tests if script execution is stopped without passing thread id."""
    self.device.switch_power.power_off(port=(self.port-1))
    self.device.embedded_script.run(script_name=self.script_name,
                                    script_args=[str(self.port)])
    self.device.embedded_script.terminate()
    current_running_threads = (self.device.embedded_script.
                               get_current_running_threads())
    asserts.assert_equal(
        first=current_running_threads,
        second="{}",
        msg="Script still in execution {}".format(current_running_threads))

  def test_terminate_script_with_thread_id(self):
    """Tests if script execution is stopped using thread id."""
    self.device.switch_power.power_off(port=(self.port-1))
    thread_id = self.device.embedded_script.run(
        script_name=self.script_name, script_args=[str(self.port)])
    self.device.embedded_script.terminate(thread_id=thread_id)
    current_running_threads = (self.device.embedded_script.
                               get_current_running_threads())
    asserts.assert_equal(
        first=current_running_threads,
        second="{}",
        msg="Script still in execution {}".format(current_running_threads))

  def teardown_test(self):
    """Turns power off for test port."""
    self.device.switch_power.power_off(port=self.port-1)
    super().teardown_test()

if __name__ == "__main__":
  gdm_test_base.main()
