# Copyright 2020 Google LLC
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

"""ExpectResponse object carries results from calls to GDM expect api.

GDM expect methods, found in switchboard.py, load results into ExpectResponse
to permit calling routines a way to evaluate device execution and behavior.
"""


class ExpectResponse(object):
    """Stores the values of expect Attributes.

    Attributes:
        index (int): index of matching pattern in pattern list (None if timeout).
        before (str): all the characters looked at before the match.
        after (str): all the characters after the first matching character.
        match (re.Match): pattern match object.
        timedout (bool): True if the expect timed out.
        time_elapsed (float): number of seconds between start and finish.
        remaining (list): patterns that have not been matched (after a timeout).
        match_list (list): of re.search Match objects.
    """

    def __init__(self,
                 index,
                 before,
                 after,
                 match,
                 time_elapsed,
                 timedout=False,
                 remaining=None,
                 match_list=None):
        self.index = index
        self.before = before
        self.after = after
        self.match = match
        self.timedout = timedout
        self.time_elapsed = time_elapsed
        self.remaining = [] if remaining is None else remaining
        self.match_list = [] if match_list is None else match_list
