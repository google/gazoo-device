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

"""ADB queries sent to devices during detection to determine their device type."""
import logging
import re
from typing import Callable
from gazoo_device.capabilities.interfaces import switchboard_base
from gazoo_device.detect_criteria import base_detect_criteria
from gazoo_device.utility import host_utils
import immutabledict


class AdbQuery(base_detect_criteria.QueryEnum):
  IS_SERIAL_NUMBER = "is_serial_number"


def _adb_is_serial_number_query(
    address: str,
    detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> bool:
  """Returns True if address is a serial number, False if it's an IP address."""
  del create_switchboard_func, detect_logger  # Unused.
  return not re.search(host_utils.IP_ADDRESS, address)

ADB_QUERY_DICT: immutabledict.immutabledict[
    AdbQuery, base_detect_criteria.DetectQueryCallable] = (
        immutabledict.immutabledict({
            AdbQuery.IS_SERIAL_NUMBER: _adb_is_serial_number_query,
        })
    )
