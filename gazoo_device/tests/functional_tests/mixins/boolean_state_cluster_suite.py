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

"""Mixin for Matter Boolean State cluster test suite."""
from mobly import asserts


class BooleanStateTestSuite:
  """Mixin for Matter Boolean State cluster test suite.

  The mixin assumes self.endpoint is set.
  """

  def _update_state_and_verify(self, state: bool) -> None:
    """Helper method to verfy state_value update."""
    self.endpoint.boolean_state.state_value = state
    asserts.assert_equal(state, self.endpoint.boolean_state.state_value)

  def test_state_value_attribute(self):
    """Tests the StateValue attribute."""
    if self.endpoint.boolean_state.state_value:
      self._update_state_and_verify(state=False)
    else:
      self._update_state_and_verify(state=True)
