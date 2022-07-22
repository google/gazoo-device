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
"""Tests for auxiliary device base class."""
from unittest import mock

from absl.testing import parameterized
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device.base_classes import auxiliary_device
from gazoo_device.capabilities import usb_hub_default
from gazoo_device.switchboard import switchboard
from gazoo_device.tests.unit_tests.device_mixin_tests import common_test
from gazoo_device.tests.unit_tests.utils import fake_device_test_case


class AuxDevTester(auxiliary_device.AuxiliaryDevice):
  """Stub class that implements abstract methods and properties."""
  COMMUNICATION_TYPE = "SshComms"
  _COMMUNICATION_KWARGS = {}
  _OWNER_EMAIL = "gdm-authors@google.com"
  DEVICE_TYPE = "aux"
  logger = auxiliary_device.logger

  def get_console_configuration(self):
    return None

  @property
  def some_property(self):
    return "something"

  @property
  def bad_property(self):
    raise errors.DeviceError("x")

  def get_detection_info(self):
    raise errors.DeviceError(
        "get_detection_info is not implemented by AuxDevTester.")

  @classmethod
  def is_connected(cls, device_config):
    return True

  def reboot(self, no_wait=False, method="shell"):
    pass

  def recover(self, error):
    pass

  def check3(self):
    """Fake health check 3.

    Raises:
      DeviceError: for testing.
    """
    raise errors.DeviceError("health check failed")

  def shell(self,
            command,
            command_name="shell",
            timeout=1,
            port=0,
            include_return_code=False):
    """Mock shell methods.

    Args:
       command (str): no op.
       command_name (str): no op.
       timeout (float): no op.
       port (int): no op.
       include_return_code (bool): no op.

    Raises:
        DeviceError: if timeout is 0.

    Returns:
        str: no op.
    """
    if timeout == 0:
      raise errors.DeviceError("command_name: {}. "
                               "Test timeout error.".format(command_name))
    return "NCC-1701"

  @decorators.CapabilityDecorator(switchboard.SwitchboardDefault)
  def switchboard(self):
    """Instance for communicating with the device."""
    switchboard_name = self._get_private_capability_name(
        switchboard.SwitchboardDefault)
    if not hasattr(self, switchboard_name):
      switchboard_kwargs = self._COMMUNICATION_KWARGS.copy()
      switchboard_kwargs.update({
          "communication_address": self.communication_address,
          "communication_type": self.COMMUNICATION_TYPE,
          "log_path": self.log_file_name,
          "device_name": self.name,
          "event_parser": None
      })
      setattr(self, switchboard_name,
              self.get_manager().create_switchboard(**switchboard_kwargs))

    return getattr(self, switchboard_name)


