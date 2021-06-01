# Copyright 2021 Google LLC
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
    install_requires=[
        "absl-py>=0.12.0",
        "protobuf>=3.17.0",
        "retry>=0.9.2",
    ]
)
