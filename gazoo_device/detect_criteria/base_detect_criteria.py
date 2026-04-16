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

"""Base class for queries sent to devices during detection."""
import enum
import functools
import logging
from typing import Callable, Mapping, Union
from gazoo_device.capabilities.interfaces import switchboard_base


@functools.total_ordering
class QueryEnum(enum.Enum):
  """Allows comparison of enum properties for sorting purposes."""

  def __lt__(self, other):
    return self.name < other.name  # pylint: disable=comparison-with-callable

DetectQueryCallable = Callable[
    [str, logging.Logger, Callable[..., switchboard_base.SwitchboardBase]],
    Union[str, bool]
]
DetectQueryMapping = Mapping[QueryEnum, DetectQueryCallable]


def get_communication_address(
    address: str, detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> str:
  """Returns the communication address.

  This detection criterion should be used in conjunction with queries returning
  USB product and vendor IDs to narrow down a match.

  For USB devices, this function is particularly useful to matching FTDI
  manufacturer IDs which should be consistent between products that use FTDI
  chipsets. The manufacturer's ID is the first two characters in the serial
  number.
  See:
  https://www.ftdichip.com/Support/Knowledgebase/howistheautomaticserialnu.htm

  Args:
    address: Communication address of the device. USB devices are addressed by
      their serial number.
    detect_logger: The logger of device interactions.
    create_switchboard_func: Method to create the switchboard.

  Returns:
    Communication address.
  """
  del create_switchboard_func, detect_logger  # Unused.
  return address
