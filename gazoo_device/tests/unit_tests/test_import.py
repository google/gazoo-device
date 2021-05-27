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

"""Tests that gazoo_device can be imported."""
import logging
import unittest


class ImportTestSuite(unittest.TestCase):
  """Tests that gazoo_device can be imported."""

  def test_import(self):
    """Tests importing gazoo_device."""
    try:
      import gazoo_device  # pylint: disable=g-import-not-at-top
    except ImportError as err:
      self.fail(f"Unable to import gazoo_device. Error: {err!r}.")
    logging.info("gazoo_device version: %s", gazoo_device.version)


if __name__ == "__main__":
  unittest.main()
