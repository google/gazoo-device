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

"""Mixin for Matter Color Control cluster test suite."""
from mobly import asserts

_TARGET_HUE = 70
_TARGET_SATURATION = 90
_TARGET_COLOR_TEMPERATURE = 108


class ColorControlClusterTestSuite:
  """Mixin for Matter Color Control cluster test suite.

  The mixin assumes self.endpoint is set.
  """

  def test_move_to_hue_command_and_current_hue_attribute(self):
    """Tests the MoveToHue command and CurrentHue attribute."""
    self.endpoint.color.move_to_hue(hue=_TARGET_HUE)
    asserts.assert_equal(_TARGET_HUE, self.endpoint.color.current_hue)

  def test_move_to_saturation_command_and_current_saturation_attribute(self):
    """Tests the MoveToSaturation command and CurrentSaturation attribute."""
    self.endpoint.color.move_to_saturation(saturation=_TARGET_SATURATION)
    asserts.assert_equal(_TARGET_SATURATION,
                         self.endpoint.color.current_saturation)

  def test_move_to_color_temperature_and_color_temperature_mireds_attribute(
      self):
    """Tests the MoveToColorTemperature and the ColorTemperatureMireds."""
    self.endpoint.color.move_to_color_temperature(
        color_temperature_mireds=_TARGET_COLOR_TEMPERATURE)
    asserts.assert_equal(_TARGET_COLOR_TEMPERATURE,
                         self.endpoint.color.color_temperature_mireds)
