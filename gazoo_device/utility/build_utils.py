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

"""build utils for obtaining firmware builds.

All builds are unzipped to /tmp/<self.name>/<build_package_name>
"""
from __future__ import absolute_import
import json
import os
import re
import shutil
import tarfile
import traceback
import zipfile
from gazoo_device import config
from gazoo_device import gdm_logger
from gazoo_device.utility import host_utils
from gazoo_device.utility import http_utils

logger = gdm_logger.get_gdm_logger()

BUILD_FOLDER = "/tmp/{name}"
GSUTIL_PREFIX = "gs://"

TEMPLATES = {
    "build_url_notimplemented": "NotImplemented",
    "firmware_notimplemented": "NotImplemented",
}

NOT_IMPLEMENTED = {
    "build_url_template": "build_url_notimplemented",
    "firmware_template": "firmware_notimplemented",
    "build_number": None
}

with open(config.DEFAULT_BUILD_INFO_FILE) as default_build_json:
    DEFAULT_BUILD_DICTIONARY = json.loads(default_build_json.read())

    # set default build info for unimplemented devices
    for device in DEFAULT_BUILD_DICTIONARY:
        if not DEFAULT_BUILD_DICTIONARY[device]:
            DEFAULT_BUILD_DICTIONARY[device] = NOT_IMPLEMENTED.copy()


