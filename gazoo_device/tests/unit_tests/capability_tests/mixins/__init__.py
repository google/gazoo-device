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

"""Mixins for testing capabilities in device classes."""


def load_tests(loader, standard_tests, pattern):
  """Prevents test discovery in the mixin modules.

  Mixin test cases can't be run directly. They have to be used in conjunction
  with a test class which performs the setup required by the mixin test cases.
  This does not prevent mixin test case discovery in test classes that inherit
  from mixins.

  Args:
    loader: A unit test loader instance. Unused.
    standard_tests: Already loaded test cases.
    pattern: Test method name pattern. Unused.

  Returns:
    Already loaded standard_tests.
  """
  del loader, pattern  # Unused.
  return standard_tests
