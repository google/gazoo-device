# Copyright 2023 Google LLC
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

"""Unit tests for py311.py.
"""
import enum

from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import py311


class _Py311StrEnum(py311.StrEnum):
  MEMBER = "value"


class _BuiltInStrEnum(enum.StrEnum):
  MEMBER = "value"


class Py311Tests(unit_test_case.UnitTestCase):
  """Unit tests for py311.py."""

  def test_enum_format(self):
    """Tests StrEnum.__format__."""
    py311_format = f"tag/{_Py311StrEnum.MEMBER}"
    builtin_format = f"tag/{_BuiltInStrEnum.MEMBER}"
    expected_format = "tag/value"
    self.assertEqual(py311_format, builtin_format)
    self.assertEqual(py311_format, expected_format)


if __name__ == "__main__":
  unit_test_case.main()
