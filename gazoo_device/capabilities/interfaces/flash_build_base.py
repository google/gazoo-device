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

"""Build Flasher capability interface."""

import abc
import dataclasses
from typing import Any, Optional, Sequence, Tuple

from gazoo_device import decorators
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import capability_base

_LOGGER = gdm_logger.get_logger()
UNKNOWN = "UNKNOWN"


@dataclasses.dataclass(frozen=True)
class BuildInfo:
  build_version: str
  build_type: str
  build_branch: str
  build_files: Tuple[str, ...]
  is_local: bool


class FlashBuildBase(capability_base.CapabilityBase):
  """Abstract base class for the build_flasher capability."""

  @abc.abstractmethod
  def upgrade(
      self,
      *unexpected_args,
      build_folder_url: Optional[str] = None,
      local_files: Optional[Sequence[str]] = None,
      forced_upgrade: bool = False,
      method: Optional[str] = None,
      file_regexes: Optional[Sequence[str]] = None,
      num_files: Optional[int] = None,
      **unexpected_kwargs: Any,
  ) -> None:
    """Upgrade the device based on the provided build arguments.

    Args:
      *unexpected_args: Captures unexpected positional arguments.
      build_folder_url: gs:// URL of the folder the build files reside in.
      local_files: Full paths to local build files.
        Mutually exclusive with build_folder_url and file_regexes.
      forced_upgrade: Reflash the firmware even if the same build is already
        installed on the device.
      method: Used by some flavors to pick between flashing methods.
      file_regexes: Regexes for finding the build files in a folder. If not
        provided, uses the default in nest_device/build_defaults/info.json
      num_files: The number of build files expected after regex matching.
      **unexpected_kwargs: Captures unexpected keyword arguments.

    Raises:
      DeviceError: Both upgrades over_the_wire & over_the_air are unsupported.
    """

  @abc.abstractmethod
  def extract_build_info(
      self,
      *unexpected_args,
      build_folder_url: Optional[str] = None,
      local_files: Optional[Sequence[str]] = None,
      forced_upgrade: bool = False,
      method: Optional[str] = None,
      file_regexes: Optional[Sequence[str]] = None,
      num_files: Optional[int] = None,
      **unexpected_kwargs: Any,
  ) -> BuildInfo:
    """Converts the provided build arguments into information about the build.

    Args:
      *unexpected_args: Captures unexpected positional arguments.
      build_folder_url: gs:// URL of the folder the remote build files reside
        in.
      local_files: Full paths to local build files.
        Mutually exclusive with build_folder_url and file_regexes.
      forced_upgrade: No-op. Not used by extract_build_info. The arg is here
        so that the method signature is identical to upgrade().
      method: Used by some flavors to pick between flashing methods.
      file_regexes: Regexes for finding the build files in a folder. If not
        provided, uses the default in nest_device/build_defaults/info.json
      num_files: The number of build files expected after regex matching.
      **unexpected_kwargs: Captures unexpected keyword arguments.

    Returns:
      BuildInfo about the requested build's version, type, and file locations.
      For upgrades from build folder URLs, this method transforms
      "build_folder_url" + "file_regexes" into remote build file locations.
    """

  @decorators.CapabilityLogDecorator(_LOGGER)
  def flash_device(
      self,
      list_of_files: Sequence[str],
      expected_version: Optional[str] = None,
      expected_build_type: Optional[str] = None,
      verify_flash: bool = True,
      method: Optional[str] = None,
  ) -> None:
    """Flashes the device over the wire given paths to build files on the host.

    This method will not delete the files provided in list_of_files.

    Args:
      list_of_files: List of local build files.
      expected_version: Expected firmware_version for the build.
      expected_build_type: Expected firmware_type for the build.
      verify_flash: If True, does a post-upgrade verification check of the
        expected vs actual build flashed on the device.
      method: Upgrade method.

    Raises:
      NotImplementedError: must be overridden in derived classes which support
        flashing over the wire.
    """
    raise NotImplementedError(f"flash_device not implemented in {type(self)}")

  @decorators.CapabilityLogDecorator(_LOGGER)
  def ota_device(
      self,
      list_of_files: Sequence[str],
      expected_version: Optional[str] = None,
      expected_build_type: Optional[str] = None,
      verify_flash: bool = True,
      method: Optional[str] = None,
  ) -> None:
    """Flashes the device over the air given paths to build files on the host.

    This method will not delete the files provided in list_of_files.

    Args:
      list_of_files: List of local build files.
      expected_version: Expected firmware_version for the build.
      expected_build_type: Expected firmware_type for the build.
      verify_flash: If True, does a post-upgrade verification check of the
        expected vs actual build flashed on the device.
      method: Upgrade method.

    Raises:
      NotImplementedError: must be overridden in derived classes which support
        flashing over the air.
    """
    raise NotImplementedError(f"ota_device not implemented in {type(self)}")
