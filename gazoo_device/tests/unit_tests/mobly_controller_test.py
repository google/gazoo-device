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

"""Tests for mobly_controller."""
import logging
import os
from unittest import mock

from absl.testing import parameterized
from gazoo_device import errors
from gazoo_device import manager
from gazoo_device import mobly_controller
from gazoo_device import package_registrar
from gazoo_device.capabilities import package_management_android
from gazoo_device.tests.unit_tests.utils import fake_devices
from gazoo_device.tests.unit_tests.utils import unit_test_case
from mobly import asserts
from mobly import base_test
from mobly import config_parser
from mobly import records

FAKE_CONTROLLER_CONFIGS = {
    "gdm_sshdevice": [{
        "id": "sshdevice-0001"
    }, {
        "label": "b",
        "id": "sshdevice-0002",
        "bypass_gdm_check": "true",
        "other": "b"
    }, {
        "id": "sshdevice-0003",
        "dimensions": {
            "bypass_gdm_check": "true",
        }
    }]
}

FAKE_CONFIGURATION = {
    "persistent": {
        "serial_number": "00000000",
        "name": "sshdevice-0000",
        "device_type": "sshdevice",
        "model": "linux",
        "console_port_name": "123.456.78.9"
    },
    "options": {
        "alias": "a"
    },
    "log_name_prefix": "test"
}


