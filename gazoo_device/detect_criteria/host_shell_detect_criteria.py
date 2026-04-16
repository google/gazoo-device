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

"""Host shell queries sent to devices during detection to determine their device type."""
import logging
from typing import Callable
from gazoo_device.capabilities.interfaces import switchboard_base
from gazoo_device.detect_criteria import base_detect_criteria
from gazoo_device.utility import host_utils
import immutabledict


class HostShellQuery(base_detect_criteria.QueryEnum):
  IS_CHIP_TOOL_PRESENT = "is_chip_tool_installed_on_host"


def _is_chip_tool_installed_on_host_query(
    address: str,
    detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase],
) -> bool:
  """Determines whether chip-tool is installed on the host."""
  del address, detect_logger, create_switchboard_func  # Unused.
  return host_utils.has_command("chip-tool")


HOST_SHELL_QUERY_DICT = immutabledict.immutabledict({
    HostShellQuery.IS_CHIP_TOOL_PRESENT: _is_chip_tool_installed_on_host_query,
})
