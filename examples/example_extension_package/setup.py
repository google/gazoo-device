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

"""Builds the example extension package."""
import os
from typing import List

import setuptools

_CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
_PACKAGE_NAME = "example_extension_package"
_README_FILE = "README.md"


def _get_packages() -> List[str]:
  """Returns packages to include in example_extension_package package."""
  sub_packages = [_PACKAGE_NAME + "." + package
                  for package in setuptools.find_packages()]
  return [_PACKAGE_NAME] + sub_packages


def _get_readme() -> str:
  """Returns contents of README.md."""
  readme_file = os.path.join(_CURRENT_DIR, _README_FILE)
  with open(readme_file) as open_file:
    return open_file.read()


setuptools.setup(
    name=_PACKAGE_NAME,
    version="0.0.1",
    description="Example extension package for gazoo-device",
    long_description=_get_readme(),
    long_description_content_type="text/markdown",
    python_requires=">=3",

    # project's homepage
    url="https://github.com/google/gazoo-device",

    # author details
    author="Google LLC",
    author_email="gdm-authors@google.com",
    license="Apache 2.0",

    # define list of packages included in distribution
    packages=_get_packages(),
    package_dir={"example_extension_package": ""},
    package_data={
        "example_extension_package": ["log_event_filters/*.json"],
    },

    # runtime dependencies that are installed by pip during install
    install_requires=[
        "absl-py>=0.12.0",
        "gazoo-device>=1.0.0",
        "immutabledict>=2.0.0",
    ])