class MoblyControllerFuncsTest(unit_test_case.UnitTestCase):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    package_registrar.register(fake_devices)

  def setUp(self):
    super().setUp()
    logging.log_path = self.artifacts_directory

  def tearDown(self):
    if hasattr(logging, "log_path"):
      del logging.log_path
    super().tearDown()

  @mock.patch.object(
      mobly_controller.manager.Manager,
      "create_device",
      return_value=mock.Mock(firmware_version="1", close=mock.Mock(), spec=[]))
  @mock.patch.object(mobly_controller.manager.Manager, "set_prop")
  def test_mobly_test(self, mock_set, mock_create_device):
    """Use a fake mobly test to verify everything actually works as expected."""

    class FakeTest(base_test.BaseTestClass):
      """Fake Mobly test to verify functionality."""

      def setup_class(self):
        self.devices = self.register_controller(fake_devices)

      def test_1(self):
        asserts.assert_equal(len(self.devices),
                             len(FAKE_CONTROLLER_CONFIGS["gdm_sshdevice"]))

    fake_config = config_parser.TestRunConfig()
    fake_config.log_path = self.artifacts_directory
    summary_file = os.path.join(self.artifacts_directory, "summary.yaml")
    fake_config.summary_writer = records.TestSummaryWriter(summary_file)
    fake_config.controller_configs = FAKE_CONTROLLER_CONFIGS
    test = FakeTest(fake_config)
    test.run(["test_1"])

    self.assertTrue(test.results.passed,
                    f"Mobly test results: {test.results.summary_str()}")
    actual_record = test.results.passed[0]
    self.assertIn(actual_record.test_name, "test_1")

  @mock.patch.object(mobly_controller.manager.Manager, "create_device")
  @mock.patch.object(mobly_controller.manager.Manager, "set_prop")
  def test_create(self, mock_set, mock_create):
    mock_devices = [mock.Mock()] * len(FAKE_CONTROLLER_CONFIGS["gdm_sshdevice"])
    mock_create.side_effect = iter(mock_devices)

    devices = mobly_controller.create(FAKE_CONTROLLER_CONFIGS["gdm_sshdevice"])

    self.assertEqual(devices, mock_devices)
    mock_create.assert_has_calls([
        mock.call("sshdevice-0001", log_directory=self.artifacts_directory),
        mock.call("sshdevice-0002", log_directory=self.artifacts_directory,
                  make_device_ready="off"),
        mock.call("sshdevice-0003", log_directory=self.artifacts_directory,
                  make_device_ready="off")])
    mock_set.assert_has_calls([
        mock.call("sshdevice-0002", "other", "b"),
        mock.call("sshdevice-0003", "dimensions", {"bypass_gdm_check": "true"})
    ])

  @mock.patch.object(mobly_controller.manager.Manager, "create_device",
                     return_value=mock.Mock())
  @mock.patch.object(mobly_controller.manager.Manager, "set_prop",
                     side_effect=errors.DeviceError(""))
  def test_create_set_prop_label_error_raise(self, mock_set, mock_create):
    with self.assertRaises(errors.DeviceError):
      mobly_controller.create(FAKE_CONTROLLER_CONFIGS["gdm_sshdevice"])

  @mock.patch.object(mobly_controller.manager.Manager, "create_device")
  @mock.patch.object(mobly_controller.manager.Manager, "set_prop")
  def test_create_set_prop_bypass_non_label_error(self, mock_set, mock_create):
    mock_devices = [mock.Mock()] * len(FAKE_CONTROLLER_CONFIGS["gdm_sshdevice"])
    mock_create.side_effect = iter(mock_devices)

    def _mock_set_prop(device_name, prop_name, _):
      if prop_name != "alias":
        raise errors.DeviceError(f"{device_name} failed to set {prop_name}")
    mock_set.side_effect = _mock_set_prop

    devices = mobly_controller.create(FAKE_CONTROLLER_CONFIGS["gdm_sshdevice"])

    self.assertEqual(devices, mock_devices)
    mock_create.assert_has_calls([
        mock.call("sshdevice-0001", log_directory=self.artifacts_directory),
        mock.call("sshdevice-0002", log_directory=self.artifacts_directory,
                  make_device_ready="off"),
        mock.call("sshdevice-0003", log_directory=self.artifacts_directory,
                  make_device_ready="off")])
    mock_set.assert_has_calls([
        mock.call("sshdevice-0002", "other", "b"),
        mock.call("sshdevice-0003", "dimensions", {"bypass_gdm_check": "true"})
    ])

  def test_get_info(self):
    expected_info = [{
        "name": "sshdevice-0000",
        "device_type": "sshdevice",
        "model": "linux",
        "platform": "sshdevice",
        "serial_number": "00000000",
        "wifi_mac_address": "Undefined",
        "firmware_version": "123",
        "firmware_branch": "DeviceError('Communication error')",
        "firmware_type": "eng",
        "alias": "a",
        "communication_address": "123.456.78.9",
        "secondary_communication_address": "Undefined",
        "build_date": "Undefined",
        "initial_code_name": "Undefined",
        "package_management.package_versions": {
            "apk1": "v1.0.0",
            "apk2": "v2.0.0",
        },
    }]

    mock_manager = mock.Mock()
    mock_device = fake_devices.FakeSSHDevice(
        mock_manager, FAKE_CONFIGURATION, log_directory="/a/b/c")
    mock_package_management = mock.MagicMock(
        spec=package_management_android.PackageManagementAndroid,
        package_versions={"apk1": "v1.0.0", "apk2": "v2.0.0"})

    with mock.patch.multiple(
        type(mock_device), create=True,
        firmware_version=mock.PropertyMock(return_value="123"),
        platform=mock.PropertyMock(return_value="sshdevice"),
        firmware_branch=mock.PropertyMock(
            side_effect=errors.DeviceError("Communication error")),
        firmware_type=mock.PropertyMock(return_value="eng"),
        package_management=mock.PropertyMock(
            return_value=mock_package_management)):
      with mock.patch.object(
          mock_device, "start_new_log",
          wraps=mock_device.start_new_log) as start_new_log_wrapper:
        info = mobly_controller.get_info([mock_device])
        self.assertDictEqual(info[0], expected_info[0])

    start_new_log_wrapper.assert_called_once_with(
        log_directory=logging.log_path,
        log_name_prefix="mobly_controller_get_info")

  def test_destroy(self):
    mock_manager = mock.Mock()
    mobly_controller._MANAGER_INSTANCE = mock_manager
    mock_device = mock.Mock()

    mobly_controller.destroy([mock_device])
    mock_device.close.assert_called()
    mock_manager.close.assert_called()
    self.assertIsNone(mobly_controller._MANAGER_INSTANCE)

  @parameterized.named_parameters(
      ("mobly_log_path", "some/mobly/log/path", "some/undeclared/outputs/dir",
       "some/mobly/log/path"),
      ("test_undeclared_outputs_dir", None, "some/undeclared/outputs/dir",
       "some/undeclared/outputs/dir"),
      ("default", None, None, None))
  def test_get_log_directory(
      self, mock_logging_log_path, mock_test_undeclared_outputs_dir,
      expected_log_directory):
    """Tests get_log_directory."""
    if mock_logging_log_path is None:
      del logging.log_path
    else:
      logging.log_path = mock_logging_log_path

    with mock.patch.object(
        os, "getenv", return_value=mock_test_undeclared_outputs_dir):
      self.assertEqual(
          mobly_controller.get_log_directory(), expected_log_directory)

  @parameterized.named_parameters(
      ("log_directory_specified", "/some/log/dir", "/some/log/dir/gdm.txt"),
      ("log_directory_not_specified", None, None))
  @mock.patch.object(mobly_controller, "_MANAGER_INSTANCE", new=None)
  @mock.patch.object(manager, "Manager")
  def test_get_manager(
      self, mock_log_directory, expected_log_file, mock_manager_class):
    """Tests get_manager()."""
    mock_manager = mock_manager_class.return_value
    with mock.patch.object(
        mobly_controller, "get_log_directory",
        return_value=mock_log_directory):
      self.assertIs(mobly_controller.get_manager(), mock_manager)
    mock_manager_class.assert_called_once_with(
        log_directory=mock_log_directory,
        gdm_log_file=expected_log_file,
        stdout_logging=False)

  def test_get_mobly_controller_config_name(self):
    """Tests get_mobly_controller_config_name."""
    expected_config_name = f"gdm_{fake_devices.FakeSSHDevice.DEVICE_TYPE}"
    self.assertEqual(
        mobly_controller.get_mobly_controller_config_name(
            fake_devices.FakeSSHDevice.DEVICE_TYPE),
        expected_config_name)


if __name__ == "__main__":
  unit_test_case.main()
