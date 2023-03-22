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
"""Unit tests for the MatterControllerChipTool capability."""

import os
import shutil
import tempfile
from unittest import mock
from absl.testing import parameterized
from gazoo_device import errors
from gazoo_device.auxiliary_devices import raspberry_pi_matter_controller
from gazoo_device.capabilities import file_transfer_scp
from gazoo_device.capabilities import matter_controller_chip_tool
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.tests.unit_tests.utils import raspberry_pi_matter_controller_device_logs
from gazoo_device.tests.unit_tests.utils import ssh_device_logs
import requests


class MatterControllerChipToolCapabilityTests(
    fake_device_test_case.FakeDeviceTestCase):
  """Unit test for MatterControllerChipTool capability implementation."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements("rpi_matter_controller-1234")
    self.device_config["persistent"]["console_port_name"] = "123.45.67.89"
    self.device_config["options"]["matter_node_id"] = 1234
    self.fake_responder.behavior_dict = {
        **raspberry_pi_matter_controller_device_logs.DEFAULT_BEHAVIOR}

    self.uut = raspberry_pi_matter_controller.RaspberryPiMatterController(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory)
    self._node_id = 1234
    self._setup_code = 20202021
    self._long_discriminator = 3840
    self._endpoint_id = 1
    self._cluster = "onoff"

  def test_matter_sdk_version(self):
    self.assertEqual(self.uut.matter_controller.version,
                     "92f834375b2075e6c1c93d12b373b663d4b9250b")

  def test_commission_over_ble_wifi(self):
    self.uut.matter_controller.commission(
        node_id=self._node_id,
        ssid="wifi-ssid",
        password="wifi-password",
        setup_code=self._setup_code,
        long_discriminator=self._long_discriminator)
    self.uut.get_manager().save_property_to_config.assert_called_once_with(
        self.uut.name, "matter_node_id", self._node_id)

  def test_commission_over_ble_wifi_with_hex(self):
    self.uut.matter_controller.commission(
        node_id=self._node_id,
        ssid="hex:776966692d73736964",
        password="hex:776966692d70617373776f7264",
        setup_code=self._setup_code,
        long_discriminator=self._long_discriminator)
    self.uut.get_manager().save_property_to_config.assert_called_once_with(
        self.uut.name, "matter_node_id", self._node_id)

  def test_commission_on_network(self):
    self.uut.matter_controller.commission(
        node_id=self._node_id, setup_code=self._setup_code)
    self.uut.get_manager().save_property_to_config.assert_called_once_with(
        self.uut.name, "matter_node_id", self._node_id)

  def test_commission_on_network_long(self):
    self.uut.matter_controller.commission(
        node_id=self._node_id,
        setup_code=self._setup_code,
        long_discriminator=self._long_discriminator)
    self.uut.get_manager().save_property_to_config.assert_called_once_with(
        self.uut.name, "matter_node_id", self._node_id)

  def test_commission_over_ble_thread(self):
    self.uut.matter_controller.commission(
        node_id=self._node_id,
        setup_code=self._setup_code,
        long_discriminator=self._long_discriminator,
        operational_dataset="abcd")
    self.uut.get_manager().save_property_to_config.assert_called_once_with(
        self.uut.name, "matter_node_id", self._node_id)

  def test_commission_timeout_failure(self):
    """Commission method should raise DeviceError when setup code is invalid."""
    invalid_setup_code = "00000000"
    with self.assertRaises(errors.DeviceError):
      self.uut.matter_controller.commission(
          node_id=self._node_id, setup_code=invalid_setup_code)

  def test_commission_over_ble_wifi_without_password(self):
    with self.assertRaises(errors.DeviceError):
      self.uut.matter_controller.commission(
          node_id=self._node_id,
          ssid="wifi-ssid",
          setup_code=self._setup_code,
          long_discriminator=self._long_discriminator)

  def test_commission_with_paa_trust_store_path(self):
    self.uut.matter_controller.commission(
        node_id=self._node_id,
        setup_code=self._setup_code,
        paa_trust_store_path="/home/pi/credentials/development/paa-root-certs")
    self.uut.get_manager().save_property_to_config.assert_called_once_with(
        self.uut.name, "matter_node_id", self._node_id)

  def test_decommission(self):
    self.uut.matter_controller.decommission()
    self.uut.get_manager().save_property_to_config.assert_called_once_with(
        self.uut.name, "matter_node_id", None)

  def test_decommission_timeout_failure(self):
    """Decommission method should raise DeviceError when node id is invalid."""
    self.device_config["options"]["matter_node_id"] = 0000
    with self.assertRaises(errors.DeviceError):
      self.uut.matter_controller.decommission()

  @parameterized.named_parameters([
      ("integer", 1234, 1234),
      ("positive_integer", "+17", 17),
      ("negative_integer", -100, -100),
      ("float", 1.47, 1.47),
      ("negative_float", -3.14, -3.14),
      ("boolean", "true", True),
      ("string", "\"TEST_VENDOR\" (11 chars)", "TEST_VENDOR"),
      ("empty_string", "\"\" (0 chars)", ""),
  ])
  def test_read_attribute(self, data, expected_value):
    response = {
        "cmd": "/usr/local/bin/chip-tool onoff read test-attribute 1234 1",
        "resp": f"CHIP:DMG: 					Data = {data},",
        "code": 0,
    }
    self.fake_responder.behavior_dict.update(
        ssh_device_logs.make_device_responses((response,)))
    self.assertEqual(
        self.uut.matter_controller.read(self._endpoint_id, self._cluster,
                                        "test-attribute"), expected_value)

  def test_write_attribute(self):
    self.uut.matter_controller.write(self._endpoint_id, self._cluster,
                                     "on-time", 100)

  def test_send_command_without_flags(self):
    """Verifies send command without additional flags."""
    self.uut.matter_controller.send(
        endpoint_id=self._endpoint_id,
        cluster=self._cluster,
        command="toggle",
        arguments=[])

  def test_send_command_with_flags(self):
    """Verifies send command with additional flags."""
    self.uut.matter_controller.send(
        endpoint_id=self._endpoint_id,
        cluster="doorlock",
        command="lock-door",
        arguments=[],
        flags=["--timedInteractionTimeoutMs", "1000"])

  def test_write_attribute_non_zero_status_code(self):
    with self.assertRaises(errors.DeviceError):
      self.uut.matter_controller.write(self._endpoint_id, self._cluster,
                                       "non-existent-attr", 0)

  def test_send_command_non_zero_status_code(self):
    with self.assertRaises(errors.DeviceError):
      self.uut.matter_controller.write(self._endpoint_id, self._cluster,
                                       "non-existent-cmd", [])

  def test_upgrade(self):
    with mock.patch.object(file_transfer_scp.FileTransferScp,
                           "send_file_to_device") as file_send:
      with mock.patch.object(self.uut.matter_controller,
                             "update_certs") as update_certs_mock:
        self.uut.matter_controller.upgrade("path/to/chip-tool",
                                           "1234",
                                           "path/to/certs-dir/")
        file_send.assert_called_once_with("path/to/chip-tool",
                                          "/usr/local/bin/chip-tool")
        update_certs_mock.assert_called_once_with("path/to/certs-dir/")

  def test_upgrade_with_default_certs_dir(self):
    with mock.patch.object(file_transfer_scp.FileTransferScp,
                           "send_file_to_device") as file_send:
      with mock.patch.object(self.uut.matter_controller,
                             "update_certs") as update_certs_mock:
        self.uut.matter_controller.upgrade("path/to/chip-tool",
                                           "1234")
        file_send.assert_called_once_with("path/to/chip-tool",
                                          "/usr/local/bin/chip-tool")
        update_certs_mock.assert_called_once_with(matter_controller_chip_tool
                                                  .DEFAULT_PAA_TRUST_STORE_PATH)

  def test_factory_reset(self):
    with mock.patch.object(
        self.uut, "shell", wraps=self.uut.shell) as shell_wrapper:
      self.uut.factory_reset()
      shell_wrapper.assert_has_calls([
          mock.call("rm -rf /tmp/chip*"),
          mock.call("/usr/local/bin/chip-tool storage clear-all"),
      ])

  @mock.patch.object(requests.Session, "get")
  def test_update_certs_failure_calling_api(self, mock_api):
    host_dest_path = "path/to/host-dest/"
    mock_api.return_value = requests.Response()
    mock_api.return_value.status_code = 400
    mock_api.return_value._content = b"{}"
    mock_api.return_value.reason = "400 Bad Request"
    with self.assertRaises(errors.DeviceError):
      self.uut.matter_controller.update_certs("path/to/device-dest",
                                              host_dest_path)

  @mock.patch.object(requests.Session, "get")
  @mock.patch.object(file_transfer_scp.FileTransferScp, "send_file_to_device")
  @mock.patch.object(shutil, "copytree")
  @mock.patch.object(tempfile, "TemporaryDirectory")
  @mock.patch.object(os, "makedirs")
  def test_update_certs_success(self, mock_os_makedirs, mock_tempfile,
                                mock_shutil, mock_scp, mock_api):
    host_dest_path = "path/to/host-dest/"
    mock_api.return_value = requests.Response()
    mock_api.return_value.status_code = 200
    mock_api.return_value.reason = "OK"
    mock_api.return_value._content = (
        b"[{ \"name\": \"Chip-Test-Cert.der\",\"path\":"
        b"\"credentials/development/paa-root-certs/Chip-Test-Cert.der\",\"type\":"
        b"\"file\",\"download_url\":\"https://raw.githubusercontent.com/path/\"}]"
    )
    mock_tempfile.return_value.__enter__.return_value = "some_temp_dir"
    with mock.patch("builtins.open", mock.mock_open()) as mock_open:
      self.uut.matter_controller.update_certs("path/to/device-dest",
                                              host_dest_path)
    mock_open.assert_called_once_with(
        os.path.join("some_temp_dir", "Chip-Test-Cert.der"), "wb")
    mock_api.assert_any_call(
        "https://api.github.com/repos/project-chip/connectedhomeip/commits/master",
        auth=None,
        params=None,
        data=None,
        headers={"Accept": "application/vnd.github.VERSION.sha"},
        timeout=10,
        verify=False)

  @mock.patch.object(requests.Session, "get")
  @mock.patch.object(file_transfer_scp.FileTransferScp, "send_file_to_device")
  @mock.patch.object(tempfile, "TemporaryDirectory")
  def test_update_certs_success_with_no_host_dest(self, mock_tempfile, mock_scp,
                                                  mock_api):
    mock_api.return_value = requests.Response()
    mock_api.return_value.status_code = 200
    mock_api.return_value.reason = "OK"
    mock_api.return_value._content = b"{}"
    mock_tempfile.return_value.__enter__.return_value = "some_temp_dir"
    self.uut.matter_controller.update_certs("path/to/device-dest")

  def test_start_subscription(self):
    with mock.patch.object(self.uut, "shell") as mock_shell:
      self.uut.matter_controller.start_subscription(self._endpoint_id,
                                                    self._cluster,
                                                    "test-attribute", 1, 2)

      mock_shell.assert_has_calls([
          mock.call("nohup /usr/local/bin/chip-tool interactive start < "
                    "<(echo 'onoff subscribe test-attribute 1 2 1234 1') "
                    "> /tmp/chip.log 2>&1 &"),
      ])

  def test_stop_subscription(self):
    with mock.patch.object(
        self.uut, "shell", wraps=self.uut.shell) as shell_wrapper:
      results = self.uut.matter_controller.stop_subscription()

      shell_wrapper.assert_has_calls([
          mock.call("kill $(pgrep -f '/usr/local/bin/chip-tool interactive "
                    "start')"),
          mock.call("grep 'Data =' /tmp/chip.log"),
      ])

      self.assertListEqual(results, [1, 2])


if __name__ == "__main__":
  fake_device_test_case.main()
