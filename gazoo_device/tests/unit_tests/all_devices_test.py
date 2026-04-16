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

"""Checks expectations of all GDM device classes for architecture requirements."""
import socket
import sys
from unittest import mock

from gazoo_device import console_config
from gazoo_device import device_types
from gazoo_device import errors
from gazoo_device import gazoo_device_controllers
from gazoo_device import manager
from gazoo_device import mobly_controller
from gazoo_device import package_registrar
from gazoo_device import version
from gazoo_device.auxiliary_devices import yepkit
from gazoo_device.switchboard.transports import pigweed_rpc_transport
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import conformance_utils
import serial

package_registrar.register(gazoo_device_controllers)

_NON_SWITCHBOARD_CLASSES = (
    "NRF52840",
    "EFR32",
    "ESP32",
)

_EXCLUDED_NON_MATCHING_SIGNATURE_METHODS = (
    "send",  # TODO(gdm-authors) Move into capability
    "send_and_expect"  # TODO(gdm-authors) Move into capability
)


def _create_device_instances(device_classes, manager_instance, log_directory):
  """Creates a device instance for each device class."""
  device_instances = []
  for device_class in device_classes:
    if "Jlink" in device_class.COMMUNICATION_TYPE.__name__:
      communication_address = (
          "/dev/serial/by-id/usb-SEGGER_J-Link_000050130117-if00")
    elif "Adb" in device_class.COMMUNICATION_TYPE.__name__:
      communication_address = "123abcde"
    else:
      communication_address = (
          "/dev/serial/by-id/usb-FTDI_FT230X_Basic_UART_1234-if02-port0")
    device_config = {
        "persistent": {
            "name": "unknown",
            "console_port_name": communication_address,
        },
        "options": {},
        "make_device_ready": "on",
    }
    with mock.patch.object(yepkit, "_check_yepkit_enabled"):
      device_instances.append(
          device_class(  # pytype: disable=not-instantiable
              manager=manager_instance,
              device_config=device_config,
              log_directory=log_directory,
              log_file_name="unknown_switchboard.txt"))

  return device_instances


