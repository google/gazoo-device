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

"""Unit tests for SshDevice class."""
from unittest import mock

from gazoo_device import errors
from gazoo_device.base_classes import ssh_device
from gazoo_device.tests.unit_tests.capability_tests.mixins import file_transfer_test
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.tests.unit_tests.utils import ssh_device_logs
from gazoo_device.utility import host_utils
import immutabledict

_BINARY_FOUND = "ls"
_BINARY_NOT_FOUND = "foo_bar"

_IP_ADDRESS = "123.45.67.89"
_PERSISTENT_PROPERTIES = immutabledict.immutabledict({
    "communication_address": _IP_ADDRESS,
    "console_port_name": _IP_ADDRESS,
    "ip_address": _IP_ADDRESS,
    "os": "Linux",
})

_REBOOT_PINGS = [True] * 5 + [False] * 20 + [True] * 5


class SshDeviceStub(ssh_device.SshDevice):
  """Add dummy implementations for abstract methods to allow instantiation of SshDevice."""

  def factory_reset(self):
    pass

  @property
  def firmware_version(self):
    pass

  @property
  def platform(self):
    return "dummy"

  @property
  def model(self):
    pass

  def reboot(self):
    pass

  def upgrade(self):
    pass


class SshDeviceTests(
    fake_device_test_case.FakeDeviceTestCase,
    file_transfer_test.TestFileTransfer):
  """Unit tests for ssh_device.py."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements("sshdevice-1234")
    self.device_config["persistent"][
        "console_port_name"] = _PERSISTENT_PROPERTIES["console_port_name"]
    del self.device_config["persistent"]["serial_number"]
    self.fake_responder.behavior_dict = {**ssh_device_logs.RESPONSES}
    self.enter_context(
        mock.patch.object(
            host_utils, "is_pingable", autospec=True, return_value=True))
    self.uut = SshDeviceStub(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory)

  def test_get_detection_info(self):
    """Validate persistent properties are set correctly during device detection."""
    with mock.patch.object(self.uut, "make_device_ready"):
      self._test_get_detection_info(
          _PERSISTENT_PROPERTIES["console_port_name"],
          device_class=SshDeviceStub,
          persistent_properties=_PERSISTENT_PROPERTIES)

  def test_is_connected_false(self):
    """Verify is_connected() returns False when device is not pingable."""
    with mock.patch.object(host_utils, "is_pingable", return_value=False):
      self.assertFalse(ssh_device.SshDevice.is_connected(self.device_config))

  def test_is_connected_true(self):
    """Verify is_connected() returns True when device is pingable."""
    with mock.patch.object(host_utils, "is_pingable", return_value=True):
      self.assertTrue(ssh_device.SshDevice.is_connected(self.device_config))

  def test_has_command_true(self):
    """Verify has_command() returns True when binary is present."""
    self.assertTrue(self.uut.shell_capability.has_command(_BINARY_FOUND))

  def test_has_command_false(self):
    """Verify has_command() returns False when binary is not present."""
    self.assertFalse(self.uut.shell_capability.has_command(_BINARY_NOT_FOUND))

  def test_check_device_ready_success(self):
    """Test check_device_ready() when all health checks succeed."""
    self.uut.check_device_ready()

  def test_check_device_ready_failure_shell_not_responsive(self):
    """Test check_device_ready() when device is not responsive to shell commands."""
    cmd = ssh_device_logs.generate_command(ssh_device.COMMANDS["GDM_HELLO"])
    del self.fake_responder.behavior_dict[cmd]  # Simulate timeout
    with self.assertRaises(errors.DeviceNotResponsiveError):
      self.uut.check_device_ready()

  def test_verify_reboot_failure_to_go_offline(self):
    """Test verify_reboot() when device fails to stop responding to ping."""
    with mock.patch.object(host_utils, "is_pingable", return_value=True):
      with self.assertRaisesRegex(
          errors.DeviceError, "{} failed to go offline".format(self.uut.name)):
        self.uut._verify_reboot()

  def test_verify_reboot_failure_to_come_online(self):
    """Test verify_reboot() when device goes offline and fails to start responding to ping."""
    pings = [True] * 5 + [False] * 200
    with mock.patch.object(host_utils, "is_pingable", side_effect=pings):
      with self.assertRaisesRegex(
          errors.DeviceNotBootupCompleteError,
          "Device failed to become pingable"):
        self.uut._verify_reboot()

  def test_verify_reboot_failure_shell_raises_error(self):
    """Test verify_reboot() when device shell is unresponsive."""
    cmd = ssh_device_logs.generate_command(ssh_device.COMMANDS["GDM_HELLO"])
    del self.fake_responder.behavior_dict[cmd]  # Simulate timeout
    with mock.patch.object(
        host_utils, "is_pingable", side_effect=_REBOOT_PINGS):
      with self.assertRaisesRegex(errors.DeviceNotBootupCompleteError,
                                  "shell error"):
        self.uut._verify_reboot()

  def test_reboot_failure_shell_returns_nonzero_return_code(self):
    """Test verify_reboot() when device shell returns a non-zero return code."""
    cmd = ssh_device_logs.generate_command(ssh_device.COMMANDS["GDM_HELLO"])
    resp = ssh_device_logs.generate_response(
        ssh_device.COMMANDS["GDM_HELLO"], "something went wrong", 1)
    self.fake_responder.behavior_dict[cmd] = resp
    with mock.patch.object(
        host_utils, "is_pingable", side_effect=_REBOOT_PINGS):
      with self.assertRaisesRegex(errors.DeviceNotBootupCompleteError,
                                  "non-zero return code"):
        self.uut._verify_reboot()

  def test_verify_reboot_success(self):
    """Test verify_reboot() in a successful scenario."""
    with mock.patch.object(
        host_utils, "is_pingable", side_effect=_REBOOT_PINGS):
      self.uut._verify_reboot()

  def test_recover_boot_up_incomplete(self):
    """Test recover() given a DeviceNotBootupCompleteError."""
    err = errors.DeviceNotBootupCompleteError(self.uut.name, "Some error")

    with mock.patch.object(self.uut, "wait_for_bootup_complete") as mock_wait:
      self.uut.recover(err)
      mock_wait.assert_called_once()

  def test_recover_other_error(self):
    """Test recover() given an error for which no recovery steps are available."""
    err_msg = "Some error"
    err = errors.CheckDeviceReadyError(self.uut.name, err_msg)

    with self.assertRaisesRegex(type(err), err_msg):
      self.uut.recover(err)

  @mock.patch.object(host_utils, "is_pingable", return_value=True)
  def test_wait_for_bootup_complete_success(self, mock_is_pingable):
    """Tests wait_for_bootup_complete() succeeded."""
    self.uut.wait_for_bootup_complete()
    mock_is_pingable.assert_called_once()
    self.mock_switchboard.open_all_transports.assert_called_once()

  @mock.patch.object(host_utils, "is_pingable", return_value=False)
  def test_wait_for_bootup_complete_timeout(self, mock_is_pingable):
    """Tests wait_for_bootup_complete() raised an error after timeout."""
    with self.assertRaises(errors.DeviceNotBootupCompleteError):
      self.uut.wait_for_bootup_complete(timeout=1)

  @mock.patch.object(ssh_device.SshDevice, "shell", return_value=("", 0))
  def test_inject_log_marker_on_success(self, mock_shell):
    """Verifies _inject_log_marker method on success."""
    self.uut._inject_log_marker()

    mock_shell.assert_called_once()

  @mock.patch.object(ssh_device.SshDevice, "shell", return_value=("error", 1))
  def test_inject_log_marker_on_failure(self, mock_shell):
    """Verifies _inject_log_marker method on failure."""
    with self.assertRaisesRegex(errors.DeviceError, "injection fails"):
      self.uut._inject_log_marker()


if __name__ == "__main__":
  fake_device_test_case.main()
