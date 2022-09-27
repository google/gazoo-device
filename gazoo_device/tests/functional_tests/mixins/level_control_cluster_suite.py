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

"""Mixin for Matter Level Control cluster test suite."""
from gazoo_device.capabilities.matter_endpoints import speaker

from mobly import asserts

_TARGET_LEVEL = 108


class LevelControlClusterTestSuite:
  """Mixin for Matter Level Control cluster test suite.

  The mixin assumes self.endpoint is set.
  """

  def test_move_to_level_command_and_current_level_attribute(self):
    """Tests the MoveToLevel command and CurrentLevel attribute."""
    if self.endpoint.has_clusters(["level_control"]):
      self.endpoint.level.move_to_level(level=_TARGET_LEVEL)
      asserts.assert_equal(_TARGET_LEVEL, self.endpoint.level.current_level)
    else:
      asserts.skip(
          f"Endpoint {self.endpoint} does not implement the Level Control "
          "cluster.")

  def test_max_and_min_level_attributes(self):
    """Tests the MaxLevel and MinLevel attributes."""
    if self.endpoint.has_clusters(["level_control"]):
      asserts.assert_is_instance(
          self.endpoint.level.max_level, int,
          "MaxLevel attribute must be the int type.")

      # TODO(b/248451689) Remove the bypass after Speaker issue is resolved
      if not isinstance(self.endpoint, speaker.SpeakerEndpoint):
        asserts.assert_is_instance(
            self.endpoint.level.min_level, int,
            "MinLevel attribute must be the int type.")
    else:
      asserts.skip(
          f"Endpoint {self.endpoint} does not implement the Level Control "
          "cluster.")
