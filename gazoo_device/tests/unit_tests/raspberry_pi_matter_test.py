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

"""Unit tests for the raspberry_pi_matter module."""
from unittest import mock
from gazoo_device import errors
from gazoo_device.base_classes import ssh_device
from gazoo_device.capabilities import matter_endpoints_accessor_pw_rpc
from gazoo_device.capabilities import pwrpc_common_default
from gazoo_device.primary_devices import raspberry_pi_matter
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.tests.unit_tests.utils import raspberry_pi_matter_device_logs
from gazoo_device.utility import retry
import immutabledict

_FAKE_DEVICE_IP = "123.45.67.89"
_FAKE_SERIAL_NUMBER = "fake-serial-number"
_CONNECT_PERSISTENT_PROPERTIES = immutabledict.immutabledict({
    "console_port_name": _FAKE_DEVICE_IP,
    "serial_number": _FAKE_SERIAL_NUMBER,
    "name": "rpimatter-1234",
    "device_type": "rpimatter",
    "model": "PROTO",
    "wpan_mac_address": "123456"
})
_MOCK_MATTER_ENDPOINT = mock.Mock(
    spec=matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc)


class RaspberryPiMatterTests(fake_device_test_case.FakeDeviceTestCase):
  """Test for RaspberryPiMatter device controller."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements("rpimatter-1234")
    self.device_config["persistent"]["console_port_name"] = _FAKE_DEVICE_IP
    self.fake_responder.behavior_dict = {
        **raspberry_pi_matter_device_logs.DEFAULT_BEHAVIOR}

    self.uut = raspberry_pi_matter.RaspberryPiMatter(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory)

  def test_os_attribute(self):
    """Verifies the os attribute."""
    self.assertEqual("Ubuntu", self.uut.os)

  def test_platform_attribute(self):
    """Verfies the platform attribute."""
    self.assertEqual("Raspberry Pi 4", self.uut.platform)

  @mock.patch.object(
      raspberry_pi_matter.RaspberryPiMatter,
      "shell_with_regex",
      return_value=_FAKE_SERIAL_NUMBER)
  def test_get_detection_info_on_success(self, mock_shell):
    """Verifies persistent properties are set correctly."""
    persistent_dict, _ = self.uut.get_detection_info()
    self.assertEqual(_CONNECT_PERSISTENT_PROPERTIES, persistent_dict)

  def test_health_check(self):
    """Verifies health_check is not empty."""
    self.assertTrue(bool(self.uut.health_checks))

  def test_check_app_present_on_success(self):
    """Verifies check_app_present on success."""
    self.uut.check_app_present()

  def test_check_app_present_on_failure(self):
    """Verifies check_app_present on failure."""
    response = {
        "cmd": "test -f /home/ubuntu/matter-linux-app",
        "resp": "",
        "code": 1,
    }
    self.fake_responder.behavior_dict.update(
        raspberry_pi_matter_device_logs.make_device_responses((response,)))
    with self.assertRaisesRegex(
        errors.DeviceBinaryMissingError,
        "The Matter sample app binary does not exist"):
      self.uut.check_app_present()

  def test_check_has_service_on_success(self):
    """Verifies check_has_service on success."""
    self.uut.check_has_service()

  def test_check_has_service_on_failure(self):
    """Verifies check_has_service on failure."""
    response = {
        "cmd": "test -f /etc/systemd/system/matter-linux-app.service",
        "resp": "",
        "code": 1,
    }
    self.fake_responder.behavior_dict.update(
        raspberry_pi_matter_device_logs.make_device_responses((response,)))
    with self.assertRaisesRegex(
        errors.DeviceMissingPackagesError,
        "The Matter sample app service file does not exist"):
      self.uut.check_has_service()

  def test_check_is_service_enabled_on_success(self):
    """Verifies is_service_enabled on success."""
    self.uut.check_is_service_enabled()

  def test_check_is_service_enabled_on_failure(self):
    """Verifies is_service_enabled on failure."""
    response = {
        "cmd": "sudo systemctl is-enabled matter-linux-app.service",
        "resp": "disabled",
        "code": 0,
    }
    self.fake_responder.behavior_dict.update(
        raspberry_pi_matter_device_logs.make_device_responses((response,)))
    with self.assertRaisesRegex(
        errors.ServiceNotEnabledError,
        "The Matter sample app service is not enabled"):
      self.uut.check_is_service_enabled()

  def test_check_app_running_on_success(self):
    """Verifies check_app_running on success."""
    self.uut.check_app_running()

  def test_check_app_running_on_failure(self):
    """Verifies check_app_running on failure."""
    response = {
        "cmd": "pgrep -f matter-linux-app",
        "resp": "",
        "code": 0,
    }
    self.fake_responder.behavior_dict.update(
        raspberry_pi_matter_device_logs.make_device_responses((response,)))
    with self.assertRaisesRegex(
        errors.ProcessNotRunningError,
        "The Matter sample app process is not running"):
      self.uut.check_app_running()

  @mock.patch.object(raspberry_pi_matter.RaspberryPiMatter, "switchboard")
  def test_check_open_pwrpc_socket_transport(self, mock_switchboard):
    """Verifies check_open_pwrpc_socket_transport on success."""
    self.uut.check_open_pwrpc_socket_transport()
    mock_switchboard.open_transport.assert_called_once()

  def test_matter_sample_app_alias(self):
    """Verifies matter_sample_app alias on success."""
    self.assertIsNotNone(self.uut.matter_sample_app)

  def test_recover_for_service_not_enabled_error(self):
    """Verifies recover method for sample app service not enabled error."""
    response = {
        "cmd": "sudo systemctl is-enabled matter-linux-app.service",
        "resp": "disabled",
        "code": 0,
    }
    self.fake_responder.behavior_dict.update(
        raspberry_pi_matter_device_logs.make_device_responses((response,)))
    fake_error = errors.ServiceNotEnabledError(
        device_name="fake-name", msg="fake-msg")
    self.uut.recover(error=fake_error)

  @mock.patch.object(raspberry_pi_matter.RaspberryPiMatter, "shell")
  def test_recover_for_process_not_running_error(self, mock_shell):
    """Verifies recover method for sample app service not running error."""
    fake_error = errors.ProcessNotRunningError(
        device_name="fake-name", msg="fake-msg")
    self.uut.recover(error=fake_error)

    mock_shell.assert_called_once()

  @mock.patch.object(
      raspberry_pi_matter.RaspberryPiMatter, "wait_for_bootup_complete")
  def test_recover_for_other_errors(self, mock_wait):
    """Verifies recover method handles for other errors."""
    fake_error = errors.DeviceNotBootupCompleteError(
        device_name="fake-name", msg="fake-msg")
    self.uut.recover(error=fake_error)

    mock_wait.assert_called_once()

  @mock.patch.object(raspberry_pi_matter.RaspberryPiMatter, "_verify_reboot")
  def test_reboot(self, mock_verify_reboot):
    """Verifies hard reboot method."""
    self.uut.reboot()

    mock_verify_reboot.assert_called_once()

  @mock.patch.object(pwrpc_common_default.PwRPCCommonDefault, "factory_reset")
  @mock.patch.object(raspberry_pi_matter.RaspberryPiMatter, "matter_sample_app")
  def test_factory_reset(self, mock_matter_sample_app, mock_factory_reset):
    """Verifies factory reset method."""
    self.uut.factory_reset()

    mock_matter_sample_app.factory_reset.assert_called_once()
    mock_factory_reset.assert_called_once()

  @mock.patch.object(retry, "retry")
  @mock.patch.object(ssh_device.SshDevice, "wait_for_bootup_complete")
  def test_wait_for_bootup_complete(self, mock_wait, mock_retry):
    """Verifies wait_for_bootup_complete on success."""
    self.uut.wait_for_bootup_complete()

    mock_wait.assert_called_once()
    self.assertEqual(2, mock_retry.call_count)

  def test_bluetooth_service_alias(self):
    """Verifies bluetooth_service alias on success."""
    self.assertIsNotNone(self.uut.bluetooth_service)


if __name__ == "__main__":
  fake_device_test_case.main()
