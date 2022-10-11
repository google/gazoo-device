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

"""Setup script for GDM's test package."""
from typing import List

import setuptools


def get_packages() -> List[str]:
  """Returns subpackages to include in this package."""
  base_package = "gazoo_device.tests"
  sub_packages = [base_package + "." + sub_package
                  for sub_package in setuptools.find_packages()]
  return [base_package] + sub_packages


setuptools.setup(
    name="gazoo_device.tests",
    version="1.0.0",
    description="GDM unit and on-device (functional) tests",
    url="https://github.com/google/gazoo-device",
    author="Google LLC",
    author_email="gdm-authors@google.com",
    license="Apache 2.0",
    packages=get_packages(),
    package_dir={
        "gazoo_device.tests": "",
    },
    package_data={
        "gazoo_device.tests": ["functional_tests/configs/*.json"],
    },
    ######################################################################
    # ../requirements.txt has similar requirements.
    # If same requirements appear at both files,
    # These dependency version specifications must match.
    ######################################################################
    install_requires=[
        "absl-py>=0.12.0",
        "cryptography>=38.0.1",
        # esptool cannot be included because of restrictive GPL v2 licence.
        "immutabledict>=2.0.0",
        "intelhex>=2.2.1",
        "mobly>=1.11.1",
        "pigweed>=0.0.3",
        "prompt-toolkit>=3.0.19",
        "protobuf>=3.17.3",
        "psutil>=5.0.1",
        "pyserial>=3.5",
        "pyudev>=0.22.0",
        "websocket-client>=0.56.0",
    ]
)
