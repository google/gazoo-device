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

"""Build Flasher capability interface."""
import abc
from gazoo_device.capabilities.interfaces import capability_base


class FlashBuildBase(capability_base.CapabilityBase):
    """Abstract base class for the build_flasher capability."""

    @abc.abstractmethod
    def download_build_file(self, remote_build_folder, local_folder):
        """Retrieves the build file(s) from the remote location and puts them in the local folder.

        Args:
            remote_build_folder (str): build folder in remote location.
            local_folder (str): local path to store build files.
        """

    @abc.abstractmethod
    def get_defaults(self):
        """Returns a dictionary of default build arguments.

        Returns:
            dict: the default build arguments for the device.
        """

    @abc.abstractmethod
    def get_firmware_version(self, build_args=None):
        """Returns the firmware version based on the build arguments.

        Args:
            build_args (dict): dictionary of build arguments.
                               If None, the default build arguments are used.

        Returns:
            str: firmware version
        """

    @abc.abstractmethod
    def get_remote_build_folder(self, build_args=None):
        """Uses the build arguments to determine the remote build folder.

        Args:
            build_args (dict): dictionary of build arguments.
                               If None, the default build arguments are used.

        Returns:
            str: the remote build folder path.
        """

    @abc.abstractmethod
    def extract_build_info(self, build_args=None):
        """Converts the provided build arguments into information about the build.

        Args:
            build_args (dict): dictionary of build arguments.
                               If None, the default build arguments are used.

        Returns:
            dict: dictionary of build information including absolute_remote_path, build_type,
                    and build_version.
        """

    @abc.abstractmethod
    def flash_device(self, list_of_files,
                     expected_version=None,
                     expected_build_type=None,
                     verify_flash=True,
                     method=None):
        """Transfer a list of local files onto the device and flash the build on the device.

        Args:
            list_of_files (list): list of files on local computer.
            expected_version (str): firmware_version that is expected for the given list of files.
            expected_build_type (str): build_type that is expected for the given list of files.
            verify_flash (bool): True if flash_device should verify the firmware_version and
                                 build_type following the upgrade.
            method (str): upgrade method.

        Note:
            The list of files and expected version will be used to do an over the wire upgrade
            for the device.
        """

    @abc.abstractmethod
    def latest_verified_build_folder(self):
        """Returns the remote build folder path for the latest verified build.

        Returns:
            str: The latest verified remote build folder path.
        """

    @abc.abstractmethod
    def upgrade(self,
                build_number=None,
                build_url=None,
                build_file=None,
                forced_upgrade=False,
                latest_verified=False,
                **other_build_args):
        """Upgrade the device based on the provided build arguments.

        Args:
            build_number(int): build number. Defaults to last_believed good build.
            build_url(str): url or gsutil to the .zip file. Defaults to last_believed good build.
            build_file(str): local path to the file.
            forced_upgrade(bool): Upgrade the firmware without checks.
            latest_verified(bool): Upgrade to latest verified build.
            **other_build_args(dict): Other build arguments that are different based
                                      on the device type.
        """

    @abc.abstractmethod
    def upgrade_over_the_wire(self, **build_args):
        """Using the build arguments, download and flash the build on the device.

        Args:
            **build_args (dict): dictionary of build arguments.
        """
