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


"""A short-lived library that provides convenient compatibility for Python 3.11.

TODO(gdm-authors): Remove this module after dropping Python 3.9 & 3.10 support.
Replace with: https://docs.python.org/3/library/enum.html#enum.StrEnum.
"""

import enum


# A convenient `StrEnum` symbol that makes `__format__()` the same between
# Python 3.10 and 3.11. See https://github.com/google/gazoo-device#enum_str_enum for the underlying
# issue.
class StrEnum(str, enum.Enum):

  def __format__(self, format_spec: str) -> str:
    # TODO(gdm-authors): Remove the disable once a new pytype release is
    # available.
    return self.value.__format__(format_spec)  # pytype: disable=attribute-error
