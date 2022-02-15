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

"""Unit tests for usb_info_linux.py and usb_info_mac.py."""
import copy
import functools
from unittest import mock

from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import usb_info_linux
from gazoo_device.utility import usb_info_mac


def get_pyserial_address(device_serial, mac_path_lookup):
  return mac_path_lookup.get(device_serial, "")


class UsbInfoTests(unit_test_case.UnitTestCase):
  """USB Info tests."""

  def test_001_usb_info_on_mac(self):
    """Tests usb_info_mac.get_address_to_usb_info_dict()."""
    test_cases = [
    ]
    for i, (mock_devices_json, mock_device_paths, mock_path_lookup,
            expected_usb_info) in enumerate(test_cases):
      mock_get_entry_address = functools.partial(
          get_pyserial_address,
          mac_path_lookup=mock_path_lookup)
      with mock.patch.object(usb_info_mac.subprocess, "check_output"):
        with mock.patch.object(
            usb_info_mac.json, "loads", return_value=mock_devices_json):
          with mock.patch.object(
              usb_info_mac,
              "_get_entry_address",
              side_effect=mock_get_entry_address):
            with mock.patch.object(
                usb_info_mac.os.path,
                "exists",
                side_effect=(
                    lambda path, paths=mock_device_paths: path in paths)):
              self.logger.info(f"Testing configuration {i+1} on Mac...")
              address_to_usb_info = usb_info_mac.get_address_to_usb_info_dict()
              self._compare_dictionaries(
                  address_to_usb_info, expected_usb_info)

  def test_get_cambrionix_model(self):
    """Tests usb_info_linux._get_cambrionix_model()."""
    mock_udev_device_1 = mock.MagicMock()
    mock_udev_device_1.properties = {"ID_MODEL": "PP8S"}
    self.assertEqual(
        "PP8S", usb_info_linux._get_cambrionix_model(mock_udev_device_1))

    mock_udev_device_2 = mock.MagicMock()
    mock_udev_device_2.properties = {}
    mock_udev_device_2.parent.parent.parent.parent.properties = {
        "ID_MODEL": "PP15S"}
    self.assertEqual(
        "PP15S", usb_info_linux._get_cambrionix_model(mock_udev_device_2))

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
