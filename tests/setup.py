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

"""Setup script for installing GDM's functional tests."""
import setuptools


setuptools.setup(
    name="gazoo_device_functional_tests",
    version="0.0.1",
    description="GDM functional (on-device) tests",
    # project's homepage
    url="https://github.com/google/gazoo-device",
    # author details
    author="Google LLC",
    author_email="gdm-authors@google.com",
    license="Apache 2.0",
    # define list of packages included in distribution
    packages=["functional_tests"],
    # runtime dependencies that are installed by pip during install
    install_requires=[
        "mobly"
    ]
)
