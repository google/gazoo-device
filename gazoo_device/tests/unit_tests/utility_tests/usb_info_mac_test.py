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

"""Unit tests for usb_info_mac.py."""
import copy
import functools
from unittest import mock

from absl.testing import parameterized
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import usb_info_mac


def get_pyserial_address(device_serial, mac_path_lookup):
  return mac_path_lookup.get(device_serial, "")


class UsbInfoTests(parameterized.TestCase):
  """USB Info tests for MAC."""

  def _compare_dictionaries(self, actual_dict, expected_dict):
    self.assertCountEqual(actual_dict.keys(), expected_dict.keys())
    for address, expected_entry in expected_dict.items():
      actual_entry = actual_dict[address]
      for key, expected_value in expected_entry.items():
        actual_value = getattr(actual_entry, key)
        if isinstance(actual_value, list):
          self.assertCountEqual(
              actual_value, expected_value, "Entry for {}'s {} "
              "does not meet expectation".format(address, key))
        else:
          self.assertEqual(
              actual_value, expected_value, "Entry for {}'s {} should "
              "be {} but is {}".format(address, key, expected_value,
                                       actual_value))

if __name__ == "__main__":
  unit_test_case.main()
