"""Tests for mobly_controller."""
import logging
import os
from unittest import mock

import gazoo_device
from gazoo_device import errors
from gazoo_device import mobly_controller
from gazoo_device.tests.unit_tests.utils import unit_test_case
from mobly import asserts
from mobly import base_test
from mobly import config_parser
from mobly import records

FAKE_CONTROLLER_CONFIGS = {
    "GazooDevice": [{
        "id": "sshdevice-0003"
    }, {
        "label": "b",
        "id": "sshdevice-0001",
        "other": "b"
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
    }
}


class MoblyControllerFuncsTest(unit_test_case.UnitTestCase):

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
      return_value=mock.Mock(firmware_version="1"))
  @mock.patch.object(mobly_controller.manager.Manager, "set_prop")
  @mock.patch.object(
      mobly_controller.manager.Manager,
      "get_device_configuration",
      return_value=FAKE_CONFIGURATION)
  def test_mobly_test(self, mock_config, mock_set, mock_create_device):
    """Use a fake mobly test to verify everything actually works as expected."""

    class FakeTest(base_test.BaseTestClass):
      """Fake Mobly test to verify functionality."""

      def setup_class(self):
        self.devices = self.register_controller(gazoo_device)

      def test_1(self):
        asserts.assert_true(len(self.devices) == 2, self.devices)

    fake_config = config_parser.TestRunConfig()
    fake_config.log_path = self.artifacts_directory
    summary_file = os.path.join(self.artifacts_directory, "summary.yaml")
    fake_config.summary_writer = records.TestSummaryWriter(summary_file)
    fake_config.controller_configs = FAKE_CONTROLLER_CONFIGS
    test = FakeTest(fake_config)
    test.run(["test_1"])
    self.assertTrue(test.results.passed,
                    "Test results: {}".format(test.results))
    actual_record = test.results.passed[0]
    self.assertIn(actual_record.test_name, "test_1")

  @mock.patch.object(mobly_controller.manager.Manager, "create_device")
  @mock.patch.object(mobly_controller.manager.Manager, "set_prop")
  def test_create(self, mock_set, mock_create):
    mock_device_1 = mock.Mock()
    mock_device_2 = mock.Mock()
    mock_create.side_effect = iter([mock_device_1, mock_device_2])
    devices = gazoo_device.create(FAKE_CONTROLLER_CONFIGS["GazooDevice"])
    self.assertEqual(devices, [mock_device_1, mock_device_2])
    mock_create.assert_called()
    mock_set.assert_called_with("sshdevice-0001", "other", "b")

  @mock.patch.object(mobly_controller.manager.Manager, "create_device")
  @mock.patch.object(mobly_controller.manager.Manager, "set_prop")
  def test_create_set_prop_error(self, mock_set, mock_create_device):
    mock_device = mock.Mock()
    mock_create_device.return_value = mock_device
    mock_set.side_effect = iter([None, errors.DeviceError("")])
    devices = gazoo_device.create(FAKE_CONTROLLER_CONFIGS["GazooDevice"])

    self.assertEqual(devices, [mock_device, mock_device])
    mock_create_device.assert_called()
    mock_set.assert_called_with("sshdevice-0001", "other", "b")

  def test_get_info(self):
    mock_manager = mock.Mock()
    mobly_controller._MANAGER_INSTANCE = mock_manager
    mock_manager.get_device_configuration.return_value = FAKE_CONFIGURATION
    mock_device = mock.Mock()
    mock_device.name = "sshdevice-0000"
    info = gazoo_device.get_info([mock_device])
    mock_manager.get_device_configuration.assert_called_with(mock_device.name)
    expected_info = [{
        "serial_number": "00000000",
        "name": "sshdevice-0000",
        "device_type": "sshdevice",
        "model": "linux",
        "console_port_name": "123.456.78.9",
        "firmware_version": "NotImplemented"
    }]
    self.assertDictEqual(info[0], expected_info[0])

  def test_destroy(self):
    mock_manager = mock.Mock()
    mobly_controller._MANAGER_INSTANCE = mock_manager
    mock_device = mock.Mock()

    gazoo_device.destroy([mock_device])
    mock_device.close.assert_called()
    mock_manager.close.assert_called()
    self.assertIsNone(mobly_controller._MANAGER_INSTANCE)


if __name__ == "__main__":
  unit_test_case.main()
