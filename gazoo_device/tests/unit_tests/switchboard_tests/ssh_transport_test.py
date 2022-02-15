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

"""Tests the ssh_transport.py module."""
from gazoo_device.switchboard.transports import ssh_transport
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import host_utils


class SSHTransportTests(unit_test_case.UnitTestCase):

  def test_001_transport_default(self):
    """SSHTransport uses shell in args."""
    address = "123.45.67.89"
    defaults = host_utils.DEFAULT_SSH_OPTIONS.split()
    uut = ssh_transport.SSHTransport(address)
    self.assertIn("root@" + address, uut._args)
    for arg in defaults:
      self.assertTrue(arg, uut._args)

  def test_002_transport_uses_logcat_in_args(self):
    """AdbTransport uses logcat in args if log_only=True."""
    address = "123.45.67.89"
    uut = ssh_transport.SSHTransport("123.45.67.89", log_cmd="logcat")
    self.assertIn("root@" + address, uut._args)
    self.assertIn("logcat", uut._args)


if __name__ == "__main__":
  unit_test_case.main()