class BuildObtainer(object):
    """Class for obtaining builds from known locations.

    Notes:
        Builds get downloaded to /tmp/<name>
    """

    def __init__(self, name, owner=""):
        """Ininitalize the build obtainer.

        Args:
            name (str): unique identifier for device. Determines where builds get downloaded.
            owner (str): optional LDAP of owner if initialize from a device class.
        """
        self.name = name
        self.owner = owner
        self.local_build_dir = BUILD_FOLDER.format(name=self.name)
        self.close()  # removes previous version of directory
        os.makedirs(self.local_build_dir, mode=0o777)
        self.build_types = {
            GSUTIL_PREFIX: self._obtain_gsutil_build
        }

        self._build_autocompleter = BuildAutoCompleter(owner=owner)
        self.templates = TEMPLATES.copy()

    def close(self):
        """Removes the build folder upon close."""
        try:
            if os.path.isdir(self.local_build_dir):
                shutil.rmtree(self.local_build_dir)
            elif os.path.isfile(self.local_build_dir):
                os.remove(self.local_build_dir)
        except Exception as err:
            logger.warning(
                "{} failed to remove build_dir {}. Err: {}".format(
                    self.name, self.local_build_dir, str(err)))

    def get_version(self, device_type, build_info):
        """Converts build_info to absolute build path and extracts build version.

        Args:
          device_type (str): device type.
          build_info (dict): build information provided by parent method.

        Returns:
          str: version in build path.

        Notes:
           Errors will be raised if files not found.
        """
        path, regex = self._build_autocompleter.get_build_url_and_file_identifier(
            device_type, is_version_check=True, **build_info)
        version = self.get_version_from_folder_files(path, regex)
        logger.info("{} target firmware_version is {}".format(self.name, version))
        return version

    def get_version_and_build_path(self, device_type, build_info):
        """Converts build_info to absolute build path and extracts build version.

        Args:
          device_type (str): device type.
          build_info (dict): build information provided by parent method.

        Returns:
          tuple: version in build path and build_path

        Notes:
           Errors will be raised if files not found.
        """
        path, regex = self._build_autocompleter.get_build_url_and_file_identifier(
            device_type, is_version_check=True, **build_info)
        version = self.get_version_from_folder_files(path, regex)
        logger.info("{} target firmware_version is {}".format(self.name, version))
        return version, path

    def get_firmware_type(self, device_type, build_info):
        """Returns the target firmware type for the build, i.e. eng or user.

        Args:
            device_type (str): device type.
            build_info (dict): build information provided by parent method.

        Returns:
            str: firmware type or "UNKNOWN" if unable to extract type from build_info.
        """
        build_type = "UNKNOWN"
        build_type = self._build_autocompleter.get_default_values(device_type).get(
            "build_type", build_type)

        if "build_type" in build_info:
            build_type = build_info["build_type"]
        elif "build_url" in build_info:
            build_type_from_url = self._get_build_type_from_build_url(
                build_info["build_url"], device_type)
            if build_type_from_url != "UNKNOWN":
                build_type = build_type_from_url

        if build_type != "UNKNOWN":
            logger.info("{} target firmware_type is {}".format(self.name, build_type))
        return build_type

    def locate_and_obtain_build(self, device_type, build_info=None):
        """Converts build_info to absolute build path and extracts build file to local path.

        Args:
          device_type (str): device type.
          build_info (dict): build information provided by parent method.

        Returns:
          str: local path to file.

        Raises:
           RuntimeError: if no files found.

        Notes:
           Errors will be raised if files not found.
        """
        if not build_info:
            build_info = {}
        path, regex = self._build_autocompleter.get_build_url_and_file_identifier(
            device_type, **build_info)
        build_info.update({"build_url": path})  # for obtaining payload properties if necessary
        files = self.get_files_matching_pattern(path, regex)
        if not files:
            raise RuntimeError("No files at {} matching {!r}".format(path, regex))
        firmware_file = files[0]
        logger.info("{} obtaining {} from {}".format(self.name, firmware_file, path))
        local_path = self.obtain_build(os.path.join(path, firmware_file))
        return local_path

    def extract_build(self, compressed_file_path, compression_type="tgz"):
        """Extract .tgz build and save it to /tmp/<self.name>/<file_name>/.

        Args:
            compressed_file_path (str): absolute path to tar file.
            compression_type (str): "tar", "tgz" or "zip"

        Returns:
            str: location of extracted build.

        Raises:
            ValueError: if compressed file does not exist.
        Note:
           Removes the compressed file
        """
        if not os.path.exists(compressed_file_path):
            raise ValueError(
                "Unable to extract. File {} doesn't exist".format(compressed_file_path))
        basename = os.path.basename(compressed_file_path)
        folder = os.path.splitext(basename)[0]
        local_folder_path = os.path.join(self.local_build_dir, folder)
        logger.info(
            "{} extracting compressed file {} into {}.",
            self.name,
            folder,
            local_folder_path)
        if compression_type == "zip":
            compressor = zipfile.ZipFile(compressed_file_path, 'r')
        elif compression_type == "tar" or compression_type == "tgz":
            compressor = tarfile.open(compressed_file_path)
        else:
            raise ValueError("Compression type {} is not supported. "
                             "It has to be either tar, tgz or zip".format(compression_type))

        compressor.extractall(path=local_folder_path)
        compressor.close()

        os.remove(compressed_file_path)
        return local_folder_path

    def extract_tgz_build(self, compressed_file_path):
        """Extract .tgz build and save it to /tmp/<self.name>/<file_name>/.

        Args:
            compressed_file_path (str): absolute path to tar file.

        Returns:
            str: location of extracted build.

        Raises:
            ValueError: if compressed file does not exist.
        Note:
           Removes the compressed file
        """
        return self.extract_build(compressed_file_path, "tgz")

    def extract_zip_build(self, compressed_file_path):
        """Extract .tgz build and save it to /tmp/<self.name>/<file_name>/.

        Args:
            compressed_file_path (str): absolute path to zip file.

        Returns:
            str: location of extracted build.

        Raises:
            ValueError: if compressed file does not exist.
        Note:
           Removes the compressed file
        """
        return self.extract_build(compressed_file_path, "zip")

    def get_file_list(self, path):
        """Get files at path.

        Args:
            path (str): absolute path to folder in which files reside(url or gsutil)

        Returns:
            list: list of file names relative to give path.

        Notes:
          file list for url includes all the hyperlinks to files on that page.
          It removes .css files but other oddities might be there.
        """
        path = os.path.join(path, "")
        prefix = self._get_valid_build_prefix(path)
        if prefix == GSUTIL_PREFIX:
            return self._get_file_list_from_gsutil(path)

    def get_version_from_folder_files(self, path, pattern):
        """Finds a file that matches the pattern and returns the version from it.

        Args:
            path (str): build path at which to find files
            pattern (regex): pattern with one group through through to extract version from a file.

        Raises:
            ValueError: if no match

        Returns:
            str: matching data

        Note:
            Cameras do not have the full version in their firmware file
            so this method uses a bit of other data.
        """
        files = self.get_file_list(path)
        versions = [re.match(pattern, a_file).group(1)
                    for a_file in files
                    if re.match(pattern, a_file)]
        if not versions:
            raise ValueError("Unable to find {} in {}".format(pattern, files))
        version = versions[0]
        return version

    def get_files_matching_pattern(self, path, pattern):
        """Get files at path that match a pattern.

        Args:
            path(str): absolute path to folder in which files reside(url or gsutil)
            pattern(regex): regex pattern that string should match.

        Returns:
            list: list of file base names(not absolute paths)
        """
        files = self.get_file_list(path)
        return [a_file for a_file in files if re.match(pattern, a_file)]

    def obtain_build(self, build_url):
        """Transfer builds to local path. Uncompresses them if desired.

        Args:
            build_url(str): absolute path to file needed to be obtained.

        Returns:
            str: path of local file
        """
        prefix = self._get_valid_build_prefix(build_url)
        method = self.build_types[prefix]
        return method(build_url)

    def _get_build_type_from_build_url(self, build_url, device_type):
        """Parses the target build type out of a build url.

        Args:
          build_url (str): url to build_folder if it exists.
          device_type (str): type of device associated with build_url.

        Returns:
           str: build_type if detected, else "UNKNOWN".

        Note:
            This method will find a build_type within a build_url by using regex matching against
            the device's build_url template. If the device does not have a default build_url
            or the default build_url does not include a build_type, "UNKNOWN" will be returned.
        """
        if device_type not in self._build_autocompleter.device_build_defaults:
            return "UNKNOWN"

        device_build_defaults = self._build_autocompleter.device_build_defaults[device_type]
        build_url_template_name = device_build_defaults.get("build_url_template")
        build_url_template = self._build_autocompleter.templates[build_url_template_name]
        if "build_type" in build_url_template:

            # replace variables in build url template with regexes
            build_info = device_build_defaults.copy()
            build_info = {key: r"(.*)" for key in build_info}
            build_info["build_type"] = r"(?P<build_type>.*)"
            build_url_regex = build_url_template.format(**build_info)

            # attempt to parse build_type out of regexed build url
            build_type_match = re.match(build_url_regex, build_url)
            if build_type_match:
                return build_type_match.group("build_type")

        return "UNKNOWN"

    def _get_file_list_from_gsutil(self, gsutil_path):
        """Returns list of files / folder at gsutil provided.

        Args:
            gsutil_path (str): Location to use to obtain list of files.

        Returns:
            list: list of relative files / folders at that location.

        Raises:
            RuntimeError: if path does not exist.

        Note:
           'gsutil ls gs://example' output is ['gs://example/file1', 'gs://example/file2'].
           Absolute path is removed to match url format and enable ease of matching file patterns.
        """
        gsutil_path = self._validate_path_or_symlinked_path_exists(gsutil_path)
        output = host_utils.gsutil_command("ls", gsutil_path)
        relative_paths = [path.replace(gsutil_path, "") for path in output.splitlines()]
        return relative_paths

    def _get_file_list_from_jenkins(self, url):
        """Returns list of files at URL provided.

        Note:
            Definition of file is a hyperlink with a "." in it that's not a .css file.
            If server response code from urlopen() is not 200 nor 404,
            the method will retry the call to urlopen() up to MAX_RETRY_URl_OPEN times
            before raising the GazooDeviceError.

        Args:
            url(str): A URL string to use to obtain a list of files.

        Raises:
          RuntimeError: Response to URL is not HTTP code 200.

        Returns:
          list: list of links to files and folders at that location.
        """
        url = os.path.join(url, "api/xml?tree=artifacts%5BrelativePath%5D")
        raw_page = http_utils.read_raw_html_page(url)
        links = re.findall(
            r'<relativePath>([a-z0-9\_\-\./]+)</relativePath>', raw_page)
        return [os.path.join('artifact', link) for link in links]

    def _get_file_list_from_url(self, url):
        """Returns list of files at URL provided.

        Note:
            Definition of file is a hyperlink with a "." in it that's not a .css file.
            If server response code from urlopen() is not 200 nor 404,
            the method will retry the call to urlopen() up to MAX_RETRY_URl_OPEN times
            before raising the GazooDeviceError.

        Args:
            url(str): A URL string to use to obtain a list of files.

        Raises:
          RuntimeError: Response to URL is not HTTP code 200.

        Returns:
          list: list of links to files and folders at that location.
        """
        raw_info = http_utils.read_raw_html_page(url)
        files = re.findall(r'href=\"([\w\/\-\_\.\*]+)\"', raw_info)
        return [a_file for a_file in files
                if not a_file.endswith(".css") and "." in a_file]

    def _get_valid_build_prefix(self, path):
        """Validates and returns build prefix.

        Args:
            path (str): build path.

        Returns:
            str: prefix

        Raises:
            ValueError: if build type is not supported.
        """
        prefix_list = [key for key in self.build_types.keys() if key in path]
        if not prefix_list:
            raise ValueError("Obtaining builds from {} not supported. "
                             "Can only load builds from: {}".format(
                                 path, " and ".join(list(self.build_types.keys()))))
        return prefix_list[0]

    def _obtain_gsutil_build(self, gs_path):
        """Obtains file through the gsutil utility.

        Args:
          gs_path (str): gsutil path starting with prefix.

        Returns:
            str: local file path

        Raises:
            RuntimeError: if gsutil folder isn't accessible by user or build doesn't exist.
        """
        folder = os.path.dirname(gs_path) + "/"
        file_name = os.path.basename(gs_path)
        folder = self._validate_path_or_symlinked_path_exists(folder)
        full_path = os.path.join(folder, file_name)
        logger.info("{} acquiring build from {}".format(self.name, gs_path))
        host_utils.gsutil_command("cp", full_path, [self.local_build_dir])

        local_file_path = os.path.join(self.local_build_dir, file_name)
        if not os.path.exists(local_file_path):
            raise RuntimeError(
                "Unable to copy file from {} to {} via gsutil.".format(full_path, local_file_path))
        logger.info("{} successfully copied build to {}".format(self.name, local_file_path))
        return local_file_path

    def _obtain_url_build(self, url):
        """Obtains file from url and saves it into /tmp/<self.name>.

        Args:
            url(str): url starting with prefix.

        Returns:
            str: local file path

        Raises:
            RuntimeError: if prefix is not accessible or build doesn't exist.
        """
        # Retrieve list of files and download image file found
        file_name = os.path.basename(url)
        local_path = os.path.join(self.local_build_dir, file_name)
        # Check if main url location is accessible
        http_utils.download_file(url, local_path)
        return local_path

    def obtain_package(self, gsutil_path, destination_folder, destination_file):
        """Obtains a package file using gsutil and saves it locally.

        Args:
            gsutil_path (str): gsutil path to the package file.
            destination_folder (str): absolute path to folder to store file locally.
            destination_file (str): filename to use when saving file.

        Returns:
            str: absolute path to downloaded local package file.

        Raises:
            RuntimeError: if file doesn't exist where it should locally.

        Note:
            Packages will be saved to /tmp/<device_name>/packages/<package_name>.
        """
        logger.info("{} acquiring packages from {}.".format(self.name, gsutil_path))
        if not os.path.exists(destination_folder):
            os.makedirs(destination_folder, mode=0o777)
        destination_path = os.path.join(destination_folder, destination_file)

        # download zip file of packages using gsutil
        host_utils.gsutil_command("cp", gsutil_path, [destination_path])
        if not os.path.exists(destination_path):
            raise RuntimeError("Unable to copy file from {} to {} using gsutil.".format(
                gsutil_path, destination_path))

        logger.info("{} successfully copied packages to {}.".format(self.name, destination_path))
        return destination_path

    def _validate_path_or_symlinked_path_exists(self, gsutil_folder):
        """Validates path exists. Find first prefix that is symlink or doesn't exist.

        Args:
           gsutil_folder (str): folder

        Returns:
          str: folder or actual path if path had symlink in it.

        Raises:
          RuntimeError: if path doesn't exist.

        Note:
           Only handles symlinks in images. If the 'images' prefix breaks, this breaks.
        """
        try:
            output = host_utils.gsutil_command("ls", gsutil_folder)

            # First line is always the folder or symlink's name itself.
            if len(output.splitlines()) > 1:
                return gsutil_folder

        except RuntimeError:
            raise RuntimeError("File {} doesn't exist. Error: {}\n"
                               .format(gsutil_folder, traceback.format_exc()))
        return gsutil_folder


