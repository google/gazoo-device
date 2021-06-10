# Copyright 2021 Google LLC
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

"""Test suite for devices using the pw_rpc_light capability."""
from typing import Type
from gazoo_device.tests.functional_tests.utils import gdm_test_base


class PwRPCLightTestSuite(gdm_test_base.GDMTestBase):
  """Tests for the pw_rpc_light capability."""

  @classmethod
  def is_applicable_to(cls, device_type: str,
                       device_class: Type[gdm_test_base.DeviceType],
                       device_name: str) -> bool:
    """Determine if this test suite can run on the given device."""
    return device_class.has_capabilities(["pw_rpc_light"])

  @classmethod
  def requires_pairing(cls) -> bool:
    """Returns True if the device must be paired to run this test suite."""
    return False

  def test_light_state(self):
    """Tests the state property."""
    light_state = self.device.pw_rpc_light.state
    self.assertIsInstance(light_state, bool)

  def test_light_on_off(self):
    """Tests toggling the light on and off."""
    on_action = (self.device.pw_rpc_light.on, True)
    off_action = (self.device.pw_rpc_light.off, False)
    if self.device.pw_rpc_light.state:
      test_sequence = (off_action, on_action)
    else:
      test_sequence = (on_action, off_action)
    for method, expected_state in test_sequence:
      method()
      off_or_on = "on" if expected_state else "off"
      self.assertEqual(self.device.pw_rpc_light.state, expected_state,
                       f"Light did not turn {off_or_on}")


if __name__ == "__main__":
  gdm_test_base.main()
