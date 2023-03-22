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

"""Mixin for file_transfer capability."""
import builtins
import glob
import os
from unittest import mock

from gazoo_device import errors
from gazoo_device.utility import adb_utils
from gazoo_device.utility import host_utils


def _any_methods_called(methods):
  return any(getattr(tup[0], tup[1]).called for tup in methods)


class MockMethods:
  """Class to mock out methods for testing."""

  def __init__(self, method_tuples, return_a_value=None, add_side_effect=None):
    self.patchs = []
    for tup in method_tuples:
      (module, method_name, return_value, side_effect) = tup
      if return_a_value and return_value:
        self.patchs.append(
            mock.patch.object(module, method_name, return_value=return_value))
      elif add_side_effect and side_effect:
        self.patchs.append(
            mock.patch.object(module, method_name, side_effect=side_effect))
      else:
        self.patchs.append(mock.patch.object(module, method_name))

  def __enter__(self):
    for patcher in self.patchs:
      patcher.start()
    return self

  def __exit__(self, a_type, value, trace):
    for patcher in self.patchs:
      patcher.stop()


class TestFileTransfer:
  """Mixin for common device unit tests  of send and recv files.

  Assumes self.uut is set.
  """

  def test_receive_file_from_device_bad_destination_path(self):
    """Verify receive_from_device raises error on bad destination path."""
    self._setup_mocks()
    sources = "/path/to/some/file"
    destination_path = "/bogus/path"
    with MockMethods(self._recv_methods):
      with mock.patch.object(
          os.path, "exists", return_value=False) as mock_exists:
        with self.assertRaises(errors.DeviceError):
          self.uut.file_transfer.recv_file_from_device(
              sources, dest=destination_path)
        self.assertTrue(mock_exists.called)
      self.assertFalse(_any_methods_called(self._recv_methods))

  def test_receive_file_from_device_def_destination_path(self):
    """Verify receive_from_device skips path check for default destination path."""
    self._setup_mocks()
    sources = "/path/to/some/file"
    with MockMethods(self._recv_methods, return_a_value=True):
      with mock.patch.object(os.path, "exists", return_value=True):
        self.uut.file_transfer.recv_file_from_device(sources)
      self.assertTrue(_any_methods_called(self._recv_methods))

  def test_receive_file_from_device_bad_pull(self):
    """Verify receive_from_device raises error when file doesn't exist."""
    self._setup_mocks()
    source = "/path/to/some/file"
    with MockMethods(self._recv_methods):
      with mock.patch.object(
          os.path, "exists", return_value=False) as mock_exists:
        with self.assertRaises(errors.DeviceError):
          self.uut.file_transfer.recv_file_from_device(source)
      self.assertTrue(mock_exists.called)
      self.assertTrue(_any_methods_called(self._recv_methods))

  def test_send_to_device_bad_source(self):
    """Verify receive_from_device raises error on bad destination path."""
    self._setup_mocks()
    sources = "/path/to/some/file"
    destination_path = "/bogus/path"
    with MockMethods(self._send_methods):
      with mock.patch.object(
          os.path, "exists", return_value=False) as mock_exists:
        with self.assertRaises(errors.DeviceError):
          self.uut.file_transfer.send_file_to_device(
              sources, dest=destination_path)
      self.assertTrue(mock_exists.called)

      self.assertFalse(_any_methods_called(self._send_methods))

  def test_send_file_to_device_def_destination_path(self):
    """Verify send_to_device skips path check for default destination path."""
    self._setup_mocks()
    sources = "/path/to/some/file"
    destination = "/x/y"
    with MockMethods(self._send_methods, return_a_value=True):
      with mock.patch.object(os.path, "exists", return_value=True):
        with mock.patch.object(glob, "glob", return_value=["some-file"]):
          self.uut.file_transfer.send_file_to_device(sources, destination)
      self.assertTrue(_any_methods_called(self._send_methods))

  def test_send_file_to_device_error_path(self):
    """Verify send_to_device raises DeviceError if send fails."""
    self._setup_mocks()
    sources = "/path/to/some/file"
    destination = "/x/y"
    with MockMethods(self._send_methods,
                     add_side_effect=errors.DeviceError("err")):
      with mock.patch.object(os.path, "exists", return_value=True):
        with mock.patch.object(glob, "glob", return_value=["some-file"]):
          with self.assertRaises(errors.DeviceError):
            self.uut.file_transfer.send_file_to_device(sources, destination)
      self.assertTrue(_any_methods_called(self._send_methods))

  def test_send_file_to_device_fails(self):
    """Verify receive_from_device skips path check for default destination path."""
    self._setup_mocks()
    sources = "/path/to/some/file"
    destination = "/x/y"
    with MockMethods(self._send_methods, add_side_effect=True):
      with mock.patch.object(os.path, "exists", return_value=True):
        with self.assertRaises(errors.DeviceError):
          self.uut.file_transfer.send_file_to_device(sources, destination)

  def _setup_mocks(self):
    self._recv_methods = [
        (host_utils, "scp_from_device", "incoming_file", None),
        (host_utils, "docker_cp_from_device", "incoming_file", None),
        (adb_utils, "is_adb_mode", True, RuntimeError("x", "y")),
        (adb_utils, "pull_from_device", "incoming_file", None),
        (builtins, "open", None, None)
    ]
    self._send_methods = [
        (host_utils, "scp_to_device", "outgoing_file", RuntimeError("x", "y")),
        (host_utils, "docker_cp_to_device", "outgoing_file",
         RuntimeError("x", "y")),
        (adb_utils, "is_adb_mode", True, RuntimeError("x", "y")),
        (adb_utils, "push_to_device", "outgoing_file", RuntimeError("x", "y")),
        (self.uut.switchboard, "echo_file_to_transport", None,
         RuntimeError("x", "y"))
    ]
