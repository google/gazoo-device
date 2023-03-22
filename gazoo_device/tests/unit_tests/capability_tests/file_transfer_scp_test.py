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
"""Unit tests for the FileTransferScp capability."""

import os
from unittest import mock

from gazoo_device import data_types
from gazoo_device import errors
from gazoo_device.capabilities import file_transfer_scp
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import host_utils


def _mock_abspath(path: str) -> str:
  if path.startswith("/"):
    return path
  else:
    return "/working_directory/" + path


class FileTransferScpTests(unit_test_case.UnitTestCase):
  """Test class to verify the FileTransferScpTests capability."""

  def setUp(self):
    super().setUp()
    self.mock_is_pingable = self.enter_context(
        mock.patch.object(
            host_utils, "is_pingable", autospec=True, return_value=True))

    self.mock_path_exist = self.enter_context(
        mock.patch.object(os.path, "exists", autospec=True, return_value=True))

    self.mock_path_abspath = self.enter_context(
        mock.patch.object(
            os.path, "abspath", autospec=True, side_effect=_mock_abspath))

    self.key_info = data_types.KeyInfo(
        file_name="key", type=data_types.KeyType.SSH, package="package")
    self.cap = file_transfer_scp.FileTransferScp(
        ip_address_or_fn="mocked_address",
        device_name="mocked_device_name",
        add_log_note_fn=lambda x: None,
        user="mocked_username",
        key_info=self.key_info)

  @mock.patch.object(host_utils, "scp_to_device")
  def test_send_file_to_device(self, mock_scp_to_device):
    """Tests send_file_to_device."""

    self.cap.send_file_to_device("/src", "/dst")
    mock_scp_to_device.assert_called_once_with(
        "mocked_address",
        "/src",
        "/dst",
        user="mocked_username",
        key_info=self.key_info)

  @mock.patch.object(host_utils, "scp_to_device")
  def test_send_file_to_device_relative(self, mock_scp_to_device):
    """Tests send_file_to_device."""

    self.cap.send_file_to_device("src", "/dst")
    mock_scp_to_device.assert_called_once_with(
        "mocked_address",
        "/working_directory/src",
        "/dst",
        user="mocked_username",
        key_info=self.key_info)

  def test_send_file_to_device_not_exist(self):
    """Tests send_file_to_device."""

    self.mock_path_exist.return_value = False
    self.assertRaises(errors.DeviceError, self.cap.send_file_to_device, "src",
                      "/dst")

  @mock.patch.object(host_utils, "scp_from_device")
  def test_recv_file_from_device(self, scp_from_device):
    """Tests recv_file_from_device."""

    self.cap.recv_file_from_device("/src", "/dst")
    scp_from_device.assert_called_once_with(
        "mocked_address",
        "/dst",
        "/src",
        user="mocked_username",
        key_info=self.key_info)


if __name__ == "__main__":
  unit_test_case.main()
