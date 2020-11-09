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

"""Build the gazoo_device Python package."""
import os
import re
import setuptools

HERE = os.path.abspath(os.path.dirname(__file__))
README_FILE = 'README.md'
REQUIREMENTS_FILE = 'requirements.txt'
VERSION_FILE = '_version.py'


def readme():
    """Returns readme file as string."""
    readme_file = os.path.join(HERE, README_FILE)
    with open(readme_file) as open_file:
        return open_file.read()


def get_requirements():
    """Get package requirements from requirements.txt file."""
    requirements_file = os.path.join(HERE, REQUIREMENTS_FILE)
    with open(requirements_file) as open_file:
        requirements = open_file.read()
        if requirements:
            return requirements.splitlines()
    raise RuntimeError('Unable to find package requirements in {}'.format(
        requirements_file))


def get_version():
    """Get version string from version.py file."""
    version_file = os.path.join(HERE, VERSION_FILE)
    if not os.path.exists(version_file):  # backwards compatibility for GoB
        version_file = os.path.join(HERE, 'gazoo_device', VERSION_FILE)
    with open(version_file) as open_file:
        contents = open_file.read()
        version_match = re.search(r'^version = "(.*)"', contents, re.M)
        if version_match:
            return version_match.group(1)
    raise RuntimeError('Unable to find "version = "<version>"" in {}'.format(
        version_file))


setuptools.setup(
    name='gazoo_device',
    version=get_version(),
    description='Gazoo Device Manager',
    long_description=readme(),
    long_description_content_type="text/markdown",
    python_requires='>=3',

    # project's homepage
    url='https://github.com/google/gazoo-device',

    # author details
    author='Google LLC',
    author_email='gdm-authors@google.com',
    license='Apache 2.0',

    # define list of packages included in distribution
    packages=setuptools.find_packages(),
    package_dir={'gazoo_device': 'gazoo_device'},
    package_data={
        'gazoo_device': ['bin/*',
                         'filters/*/*',
                         'device_scripts/*',
                         'build_defaults/*',
                         'keys/*']},

    # runtime dependencies that are installed by pip during install
    install_requires=get_requirements(),
    entry_points={
        'console_scripts': [
            'gdm=gazoo_device.gdm_cli:main'
        ],
    })
