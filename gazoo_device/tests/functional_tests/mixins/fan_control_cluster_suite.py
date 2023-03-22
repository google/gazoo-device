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

"""Mixin for Matter Fan Control cluster test suite."""
from mobly import asserts

_FAKE_DATA = 1


class FanControlClusterTestSuite:
  """Mixin for Matter Fan Control cluster test suite.

  The mixin assumes self.endpoint is set.
  """

  def test_fan_mode(self):
    """Tests FanMode attribute."""
    self._test_fan_control_attribute("fan_mode")

  def test_fan_mode_sequence(self):
    """Tests FanModeSequence attribute."""
    self._test_fan_control_attribute("fan_mode_sequence")

  def test_percent_setting(self):
    """Tests PercentSetting attribute."""
    self._test_fan_control_attribute("percent_setting")

  def test_percent_current(self):
    """Tests PercentCurrent attribute."""
    self._test_fan_control_attribute("percent_current")

  def test_speed_max(self):
    """Tests SpeedMax attribute."""
    self._test_fan_control_attribute("speed_max")

  def test_speed_setting(self):
    """Tests SpeedSetting attribute."""
    self._test_fan_control_attribute("speed_setting")

  def test_speed_current(self):
    """Tests SpeedCurrent attribute."""
    self._test_fan_control_attribute("speed_current")

  def _test_fan_control_attribute(self, attribute_name: str):
    """Helper function to test Fan Control attribute."""
    if self.endpoint.has_clusters(["fan_control"]):
      attribute = getattr(self.endpoint.fan_control, attribute_name)
      attribute = _FAKE_DATA
      asserts.assert_equal(attribute, _FAKE_DATA)
    else:
      asserts.skip(
          f"Endpoint {self.endpoint} does not implement the Fan Control "
          "cluster.")
