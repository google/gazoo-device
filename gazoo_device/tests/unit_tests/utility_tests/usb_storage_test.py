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

"""Unit tests for functions in the usb_storage module."""
import os
import shutil
import stat
import subprocess
from unittest import mock

from gazoo_device import errors
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import usb_config
from gazoo_device.utility import usb_storage
from gazoo_device.utility import usb_utils
import psutil


class FakePartition:

  def __init__(self, device, mountpoint):
    self.device = device
    self.mountpoint = mountpoint


class UsbStorageUtilsTests(unit_test_case.UnitTestCase):
  """USB storage utility tests."""

  def setUp(self):
    super(UsbStorageUtilsTests, self).setUp()
    self.usb_info_response = {
        "/dev/tty.usbserial-5678":
            usb_config.UsbInfo(serial_number="5678", disk="/dev/sdb"),
        "/dev/tty.usbserial-1234":
            usb_config.UsbInfo(serial_number="1234", disk="/dev/sda"),
        "/dev/tty.usbserial-910":
            usb_config.UsbInfo(serial_number="910", disk="/dev/sdc")
    }
    self.disk_partition_responses = [
        FakePartition(device="/dev/sda", mountpoint="lol")
    ]
    self.example_storage = usb_storage.UsbStorage(serial_number="1234")
    self.add_time_mocks()

  @mock.patch.object(usb_storage.UsbStorage, "mount")
  @mock.patch.object(usb_storage.UsbStorage, "unmount")
  @mock.patch.object(usb_storage.UsbStorage, "eject")
  def test_usb_storage_works_as_decorator(self, mock_eject, mock_unmount,
                                          mock_mount):
    """Check UsbStorage object works as a decorator."""
    with usb_storage.UsbStorage(serial_number="1234"):
      pass
    mock_unmount.assert_not_called()
    mock_mount.assert_called()
    mock_eject.assert_called()

  @mock.patch.object(usb_storage.UsbStorage, "mount")
  @mock.patch.object(usb_storage.UsbStorage, "unmount")
  @mock.patch.object(usb_storage.UsbStorage, "eject")
  def test_usb_storage_works_as_decorator_no_eject(self, mock_eject,
                                                   mock_unmount,
                                                   mock_mount):
    """Check UsbStorage objects works as a decorator with no eject."""
    with usb_storage.UsbStorage(serial_number="1234", eject_on_exit=False):
      pass
    mock_unmount.assert_called()
    mock_mount.assert_called()
    mock_eject.assert_not_called()

  def test_usb_storage_get_properties(self):
    """Check properties are fetched by usb storage."""

    values_1234 = {"disk": "/dev/sda", "mount_point": "lol"}
    values_910 = {"disk": "/dev/sdc", "mount_point": None}

    with mock.patch.object(
        usb_utils,
        "get_address_to_usb_info_dict",
        return_value=self.usb_info_response):
      with mock.patch.object(
          psutil, "disk_partitions",
          return_value=self.disk_partition_responses):
        storage = usb_storage.UsbStorage(serial_number="1234")
        for key, value in values_1234.items():
          self.assertEqual(getattr(storage, key), value)
        self.assertTrue(storage.is_mounted())
        self.assertTrue(storage.is_found())

        storage = usb_storage.UsbStorage(serial_number="910")
        for key, value in values_910.items():
          self.assertEqual(getattr(storage, key), value)
        self.assertFalse(storage.is_mounted())
        self.assertTrue(storage.is_found())

        storage = usb_storage.UsbStorage(serial_number="gobbly")
        self.assertFalse(storage.is_mounted())
        self.assertFalse(storage.is_found())

  @mock.patch.object(shutil, "copyfile")
  @mock.patch.object(usb_storage, "_path_exists")
  @mock.patch.object(os, "makedirs")
  def test_usb_storage_copy_file_to(self, mock_make, mock_exists,
                                    mock_copyfile):
    """Check usb storage and its several errors."""
    with mock.patch.object(
        usb_utils,
        "get_address_to_usb_info_dict",
        return_value=self.usb_info_response):
      with mock.patch.object(
          psutil, "disk_partitions",
          return_value=self.disk_partition_responses):
        # Not Mounted
        storage = usb_storage.UsbStorage(serial_number="789")
        with self.assertRaisesRegex(errors.DeviceError, "mount"):
          storage.copy_file_to("/gobbly", "gook")

        storage = usb_storage.UsbStorage(serial_number="1234")

        # Success
        mock_exists.return_value = True
        storage.copy_file_to("/gobbly", "gook")

        # Failure for desintation
        mock_exists.side_effect = [True, False]
        with self.assertRaisesRegex(errors.DeviceError, "destination"):
          storage.copy_file_to("/gobbly")

        # Failure for source file
        mock_exists.side_effect = None
        mock_exists.return_value = False
        with self.assertRaisesRegex(errors.DeviceError, "gobbly"):
          storage.copy_file_to("/gobbly")

  @mock.patch.object(shutil, "copy")
  @mock.patch.object(usb_storage, "_path_exists")
  @mock.patch.object(os, "remove")
  def test_usb_storage_move_file_from(self, mock_remove, mock_exists,
                                      mock_copyfile):
    """Check usb storage and its several errors."""
    with mock.patch.object(
        usb_utils,
        "get_address_to_usb_info_dict",
        return_value=self.usb_info_response):
      with mock.patch.object(
          psutil, "disk_partitions",
          return_value=self.disk_partition_responses):
        # Not Mounted
        storage = usb_storage.UsbStorage(serial_number="789")
        with self.assertRaisesRegex(errors.DeviceError, "mount"):
          storage.move_file_from("/gobbly", "gook")

        storage = usb_storage.UsbStorage(serial_number="1234")

        # Success
        mock_exists.return_value = True
        storage.move_file_from("/gobbly", "gook")
        mock_remove.assert_called()

        # Failure for desintation
        mock_exists.side_effect = [True, False]
        with self.assertRaisesRegex(errors.DeviceError, "destination"):
          storage.move_file_from("/gobbly", "gook")

        # Failure for source file
        mock_exists.side_effect = None
        mock_exists.return_value = False
        with self.assertRaisesRegex(errors.DeviceError, "gobbly"):
          storage.move_file_from("/gobbly", "gook")

  @mock.patch.object(subprocess, "check_output")
  @mock.patch("sys.platform", "linux")
  def test_mount(self, mock_subprocess):
    """Check mounting usb storage on Linux."""
    mock_stat_return = mock.Mock()
    mock_stat_return.st_mode = stat.S_ISUID
    with mock.patch.object(os, "stat", return_value=mock_stat_return):
      with mock.patch.object(
          usb_utils,
          "get_address_to_usb_info_dict",
          return_value=self.usb_info_response):
        with mock.patch.object(
            psutil,
            "disk_partitions",
            return_value=self.disk_partition_responses) as mock_part:
          storage = usb_storage.UsbStorage(serial_number="1234")
          # Success Already mounted
          storage.mount()

          # Success from mounting
          mock_part.side_effect = [[], self.disk_partition_responses,
                                   self.disk_partition_responses]
          storage.mount()

          # Failure from final mount
          mock_part.side_effect = None
          mock_part.return_value = []
          with self.assertRaisesRegex(errors.DeviceError, "mount failed"):
            storage.mount()

          # Failure from subprocess
          mock_subprocess.side_effect = subprocess.CalledProcessError(
              output="Not authorized", cmd="x", returncode=1)
          mock_part.return_value = []
          with self.assertRaisesRegex(errors.DeviceError, "permission error"):
            storage.mount()

          # Failure from stat
          mock_stat_return.st_mode = None
          with self.assertRaisesRegex(errors.DeviceError, "Missing SUID bit"):
            storage.mount()

          # Failure because device is not attached.
          storage = usb_storage.UsbStorage(serial_number="000")
          with self.assertRaisesRegex(errors.DeviceError, "not found"):
            storage.mount()

  @mock.patch.object(subprocess, "check_output")
  @mock.patch("sys.platform", "linux")
  def test_unmount(self, mock_subprocess):
    """Check unmounting usb storage on Linux."""
    mock_stat_return = mock.Mock()
    mock_stat_return.st_mode = stat.S_ISUID
    mock_stat_return.st_dev = 0x12345678
    with mock.patch.object(os, "stat", return_value=mock_stat_return):
      with mock.patch.object(
          usb_utils,
          "get_address_to_usb_info_dict",
          return_value=self.usb_info_response):
        with mock.patch.object(usb_storage.UsbStorage,
                               "is_mounted") as mock_is_mounted:
          storage = usb_storage.UsbStorage(serial_number="1234")

          # Success Already unmounted
          mock_is_mounted.return_value = False
          storage.unmount()

          # Success from Unmounting
          mock_is_mounted.return_value = True
          storage.unmount()

          # Failure: never unmounts
          with mock.patch.object(
              psutil,
              "disk_partitions",
              return_value=self.disk_partition_responses):
            with self.assertRaisesRegex(errors.DeviceError, "unmount failed"):
              storage.unmount(.1)

  @mock.patch("sys.platform", "linux")
  def test_is_device_ejected(self):
    """Check if the device is ejected on Linux."""
    with mock.patch.object(
        usb_utils,
        "get_address_to_usb_info_dict",
        return_value=self.usb_info_response):
      storage = usb_storage.UsbStorage(serial_number="0000")

      # Success, not attached
      self.assertTrue(storage.is_device_ejected())

      # Success, appears ejected
      storage = usb_storage.UsbStorage(serial_number="1234")
      with mock.patch.object(usb_storage, "open",
                             mock.mock_open(read_data="/dev/sdc")):
        self.assertTrue(storage.is_device_ejected(timeout=.05))

      # Failure
      with mock.patch.object(usb_storage, "open",
                             mock.mock_open(read_data="/dev/sda")):
        self.assertFalse(storage.is_device_ejected(timeout=.05))

  @mock.patch.object(usb_storage.UsbStorage, "unmount")
  @mock.patch.object(
      usb_storage.UsbStorage, "is_device_ejected", return_value=True)
  @mock.patch.object(usb_storage, "_validate_suid_bit")
  @mock.patch.object(subprocess, "check_output")
  @mock.patch("sys.platform", "linux")
  def test_eject(self, mock_check_output, mock_validate, mock_is_ejected,
                 mock_unmount):
    """Check the device can be ejected on Linux."""
    with mock.patch.object(
        usb_utils,
        "get_address_to_usb_info_dict",
        return_value=self.usb_info_response):
      storage = usb_storage.UsbStorage(serial_number="0000")
      # Success, already ejected
      storage.eject()

      # Success, ejects
      mock_is_ejected.side_effect = [False, True]
      storage.eject()

      # Failure, never ejects
      mock_is_ejected.side_effect = None
      mock_is_ejected.return_value = False
      with self.assertRaisesRegex(errors.DeviceError, "Unable to eject"):
        storage.eject()

      # Failure with binary
      mock_check_output.side_effect = subprocess.CalledProcessError(
          cmd="/usr/bin/eject", returncode=1, output=b"Permission error")
      with self.assertRaisesRegex(errors.DeviceError, "/usr/bin/eject"):
        storage.eject()


if __name__ == "__main__":
  unit_test_case.main()
