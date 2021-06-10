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

"""Utility module for working with USB mass storage device.

This module uses a combination of ``pyudev`` and ``psutil`` to list and filter
USB mass storage devices.

.. note:

    According to the udiskctl man page
    http://manpages.ubuntu.com/manpages/trusty/man8/udisks.8.html#contenttoc5

    Therefore, applications can not rely on tools like e.g.  udisksctl(1) to be
    available. Additionally, there is no guarantee that the options,
    command-line switches etc. of command-line tools or similar will remain
    stable.

    Instead, applications should only use the D-Bus API, the libudisks2
    library or tools such as dbus-send(1) or gdbus(1) to interact with
    udisksd(8).
"""
import os
import re
import shutil
import stat
import subprocess
import sys
import time
import psutil
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.utility import usb_utils

logger = gdm_logger.get_logger()


def _validate_suid_bit(cmd_str):
  if sys.platform == "darwin":
    return
  binary = cmd_str.split()[0]
  if not os.stat(binary).st_mode and stat.S_ISUID:
    raise errors.DeviceError(
        "Missing SUID bit on {binary} "
        "Fix using 'sudo chmod u+s {binary}'".format(binary=binary))


class UsbStorage(object):
  """USB mass storage device class.

  Used in 'with block' and will mount the USB mass storage device upon entering
  the with block and eject the USB mass storage device upon exiting the
  'with block'. If the UsbStorage class is not used within a 'with block' then
  the methods of mount, unmount, and eject can be called separately.
  """
  commands_dict = {
      "darwin": {
          "EJECT": "diskutil eject {}",
          "MOUNT": "diskutil mount {}",
          "UNMOUNT": "diskutil unmount {}"
      },
      "linux": {
          "EJECT": "/usr/bin/eject {}",
          "MOUNT": "/usr/bin/udisksctl mount --no-user-interaction -b {}",
          "UNMOUNT": "/bin/umount {}"
      }
  }

  def __init__(self, serial_number, add_log_note_func=None, eject_on_exit=True):
    """Initialize the USB mass storage device instance with the information specified.

    Args:
        serial_number (str): serial number to identify device.
        add_log_note_func (func): function to log usb serial methods to
          device logs.
        eject_on_exit (bool): whether to eject or unmount on exit from
          context manager.
    """
    self._serial_number = serial_number
    self.add_log_note_func = add_log_note_func
    self.eject_on_exit = eject_on_exit
    if sys.platform == "darwin":
      self.commands = self.commands_dict["darwin"]
    else:
      self.commands = self.commands_dict["linux"]

  def __enter__(self):
    self.mount()
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    if self.eject_on_exit:
      self.eject()
    else:
      self.unmount()

  @property
  def disk(self):
    """Disk that device mounted to. Empty if not mounted."""
    devices_info = self._get_devices_info()
    return devices_info[0].disk if devices_info else ""

  @property
  def mount_point(self):
    """Returns the mass storage mount point to the caller.

    Returns:
        str: mount path location for caller to use in opening files on the
        mass storage device
    """
    usb_endpoint_infos = self._get_devices_info()
    if usb_endpoint_infos:
      partitions = psutil.disk_partitions()
      for usb_info_inst in usb_endpoint_infos:
        for partition in partitions:
          if partition.device == usb_info_inst.disk:
            return partition.mountpoint
    return None

  def add_log_note(self, msg):
    """Adds note in device logs if method available."""
    if self.add_log_note_func:
      self.add_log_note_func(msg)

  def copy_file_to(self, source_file_path, relative_destination_dir=None):
    """Copies source file to destination directory specified.

    Args:
        source_file_path (str): path to source file to copy to mass storage
          device
        relative_destination_dir (str): optional path relative to the mount
          path of the mass storage device

    Raises:
        DeviceError: if storage is not mounted, the mount path doesn't
        exist, or if the source file doesn't exist after copying the source file
        to the mount path + relative destination directory destination

    Note:
        The storage device must be mounted before calling this method. If the
        relative destination directory specified doesn't exist it will be
        created before the source file is copied
    """
    if not self.is_mounted():
      raise errors.DeviceError("Device copy file failed. "
                               "Device with Serial {} is not mounted.".format(
                                   self._serial_number))

    mount_point = self.mount_point
    if relative_destination_dir is not None:
      dst_file_path = os.path.join(mount_point, relative_destination_dir)
    else:
      dst_file_path = mount_point

    if not os.path.exists(dst_file_path):
      logger.debug("Creating destination path %s", dst_file_path)
      os.makedirs(dst_file_path)

    file_name = os.path.basename(source_file_path)
    dst_file_path = os.path.join(dst_file_path, file_name)
    msg = "Copying {} to {}".format(source_file_path, dst_file_path)
    logger.debug(msg)
    self.add_log_note(msg)
    shutil.copyfile(source_file_path, dst_file_path)
    if not os.path.exists(dst_file_path):
      raise errors.DeviceError(
          "Device copy file failed. "
          "File does not exist at destination {}"
          "Check destination path permissions.".format(dst_file_path))
    msg = "Copying {} to {} completed".format(source_file_path, dst_file_path)
    logger.debug(msg)
    self.add_log_note(msg)

  def eject(self, timeout=100.0):
    """Unmounts and ejects the mass storage device within the timeout specified.

    Args:
        timeout (float): time to wait to confirm the mass storage has been
          unmounted and ejected

    Raises:
        DeviceError: if timeout is exceeded before storage is confirmed as
        being unmounted or ejected.
    """
    start_time = time.time()
    self.add_log_note("{} eject requested.".format(self._serial_number))
    if self.is_device_ejected(timeout=.1):
      self.add_log_note("{} already ejected.".format(self._serial_number))
      return
    self.unmount(timeout=timeout)
    _validate_suid_bit(self.commands["EJECT"])
    cmd_list = self.commands["EJECT"].format(self.disk).split()
    try:
      subprocess.check_output(cmd_list)
    except subprocess.CalledProcessError as err:
      raise errors.DeviceError("Device eject failed. "
                               "{} produced this error: {!r}".format(
                                   cmd_list, err.output))
    if self.is_device_ejected(timeout=timeout):
      self.add_log_note("{} ejected in {}s".format(
          self._serial_number, int(time.time() - start_time)))
      return
    raise errors.DeviceError("Device eject failed. "
                             "Unable to eject USB mass storage {} in {}s"
                             "Check if device is currently in use. ".format(
                                 self.mount_point, timeout))

  def is_device_ejected(self, timeout=20):
    """Check whether device is ejected from the system.

    Args:
        timeout (int):  Number of seconds to wait for successful eject.

    Returns:
        bool: True if device is ejected.
    """
    exit_time = time.time() + timeout
    while time.time() < exit_time:
      devices_info = self._get_devices_info()
      if not devices_info:
        return True
      if sys.platform != "darwin":
        device_id_path = devices_info[0].disk
        with open("/etc/fstab", "r") as open_file:
          text = open_file.read()
        if not re.search(device_id_path, text):
          return True
      time.sleep(.5)
    return False

  def is_found(self):
    """Returns True if the mass storage device has been detected and is available to mount.

    Returns:
        bool: True if mass storage device is detected
    """
    return bool(self._get_devices_info())

  def is_mounted(self, timeout=20):
    """Returns True if the mass storage device is currently mounted.

    Args:
        timeout (float): time to wait for it to mount before timeout.

    Returns:
        bool: True if mass storage device is mounted

    Note:
        Uses a timeout as not all devices are using mount to mount the device
        and it can take a few seconds for the computers to register the external
        mount.
    """
    start_time = time.time()
    exit_time = start_time + timeout
    while time.time() < exit_time:
      if self.mount_point:
        msg = "{} found mounted at {} in {}s".format(
            self._serial_number, self.mount_point,
            int(time.time() - start_time))
        self.add_log_note(msg)
        logger.debug(msg)
        return True
    return False

  def mount(self, timeout=180):
    """Mounts the mass storage device within the timeout specified.

    Args:
        timeout (float): time to wait to confirm storage has been mounted
          and/or after manually attempting to mount the storage

    Raises:
        DeviceError: if timeout is exceeded before storage is confirmed as
        being mounted.

    Note:
        Since there is a udev rule that is responsible for performing the
        actual mounting of
        the device this method will wait up to the timeout specified before
        attempting to
        manually mount the device and then wait again for the timeout
        specified to confirm
        that the device has been successfully mounted
    """
    self.add_log_note("{} mount requested.".format(self._serial_number))
    if self.is_mounted():
      return
    if not self.is_found():
      self.add_log_note("Error: {} not found on machine.".format(
          self._serial_number))
      raise errors.DeviceError(
          "Device mount failed. "
          "USB mass storage matching Serial#={} was not found. "
          "\nCheck cables and device or try rebooting.".format(
              self._serial_number))
    msg = "Mounting {}".format(self.disk)
    logger.debug(msg)
    self.add_log_note(msg)
    _validate_suid_bit(self.commands["MOUNT"])
    cmd_list = self.commands["MOUNT"].format(self.disk).split()
    try:
      subprocess.check_output(cmd_list)
    except subprocess.CalledProcessError as err:
      if isinstance(err.output, bytes):
        err.output = err.output.decode("utf-8")
      if "Not authorized" in err.output:
        err = "Try running 'sudo chmod u+s {}' to fix permission error.".format(
            " ".join(cmd_list[0]))
      raise errors.DeviceError("Device mount failed. Err: {!r}".format(err))

    if not self.is_mounted(timeout=timeout):
      raise errors.DeviceError(
          "Device mount failed. Not mounted after {}s".format(timeout))

  def move_file_from(self,
                     relative_source_file_path,
                     destination,
                     delete_file=True):
    """Moves file from storage mount point to destination directory specified.

    Args:
        relative_source_file_path (str): relative path to file on device to
          copy over.
        destination (str): destination directory or file name path
        delete_file (bool): delete file from device.

    Raises:
        DeviceError: if storage is not mounted, the mount path doesn't
        exist, or if the source file doesn't exist

    Note:
        The storage device must be mounted before calling this method.
    """
    if not self.is_mounted():
      raise errors.DeviceError("Move_file_from failed. "
                               "Device with Serial {} is not mounted.".format(
                                   self._serial_number))

    source_file_path = os.path.join(self.mount_point, relative_source_file_path)

    if not os.path.exists(source_file_path):
      raise errors.DeviceError(
          "Device copy file failed. "
          "Source file {} doesn't exist. ".format(source_file_path))

    msg = "Copying {} to {}".format(source_file_path, destination)
    logger.debug(msg)
    self.add_log_note(msg)
    shutil.copy(source_file_path, destination)

    if delete_file:
      logger.debug("Removing %s", source_file_path)
      os.remove(source_file_path)

    if not os.path.exists(destination):
      raise errors.DeviceError(
          "Device copy file failed. "
          "Destination {} does not exist. "
          "Check destination path permissions.".format(destination))
    msg = "Copying {} to {} completed.".format(relative_source_file_path,
                                               destination)
    logger.debug(msg)
    self.add_log_note(msg)

  def unmount(self, timeout=180.0):
    """Unmounts the mass storage device within the timeout specified.

    Args:
        timeout (float): time to wait to confirm storage and successfully
          unmounted

    Raises:
        DeviceError: if timeout is exceeded before storage is confirmed as
        being unmounted
    """
    start_time = time.time()
    exit_time = start_time + timeout
    self.add_log_note("{} unmount requested".format(self._serial_number))
    mount_point = self.mount_point
    if not mount_point:
      self.add_log_note("{} already unmounted".format(self._serial_number))
      return
    self.add_log_note("{} unmounting from {}".format(self._serial_number,
                                                     mount_point))

    _validate_suid_bit(self.commands["UNMOUNT"])
    cmd_list = self.commands["UNMOUNT"].format(mount_point).split()
    try:
      subprocess.check_output(cmd_list)
    except subprocess.CalledProcessError as err:
      raise errors.DeviceError("Device unmount failed. "
                               "Error when calling /bin/umount: {}".format(
                                   err.output))

    while time.time() < exit_time:
      if not self.mount_point:
        msg = "{} successfully unmounted in {}s".format(
            self._serial_number, int(time.time() - start_time))
        logger.debug(msg)
        self.add_log_note(msg)
        return

    raise errors.DeviceError(
        "Device unmount failed. "
        "Unmounting USB mass storage at {} failed after {}s".format(
            self.mount_point, timeout))

  def _get_devices_info(self):
    """Returns info for the device.

    Returns:
      list: one or more matching usbinfo objects for each usb endpoint that
      matches.
    """
    return usb_utils.find_matching_connections(
        {"serial_number": {
            "include_regex": self._serial_number
        }})
