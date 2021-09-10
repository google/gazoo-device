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

"""Unit tests for GazooDeviceBase class."""
import os
from unittest import mock
import weakref

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import extensions
from gazoo_device.auxiliary_devices import cambrionix
from gazoo_device.base_classes import gazoo_device_base
from gazoo_device.capabilities import comm_power_default
from gazoo_device.capabilities import event_parser_default
from gazoo_device.capabilities import usb_hub_default
from gazoo_device.switchboard import log_process
from gazoo_device.switchboard import switchboard
from gazoo_device.tests.unit_tests.device_mixin_tests import common_test
from gazoo_device.tests.unit_tests.utils import fake_capabilities
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.tests.unit_tests.utils import fake_gazoo_device_base
from gazoo_device.tests.unit_tests.utils import gc_test_utils


class GazooDeviceBaseStub(fake_gazoo_device_base.FakeGazooDeviceBase):
  """Stub GazooDevice implementation with additional attributes for testing."""
  COMMUNICATION_TYPE = "SshComms"
  DEVICE_TYPE = "devicestub"
  _COMMUNICATION_KWARGS = {}

  @decorators.DynamicProperty
  def firmware_type(self):
    return "some_type"

  @decorators.DynamicProperty
  def bad_property(self):
    raise errors.DeviceError("x")

  def check1(self):
    """Fake health check 1.

    Raises:
      CheckDeviceReadyError: for testing.
    """
    raise errors.CheckDeviceReadyError(self.name, "health check failed")

  def check2(self):
    """Fake health check 2.

    Raises:
      CheckDeviceReadyError: for testing.
    """
    raise errors.CheckDeviceReadyError(self.name, "health check failed")


