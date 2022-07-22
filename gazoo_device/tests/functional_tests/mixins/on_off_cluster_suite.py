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

"""Mixin for Matter On/Off cluster test suite."""
from mobly import asserts


class OnOffClusterTestSuite:
  """Mixin for Matter On/Off cluster test suite.

  The mixin assumes self.endpoint is set.
  """

  def test_on_off_command_and_onoff_attribute(self):
    """Tests the On Off command and OnOff attribute."""
    if self.endpoint.on_off.onoff:
      self._turn_off_and_verify()
      self._turn_on_and_verify()
    else:
      self._turn_on_and_verify()
      self._turn_off_and_verify()

  def test_toggle_command(self):
    """Tests the Toggle command."""
    current_state = self.endpoint.on_off.onoff
    self.endpoint.on_off.toggle()
    asserts.assert_equal(not current_state, self.endpoint.on_off.onoff)

  def _turn_off_and_verify(self):
    """Turns off the device and verifies."""
    self.endpoint.on_off.off()
    asserts.assert_false(self.endpoint.on_off.onoff,
                         "OnOff attribute should be off")

  def _turn_on_and_verify(self):
    """Turns on the device and verifies."""
    self.endpoint.on_off.on()
    asserts.assert_true(self.endpoint.on_off.onoff,
                        "OnOff attribute should be on")