class BuildAutoCompleter(object):
    """Object for converting build information to build_url and firmware_identifier.
    """

    def __init__(self, owner=""):
        """Ininitalize the build autocompleter.

        Args:
            owner (str): optional LDAP of owner if initialized from a device class.
        """
        self.owner = owner
        self.templates = TEMPLATES.copy()
        self.device_build_defaults = DEFAULT_BUILD_DICTIONARY.copy()

    def get_build_url_and_file_identifier(self, device_type, is_version_check=False,
                                          build_url=None, **user_info):
        """Returns build path and file_identifier.

        Args:
            device_type (str): device type
            is_version_check (bool): Whether this is a version check.
            build_url (str): path to build folder that holds firmware.
            **user_info (dict): optional dictionary of build info to override default values.

        Return:
            tuple: build_url, file_identifier

        Raises:
            NotImplementedError: not implemented.
        """
        raise NotImplementedError("Not implemented.")

    def get_default_values(self, device_type):
        """Return default_build info for that device type.

        Args:
            device_type (str): device type to get.

        Returns:
            dict: dictionary of build_info
        """
        if device_type in self.device_build_defaults:
            default_build_info = self.device_build_defaults[device_type]

            # autocomplete default templates
            completed_build_templates = {}
            for build_prop_name, build_prop in default_build_info.items():
                if build_prop in self.templates:
                    prop_name = build_prop_name.replace("_template", "_default")
                    try:
                        prop_value = self.templates[build_prop].format(
                            device_type=device_type, **default_build_info)
                    except KeyError:
                        continue
                    completed_build_templates[prop_name] = prop_value
            self.device_build_defaults[device_type].update(completed_build_templates)

            return self.device_build_defaults[device_type]
        logger.warning(
            "{} does not currently support autocompletion of build info.".format(device_type))
        return {}

    def get_supported_device_types(self):
        """Returns all the devices supported by autocompleter.

        Returns:
            list: list of all device_types supported
        """
        device_types = []
        keys = list(self.device_build_defaults.keys())
        for key in keys:
            device_types += key.split("/")
        return device_types
