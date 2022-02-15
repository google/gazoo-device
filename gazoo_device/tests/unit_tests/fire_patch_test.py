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

"""Unit tests for GDM's patch of the Python Fire library."""
import sys
from unittest import mock

import fire
from gazoo_device import fire_patch
from gazoo_device.tests.unit_tests.utils import unit_test_case

_TEST_TEXT = ["foo\nbar\nbaz\n"]


class TestComponent:
  """Class for testing the evaluation of object attributes."""

  @property
  def unstable_property(self):
    raise RuntimeError

  @property
  def public_property(self):
    return "gobbly"

  @property
  def _private_property(self):
    return "gook"

  def public_attribute(self):
    pass

  def _private_attribute(self):
    pass


class FirePatchTests(unit_test_case.UnitTestCase):
  """Class for testing fire_patch.py code."""

  def test_apply_patch(self):
    """Verifies that apply_patch patches fire methods."""
    fire_patch.apply_patch()
    self.assertEqual(id(fire.core.Display), id(fire_patch.display))

  def test_safely_get_members(self):
    """Tests that _safely_get_members works on attributes that raise errors."""
    unstable_component = TestComponent()
    with self.assertRaises(RuntimeError):
      unstable_component.unstable_property  # pylint: disable=pointless-statement
    fire_patch._safely_get_members(unstable_component)

  def test_display_to_stdout(self):
    """Verifies that the display method writes plain text to stdout."""
    with mock.patch.object(
        sys, "stdout", new_callable=mock.PropertyMock) as mock_stdout:
      fire_patch.display(_TEST_TEXT, sys.stdout)
      mock_stdout.write.assert_called_once()

  def test_display_to_stderr(self):
    """Verifies that the display method writes plain text to stderr."""
    with mock.patch.object(
        sys, "stderr", new_callable=mock.PropertyMock) as mock_stderr:
      fire_patch.display(_TEST_TEXT, sys.stderr)
      mock_stderr.write.assert_called_once()

  def test_display_to_unknown_out(self):
    """Verifies that display prints plain text if unknown output is provided."""
    with mock.patch.object(
        sys, "stdout", new_callable=mock.PropertyMock) as mock_stdout:
      fire_patch.display(_TEST_TEXT, None)
      mock_stdout.write.assert_called_once()

  def test_visible_members_contains_callable_public_object_attributes(self):
    """Verifies that visible_members returns callable public attributes."""
    test_component = TestComponent()
    expected_visible_members = [("public_attribute",
                                 test_component.public_attribute),
                                ("public_property", "gobbly")]
    visible_members = fire_patch.visible_members(test_component)
    self.assertEqual(visible_members, expected_visible_members)

  def test_visible_members_contains_dictionary_entries(self):
    """Verifies that visible_members returns dict entries when dict provided."""
    test_component = {"public_entry": "gobbly", "_private_entry": "gook"}
    expected_visible_members = [("public_entry", "gobbly")]
    visible_members = fire_patch.visible_members(test_component)
    self.assertEqual(visible_members, expected_visible_members)

  def test_safely_get_all_members(self):
    """Verifies that _safely_get_members gets all members."""
    test_component = TestComponent()
    members = fire_patch._safely_get_members(test_component)
    self.assertGreater(len(members), 1)


if __name__ == "__main__":
  unit_test_case.main()
