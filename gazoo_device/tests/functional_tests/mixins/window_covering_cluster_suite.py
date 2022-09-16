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

"""Mixin for Matter Window Covering cluster test suite."""
from mobly import asserts

_TEST_DATA = 5


class WindowCoveringClusterTestSuite:
  """Mixin for Window Covering cluster test suite.

  The mixin assumes self.endpoint is set.
  """

  def test_current_position_lift_percentage_attribute(self):
    """Tests the current_position_lift_percentage attribute."""
    self.endpoint.window_covering.current_position_lift_percentage = _TEST_DATA
    data = self.endpoint.window_covering.current_position_lift_percentage
    asserts.assert_equal(data, _TEST_DATA)
    asserts.assert_is_instance(
        data, int,
        "current_position_lift_percentage attribute must be the int type.")

  def test_current_position_tilt_percentage_attribute(self):
    """Tests the current_position_tilt_percentage attribute."""
    self.endpoint.window_covering.current_position_tilt_percentage = _TEST_DATA
    data = self.endpoint.window_covering.current_position_lift_percentage
    asserts.assert_equal(data, _TEST_DATA)
    asserts.assert_is_instance(
        data, int, "current_position_tilt_percentage must be the int type.")
