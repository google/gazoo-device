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
"""Capability unit test for bluetooth_linux module."""
from unittest import mock

from gazoo_device import errors
from gazoo_device.base_classes import gazoo_device_base
from gazoo_device.capabilities import bluetooth_service_linux
from gazoo_device.capabilities import shell_ssh
from gazoo_device.tests.unit_tests.utils import fake_device_test_case


class BluetoothServiceLinuxTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for BluetoothServiceLinux."""

  def setUp(self):
    super().setUp()
    self.fake_shell = mock.Mock(spec=shell_ssh.ShellSSH.shell)
    self.fake_shell_with_regex = mock.Mock(
        spec=gazoo_device_base.GazooDeviceBase.shell_with_regex)
    self.uut = bluetooth_service_linux.BluetoothServiceLinux(
        device_name="fake-device-name",
        shell_fn=self.fake_shell,
        shell_with_regex_fn=self.fake_shell_with_regex)

  def test_status(self):
    """Verifies status property on success."""
    self.fake_shell_with_regex.return_value = "active"
    self.assertTrue(self.uut.status)

  def test_start_on_success(self):
    """Verifies start method on success."""
    self.fake_shell_with_regex.return_value = "active"
    self.uut.start()
    self.fake_shell.assert_called_once()

  def test_start_on_failure(self):
    """Verifies start method on failure."""
    self.fake_shell_with_regex.return_value = "inactive"
    with self.assertRaisesRegex(errors.DeviceError, "failed to start"):
      self.uut.start()

  def test_stop_on_success(self):
    """Verifies stop on success."""
    self.fake_shell_with_regex.return_value = "inactive"
    self.uut.stop()
    self.fake_shell.assert_called_once()

  def test_stop_on_failure(self):
    """Verifies stop on failure."""
    self.fake_shell_with_regex.return_value = "active"
    with self.assertRaisesRegex(errors.DeviceError, "failed to stop"):
      self.uut.stop()

  def test_restart_on_success(self):
    """Verifies restart on success."""
    self.fake_shell_with_regex.return_value = "active"
    self.uut.restart()
    self.fake_shell.assert_called_once()

  def test_restart_on_failure(self):
    """Verifies restart on failure."""
    self.fake_shell_with_regex.return_value = "inactive"
    with self.assertRaisesRegex(errors.DeviceError, "failed to restart"):
      self.uut.restart()


if __name__ == "__main__":
  fake_device_test_case.main()