class TestAuxiliaryDevice(fake_device_test_case.FakeDeviceTestCase,
                          common_test.CommonTestMixin):
  """Tests for auxiliary_device.py."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements("aux-device-1234")
    self.uut = AuxDevTester(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory)

  def test_alias(self):
    """Tests alias property."""
    alias = "aux-dev-base-1234"
    self.uut.props["optional"]["alias"] = alias
    self.assertEqual(self.uut.alias, alias)

  def test_communication_address(self):
    """Tests communication_address property."""
    comm_addr = "aux-console-port"
    self.uut.props["persistent_identifiers"]["console_port_name"] = comm_addr
    self.assertEqual(self.uut.communication_address, comm_addr)

  def test_model(self):
    """Tests model property."""
    model = "aux-model"
    self.uut.props["persistent_identifiers"]["model"] = model
    self.assertEqual(self.uut.model, model)

  def test_name(self):
    """Tests name property."""
    name = "aux-name-1234"
    self.uut.props["persistent_identifiers"]["name"] = name
    self.assertEqual(self.uut.name, name)

  def test_serial_number(self):
    """Tests serial_number property."""
    serial_number = "aux-1234-abcd-5678"
    self.uut.props["persistent_identifiers"]["serial_number"] = serial_number
    self.assertEqual(self.uut.serial_number, serial_number)

  def test_command_with_regex(self):
    """Verify shell with regex is successful."""
    result = self.uut.command_with_regex("enterprise -serial", r"\S+[-](\d+)",
                                         self.uut.shell)
    self.assertEqual(result, "1701")

  @mock.patch.object(
      AuxDevTester, "shell", side_effect=errors.DeviceError("Some error."))
  def test_command_with_regex_throws_error(self, mock_shell):
    """Verify shell with regex throws error."""
    with self.assertRaisesRegex(errors.DeviceError, "unable to retrieve"):
      self.uut.command_with_regex(
          "enterprise -serial",
          r"\S+[-](\d+)",
          self.uut.shell,
          raise_error=True)

  @mock.patch.object(
      AuxDevTester, "shell", side_effect=errors.DeviceError("Some error."))
  def test_command_with_regex_just_logs_error(self, mock_shell):
    """Verify shell with regex just logs error."""
    result = self.uut.command_with_regex("enterprise -serial", r"\S+[-](\d+)",
                                         self.uut.shell)
    self.assertEqual(result, "")

  def test_command_with_regex_group_bigger_than_max(self):
    """Verify shell with regex just logs error."""
    result = self.uut.command_with_regex(
        "enterprise -serial", r"\S+[-](\d+)", self.uut.shell, regex_group=3)
    self.assertEqual(result, "")

  def test_get_regexes(self):
    """Tests regexes property."""
    self.assertEqual(self.uut.regexes, self.uut._regexes)

  def test_switchboard_returns_valid_object(self):
    """Verify a switchboard object is returned without error."""
    self.assertIsNotNone(self.uut.switchboard)

  def test_command_fn_kwargs_are_passed_to_shell(self):
    """Verify that named arguments are passed to the test shell method."""
    with self.assertRaises(errors.DeviceError):
      self.uut.command_with_regex(
          "enterprise -serial",
          r"\S+[-](\d+)",
          self.uut.shell,
          regex_group=3,
          raise_error=True,
          timeout=0)

  def test_check_device_connected_works(self):
    """Verify check_device_connected() works."""
    self.check_device_connected_patch_auxiliary.stop()
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
      self.check_device_connected_patch_auxiliary.start()

  def test_device_does_not_have_fake_capability(self):
    """Verify that has_capability returns False for a fake capability."""
    with self.assertRaisesRegex(errors.DeviceError, "not recognized"):
      self.uut.has_capabilities(["fake_capabiltiy"])

  def test_has_capabilities_invalid_type(self):
    """Verify that an invalid type raises an exception."""
    with self.assertRaisesRegex(errors.DeviceError, "string type"):
      self.uut.has_capabilities([10])

  def test_has_capabilities_invalid_type_not_list(self):
    """Verify that an invalid type raises an exception."""
    with self.assertRaisesRegex(errors.DeviceError, "Invalid type"):
      self.uut.has_capabilities("not_a_list")

  def test_supported_capabilities(self):
    supported_list = self.uut.get_supported_capabilities()
    self.assertIn("switchboard", supported_list)

  def test_reset_all_capabilities(self):
    """Verify able to reset capability."""
    self.assertTrue(self.uut.switchboard)
    self.assertTrue(self.uut.is_capability_initialized("switchboard"))
    self.uut.reset_all_capabilities()
    self.assertFalse(self.uut.is_capability_initialized("switchboard"))

  def test_is_capability_initialized_valid_capability(self):
    """Test is_capability_initialized() with a valid capability."""
    self.assertTrue(self.uut.switchboard)  # Initialize Switchboard
    self.assertTrue(self.uut.is_capability_initialized("switchboard"))
    self.uut.reset_capability("switchboard")
    self.assertFalse(self.uut.is_capability_initialized("switchboard"))

  def test_is_capability_initialized_invalid_capability(self):
    """Test is_capability_initialized() raises for invalid capability."""
    err_regex = "Capability foobar is not recognized"
    with self.assertRaisesRegex(errors.DeviceError, err_regex):
      self.uut.is_capability_initialized("foobar")
    with self.assertRaisesRegex(errors.DeviceError, err_regex):
      self.uut.reset_capability("foobar")

  def test_is_capability_initialized_unsupported_capability(self):
    """Test is_capability_initialized() raises for unsupported capability."""
    err_regex = "Capability file_transfer is not supported"
    with self.assertRaisesRegex(errors.DeviceError, err_regex):
      self.uut.is_capability_initialized("file_transfer")
    with self.assertRaisesRegex(errors.DeviceError, err_regex):
      self.uut.reset_capability("file_transfer")

  def test_get_capability_classes(self):
    """Test that get_capability_classes() returns capability flavors."""
    self.assertEqual(
        self.uut.get_capability_classes("switchboard"),
        [switchboard.SwitchboardDefault])

  def test_persistent_props_works(self):
    """Verify retrieving presistent props works."""
    expected_dict = {
        "DEVICE_TYPE": "aux",
        "serial_number": "123456",
        "DETECT_MATCH_CRITERIA": None,
        "commands": {},
        "health_checks": [self.uut.check_device_connected],
        "model": "Development",
        "communication_address": "123.456.78.9",
        "regexes": {},
        "timeouts": {
            "CONNECTED": 3,
            "SHELL": 60
        },
        "name": "aux-device-1234",
        "owner": "gdm-authors@google.com",
        "COMMUNICATION_TYPE": "SshComms"
    }
    self.assertEqual(self.uut.get_persistent_properties(), expected_dict)

  def test_optional_props_works(self):
    """Verify retrieving optional props works."""
    expected_dict = {"alias": None}

    self.assertEqual(self.uut.get_optional_properties(), expected_dict)

  def test_optional_props_saved_to_device_configs_at_manager(self):
    """Verify optional props saved to config at manager."""
    optional_prop = "optional1"
    self.uut.set_property(optional_prop, 123)
    self.uut.get_manager(
        ).save_property_to_config.assert_called_once_with(
            self.uut.name, optional_prop, 123)

  def test_dynamic_props_works(self):
    """Verify retrieving dynamic props works."""
    expected_keys = [
        "connected", "log_file_name", "switchboard.healthy",
        "switchboard.number_transports", "switchboard.health_checked"
    ]
    self.assertCountEqual(expected_keys,
                          list(self.uut.get_dynamic_properties().keys()))

  def test_get_property_handles_capability_properties(self):
    """Verify get_property can take in capability properties."""
    self.uut.usb_hub = usb_hub_default.UsbHubDefault(
        device_name=self.uut.name,
        get_manager=self.uut.get_manager,
        hub_name="cambrionix-1234",
        device_port=1,
        get_switchboard_if_initialized=lambda: self.mock_switchboard)
    self.assertEqual(self.uut.get_property("usb_hub.name"), "cambrionix-1234")

  def test_get_property_handles_bad_properties_raise_error_off(self):
    """Verify get_property handles inability to retrieve a specific property."""
    self.assertEqual(
        self.uut.get_property("some_propety"),
        "aux-device-1234 does not have a known property 'some_propety'. "
        "Close matches: ")
    self.assertEqual(
        self.uut.get_property("bad_property"), "Exception_DeviceError")

  def test_get_property_handles_bad_properties_raise_error_on(self):
    with self.assertRaisesRegexp(AttributeError, "some_propety"):
      self.uut.get_property("some_propety", raise_error=True)
    with self.assertRaisesRegex(errors.DeviceError, "x"):
      self.uut.get_property("bad_property", raise_error=True)

  def test_get_property_raises_for_method(self):
    """Verify get_property raises an error for methods."""
    with self.assertRaisesRegex(errors.DeviceError,
                                "make_device_ready is a method"):
      self.uut.get_property("make_device_ready", raise_error=True)

  @parameterized.named_parameters(("one_user_without_force", 1, False, True),
                                  ("many_users_without_force", 5, False, False),
                                  ("many_users_with_force", 5, True, True))
  def test_close_auxiliary_device(self, user_count: int, force: bool,
                                  should_release_resources: bool):
    """Tests whether close() releases resources depending on the user count."""
    self.uut._user_count = user_count
    with mock.patch.object(self.uut, "_close") as mock_close:
      self.uut.close(force=force)
    if should_release_resources:
      mock_close.assert_called_once()
    else:
      mock_close.assert_not_called()

  @parameterized.named_parameters(("one_user", 1), ("many_users", 5))
  def test_del_auxiliary_device(self, user_count: int):
    """Tests that __del__ releases resources regardless of the user count."""
    self.uut._user_count = user_count
    mock_close = mock.MagicMock(spec=self.uut._close)
    # Note: can't use a "with mock.patch.object" context manager here as it
    # stores a reference to the instance method (and therefore to self.uut),
    # preventing garbage collection.
    self.uut._close = mock_close
    del self.uut
    mock_close.assert_called_once()

  @parameterized.named_parameters(("str", str), ("repr", repr))
  def test_str_handle_no_props(self, test_func):
    """Tests that __str__ and __repr__ handle missing props attribute."""
    with mock.patch.object(
        auxiliary_device.AuxiliaryDevice,
        "name",
        new_callable=mock.PropertyMock) as mock_name:
      mock_name.side_effect = AttributeError
      self.assertNotIn(
          "aux-device-1234", test_func(self.uut),
          f"AuxiliaryDevice.__{test_func.__name__}__ does not have correct "
          "format")

  @parameterized.named_parameters(("str", str), ("repr", repr))
  def test_str_format(self, test_func):
    """Tests that __str__ and __repr__ have correct format."""
    self.assertIn(
        "<aux-device-1234", test_func(self.uut),
        f"AuxiliaryDevice.__{test_func.__name__}__ does not have correct "
        "format")

  @mock.patch.object(auxiliary_device, "issubclass", return_value=True)
  def test_get_property_names_skip_matter_endpoints(self, mock_issubclass):
    """Verifies _get_property_names skipping Matter endpoints."""
    self.assertEqual(0, len(self.uut._get_property_names("")))


if __name__ == "__main__":
  fake_device_test_case.main()