class TestAllDevices(unit_test_case.UnitTestCase):
  """Unit tests which run on all supported GDM device classes."""
  MANAGER_INSTANCE: manager.Manager
  _DEVICE_CLASS_MODULE_PREFIX = "gazoo_device"
  _ALL_DEVICE_CLASSES: tuple[type[device_types.Device]]
  _ALL_DEVICE_INSTANCES: tuple[device_types.Device]

  @classmethod
  def setUpClass(cls):
    super().setUpClass()

    cls.MANAGER_INSTANCE = manager.Manager()
    cls._ALL_DEVICE_CLASSES = tuple(
        device_class
        for device_class in manager.Manager.get_all_supported_device_classes()
        if device_class.__module__.startswith(cls._DEVICE_CLASS_MODULE_PREFIX))
    cls._ALL_DEVICE_INSTANCES = tuple(
        _create_device_instances(
            cls._ALL_DEVICE_CLASSES,
            cls.MANAGER_INSTANCE,
            cls.artifacts_directory))

  @classmethod
  def tearDownClass(cls):
    cls.MANAGER_INSTANCE.close()
    super().tearDownClass()

  @classmethod
  def _get_expected_mobly_controller_config_name(cls, device_type: str) -> str:
    """Returns the expected MOBLY_CONTROLLER_CONFIG_NAME."""
    return mobly_controller.get_mobly_controller_config_name(device_type)

  def test_validate_api_decorators(self):
    """Ensures all public APIs with return values are wrapped with LogDecorator.

    Decorator syntax: @LogDecorator(your_logger, log_level)
    Public APIs with a return value do not need to be decorated.
    """
    for device_class in self._ALL_DEVICE_CLASSES:
      with self.subTest(device_class=device_class.__name__):
        incompliant_apis = conformance_utils.get_log_decorator_violators(
            device_class)
        self.assertFalse(
            incompliant_apis,
            "Public APIs have not been decorated with "
            f"@decorators.LogDecorator(logger): {incompliant_apis}")

  def test_validate_api_signatures(self):
    """Tests that all derived classes do not override parent signatures."""
    for device_class in self._ALL_DEVICE_CLASSES:
      with self.subTest(device_class=device_class.__name__):
        mismatches_str_list = (
            conformance_utils.get_mismatching_signature_err_strs(
                self._ALL_DEVICE_CLASSES,
                _EXCLUDED_NON_MATCHING_SIGNATURE_METHODS))
        self.assertFalse(
            mismatches_str_list,
            "Inherited method API signatures are overridden.\n"
            "Make sure the API signature of the child class starts with the "
            "parent signature.\n{}".format("\n".join(mismatches_str_list)))

  def test_validate_capability_definitions(self):
    """Ensures all capability definitions in device classes are valid."""
    for device_class in self._ALL_DEVICE_CLASSES:
      with self.subTest(device_class=device_class.__name__):
        invalid_definitions = (
            conformance_utils.get_invalid_capability_definitions(device_class))
        self.assertFalse(
            invalid_definitions,
            "{} failed capability definition verification.\n{}"
            .format(device_class,
                    "\n".join(f"Capability {cap!r}: {err}"
                              for cap, err in invalid_definitions)))

  def test_validate_devices_do_not_define_new_public_methods(self):
    """Ensures that device classes do not define public methods.

    The only allowed public methods are:
      * the ones required by base_classes/primary_device_base.py;
      * the ones added in base_classes/nest_device_base.py;
      * health checks;
      * deprecated aliases.

    All other public functionality in device classes must be implemented as
    capabilities.
    """
    for device_class in self._ALL_DEVICE_CLASSES:
      with self.subTest(device_class=device_class.__name__):
        incompliant_attrs = conformance_utils.get_invalid_public_methods(
            device_class, package_registrar.PUBLIC_METHOD_EXCEPTIONS)
        self.assertFalse(
            incompliant_attrs,
            "Defining public device class methods is not allowed. "
            "Public features should go into capabilities instead. "
            f"Public device class methods: {incompliant_attrs}")

  def test_validate_properties_are_categorized(self):
    """Ensures that device classes have their properties in specific categories.

    Categories:
      * Capability
      * PersistentProperty
      * OptionalProperty
      * DynamicProperty
    See nest_device.decorators for more information.
    """
    for device_class in self._ALL_DEVICE_CLASSES:
      with self.subTest(device_class=device_class.__name__):
        uncategorized_properties = (
            conformance_utils.get_uncategorized_properties(device_class))
        self.assertFalse(
            uncategorized_properties,
            "Device class {} has uncategorized public properties {}. Each "
            "public property must be categorized as Persistent, Optional, "
            "Dynamic, or a Capability.".format(device_class,
                                               uncategorized_properties))

  def test_validate_required_device_class_constants_set(self):
    """Ensures device classes have appropriate class properties set."""
    for device_class in self._ALL_DEVICE_CLASSES:
      with self.subTest(device_class=device_class.__name__):
        missing_constants = conformance_utils.get_unset_constants(device_class)
        self.assertFalse(
            missing_constants,
            f"Class constants {missing_constants} are not set.")

  def test_validate_health_check_naming(self):
    """Ensures that all health checks adhere to "check_<...>" naming."""
    for device_class in self._ALL_DEVICE_CLASSES:
      with self.subTest(device_class=device_class.__name__):
        incompliant_attrs = conformance_utils.get_invalid_health_check_names(
            device_class)
        self.assertFalse(
            incompliant_attrs,
            "Health checks must follow check_<...>' naming convention. "
            f"Non-conformant health checks: {incompliant_attrs}")

  def test_console_configurations(self):
    """Ensures that all devices define a valid console configuration."""
    self.mock_out_transports()
    self.mock_out_usb_utils_methods()
    for device in self._ALL_DEVICE_INSTANCES:
      with self.subTest(device_class=type(device).__name__):
        console_configuration = device.get_console_configuration()
        self.assertIsInstance(
            console_configuration,
            (type(None), console_config.ConsoleConfiguration),
            f"Unexpected console configuration type for {device}")

  @mock.patch.object(pigweed_rpc_transport, "isinstance", return_value=True)
  @mock.patch.object(socket, "socket")
  @mock.patch.object(serial, "Serial")
  def test_switchboard_initialization(
      self, mock_serial, mock_socket, mock_isinstance):
    """Tests all devices that have switchboards can initialize them."""
    self.mock_out_transports()
    self.mock_out_usb_utils_methods()
    for device in self._ALL_DEVICE_INSTANCES:
      with self.subTest(device_class=type(device).__name__):
        if (not device.has_capabilities(["switchboard"])
            or type(device).__name__ in _NON_SWITCHBOARD_CLASSES):
          continue

        try:
          self.logger.info(device.switchboard)
          if (hasattr(device, "_COMMUNICATION_KWARGS") and
              "locked_port_kwargs" in device._COMMUNICATION_KWARGS):
            device.switchboard.transport_tcp_raise_error_if_port_in_use(
                **device._COMMUNICATION_KWARGS["locked_port_kwargs"])

        except errors.SwitchboardCreationError as err:
          self.fail(f"{device}: {err}")

  def test_mobly_controller(self):
    """Tests that all device modules are valid Mobly controllers."""
    for device_class in self._ALL_DEVICE_CLASSES:
      module = sys.modules[device_class.__module__]
      with self.subTest(module=device_class.__module__):
        expected_controller_config_name = (
            self._get_expected_mobly_controller_config_name(
                device_class.DEVICE_TYPE))
        self.assertEqual(
            module.MOBLY_CONTROLLER_CONFIG_NAME,
            expected_controller_config_name)
        self.assertIs(module.create, mobly_controller.create)
        self.assertIs(module.destroy, mobly_controller.destroy)
        self.assertIs(module.get_info, mobly_controller.get_info)
        self.assertIs(module.get_manager, mobly_controller.get_manager)
        self.assertEqual(
            module.__version__,  # pytype: disable=attribute-error
            version.VERSION)

  def test_gdm_extension_package(self):
    """Tests that all device modules are valid GDM extension packages."""
    for device_class in self._ALL_DEVICE_CLASSES:
      module = sys.modules[device_class.__module__]
      with self.subTest(module=device_class.__module__):
        package_registrar.register(module)


if __name__ == "__main__":
  unit_test_case.main()
