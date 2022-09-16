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
from typing import Any, Dict, Optional, Sequence, Tuple

from gazoo_device.capabilities.interfaces import capability_base


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
      forced_upgrade: Optional[bool] = None,
      method: Optional[str] = None,
      file_regexes: Optional[Sequence[str]] = None,
      num_files: Optional[int] = None,
      **unexpected_kwargs: Any,
  ) -> None:
    """Upgrade the device based on the provided build arguments.

    Args:
        *unexpected_args: Captures unexpected positional arguments.
        build_folder_url: gs:// URL of the folder the remote build files reside
          in.
        local_files: Full paths to local build files.
          Mutually exclusive with build_folder_url and file_regexes.
        forced_upgrade: Upgrade the firmware without checks.
        method: Used by some flavors to pick between flashing methods.
        file_regexes: Regexes for finding the build files in a folder. If not
          provided, uses the default in nest_device/build_defaults/info.json
        num_files: The number of build files expected after regex matching.
        **unexpected_kwargs: Captures unexpected keyword arguments.

    Raises:
        DeviceError: Both upgrades over_the_wire & over_the_air are unsupported.
    """

  @abc.abstractmethod
  def upgrade_over_the_wire(self, **build_args):
    """Using the build arguments, download and flash the build on the device.

    Args:
        **build_args (dict): dictionary of build arguments.
    """

  @abc.abstractmethod
  def extract_build_info(
      self,
      *unexpected_args,
      build_folder_url: Optional[str] = None,
      local_files: Optional[Sequence[str]] = None,
      forced_upgrade: Optional[bool] = None,
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
        forced_upgrade: Upgrade the firmware without checks.
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

  @abc.abstractmethod
  def flash_device(self,
                   list_of_files,
                   expected_version=None,
                   expected_build_type=None,
                   verify_flash=True,
                   method=None):
    """Transfer a list of local files onto the device and flash the build on the device.

    Args:
        list_of_files (list): list of files on local computer.
        expected_version (str): firmware_version that is expected for the
          given list of files.
        expected_build_type (str): build_type that is expected for the given
          list of files.
        verify_flash (bool): True if flash_device should verify the
          firmware_version and build_type following the upgrade.
        method (str): upgrade method.

    Note: The list of files and expected version will be used to do an over
        the wire upgrade for the device.
    """

  # Deprecated methods below.

  @abc.abstractmethod
  def download_build_file(self, remote_build_folder, local_folder) -> None:
    """Retrieves the build file(s) from the remote location and puts them in the local folder.

    Args:
        remote_build_folder (str): build folder in remote location.
        local_folder (str): local path to store build files.
    """

  @abc.abstractmethod
  def get_defaults(self) -> Dict[str, Any]:
    """Returns a dictionary of default build arguments.

    Returns:
        dict: the default build arguments for the device.
    """

  @abc.abstractmethod
  def get_firmware_type(self, build_args=None) -> str:
    """Returns the firmware type of the requested build.

    Args:
        build_args (dict): dictionary of build arguments. If None, the
          default build arguments are used.

    Returns:
        str: firmware type
    """

  @abc.abstractmethod
  def get_firmware_version(self, build_args=None) -> str:
    """Returns the firmware version based on the build arguments.

    Args:
        build_args (dict): dictionary of build arguments. If None, the
          default build arguments are used.

    Returns:
        str: firmware version
    """

  @abc.abstractmethod
  def get_remote_build_folder(self, build_args=None) -> str:
    """Uses the build arguments to determine the remote build folder.

    Args:
        build_args (dict): dictionary of build arguments. If None, the
          default build arguments are used.

    Returns:
        str: the remote build folder path.
    """

  @abc.abstractmethod
  def latest_verified_build_folder(self):
    """Returns the remote build folder path for the latest verified build.

    Returns:
        str: The latest verified remote build folder path.
    """
