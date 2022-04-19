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

"""ExpectResponse object carries results from calls to GDM expect API.

GDM expect methods, found in switchboard.py, load results into ExpectResponse
to permit calling routines a way to evaluate device execution and behavior.
"""
import dataclasses
import re
from typing import List, Optional


@dataclasses.dataclass
class ExpectResponse(object):
  """Stores the values of expect Attributes.

  Attributes:
      index: index of matching pattern in pattern list (None if timeout).
      before: all the characters looked at before the match.
      after: all the characters after the first matching character.
      match: pattern match object.
      timedout: True if the expect timed out.
      time_elapsed: number of seconds between start and finish.
      remaining: patterns that have not been matched (after a timeout).
      match_list: of re.search Match objects.
  """
  index: Optional[int] = None
  before: str = ""
  after: str = ""
  match: Optional[re.Match] = None
  time_elapsed: float = 0
  timedout: bool = False
  remaining: List[str] = dataclasses.field(default_factory=list)
  match_list: List[re.Match] = dataclasses.field(default_factory=list)