class GazooDeviceBaseTests(fake_device_test_case.FakeDeviceTestCase,
                           common_test.CommonTestMixin,
                           gc_test_utils.GCTestUtilsMixin):
  """Unit tests for gazoo_device_base.py."""

  def setUp(self):
    super().setUp()
    self.usb_mode = "off"

    def power_on(port_num, data_sync=True):
      del port_num  # Not used by the mock implementation
      if data_sync:
        self.usb_mode = "sync"
      else:
        self.usb_mode = "charge"

    def power_off(port_num):
      del port_num  # Not used by the mock implementation
      self.usb_mode = "off"

    self.usb_hub = mock.MagicMock(spec=cambrionix.Cambrionix)
    self.usb_hub.power_off.side_effect = power_off
    self.usb_hub.power_on.side_effect = power_on
    self.setup_fake_device_requirements("devicestub-1234")
    self.device_config["persistent"]["console_port_name"] = "la"
    self.mock_manager.create_device = mock.MagicMock(return_value=self.usb_hub)

    self.uut = GazooDeviceBaseStub(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory)

  def test_001_close_called_twice(self):
    """Test that calling GazooDeviceBase.close() twice has no effect."""
    self.assertTrue(self.uut.switchboard)  # Create Switchboard
    self.uut.close()
    self.mock_switchboard.close.assert_called_once()
    self.uut.close()
    self.mock_switchboard.close.assert_called_once()

  def test_002_manager_available_after_device_is_closed(self):
    """Test that the Manager instance is available after device is closed."""
    self.assertIsNotNone(self.uut.manager_weakref())
    self.uut.close()
    self.assertIsNotNone(self.uut.manager_weakref())

  def test_010_make_device_ready_must_be_a_string(self):
    """Verify that an exception is raised if make_device_ready is a bool."""
    self.device_config["make_device_ready"] = False
    with self.assertRaisesRegex(errors.DeviceError, "should be a string."):
      GazooDeviceBaseStub(self.mock_manager, self.device_config)

  def test_011_make_device_ready_must_be_a_string(self):
    """Verify that an error is raised if make_device_ready value is invalid."""
    self.device_config["make_device_ready"] = "yes"
    with self.assertRaisesRegex(errors.DeviceError,
                                "should be 'on', 'off' or 'check_only'"):
      GazooDeviceBaseStub(self.mock_manager, self.device_config)

  def test_050_gazoo_device_base_close_manager_weakref_dead(self):
    """Verify GazooDeviceBase can close when Manager weakref is dead."""
    with mock.patch.object(self.uut, "manager_weakref",
                           new=mock.Mock(return_value=None)):
      self.uut.close()

  @mock.patch.object(GazooDeviceBaseStub, "check1")
  @mock.patch.object(GazooDeviceBaseStub, "check2")
  def test_80_execute_health_check_methods(self, mock_health_check1,
                                           mock_health_check2):
    """Test _execute_health_check_methods when health checks succeed."""
    mock_health_check1.__name__ = "mock_health_check1"
    mock_health_check2.__name__ = "mock_health_check2"
    health_checks = [mock_health_check1, mock_health_check2]
    self.uut._execute_health_check_methods(health_checks)
    mock_health_check1.assert_called_once()
    mock_health_check2.assert_called_once()

  def test_81_execute_health_check_methods_failure(self):
    """Test _execute_health_check_methods when a health check fails."""
    health_checks = [self.uut.check1, self.uut.check2]
    with self.assertRaises(errors.CheckDeviceReadyError):
      self.uut._execute_health_check_methods(health_checks)

  def test_101_gazoo_device_base_start_new_log(self):
    """Verify start_new_log calls console_port.start_new_log."""
    self.assertTrue(self.uut.switchboard)  # Create Switchboard
    old_log_file_name = self.uut.log_file_name
    self.uut.start_new_log()
    self.assertNotEqual(
        old_log_file_name, self.uut.log_file_name,
        "Expected log file name to change from {}".format(old_log_file_name))
    self.assertIsNone(self.uut.log_file_symlink)
    self.assertIsNone(self.uut.event_file_symlink)
    self.assertTrue(self.uut.switchboard.start_new_log.called,
                    "Expected Switchboard start_new_log to be called")

  def test_102_gazoo_device_base_start_new_log_with_log_dir(self):
    """Verify start_new_log saves new log directory."""
    self.assertTrue(self.uut.switchboard)  # Create Switchboard
    old_log_file_name = self.uut.log_file_name
    log_directory = os.path.join(self.artifacts_directory, self._testMethodName)
    self.uut.start_new_log(log_directory)
    self.assertNotEqual(
        old_log_file_name, self.uut.log_file_name,
        "Expected log file name to change from {}".format(old_log_file_name))
    self.assertEqual(
        log_directory, self.uut.log_directory,
        "Expected log directory to change to {}".format(log_directory))

  def test_110_gazoo_device_base_log_file_name(self):
    """Verify log_file_name property works as expected."""
    old_log_filename = self.uut.log_file_name
    # Create fake rotated log file
    next_log_filename = log_process.get_next_log_filename(old_log_filename)
    with open(next_log_filename, "w+") as log_file:
      log_file.write("")
    actual_log_filename = self.uut.log_file_name
    self.assertNotEqual(
        old_log_filename, actual_log_filename,
        "Expected {} != {}".format(old_log_filename, actual_log_filename))

  def test_201_gazoo_device_base_set_max_log_size(self):
    """Verify set_max_log_size calls console_port.set_max_log_size."""
    self.assertTrue(self.uut.switchboard)  # Create Switchboard
    max_log_size = 100
    self.uut.set_max_log_size(max_log_size)
    self.assertTrue(self.uut.switchboard.set_max_log_size.called,
                    "Expected Switchboard set_max_log_size to be called")

  def test_202_gazoo_device_base_add_new_filter_bad_path(self):
    """Verifies add_new_filter raises error if given bad path."""
    with self.assertRaisesRegex(errors.DeviceError, "Unable to access"):
      self.uut.add_new_filter("bad_path")

  def test_204_gazoo_device_base_add_new_filterload_filter_file_error(self):
    """Verifies add_new_filter raises error if load_filter_file errors."""
    self.assertTrue(self.uut.switchboard)  # Create Switchboard
    with mock.patch.object(event_parser_default, "EventParserDefault"):
      self.uut.event_parser.load_filter_file.side_effect = errors.ParserError(
          "some error")
      with self.assertRaisesRegex(errors.DeviceError, "some error"):
        self.uut.add_new_filter("/some/filter/file.json")

  def test_210_gazoo_device_base_add_new_filter_successful(self):
    """Verifies add_new_filter is successful using valid input."""
    self.assertTrue(self.uut.switchboard)  # Create Switchboard
    with mock.patch.object(event_parser_default, "EventParserDefault"):
      filter_file = "/some/filter/file.json"
      self.uut.add_new_filter(filter_file)
      self.uut.event_parser.load_filter_file.assert_called_once_with(
          filter_file)
      self.uut.switchboard.add_new_filter.assert_called_once_with(filter_file)

  def test_604_expect(self):
    """Verify expect() calls Switchboard.expect()."""
    self.assertTrue(self.uut.switchboard)  # Create Switchboard
    self.uut.switchboard.expect(["something"])
    self.uut.switchboard.expect.assert_called_with(["something"])

    self.uut.switchboard.expect(["something"], 15, 10, "response", "all")
    self.uut.switchboard.expect.assert_called_with(["something"], 15, 10,
                                                   "response", "all")

  def test_610_shell_with_regex_success_first_try(self):
    """Verify shell_with_regex() works when it succeeds on the first try."""
    return_value = ("asdalsd gobbly", 0)
    with mock.patch.object(
        self.uut, "shell", return_value=return_value) as mock_shell:
      result = self.uut.shell_with_regex("some command", r"(gobbly)")
      self.assertEqual(result, "gobbly")
      mock_shell.assert_called_once()

  def test_611_shell_with_regex_success_with_retries(self):
    """Verify shell_with_regex() works when it has to retry."""
    shell_responses = [
        errors.DeviceError("Error 1"),
        errors.DeviceError("Error 2"), ("gobbly", 0)
    ]
    with mock.patch.object(
        self.uut, "shell", side_effect=shell_responses) as mock_shell:
      result = self.uut.shell_with_regex("some command", r"(.*)", tries=3)
      self.assertEqual(result, "gobbly")
      self.assertEqual(mock_shell.call_count, 3)

  def test_612_shell_with_regex_failure_error_no_raise(self):
    """Verify shell_with_regex(raise_error=False) warning on failure."""
    with mock.patch.object(gazoo_device_base, "logger"):
      with mock.patch.object(
          self.uut, "shell", side_effect=errors.DeviceError("Some error")):
        result = self.uut.shell_with_regex(
            "some command", r"(.*)", raise_error=False)
        self.assertEqual(result, "")
        gazoo_device_base.logger.warning.assert_called_once()

  def test_613_shell_with_regex_failure_error_raise(self):
    """Verify shell_with_regex(raise_error=True) error on failure."""
    with mock.patch.object(
        self.uut, "shell", side_effect=errors.DeviceError("Some error")):
      with self.assertRaisesRegex(errors.DeviceError, "unable to retrieve"):
        self.uut.shell_with_regex("some command", r"(.*)", raise_error=True)

  def test_614_shell_with_regex_failure_no_match_raise(self):
    """Verify shell_with_regex() raises an error when regex doesn't match."""
    with mock.patch.object(self.uut, "shell", return_value=("top kek", 0)):
      with self.assertRaisesRegex(errors.DeviceError, "unable to retrieve"):
        self.uut.shell_with_regex("some command", r"(gobbly)", raise_error=True)

  def test_615_shell_with_regex_failure_group_number_too_high(self):
    """Verify shell_with_regex() failure when regex group number is too high."""
    cmd = "some command"
    regex = r"(.*)"
    tries = 2
    error_rx = "unable to retrieve {!r} from {!r} after {} tries".format(
        regex, cmd, tries)

    with mock.patch.object(gazoo_device_base, "logger"):
      with mock.patch.object(
          self.uut, "shell", return_value=("gobbly gook", 0)):
        with self.assertRaisesRegex(errors.DeviceError, error_rx):
          self.uut.shell_with_regex(
              cmd, regex, regex_group=2, tries=tries, raise_error=True)
        gazoo_device_base.logger.warning.assert_called()

  def test_616_shell_with_regex_failure_no_groups_in_regex_raise(self):
    """Verify shell_with_regex() failure for regex without capturing groups."""
    with mock.patch.object(gazoo_device_base, "logger"):
      with mock.patch.object(
          self.uut, "shell", return_value=("gobbly gook", 0)):
        with self.assertRaisesRegex(errors.DeviceError, "unable to retrieve"):
          self.uut.shell_with_regex(
              "some command", "gobbly", tries=2, raise_error=True)
        gazoo_device_base.logger.warning.assert_called()

  def test_617_shell_with_regex_success_group_num_more_than_1(self):
    """Verify shell_with_regex() works for capturing groups >= 1."""
    return_value = ("asd1337", 0)
    with mock.patch.object(self.uut, "shell", return_value=return_value):
      result = self.uut.shell_with_regex(
          "some command", r"([a-z]*)(\d*)", regex_group=2)
      self.assertEqual(result, "1337")

  def test_618_shell_with_regex_check_return_code_failure_nonzero_return_code(
      self):
    """Verify shell_with_regex() failure due to non-zero return code."""
    with mock.patch.object(self.uut, "shell", return_value=("gobbly gook", 1)):
      with self.assertRaisesRegex(errors.DeviceError, "unable to retrieve"):
        self.uut.shell_with_regex(
            "some command", "gobbly", raise_error=True, check_return_code=True)

  def test_619_shell_with_regex_check_return_code_success(self):
    """Verify shell_with_regex() checks return code and succeeds if it's 0."""
    shell_responses = [("foo", 1), ("gobbly", 0)]
    with mock.patch.object(self.uut, "shell", side_effect=shell_responses):
      self.uut.shell_with_regex(
          "some command",
          "(gobbly)",
          raise_error=True,
          tries=2,
          check_return_code=True)

  def test_641_get_default_event_filters_warning_no_filters(self):
    """Verify _get_default_event_filters warns for missing filters."""

    class GazooDeviceBaseStubNoFilters(GazooDeviceBaseStub):
      _DEFAULT_FILTERS = []

    with mock.patch.object(gazoo_device_base, "logger") as mock_logger:
      GazooDeviceBaseStubNoFilters(
          self.mock_manager,
          self.device_config,
          log_directory=self.artifacts_directory)
      mock_logger.warning.assert_called_once()

  def test_642_default_event_filters(self):
    """Test that default event filters are present in filter_paths."""
    test_filters = ["/path/to/folder1/name1.json", "/path/to/name2.json"]

    class GazooDeviceBaseStubWithFilters(GazooDeviceBaseStub):
      _DEFAULT_FILTERS = test_filters

    uut = GazooDeviceBaseStubWithFilters(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory)
    for filter_path in test_filters:
      self.assertIn(filter_path, uut.filter_paths)

  def test_660_get_private_capability_name(self):
    """Test that private capability name generation works."""
    private_attribute_name = (
        gazoo_device_base.GazooDeviceBase._get_private_capability_name(
            comm_power_default.CommPowerDefault))
    self.assertEqual("_comm_power", private_attribute_name)

  def test_661_is_capability_initialized_valid_capability(self):
    """Test is_capability_initialized() with a valid capability."""
    self.assertTrue(self.uut.switchboard)  # Initialize Switchboard
    self.assertTrue(self.uut.is_capability_initialized("switchboard"))
    self.uut.reset_capability("switchboard")
    self.assertFalse(self.uut.is_capability_initialized("switchboard"))

  def test_662_is_capability_initialized_invalid_capability(self):
    """Test is_capability_initialized() raises for invalid capability."""
    err_regex = "Capability foobar is not recognized"
    with self.assertRaisesRegex(errors.DeviceError, err_regex):
      self.uut.is_capability_initialized("foobar")
    with self.assertRaisesRegex(errors.DeviceError, err_regex):
      self.uut.reset_capability("foobar")

  def test_663_is_capability_initialized_unsupported_capability(self):
    """Test is_capability_initialized() raises for unsupported capability."""
    err_regex = "Capability file_transfer is not supported"
    with self.assertRaisesRegex(errors.DeviceError, err_regex):
      self.uut.is_capability_initialized("file_transfer")
    with self.assertRaisesRegex(errors.DeviceError, err_regex):
      self.uut.reset_capability("file_transfer")

  def test_664_reset_all_capabilities(self):
    """Test that reset_all_capabilities resets all initialized capabilities."""
    capabilities = ["switchboard", "event_parser"]
    for capability in capabilities:
      self.assertFalse(self.uut.is_capability_initialized(capability))

    # Initialize capabilities
    for capability in capabilities:
      self.assertTrue(getattr(self.uut, capability))

    for capability in capabilities:
      self.assertTrue(self.uut.is_capability_initialized(capability))

    self.uut.reset_all_capabilities()

    for capability in capabilities:
      self.assertFalse(self.uut.is_capability_initialized(capability))

  def test_665_get_capability_classes(self):
    """Test that get_capability_classes() returns capability flavors."""
    self.assertEqual(
        self.uut.get_capability_classes("switchboard"),
        [switchboard.SwitchboardDefault])
    self.assertEqual(
        self.uut.get_capability_classes("event_parser"),
        [event_parser_default.EventParserDefault])

  def test_670_no_reference_loops(self):
    """Test that deleting last reference to object deletes the object.

    If there are any reference loops, the object will not be deleted
    immediately (synchronously), and will be destroyed by periodic GC later
    (asynchronously).
    """
    args = (self.mock_manager, self.device_config)
    kwargs = {"log_directory": self.artifacts_directory}
    self.verify_no_reference_loops(GazooDeviceBaseStub, args, kwargs)

  def test_1120_check_device_connected_works(self):
    """Verify check_device_connected() calls device.is_connected()."""
    self.check_device_connected_patch_primary.stop()
    try:
      with mock.patch.object(
          self.uut, "is_connected", autospec=True) as mock_is_connected:
        mock_is_connected.return_value = True
        self.uut.check_device_connected()

        mock_is_connected.return_value = False
        with self.assertRaises(errors.DeviceNotConnectedError):
          self.uut.check_device_connected()
        mock_is_connected.assert_called()
    finally:
      self.check_device_connected_patch_primary.start()

  def test_1130_persistent_props_works(self):
    """Verify get_persistent_properties() works."""
    expected_dict = {
        "commands": {},
        "timeouts": {
            "CONNECTED": 3,
            "POWER_CYCLE": 2,
            "SHELL": 60
        },
        "DETECT_MATCH_CRITERIA": None,
        "communication_address": "la",
        "COMMUNICATION_TYPE": "SshComms",
        "DEVICE_TYPE": "devicestub",
        "health_checks": [],
        "os": "Linux",
        "platform": "SomethingPlatform",
        "regexes": {},
        "model": "Development",
        "name": "devicestub-1234",
        "serial_number": "123456",
        "owner": ""
    }
    self.assertEqual(self.uut.get_persistent_properties(), expected_dict)

  def test_1131_settable_props_works(self):
    """Verify get_optional_properties() works."""
    expected_dict = {"alias": None}
    self.assertEqual(self.uut.get_optional_properties(), expected_dict)

  def test_1132_dynamic_props_works(self):
    """Dynamic props works even when some property values are bad."""
    # Since log_file_name changes every run, can't assert on values.

    expected_keys = [
        "firmware_type", "firmware_version", "connected", "log_file_name",
        "bad_property", "dynamic_bad", "event_parser.healthy",
        "switchboard.healthy", "switchboard.number_transports"
    ]
    self.assertCountEqual(expected_keys,
                          list(self.uut.get_dynamic_properties().keys()))

  def test_1333_get_property_handles_capability_properties(self):
    """Verify get_property() handles capability (nested) properties."""
    self.uut.usb_hub = usb_hub_default.UsbHubDefault(
        device_name=self.uut.name,
        manager_weakref=weakref.ref(self.mock_manager),
        hub_name="cambrionix-1234",
        device_port=1,
        get_switchboard_if_initialized=lambda: self.mock_switchboard)
    self.assertEqual(self.uut.get_property("usb_hub.name"), "cambrionix-1234")

  def test_1334_get_property_handles_bad_properties_raise_error_off(self):
    """Verify get_property() returns a placeholder when the property raises."""
    self.assertIn(
        "devicestub-1234 does not have a known property 'fimware_version'. "
        "Close matches:",
        self.uut.get_property("fimware_version"))
    self.assertEqual(
        self.uut.get_property("bad_property"), "Exception_DeviceError")

  def test_1335_get_property_handles_bad_properties_raise_error_on(self):
    """Verify get_property() raises an error when the property raises."""
    with self.assertRaisesRegex(AttributeError, "fimware_version"):
      self.uut.get_property("fimware_version", raise_error=True)
    with self.assertRaisesRegex(errors.DeviceError, "x"):
      self.uut.get_property("bad_property", raise_error=True)

  def test_1340_recover_raises_error(self):
    """Test recover() raising the error."""
    error = errors.CheckDeviceReadyError(self.uut.name, "")
    with self.assertRaisesRegex(errors.CheckDeviceReadyError, str(error)):
      self.uut.recover(error)

  def test_1341_recover_comm_power(self):
    """Test recovery from SwitchboardCreationError with comm_power."""
    self.uut.reset_capability("switchboard")
    with mock.patch.object(
        gazoo_device_base.GazooDeviceBase, "has_capabilities",
        return_value=True) as mock_has_capabilities:
      self.uut.comm_power = mock.Mock(spec=comm_power_default.CommPowerDefault)
      error = errors.SwitchboardCreationError(self.uut.name, "FtdiError")
      self.uut.recover(error)
      self.uut.comm_power.cycle.assert_called_once()
      mock_has_capabilities.assert_called_once()

  def test_1342_recover_no_comm_power_raises_error(self):
    """Test recovery from SwitchboardCreationError without comm_power."""
    self.uut.reset_capability("switchboard")
    with mock.patch.object(
        gazoo_device_base.GazooDeviceBase, "has_capabilities",
        return_value=False) as mock_has_capabilities:
      error = errors.SwitchboardCreationError(self.uut.name, "FtdiError")
      with self.assertRaisesRegex(errors.SwitchboardCreationError, str(error)):
        self.uut.recover(error)
      mock_has_capabilities.assert_called_once()

  def test_1343_recover_comm_power_unconfigured(self):
    """Test recovery with comm_power unconfigured."""
    self.uut.reset_capability("switchboard")
    with mock.patch.object(
        gazoo_device_base.GazooDeviceBase,
        "has_capabilities",
        return_value=True):
      self.uut.comm_power = mock.Mock(spec=comm_power_default.CommPowerDefault)
      self.uut.comm_power.cycle.side_effect = errors.CapabilityNotReadyError(
          "device", "Error")
      error = errors.SwitchboardCreationError(self.uut.name, "FtdiError")
      with self.assertRaisesRegex(errors.SwitchboardCreationError, str(error)):
        self.uut.recover(error)


