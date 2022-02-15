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

"""Build the gazoo_device Python package."""
import os
import re
from typing import List

import setuptools

_CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
_README_FILE = 'README.md'
_REQUIREMENTS_FILE = 'requirements.txt'
_SOURCE_CODE_DIR_NAME = 'gazoo_device'
_VERSION_FILE = '_version.py'


def _get_readme() -> str:
  """Returns contents of README.md."""
  readme_file = os.path.join(_CURRENT_DIR, _README_FILE)
  with open(readme_file) as open_file:
    return open_file.read()


def _get_requirements() -> List[str]:
  """Returns package requirements from requirements.txt."""
  requirements_file = os.path.join(_CURRENT_DIR, _REQUIREMENTS_FILE)
  with open(requirements_file) as open_file:
    requirements = open_file.read()
    if requirements:
      return requirements.splitlines()
  raise RuntimeError('Unable to find package requirements in {}'.format(
      requirements_file))


def _get_version() -> str:
  """Returns version from version.py."""
  version_file = os.path.join(
      _CURRENT_DIR, _SOURCE_CODE_DIR_NAME, _VERSION_FILE)
  with open(version_file) as open_file:
    contents = open_file.read()
    version_match = re.search(r'^version = "(.*)"', contents, re.M)
    if version_match:
      return version_match.group(1)
  raise RuntimeError(f'Unable to find "version = <version>" in {version_file}')


setuptools.setup(
    name='gazoo_device',
    version=_get_version(),
    description='Gazoo Device Manager',
    long_description=_get_readme(),
    long_description_content_type='text/markdown',
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: MacOS',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Software Development :: Embedded Systems',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Testing',
    ],

    # project's homepage
    url='https://github.com/google/gazoo-device',

    # author details
    author='Google LLC',
    author_email='gdm-authors@google.com',
    license='Apache 2.0',

    # define list of packages included in distribution
    packages=setuptools.find_packages(exclude=['gazoo_device.tests*']),
    package_dir={'gazoo_device': _SOURCE_CODE_DIR_NAME},
    package_data={
        'gazoo_device': [],
    },

    # runtime dependencies that are installed by pip during install
    install_requires=_get_requirements(),
    entry_points={
        'console_scripts': [
            'gdm=gazoo_device.gdm_cli:main'
        ],
    })
