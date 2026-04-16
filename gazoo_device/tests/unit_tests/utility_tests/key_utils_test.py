# Copyright 2023 Google LLC
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

"""Unit tests for key_utils.py."""
from gazoo_device import data_types
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import key_utils


class KeyUtilsTests(unit_test_case.UnitTestCase):
  """Key utility tests."""

  def test_download_key(self):
    """Tests the download_key function."""
    mock_key_info = data_types.KeyInfo(
        "my_ssh_key", data_types.KeyType.SSH, "gazoo_device_controllers")
    regex = r"GDM doesn't come with built-in SSH key.*my_ssh_key"
    with self.assertRaisesRegex(RuntimeError, regex):
      key_utils.download_key(mock_key_info, self.artifacts_directory)


if __name__ == "__main__":
  unit_test_case.main()
