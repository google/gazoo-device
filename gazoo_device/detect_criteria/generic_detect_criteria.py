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

"""Generic queries sent to devices during detection to determine their device type."""
import logging
from typing import Callable
from gazoo_device.capabilities.interfaces import switchboard_base
from gazoo_device.detect_criteria import base_detect_criteria
import immutabledict


class GenericQuery(base_detect_criteria.QueryEnum):
  ALWAYS_TRUE = "always_true"


def _always_true_query(
    address: str, detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> bool:
  """Used when there is just one type of device for a communication type."""
  del address, create_switchboard_func, detect_logger  # Unused.
  return True


GENERIC_QUERY_DICT: immutabledict.immutabledict[
    GenericQuery, base_detect_criteria.DetectQueryCallable
] = immutabledict.immutabledict({
    GenericQuery.ALWAYS_TRUE: _always_true_query,
})
