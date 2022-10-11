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
"""Unit tests for gazoo_device.utility.ssh_utils.py."""

import os
import subprocess
from unittest import mock

from gazoo_device import data_types
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import host_utils
from gazoo_device.utility import ssh_utils


class SshUtilsTests(unit_test_case.UnitTestCase):
  """Unit tests for gazoo_device.utility.host_utils.py."""

  @mock.patch.object(os.path, 'exists')
  @mock.patch.object(subprocess, 'Popen')
  def test_ssh_port_forward(self, mock_popen, mock_path_exits):
    mock_path_exits.return_value = True

    process_mock = mock.Mock()
    process_mock.terminate = mock.Mock(return_value=None)
    process_mock.wait = mock.Mock(return_value=None)

    mock_popen_context = mock.Mock()
    mock_popen_context.__enter__ = mock.Mock(return_value=process_mock)
    mock_popen_context.__exit__ = mock.Mock(return_value=False)

    mock_popen.return_value = mock_popen_context

    key_info = data_types.KeyInfo(
        file_name='key', type=data_types.KeyType.SSH, package='package')

    with ssh_utils.port_forward(
        username='username',
        address='address',
        key_info=key_info,
        remote_port='80',
        remote_host='localhost') as f:
      local = f

    mock_popen.assert_called_with([
        'ssh', '-N', '-T', '-oPasswordAuthentication=no',
        '-oStrictHostKeyChecking=no', '-oBatchMode=yes', '-oConnectTimeout=3',
        '-i',
        host_utils.get_key_path(key_info), 'username@address',
        f'-L{local}:localhost:80'
    ])
    mock_popen_context.__enter__.assert_called_with()
    mock_popen_context.__exit__.assert_called_with(None, None, None)
    process_mock.terminate.assert_called_with()


if __name__ == '__main__':
  unit_test_case.main()