class GazooDeviceCapabilityTests(fake_device_test_case.FakeDeviceTestCase):
  """Unit tests for capability methods in gazoo_device_base.py."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements("devicestub-1234")
    self.device_config["persistent"]["console_port_name"] = "la"

    supported_interface_patcher = mock.patch.dict(
        extensions.capability_interfaces,
        fake_capabilities.SUPPORTED_INTERFACES)
    supported_interface_patcher.start()
    self.addCleanup(supported_interface_patcher.stop)

    supported_flavor_patcher = mock.patch.dict(
        extensions.capability_flavors,
        fake_capabilities.SUPPORTED_FLAVORS)
    supported_flavor_patcher.start()
    self.addCleanup(supported_flavor_patcher.stop)

    supported_capability_patcher = mock.patch.dict(
        extensions.capabilities,
        fake_capabilities.CAPABILITIES)
    supported_capability_patcher.start()
    self.addCleanup(supported_capability_patcher.stop)

    self.gazoo_device_base_capabilities = {
        event_parser_default.EventParserDefault, switchboard.SwitchboardDefault
    }
    self.gazoo_device_base_capability_names = [
        capability.get_capability_name()
        for capability in self.gazoo_device_base_capabilities
    ]

    self.uut = GazooDeviceBaseStub(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory)

  def test_671_get_supported_capability_flavors(self):
    """Test successful get_supported_capability_flavors() calls."""
    fc = fake_capabilities
    test_cases = [
        (fc.DeviceNoCapabilities, set()),
        (fc.DeviceOneFlavorCapability, set([fc.ValidCapabilityFlavor])),
        (fc.DeviceOneFlavorCapabilityList, set([fc.ValidCapabilityFlavor])),
        (fc.DeviceParentFlavorCapability, set([fc.ValidParentCapabilityFlavor
                                              ])),
        (fc.DeviceChildFlavorCapability, set([fc.ValidChildCapabilityFlavor])),
        (fc.DeviceMultipleFlavorsCapabilityList,
         set([fc.ValidCapabilityFlavor, fc.ValidCapabilityFlavor1])),
        (fc.DeviceMultipleFlavorsCapabilityTuple,
         set([fc.ValidCapabilityFlavor, fc.ValidCapabilityFlavor1])),
        (fc.DeviceMultipleCapabilities,
         set([fc.ValidCapabilityFlavor, fc.ValidOtherCapabilityFlavor])),
        (fc.DeviceMultipleCapabilitiesMultipleFlavors,
         set([
             fc.ValidCapabilityFlavor, fc.ValidCapabilityFlavor1,
             fc.ValidOtherCapabilityFlavor
         ]))
    ]

    for device_class, expected_capability_flavors in test_cases:
      expected_capability_flavors = expected_capability_flavors.union(
          self.gazoo_device_base_capabilities)
      actual_capability_flavors = device_class.get_supported_capability_flavors(
      )
      self.assertEqual(
          actual_capability_flavors, expected_capability_flavors,
          (f"Expected {device_class}.get_supported_capability_flavors() to "
           f"return {expected_capability_flavors}, found "
           f"{actual_capability_flavors}"))

  def test_672_get_supported_capabilities(self):
    """Test successful get_supported_capabilities() calls."""
    fc = fake_capabilities
    test_cases = [
        (fc.DeviceNoCapabilities, []),
        (fc.DeviceOneFlavorCapability, [fc.VALID_CAPABILITY_NAME]),
        (fc.DeviceOneFlavorCapabilityList, [fc.VALID_CAPABILITY_NAME]),
        (fc.DeviceParentFlavorCapability, [fc.PARENT_CAPABILITY_NAME]),
        (fc.DeviceChildFlavorCapability, [fc.CHILD_CAPABILITY_NAME]),
        (fc.DeviceMultipleFlavorsCapabilityList, [fc.VALID_CAPABILITY_NAME]),
        (fc.DeviceMultipleFlavorsCapabilityTuple, [fc.VALID_CAPABILITY_NAME]),
        (fc.DeviceMultipleCapabilities,
         sorted([fc.VALID_CAPABILITY_NAME, fc.OTHER_VALID_CAPABILITY_NAME])),
        (fc.DeviceMultipleCapabilitiesMultipleFlavors,
         sorted([fc.VALID_CAPABILITY_NAME, fc.OTHER_VALID_CAPABILITY_NAME]))
    ]

    for device_class, expected_capability_names in test_cases:
      expected_capability_names = sorted(
          expected_capability_names + self.gazoo_device_base_capability_names)
      actual_capability_names = device_class.get_supported_capabilities()
      self.assertEqual(
          actual_capability_names, expected_capability_names,
          "Expected {}.get_supported_capabilities() to return {}, found {}"
          .format(device_class, expected_capability_names,
                  actual_capability_names))

  def test_673_has_capabilities_error_invalid_type(self):
    """Test that has_capabilities() raises if input is not a list of strings."""
    test_cases = [
        "foo_capability", fake_capabilities.ValidCapabilityBase,
        fake_capabilities.ValidCapabilityFlavor,
        ["capability_1", "capability_2", fake_capabilities.ValidCapabilityBase]
    ]

    for capability in test_cases:
      with self.assertRaisesRegex(errors.DeviceError, "type"):
        fake_capabilities.DeviceOneFlavorCapability.has_capabilities(capability)

  def test_674_has_capabilities_error_unknown_capability_name(self):
    """Test that has_capabilities() raises if capability is not supported."""
    capability = "foo_bar_baz"
    with self.assertRaisesRegex(
        errors.DeviceError,
        "Capability {} is not recognized.".format(capability)):
      fake_capabilities.DeviceOneFlavorCapability.has_capabilities([capability])

  def test_675_has_capabilities(self):
    """Test successful has_capabilities() calls."""
    fc = fake_capabilities
    get_interface_name = fake_capabilities.get_interface_name
    get_flavor_name = fake_capabilities.get_flavor_name

    # Test "suite" is a map: device class -> list of test cases for that device
    # class. Each test case is a tuple of
    # (capability_names, expected_return_value).
    # capability_names (list of strings) is the input to has_capabilities()
    # call. expected_return_value is a bool (whether all capability_names are
    # supported by the device class).
    all_test_cases = {
        fc.DeviceNoCapabilities: [
            ([], True),
            ([get_flavor_name(fc.ValidCapabilityFlavor)], False),
            ([get_interface_name(fc.ValidCapabilityBase)], False),
            ([fc.VALID_CAPABILITY_NAME], False),
        ],
        fc.DeviceOneFlavorCapability: [
            ([], True), ([fc.VALID_CAPABILITY_NAME], True),
            ([get_interface_name(fc.ValidCapabilityBase)], True),
            ([get_flavor_name(fc.ValidCapabilityFlavor)], True),
            ([
                fc.VALID_CAPABILITY_NAME,
                get_interface_name(fc.ValidCapabilityBase),
                get_flavor_name(fc.ValidCapabilityFlavor)
            ], True),
            ((fc.VALID_CAPABILITY_NAME,
              get_interface_name(fc.ValidCapabilityBase),
              get_flavor_name(fc.ValidCapabilityFlavor)), True),
            (set([
                fc.VALID_CAPABILITY_NAME,
                get_interface_name(fc.ValidCapabilityBase),
                get_flavor_name(fc.ValidCapabilityFlavor)
            ]), True), ([fc.OTHER_VALID_CAPABILITY_NAME], False),
            ([get_interface_name(fc.ValidOtherCapabilityBase)], False),
            ([get_flavor_name(fc.ValidOtherCapabilityFlavor)], False),
            ([fc.VALID_CAPABILITY_NAME, fc.OTHER_VALID_CAPABILITY_NAME], False)
        ],
        fc.DeviceOneFlavorCapabilityList: [
            ([], True), ([fc.VALID_CAPABILITY_NAME], True),
            ([get_interface_name(fc.ValidCapabilityBase)], True),
            ([get_flavor_name(fc.ValidCapabilityFlavor)], True),
            ([
                fc.VALID_CAPABILITY_NAME,
                get_interface_name(fc.ValidCapabilityBase),
                get_flavor_name(fc.ValidCapabilityFlavor)
            ], True), ([fc.OTHER_VALID_CAPABILITY_NAME], False),
            ([get_interface_name(fc.ValidOtherCapabilityBase)], False),
            ([get_flavor_name(fc.ValidOtherCapabilityFlavor)], False)
        ],
        fc.DeviceParentFlavorCapability: [
            ([get_flavor_name(fc.ValidParentCapabilityFlavor)], True),
            ([get_interface_name(fc.ValidParentCapabilityBase)], True),
            ([fc.PARENT_CAPABILITY_NAME], True),
            ([get_flavor_name(fc.ValidChildCapabilityFlavor)], False),
            ([get_interface_name(fc.ValidChildCapabilityBase)], False),
            ([fc.CHILD_CAPABILITY_NAME], False)
        ],
        fc.DeviceChildFlavorCapability: [
            ([get_flavor_name(fc.ValidParentCapabilityFlavor)], False),
            ([get_interface_name(fc.ValidParentCapabilityBase)], True),
            ([fc.PARENT_CAPABILITY_NAME], True),
            ([get_flavor_name(fc.ValidChildCapabilityFlavor)], True),
            ([get_interface_name(fc.ValidChildCapabilityBase)], True),
            ([fc.CHILD_CAPABILITY_NAME], True)
        ],
        fc.DeviceMultipleFlavorsCapabilityList: [
            ([], True),
            ([
                get_flavor_name(fc.ValidCapabilityFlavor),
                get_flavor_name(fc.ValidCapabilityFlavor1)
            ], True), ([get_interface_name(fc.ValidCapabilityBase)], True),
            ([fc.VALID_CAPABILITY_NAME], True),
            ([get_interface_name(fc.ValidOtherCapabilityBase)], False)
        ],
        fc.DeviceMultipleFlavorsCapabilityTuple: [
            ([], True),
            ([
                get_flavor_name(fc.ValidCapabilityFlavor),
                get_flavor_name(fc.ValidCapabilityFlavor1)
            ], True), ([get_interface_name(fc.ValidCapabilityBase)], True),
            ([fc.VALID_CAPABILITY_NAME], True),
            ([get_interface_name(fc.ValidOtherCapabilityBase)], False)
        ],
        fc.DeviceMultipleCapabilities: [
            ([], True),
            ([fc.VALID_CAPABILITY_NAME, fc.OTHER_VALID_CAPABILITY_NAME], True),
            ([
                get_flavor_name(fc.ValidCapabilityFlavor),
                get_flavor_name(fc.ValidOtherCapabilityFlavor)
            ], True),
            ([fc.VALID_CAPABILITY_NAME,
              get_interface_name(fc.ValidOtherCapabilityBase)], True),
            ([fc.VALID_CAPABILITY_NAME,
              get_flavor_name(fc.ValidOtherCapabilityBase)], True),
            ([get_flavor_name(fc.ValidOtherCapabilityBase),
              fc.VALID_CAPABILITY_NAME], True),
            (set([
                fc.VALID_CAPABILITY_NAME, fc.OTHER_VALID_CAPABILITY_NAME,
                fc.PARENT_CAPABILITY_NAME
            ]), False),
        ],
        fc.DeviceMultipleCapabilitiesMultipleFlavors: [
            ([
                get_flavor_name(fc.ValidCapabilityFlavor),
                get_flavor_name(fc.ValidCapabilityFlavor1),
                get_flavor_name(fc.ValidOtherCapabilityFlavor)
            ], True),
            ([
                get_interface_name(fc.ValidCapabilityBase),
                get_flavor_name(fc.ValidOtherCapabilityFlavor)
            ], True),
            ([
                fc.VALID_CAPABILITY_NAME,
                get_flavor_name(fc.ValidOtherCapabilityFlavor)
            ], True),
            ([fc.VALID_CAPABILITY_NAME, fc.OTHER_VALID_CAPABILITY_NAME], True),
            ([
                fc.VALID_CAPABILITY_NAME, fc.OTHER_VALID_CAPABILITY_NAME,
                fc.PARENT_CAPABILITY_NAME
            ], False)
        ],
        fc.DeviceNonConformingNameFlavor: [
            ((get_flavor_name(fc.NonConformingInterfaceNameFlavor),), True),
            ([get_interface_name(
                fc.NonConformingCapabilityInterfaceNameWithOverride)],
             True), (set([fc.NONCONFORMING_CAPABILITY_NAME]), True)
        ]
    }

    for device_class, test_cases in all_test_cases.items():
      for capability_names, expected_return_value in test_cases:
        actual_return_value = device_class.has_capabilities(capability_names)
        self.assertEqual(
            actual_return_value, expected_return_value,
            "Expected {}.has_capabilities({}) to return {}, found {}".format(
                device_class, capability_names, expected_return_value,
                actual_return_value))


if __name__ == "__main__":
  fake_device_test_case.main()
