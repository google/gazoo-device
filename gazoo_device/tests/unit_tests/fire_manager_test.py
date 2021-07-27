# Copyright 2021 Google LLC
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

"""This test script verifies FireManager is working."""
import json
import multiprocessing
import os
import re
from unittest import mock

from gazoo_device import errors
from gazoo_device import fire_manager
from gazoo_device import gdm_logger
from gazoo_device import manager
from gazoo_device import package_registrar
from gazoo_device import testbed
from gazoo_device.switchboard import switchboard
from gazoo_device.tests.unit_tests import manager_test
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import usb_utils
import yaml

logger = gdm_logger.get_logger()


class FireManagerTests(manager_test.ManagerTestsSetup):
  """Unit tests for the fire_manager.py module (CLI extension of manager.py)."""

  def setUp(self):
    super().setUp()

    with mock.patch.object(multiprocessing, "Manager"):
      self.uut = fire_manager.FireManager(
          debug=False, dev_debug=False, quiet=False)
    self.mock_switchboard = mock.MagicMock(spec=switchboard.SwitchboardDefault)
    self.mock_switchboard.device_name = "FakeDevice"
    self.uut.create_switchboard = mock.MagicMock(
        return_value=self.mock_switchboard)
    self.uut.reload_configuration(  # Load the mock device configuration files
        device_file_name=self.files["device_file_name"],
        options_file_name=self.files["device_options_file_name"],
        testbeds_file_name=self.files["testbeds_file_name"],
        gdm_config_file_name=self.files["gdm_config_file_name"],
        log_directory=self.artifacts_directory)

  def test_01a_man_all(self):
    """Test "gdm man" without parameters. Same as "gdm helpfull"."""
    # Some examples from each device group. Examples don't have to be exhaustive
    test_cases = {
        "Primary": ["sshdevice"],
        "Auxiliary": ["cambrionix", "powerswitch", "yepkit"]
    }

    with mock.patch.object(fire_manager.logger, "info") as mock_logger_info:
      fire_manager.FireManager.man()
    mock_logger_info.assert_called_once()
    man = mock_logger_info.call_args[0][0]

    for device_group, some_expected_devices in test_cases.items():
      regex = r"{group}:\n((?:\s+\w+)+)\n\n".format(group=device_group)
      actual_devices = re.search(regex, man).group(1).splitlines()
      actual_devices = [device.strip() for device in actual_devices]
      for expected_device in some_expected_devices:
        self.assertIn(expected_device, actual_devices)

  def test_01b_helpfull(self):
    """Verify the helpfull() method works."""
    fire_manager.FireManager.helpfull()

  def test_02_man_valid_device_types(self):
    """Test "gdm man <device_type>" for several device types."""
    for device_type in ["sshdevice", "cambrionix"]:
      fire_manager.FireManager.man(device_type)

  def test_03_man_invalid_device_type(self):
    """Test "gdm man <device_type>" for an invalid device type."""
    err_msg = "Device type tthdevice is not known."
    with self.assertRaisesRegex(errors.DeviceError, err_msg):
      fire_manager.FireManager.man("tthdevice")
    with self.assertRaisesRegex(errors.DeviceError, err_msg):
      fire_manager.FireManager.man("tthdevice", "reboot")

  def test_04_man_class_member(self):
    """Test "gdm man <device_type> <class_member>" for valid attributes."""
    test_cases = [
        ("sshdevice", "reboot"),  # Method of a primary device
        ("sshdevice", "file_transfer"),  # Capability of a primary device
        ("sshdevice", "_verify_reboot"),  # Private method
        ("sshdevice", "communication_address"),  # Property
        ("sshdevice", "console_port_name"),  # Deprecated property alias
        ("cambrionix", "set_mode"),  # Deprecated method alias
    ]

    for device_type, class_member_name in test_cases:
      fire_manager.FireManager.man(device_type, class_member_name)

  def test_05_man_class_member_unknown(self):
    """Test "gdm man <device_type> <class member>" for invalid member."""
    regex = r"sshdevice.*does not have attribute 'foo'"
    with self.assertRaisesRegex(AttributeError, regex):
      fire_manager.FireManager.man("sshdevice", "foo")

  def test_06a_man_capability_attributes(self):
    """Test man on capability attributes ("gdm man device.capability.attr")."""
    test_cases = (
        # Capability method
        ("cambrionix", "switch_power", "power_off"),
        # Capability property
        ("cambrionix", "switch_power", "supported_modes"),
        # Capability deprecated property
        ("sshdevice", "usb_hub", "power_off"),

    )

    for device_type, capability, capability_attr in test_cases:
      command = f"man {device_type} {capability} {capability_attr}"
      with self.subTest(command=command):
        fire_manager.FireManager.man(device_type, capability, capability_attr)

  def test_06b_man_bad_capability_attribute(self):
    """Test man on nonexistent/non-capability class attributes."""
    regex = r"cambrionix.switch_power.*does not have attribute 'foo'"
    with self.assertRaisesRegex(AttributeError, regex):
      fire_manager.FireManager.man("cambrionix", "switch_power", "foo")
    regex = r"cambrionix.reboot.*is not a capability"
    with self.assertRaisesRegex(TypeError, regex):
      fire_manager.FireManager.man("cambrionix", "reboot", "something")

  def test_07_man_nested_access(self):
    """Test nested access "gdm man <device_type>.<class member>"."""
    expected_docs = fire_manager.FireManager.man("cambrionix", "reboot")
    actual_docs = fire_manager.FireManager.man("cambrionix.reboot")
    self.assertEqual(expected_docs, actual_docs)

    expected_docs = fire_manager.FireManager.man("cambrionix", "switch_power",
                                                 "power_off")
    actual_docs = fire_manager.FireManager.man(
        "cambrionix.switch_power.power_off")
    self.assertEqual(expected_docs, actual_docs)

  def test_07a_man_dash_separated_vs_underscore(self):
    """Verify dash-separated names are converted to underscore_separated."""
    expected_docs = fire_manager.FireManager.man("unifi_switch", "switch_power",
                                                 "power_off")
    actual_docs = fire_manager.FireManager.man("unifi-switch", "switch-power",
                                               "power-off")
    self.assertEqual(expected_docs, actual_docs)

  def test_08_man_device_type_deprecated(self):
    """Test "gdm man <device_type> --deprecated"."""
    for device_type in ["sshdevice", "cambrionix"]:
      fire_manager.FireManager.man(device_type, deprecated=True)

  @mock.patch.object(
      usb_utils,
      "get_address_to_usb_info_dict",
      return_value=manager_test.USB_INFO_DICT)
  def test_10_print_usb_info(self, mock_usb_info_dict):
    """Test usb_info keys are printed."""
    self.uut.print_usb_info()
    mock_usb_info_dict.assert_called_once()

  def test_11_issue(self):
    """Test that FireManager.issue() runs all health checks."""
    with manager_test.MockOutDevices():
      self.uut.issue("sshdevice-0000")
      manager_test.FakeSSHDevice.make_device_ready.assert_called_once_with("on")

  def test_12_exec(self):
    """Test that FireManager.exec() does not run health checks."""
    with manager_test.MockOutDevices():
      self.uut.exec("sshdevice-0000")
      manager_test.FakeSSHDevice.make_device_ready.assert_called_once_with(
          "off")

  @mock.patch.object(manager_test.FakeSSHDevice, "close")
  def test_13_health_check_success_without_recover(self, mock_close):
    """Test FireManager.health_check(recover=False) success."""
    with manager_test.MockOutDevices():
      self.uut.health_check("sshdevice-0000", recover=False)
      manager_test.FakeSSHDevice.make_device_ready.assert_called_with(
          setting="check_only")
    mock_close.assert_called_once()

  @mock.patch.object(manager_test.FakeSSHDevice, "close")
  def test_14_health_check_success_with_recover(self, mock_close):
    """Test FireManager.health_check(recover=True) success."""
    with manager_test.MockOutDevices():
      self.uut.health_check("sshdevice-0000", recover=True)
      manager_test.FakeSSHDevice.make_device_ready.assert_called_with(
          setting="on")
    mock_close.assert_called_once()

  @mock.patch.object(manager_test.FakeSSHDevice, "close")
  def test_15_health_check_raises_on_error(self, mock_close):
    """Test that FireManager.health_check() raises when health checks fail."""

    def mock_make_device_ready(setting="on"):
      """Succeeds if health checks are skipped, but fails if they do run."""
      if setting == "off":
        return
      raise errors.DeviceNotResponsiveError("sshdevice-0000",
                                            "Did not respond to 'foo' in 10s")

    with manager_test.MockOutDevices():
      manager_test.FakeSSHDevice.make_device_ready = mock.Mock(
          side_effect=mock_make_device_ready)
      with self.assertRaises(errors.DeviceNotResponsiveError):
        self.uut.health_check("sshdevice-0000")
      manager_test.FakeSSHDevice.make_device_ready.assert_called_with(
          setting="check_only")
      mock_close.assert_called_once()

  def test_16_get_prop(self):
    """Test FireManager.get_prop() retrieves all properties successfully."""
    with manager_test.MockOutDevices():
      self.uut.get_prop("sshdevice-0000")

  def test_17_get_prop_single_property(self):
    """Test FireManager.get_prop() retrieves a single property successfully."""
    with manager_test.MockOutDevices():
      self.uut.get_prop("sshdevice-0000", "firmware_version")

  def test_18_get_prop_manager_no_such_property(self):
    """Test get_prop() raises an error when property isn't in Manager config."""
    with self.assertRaisesRegex(errors.DeviceError,
                                "Unable to find prop foobar in manager config"):
      self.uut.get_prop("manager", "foobar")

  def test_19_log_file_never_created(self):
    """Ensures stream device raises error if log file is never created."""
    with mock.patch.object(
        fire_manager, "MAX_TIME_TO_WAIT_FOR_INITATION", new=0.1):
      with self.assertRaisesRegex(errors.DeviceError,
                                  "Log file not created within 0.1 seconds"):
        with manager_test.MockOutDevices():
          self.uut.log("sshdevice-0000", self.device_log_file, duration=0.1)

  def test_20_log_success(self):
    """Places logs in the file and invokes log and stops when requested."""
    with manager_test.MockOutDevices():
      self._create_log_file(2)
      self.uut.log(
          "sshdevice-0000", os.path.basename(self.device_log_file), duration=.2)

  @mock.patch.object(testbed.Testbed, "make_testbed_ready")
  def test_30_make_devices_ready_success(self, make_testbed_ready_mock):
    """Verify make_devices_ready returns is_healthy=True."""
    self.addCleanup(logger.setLevel, logger.getEffectiveLevel())
    testing_props = {
        "paired": True,
        "wifi_ssid": "GazooDevice!"
    }
    with manager_test.MockOutDevices():
      mock_devices_health = json.loads(
          self.uut.make_devices_ready(self.first_name + "," + self.second_name,
                                      testing_props))
      self.assertTrue(mock_devices_health[self.first_name]["is_healthy"])
      self.assertTrue(mock_devices_health[self.second_name]["is_healthy"])
    make_testbed_ready_mock.assert_called_once()

  def test_31_make_devices_ready_single_device_success(self):
    """Verify _make_devices_ready_single_device returns is_healthy=True."""
    self.addCleanup(logger.setLevel, logger.getEffectiveLevel())
    with manager_test.MockOutDevices():
      device = self.uut.create_device(self.first_name)
      parameter_dict = {"sshdevice": {"setting": "on"}}
      device_health = self.uut._make_devices_ready_single_device(
          device, parameter_dict)
      self.assertTrue(device_health[self.first_name]["is_healthy"])

  def test_32_make_devices_ready_single_device_log_path(self):
    """Verify _make_devices_ready_single_device returns log path."""
    self.addCleanup(logger.setLevel, logger.getEffectiveLevel())
    with manager_test.MockOutDevices():
      device = self.uut.create_device(self.first_name)
      parameter_dict = {"sshdevice": {"setting": "on"}}
      device_health = self.uut._make_devices_ready_single_device(
          device, parameter_dict)
      self.assertEqual(device_health[self.first_name]["logs"],
                       device.log_file_name)

  def test_33_make_devices_ready_unhealthy_not_known(self):
    """Verify make_devices_ready returns correct unhealthy reason."""
    self.addCleanup(logger.setLevel, logger.getEffectiveLevel())
    unknown_device_name = "gobbly-gook"
    expected_error = errors.DeviceError(
        "Device {} is not known. Close matches: ".format(unknown_device_name))
    with manager_test.MockOutDevices():
      mock_devices_health = json.loads(
          self.uut.make_devices_ready([unknown_device_name, self.first_name]))
      self.assertFalse(mock_devices_health[self.first_name]["unhealthy_reason"])
      self.assertEqual(
          mock_devices_health[unknown_device_name]["unhealthy_reason"],
          str(expected_error))

  def test_34_make_devices_ready_unhealthy_not_responsive(self):
    """Verify make_devices_ready returns correct error."""
    self.addCleanup(logger.setLevel, logger.getEffectiveLevel())
    testing_props = {
        "paired": True,
        "wifi_ssid": "GazooDevice!"
    }
    sshdevice_1, sshdevice_2, cambrionix = [
        "sshdevice-0000", "sshdevice-0001", "cambrionix-1234"]
    expected_error = errors.DeviceNotResponsiveError(
        sshdevice_1, "failed make_device_ready")
    expected_testbed_error = errors.CheckTestbedReadyError(
        "wifi ssid not pingable")
    with manager_test.MockOutDevices():
      with mock.patch.object(
          manager_test.FakeSSHDevice,
          "make_device_ready",
          side_effect=expected_error):
        with mock.patch.object(
            testbed.Testbed,
            "make_testbed_ready",
            side_effect=expected_testbed_error):
          mock_devices_health = json.loads(
              self.uut.make_devices_ready(
                  [sshdevice_1, sshdevice_2, cambrionix],
                  testing_props))
          self.assertEqual(mock_devices_health[sshdevice_1]["err_type"],
                           type(expected_error).__name__)
          self.assertEqual(mock_devices_health[sshdevice_2]["err_type"],
                           type(expected_error).__name__)
          self.assertEqual(mock_devices_health["testbed"]["err_type"],
                           type(expected_testbed_error).__name__)
          self.assertFalse(mock_devices_health[cambrionix]["err_type"])

  def test_35_make_devices_ready_single_device_unhealthy_not_responsive(self):
    """Verify _make_devices_ready_single_device returns unhealthy_reason."""
    self.addCleanup(logger.setLevel, logger.getEffectiveLevel())
    expected_error = errors.DeviceNotResponsiveError(
        self.first_name, "failed make_device_ready")
    with manager_test.MockOutDevices():
      device = self.uut.create_device("sshdevice-0000")
      with mock.patch.object(
          manager_test.FakeSSHDevice,
          "make_device_ready",
          side_effect=expected_error):
        parameter_dict = {"sshdevice": {"setting": "on"}}
        device_health = self.uut._make_devices_ready_single_device(
            device, parameter_dict)
        self.assertEqual(device_health["sshdevice-0000"]["unhealthy_reason"],
                         str(expected_error))

  def test_36_get_persistent_prop_devices_success(self):
    """Verify get_persistent_prop_devices returns persistent device props."""
    self.addCleanup(logger.setLevel, logger.getEffectiveLevel())
    with manager_test.MockOutDevices():
      mock_devices_props = yaml.safe_load(
          self.uut.get_persistent_prop_devices(
              [self.first_name, self.second_name]))
      for device_name in mock_devices_props:
        expected_props = manager_test.FAKE_DEVICES["devices"][device_name]
        self.assertEqual(mock_devices_props[device_name], expected_props)

  def test_37_get_persistent_prop_devices_unhealthy_devices(self):
    """Verify get_persistent_prop_devices returns empty json object."""
    self.addCleanup(logger.setLevel, logger.getEffectiveLevel())
    exception = errors.DeviceNotResponsiveError(self.first_name,
                                                "failed make_device_ready")
    with manager_test.MockOutDevices():
      with mock.patch.object(
          self.uut, "get_device_configuration", side_effect=exception):
        mock_devices_props = yaml.safe_load(
            self.uut.get_persistent_prop_devices(
                [self.first_name, self.second_name]))
        for device_name in mock_devices_props:
          self.assertEqual(mock_devices_props[device_name], {})

  def test_38_construct_health_dict_from_exception(self):
    """Verify health dictionary constructed in proper format from exception."""
    err_msg = "device is unresponsive"
    checks_passed = ["first_health_check", "second_health_check"]
    properties = {"prop_name": "prop_val", "other_prop_name": "other_prop_val"}
    exception = errors.CheckDeviceReadyError("device-1234", err_msg)
    exception.checks_passed = checks_passed
    exception.properties = properties

    health_dict = self.uut._construct_health_dict_from_exception(exception)
    self.assertEqual(health_dict.get("is_healthy"), False)
    self.assertIn(err_msg, health_dict.get("unhealthy_reason"))
    self.assertEqual(health_dict.get("err_type"), "CheckDeviceReadyError")
    self.assertEqual(health_dict.get("checks_passed"), checks_passed)
    self.assertEqual(health_dict.get("properties"), properties)

  @mock.patch.object(
      package_registrar, "import_and_register", return_value=True)
  @mock.patch.object(manager.logger, "info")
  def test_40_register_already_registered(self, mock_info,
                                          mock_import_and_register):
    """Test register() when package has already been registered."""
    with mock.patch.object(
        self.uut,
        "config",
        new={"cli_extension_packages": ["registered_package"]}):
      self.uut.register("registered_package")
      self.assertEqual(self.uut.config["cli_extension_packages"],
                       ["registered_package"])
    mock_import_and_register.assert_not_called()
    mock_info.assert_called_once_with(
        "Package 'registered_package' is already registered with GDM CLI.")

  @mock.patch.object(
      package_registrar, "import_and_register", return_value=False)
  @mock.patch.object(manager.logger, "info")
  def test_41_register_failure(self, mock_info, mock_import_and_register):
    """Test register() when package registration or import fails."""
    with mock.patch.object(
        self.uut, "config", new={"cli_extension_packages": []}):
      self.uut.register("invalid_or_missing_package")
      self.assertEqual(self.uut.config["cli_extension_packages"], [])
    mock_import_and_register.assert_called_once_with(
        "invalid_or_missing_package", include_cli_instructions=True)
    mock_info.assert_not_called()

  @mock.patch.object(
      package_registrar, "import_and_register", return_value=True)
  @mock.patch.object(manager.logger, "info")
  def test_42_register_success(self, mock_info, mock_import_and_register):
    """Test register() when package registration succeeds."""
    with mock.patch.object(
        self.uut, "config", new={"cli_extension_packages": []}):
      self.uut.register("valid_package")
      self.assertEqual(self.uut.config["cli_extension_packages"],
                       ["valid_package"])
    mock_import_and_register.assert_called_once_with(
        "valid_package", include_cli_instructions=True)
    mock_info.assert_called_once_with(
        "Registered package 'valid_package' with GDM CLI.")

  @mock.patch.object(manager.logger, "info")
  def test_45_unregister_not_found(self, mock_info):
    """Test unregister() when package isn't registered."""
    with mock.patch.object(
        self.uut, "config", new={"cli_extension_packages": ["other_package"]}):
      self.uut.unregister("not_registered_package")
      self.assertEqual(self.uut.config["cli_extension_packages"],
                       ["other_package"])
    mock_info.assert_called_once_with(
        "Package 'not_registered_package' is not registered with GDM CLI.")

  @mock.patch.object(manager.logger, "info")
  def test_46_unregister_success(self, mock_info):
    """Test unregister() for a registered package."""
    with mock.patch.object(
        self.uut,
        "config",
        new={"cli_extension_packages": ["some_package", "other_package"]}):
      self.uut.unregister("some_package")
      self.assertEqual(self.uut.config["cli_extension_packages"],
                       ["other_package"])
    mock_info.assert_called_once_with(
        "Removed package 'some_package' from GDM CLI.")


if __name__ == "__main__":
  unit_test_case.main()
