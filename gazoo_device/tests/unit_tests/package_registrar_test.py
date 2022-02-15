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
"""Unit tests for package_registrar.py."""
import abc
import builtins
import importlib
import json
import os.path
import re
from unittest import mock

from gazoo_device import data_types
from gazoo_device import decorators
from gazoo_device import detect_criteria
from gazoo_device import errors
from gazoo_device import extensions
from gazoo_device import fire_manager
from gazoo_device import gdm_logger
from gazoo_device import package_registrar
from gazoo_device.base_classes import auxiliary_device
from gazoo_device.base_classes import gazoo_device_base
from gazoo_device.capabilities import event_parser_default
from gazoo_device.capabilities.interfaces import capability_base
from gazoo_device.switchboard import communication_types
from gazoo_device.tests.unit_tests.utils import fake_devices
from gazoo_device.tests.unit_tests.utils import unit_test_case
import immutabledict

logger = gdm_logger.get_logger()
_TEST_PACKAGE_NAME = "my_extension_package"
_TEST_PACKAGE_IMPORT_PATH = "parent_package." + _TEST_PACKAGE_NAME


class GoodCapabilityBase(capability_base.CapabilityBase):
  """A dummy valid capability interface class."""


class AbstractAuxiliaryDevice(auxiliary_device.AuxiliaryDevice):
  """Dummy abstract auxiliary device class."""

  @abc.abstractmethod
  def some_abstract_method(self):
    """Some abstract method to ensure the class is abstract."""


class AbstractPrimaryDevice(gazoo_device_base.GazooDeviceBase):
  """Dummy abstract primary device class."""

  @abc.abstractmethod
  def some_abstract_method(self):
    """Some abstract method to ensure the class is abstract."""


class AbstractVirtualDevice(gazoo_device_base.GazooDeviceBase):
  """Dummy abstract virtual device class."""

  @abc.abstractmethod
  def some_abstract_method(self):
    """Some abstract method to ensure the class is abstract."""


class AbstractCommunicationType(communication_types.CommunicationType):
  """Dummy abstract communication type class."""

  @abc.abstractmethod
  def some_abstract_method(self):
    """Some abstract method to ensure the class is abstract."""


class AbstractCapabilityFlavorDefault(GoodCapabilityBase):
  """Dummy abstract capability flavor class."""

  @abc.abstractmethod
  def some_abstract_method(self):
    """Some abstract method to ensure the class is abstract."""


class ClassNotInheritingFromInterface:
  """Class which does not inherit from any interface."""


class GoodCommunicationType(communication_types.CommunicationType):
  """A valid concrete communication type class."""

  @classmethod
  def get_comms_addresses(cls):
    return []

  def get_transport_list(self):
    del self  # Unused by the dummy implementation
    return []


class GoodQueryKey(detect_criteria.QueryEnum):
  """A valid detection query key type."""
  some_valid_query = "some_valid_query"
  another_valid_query = "another_valid_query"


class GoodPrimaryDevice(fake_devices.FakeGazooDeviceBase):
  DEVICE_TYPE = "some_primary_device"
  COMMUNICATION_TYPE = "GoodCommunicationType"
  DETECT_MATCH_CRITERIA = immutabledict.immutabledict(
      {GoodQueryKey.some_valid_query: "some_value"})
  _OWNER_EMAIL = "gdm-authors@google.com"


class GoodVirtualDevice(fake_devices.FakeGazooDeviceBase):
  """A dummy valid concrete virtual device class."""
  DEVICE_TYPE = "some_virtual_device"
  COMMUNICATION_TYPE = "GoodCommunicationType"
  DETECT_MATCH_CRITERIA = immutabledict.immutabledict(
      {GoodQueryKey.some_valid_query: "some_value"})
  _OWNER_EMAIL = "gdm-authors@google.com"


class GoodAuxiliaryDevice(auxiliary_device.AuxiliaryDevice):
  """A dummy valid concrete auxiliary device class."""
  DEVICE_TYPE = "some_auxiliary_device"
  COMMUNICATION_TYPE = "GoodCommunicationType"
  DETECT_MATCH_CRITERIA = immutabledict.immutabledict(
      {GoodQueryKey.some_valid_query: "some_value"})
  _OWNER_EMAIL = "gdm-authors@google.com"

  @decorators.LogDecorator(logger)
  def get_console_configuration(self):
    """Dummy get_console_configuration implementation: console not supported."""
    del self  # Unused because console is not supported.
    return None

  @classmethod
  def is_connected(cls, device_config):
    """Dummy is_connected() implementation."""
    return True

  @decorators.LogDecorator(logger)
  def recover(self, error):
    """Dummy recover implementation."""
    del self  # Unused by the dummy implementation

  @decorators.LogDecorator(logger)
  def get_detection_info(self):
    """Dummy get_detection_info() implementation."""
    del self  # Unused by the dummy implementation
    return {}, {}


class GoodCapabilityDefault(GoodCapabilityBase):
  """A dummy valid concrete capability flavor class."""


class CapabilityWithSameNameBase(capability_base.CapabilityBase):
  """Capability interface with same capability name as GoodCapabilityBase."""

  @classmethod
  def get_capability_name(cls):
    """Overrides the default capability name."""
    return GoodCapabilityBase.get_capability_name()


def good_detection_query(address, detect_logger, create_switchboard_func):
  """Dummy detection query with correct arguments."""
  # Unused: this is a dummy implementation
  del address, detect_logger, create_switchboard_func
  return True


def another_good_detection_query(address, detect_logger,
                                 create_switchboard_func):
  """Dummy detection query with correct arguments."""
  # Unused: this is a dummy implementation
  del address, detect_logger, create_switchboard_func
  return "foobar"


class BadPrimaryDeviceNoLogDecorator(GoodPrimaryDevice):
  """Primary device class which is missing LogDecorator on a method."""

  def factory_reset(self):
    """This method is missing LogDecorator."""


class BadPrimaryDeviceSignatureOverride(GoodPrimaryDevice):
  """Primary device class which is overriding signature for a method."""

  @decorators.LogDecorator(logger)
  def reboot(self):
    """This method is missing required "no_wait", "method" arguments."""


class BadPrimaryDeviceNewPublicMethod(GoodPrimaryDevice):
  """Primary device class which adds a new public method."""

  @decorators.LogDecorator
  def new_method(self):
    """This is a new public method."""


class BadPrimaryDeviceUncategorizedProperty(GoodPrimaryDevice):
  """Primary device class which adds an uncategorized property."""

  @property
  def new_property(self):
    """This is a new uncategorized (plain @property) property."""


class BadPrimaryDeviceMisnamedHealthCheck(GoodPrimaryDevice):
  """Primary device class which misnames a health check."""

  @decorators.health_check
  def misnamed_health_check(self):
    """All health checks should be prefixed with "check_<...>"."""


class BadPrimaryDeviceMissingClassConstants(fake_devices.FakeGazooDeviceBase):
  """Primary device class which misses several required class constants."""


class BadPrimaryDeviceMisnamedCapability(GoodPrimaryDevice):
  """Primary device class which defines a capability under a wrong name."""

  @decorators.CapabilityDecorator(event_parser_default.EventParserDefault)
  def wrong_name(self):
    """The capability must be defined as "event_parser"."""


GoodKey = data_types.KeyInfo(
    file_name="good_key",
    type=data_types.KeyType.SSH,
    package=_TEST_PACKAGE_NAME)
BadKeyMismatchingPackage = data_types.KeyInfo(
    file_name="bad_key",
    type=data_types.KeyType.SSH,
    package="mismatching_name")


class GoodManagerCliMixin(fire_manager.FireManager):
  """A valid CLI FireManager mixin class."""

  def some_cli_command(self):
    pass


class PackageRegistrarTests(unit_test_case.UnitTestCase):
  """Unit tests for package_registrar.py."""

  def setUp(self):
    super().setUp()
    self.mock_package = mock.MagicMock(
        spec=["__name__", "__version__", "export_extensions", "download_key"])
    self.mock_package.__name__ = _TEST_PACKAGE_IMPORT_PATH
    self.mock_package.__version__ = "0.0.1"
    self.mock_package.export_extensions.return_value = {}

  def test_register_package_without_version(self):
    """Test registering a package without __version__ attribute."""
    del self.mock_package.__version__
    error_regex = r"Expected __version__ to be a string, found None"
    with self.assertRaisesRegex(errors.PackageRegistrationError, error_regex):
      package_registrar.register(self.mock_package)

  def test_register_package_without_required_functions(self):
    """Test registering a package which does not define required functions."""
    del self.mock_package.export_extensions  # Missing function.
    self.mock_package.download_key = None  # Not a function.
    regex = r"Package must define functions.*download_key.*export_extensions"
    with self.assertRaisesRegex(errors.PackageRegistrationError, regex):
      package_registrar.register(self.mock_package)

  @mock.patch.object(
      extensions,
      "package_info",
      new={
          _TEST_PACKAGE_NAME:
              immutabledict.immutabledict({
                  "version": "0.0.1",
                  "key_download_function": lambda: None,
                  "import_path": _TEST_PACKAGE_IMPORT_PATH,
              })
      })
  def test_register_already_known_package(self):
    """Test registering package which has already been registered."""
    error_regex = r"Package 'my_extension_package' has already been registered"
    with self.assertRaisesRegex(errors.PackageRegistrationError, error_regex):
      package_registrar.register(self.mock_package)

  def test_register_not_a_class(self):
    """Test registering an object which is not a class."""
    test_cases = [
        "auxiliary_devices", "primary_devices", "virtual_devices",
        "communication_types", "capability_interfaces", "capability_flavors"
    ]
    for extension in test_cases:
      with self.subTest(extension=extension):
        self.mock_package.export_extensions.return_value = {
            extension: [None, "foo"]
        }
        with self.assertRaisesRegex(errors.PackageRegistrationError,
                                    r"must be class objects"):
          package_registrar.register(self.mock_package)

  def test_register_abstract_class(self):
    """Test registering an abstract class."""
    test_cases = [("auxiliary_devices", [AbstractAuxiliaryDevice]),
                  ("primary_devices", [AbstractPrimaryDevice]),
                  ("virtual_devices", [AbstractVirtualDevice]),
                  ("communication_types", [AbstractCommunicationType]),
                  ("capability_flavors", [AbstractCapabilityFlavorDefault])]
    for extension, extension_classes in test_cases:
      with self.subTest(
          extension=extension, extension_classes=extension_classes):
        self.mock_package.export_extensions.return_value = {
            extension: extension_classes
        }
        with self.assertRaisesRegex(errors.PackageRegistrationError,
                                    r"must not be abstract"):
          package_registrar.register(self.mock_package)

  def test_register_class_with_incorrect_base_class(self):
    """Test registering a class with unexpected base class."""
    test_cases = [("auxiliary_devices", auxiliary_device.AuxiliaryDevice),
                  ("primary_devices", gazoo_device_base.GazooDeviceBase),
                  ("virtual_devices", gazoo_device_base.GazooDeviceBase),
                  ("communication_types",
                   communication_types.CommunicationType),
                  ("capability_interfaces", capability_base.CapabilityBase),
                  ("capability_flavors", capability_base.CapabilityBase)]
    for extension, expected_base_class in test_cases:
      with self.subTest(
          extension=extension, expected_base_class=expected_base_class):
        self.mock_package.export_extensions.return_value = {
            extension: [ClassNotInheritingFromInterface]
        }
        regex = r"must be subclasses of {}".format(expected_base_class.__name__)
        with self.assertRaisesRegex(errors.PackageRegistrationError, regex):
          package_registrar.register(self.mock_package)

  @mock.patch.object(
      extensions,
      "communication_types",
      new={GoodCommunicationType.__name__: GoodCommunicationType})
  def test_register_duplicate_comm_type(self):
    """Test registering a duplicate communication type."""
    self.mock_package.export_extensions.return_value = {
        "communication_types": [GoodCommunicationType]
    }
    regex = (r"New communication types .*GoodCommunicationType.* have same "
             r"names \(\[.*GoodCommunicationType.*\]\) as existing "
             r"communication types .*GoodCommunicationType.*")
    with self.assertRaisesRegex(errors.PackageRegistrationError, regex):
      package_registrar.register(self.mock_package)

  @mock.patch.object(extensions, "primary_devices", new=[GoodPrimaryDevice])
  def test_register_duplicate_device_class(self):
    """Test registering a duplicate device class."""
    self.mock_package.export_extensions.return_value = {
        "primary_devices": [GoodPrimaryDevice]
    }
    regex = r"Device types.*some_primary_device.*are already defined in GDM"
    with self.assertRaisesRegex(errors.PackageRegistrationError, regex):
      package_registrar.register(self.mock_package)

  def test_register_nonconformant_device_class(self):
    """Test registering a device class which fails conformance checks."""
    err_template = (
        r"Failed to register package 'my_extension_package' with GDM "
        r"architecture\. The following device class\(es\) are incompliant with "
        r"GDM architecture:\n{cls}\n\t{err}")
    test_cases = (
        (BadPrimaryDeviceNoLogDecorator,
         (r"Public methods without return values must be decorated with "
          r"@decorators\.LogDecorator\(<logger>\)\. "
          r"Incompliant methods: \['factory_reset'\]")),
        (BadPrimaryDeviceSignatureOverride,
         (r"Methods may not fully override signatures inherited from parents\."
          r" Only extending the argument list is allowed\. Incompliant method "
          r"signatures: \[\"Method 'reboot', child signature "
          r".*BadPrimaryDeviceSignatureOverride\.reboot\(self\), inherited "
          r"signature\(s\) \['.*FakeGazooDeviceBase\.reboot\(self, no_wait, "
          r"method\)', '.*PrimaryDeviceBase.reboot\(self, no_wait, "
          r"method\)'\].\"\]")),
        (BadPrimaryDeviceNewPublicMethod,
         (r"New public methods are not allowed, except for health checks\. "
          r"Methods must either be private or, if public, moved into "
          r"capabilities\. Incompliant methods: \['new_method'\]")),
        (BadPrimaryDeviceUncategorizedProperty,
         (r"Public properties must be categorized as either "
          r"@decorators\.DynamicProperty, \.PersistentProperty, "
          r"\.OptionalProperty, or \.CapabilityDecorator\. "
          r"Incompliant properties: \['new_property'\]")),
        (BadPrimaryDeviceMisnamedHealthCheck,
         (r"Health checks must follow the <check_\.\.\.> naming convention\. "
          r"Incompliant health checks: \['misnamed_health_check'\]")),
        (BadPrimaryDeviceMissingClassConstants,
         (r"Class constants \['DEVICE_TYPE', 'COMMUNICATION_TYPE', "
          r"'DETECT_MATCH_CRITERIA', '_OWNER_EMAIL'\] are not set")),
        (BadPrimaryDeviceMisnamedCapability,
         (r"Capability definition\(s\) are invalid\. "
          r"Capability 'wrong_name': RuntimeError\(\"Attempting to define "
          r"capability flavor\(s\) .*EventParserDefault'.* under invalid name "
          r"wrong_name.*expected name: event_parser\.\"\)")),
    )
    for bad_device_class, expected_error_regex in test_cases:
      with self.subTest(device_class=bad_device_class):
        self.mock_package.export_extensions.return_value = {
            "primary_devices": [bad_device_class]
        }
        error_regex = err_template.format(
            cls=bad_device_class, err=expected_error_regex)
        with self.assertRaisesRegex(errors.PackageRegistrationError,
                                    error_regex):
          package_registrar.register(self.mock_package)

  @mock.patch.object(
      extensions,
      "capability_interfaces",
      new={"good_capability_base": GoodCapabilityBase})
  @mock.patch.object(
      extensions,
      "capability_flavors",
      new={"good_capability_default": GoodCapabilityDefault})
  @mock.patch.object(
      extensions,
      "capabilities",
      new={"good_capability": "good_capability_base"})
  def test_register_duplicate_capability_interface(self):
    """Test registering a duplicate capability interface."""
    self.mock_package.export_extensions.return_value = {
        "capability_interfaces": [GoodCapabilityBase]
    }
    regex = (r"New capability interfaces .*GoodCapabilityBase.* have "
             r"same names \(\[.*good_capability_base.*\]\) as "
             r"existing capability interfaces .*GoodCapabilityBase.*")
    with self.assertRaisesRegex(errors.PackageRegistrationError, regex):
      package_registrar.register(self.mock_package)

  @mock.patch.object(
      extensions,
      "capability_interfaces",
      new={"good_capability_base": GoodCapabilityBase})
  @mock.patch.object(extensions, "capability_flavors",
                     {"good_capability_default": GoodCapabilityDefault})
  @mock.patch.object(extensions, "capabilities",
                     {"good_capability": "good_capability_base"})
  def test_register_duplicate_capability_flavor(self):
    """Test registering a duplicate capability flavor."""
    self.mock_package.export_extensions.return_value = {
        "capability_flavors": [GoodCapabilityDefault]
    }
    regex = (r"New capability flavors .*GoodCapabilityDefault.* have "
             r"same names \(\[.*good_capability_default.*\]\) as "
             r"existing capability flavors .*GoodCapabilityDefault.*")
    with self.assertRaisesRegex(errors.PackageRegistrationError, regex):
      package_registrar.register(self.mock_package)

  @mock.patch.object(
      extensions,
      "capability_interfaces",
      new={"good_capability_base": GoodCapabilityBase})
  @mock.patch.object(
      extensions,
      "capability_flavors",
      new={"good_capability_default": GoodCapabilityDefault})
  @mock.patch.object(
      extensions,
      "capabilities",
      new={"good_capability": "good_capability_base"})
  def test_register_capability_with_duplicate_name(self):
    """Test registering a capability with a duplicate name."""
    self.mock_package.export_extensions.return_value = {
        "capability_interfaces": [CapabilityWithSameNameBase]
    }
    regex = (r"New capabilities .*CapabilityWithSameNameBase.* have "
             r"same names \(\[.*good_capability.*\]\) as "
             r"existing capabilities .*GoodCapabilityBase.*")
    with self.assertRaisesRegex(errors.PackageRegistrationError, regex):
      package_registrar.register(self.mock_package)

  @mock.patch.object(
      extensions,
      "communication_types",
      new={GoodCommunicationType.__name__: GoodCommunicationType})
  def test_register_detection_query_invalid_key_type(self):
    """Test registering detection query with invalid key type."""
    invalid_query_dict = {
        "foo_query": good_detection_query  # Invalid key type (str)
    }
    self.mock_package.export_extensions.return_value = {
        "detect_criteria":
            immutabledict.immutabledict(
                {GoodCommunicationType.__name__: invalid_query_dict})
    }
    regex = (r"Unable to register query {} for communication type {!r}. "
             "Detection query keys must be {} instances.".format(
                 "foo_query", GoodCommunicationType.__name__,
                 detect_criteria.QueryEnum.__name__))
    with self.assertRaisesRegex(errors.PackageRegistrationError, regex):
      package_registrar.register(self.mock_package)

  @mock.patch.object(
      extensions,
      "communication_types",
      new={GoodCommunicationType.__name__: GoodCommunicationType})
  def test_register_detection_query_invalid_query(self):
    """Test registering detection query with invalid query type."""
    invalid_query_dict_bad_query_type = {
        GoodQueryKey.some_valid_query: None  # Invalid query type (None)
    }
    self.mock_package.export_extensions.return_value = {
        "detect_criteria":
            immutabledict.immutabledict({
                GoodCommunicationType.__name__:
                    invalid_query_dict_bad_query_type
            })
    }
    regex = (r"Unable to register query {} for communication type {!r}. "
             "Detection queries must be callable".format(
                 GoodQueryKey.some_valid_query, GoodCommunicationType.__name__))

    with self.assertRaisesRegex(errors.PackageRegistrationError, regex):
      package_registrar.register(self.mock_package)

    invalid_query_dict_bad_args = {
        GoodQueryKey.some_valid_query: lambda: None  # Invalid query args
    }
    self.mock_package.export_extensions.return_value = {
        "detect_criteria":
            immutabledict.immutabledict(
                {GoodCommunicationType.__name__: invalid_query_dict_bad_args})
    }

    args = r"\('address', 'detect_logger', 'create_switchboard_func'\)"
    regex = (r"Unable to register query {} for communication type {!r}. "
             r"Detection queries must be callable functions which accept 3 "
             r"arguments: {}".format(GoodQueryKey.some_valid_query,
                                     GoodCommunicationType.__name__, args))

    with self.assertRaisesRegex(errors.PackageRegistrationError, regex):
      package_registrar.register(self.mock_package)

  @mock.patch.object(extensions, "communication_types", new={})
  def test_register_detect_query_for_unknown_comm_type(self):
    """Test registering a detect query comm type not known to GDM."""
    valid_query_dict = {GoodQueryKey.some_valid_query: good_detection_query}
    self.mock_package.export_extensions.return_value = {
        "detect_criteria":
            immutabledict.immutabledict(
                {"SomeUnknownCommunicationType": valid_query_dict})
    }
    regex = (r"Unable to register detection criteria for communication type "
             "{!r} as it has not been exported by the package.".format(
                 "SomeUnknownCommunicationType"))
    with self.assertRaisesRegex(errors.PackageRegistrationError, regex):
      package_registrar.register(self.mock_package)

  @mock.patch.object(
      extensions,
      "communication_types",
      new={GoodCommunicationType.__name__: GoodCommunicationType})
  @mock.patch.object(
      extensions,
      "detect_criteria",
      new={
          GoodCommunicationType.__name__:
              immutabledict.immutabledict(
                  {GoodQueryKey.some_valid_query: good_detection_query})
      })
  def test_register_duplicate_detect_query(self):
    """Test registering a duplicate detect query."""
    duplicate_query_dict = {GoodQueryKey.some_valid_query: good_detection_query}
    self.mock_package.export_extensions.return_value = {
        "detect_criteria":
            immutabledict.immutabledict(
                {GoodCommunicationType.__name__: duplicate_query_dict})
    }
    regex = re.escape(
        r"Detection queries {} for communication type {!r} are already "
        "defined in GDM.".format(
            list(duplicate_query_dict.keys()), GoodCommunicationType.__name__))
    with self.assertRaisesRegex(errors.PackageRegistrationError, regex):
      package_registrar.register(self.mock_package)

  def test_register_invalid_key_types(self):
    """Test registering a package which exports invalid key types."""
    self.mock_package.export_extensions.return_value = {
        "keys": [GoodKey, 1, None]
    }
    regex = r"Keys must be data_types\.KeyInfo instances"
    with self.assertRaisesRegex(errors.PackageRegistrationError, regex):
      package_registrar.register(self.mock_package)

  def test_register_mismatching_key_package_name(self):
    """Test registering a package with keys which have mismatching package."""
    self.mock_package.export_extensions.return_value = {
        "keys": [BadKeyMismatchingPackage]
    }
    regex = (r"KeyInfo\.package attribute must match the name of the package "
             r"\('my_extension_package'\)")
    with self.assertRaisesRegex(errors.PackageRegistrationError, regex):
      package_registrar.register(self.mock_package)

  def test_register_invalid_manager_cli_mixin_type(self):
    """Test registering a package with a bad Manager CLI mixin type."""
    test_cases = [
        1,  # Not a class object.
        int,  # Class object, but does not inherit from FireManager.
    ]

    for manager_cli_mixin in test_cases:
      with self.subTest(manager_cli_mixin=manager_cli_mixin):
        self.mock_package.export_extensions.return_value = {
            "manager_cli_mixin": manager_cli_mixin,
        }
        regex = "FireManager mixin class is invalid"
        with self.assertRaisesRegex(errors.PackageRegistrationError, regex):
          package_registrar.register(self.mock_package)

  @mock.patch.object(extensions, "primary_devices", new=[])
  @mock.patch.dict(extensions.capability_interfaces)
  @mock.patch.dict(extensions.capability_flavors)
  @mock.patch.dict(extensions.capabilities)
  def test_failed_registration_does_not_change_state(self):
    """Test that failed registration doesn't change known supported classes."""
    self.mock_package.export_extensions.return_value = {
        "primary_devices": [BadPrimaryDeviceNoLogDecorator],
        "capability_interfaces": [GoodCapabilityBase],
        "capability_flavors": [GoodCapabilityDefault]
    }
    primary_devices_before = extensions.primary_devices.copy()
    capability_interfaces_before = extensions.capability_interfaces.copy()
    capability_flavors_before = extensions.capability_flavors.copy()
    capabilities_before = extensions.capabilities.copy()

    with self.assertRaises(errors.PackageRegistrationError):
      package_registrar.register(self.mock_package)
    self.assertEqual(primary_devices_before, extensions.primary_devices)
    self.assertEqual(capability_interfaces_before,
                     extensions.capability_interfaces)
    self.assertEqual(capability_flavors_before, extensions.capability_flavors)
    self.assertEqual(capabilities_before, extensions.capabilities)

  @mock.patch.object(extensions, "detect_criteria", new={})
  @mock.patch.object(extensions, "communication_types", new={})
  @mock.patch.object(extensions, "package_info", new={})
  @mock.patch.object(extensions, "auxiliary_devices", new=[])
  @mock.patch.object(extensions, "primary_devices", new=[])
  @mock.patch.object(extensions, "virtual_devices", new=[])
  @mock.patch.object(extensions, "keys", new=[])
  @mock.patch.object(extensions, "manager_cli_mixins", new=[])
  @mock.patch.dict(extensions.capability_interfaces)
  @mock.patch.dict(extensions.capability_flavors)
  @mock.patch.dict(extensions.capabilities)
  def test_valid_registration(self):
    """Test registering a valid extension dictionary."""
    self.mock_package.export_extensions.return_value = {
        "auxiliary_devices": [GoodAuxiliaryDevice],
        "primary_devices": [GoodPrimaryDevice],
        "virtual_devices": [GoodVirtualDevice],
        "communication_types": [GoodCommunicationType],
        "detect_criteria": {
            GoodCommunicationType.__name__:
                immutabledict.immutabledict(
                    {GoodQueryKey.some_valid_query: good_detection_query})
        },
        "capability_interfaces": [GoodCapabilityBase],
        "capability_flavors": [GoodCapabilityDefault],
        "keys": [GoodKey],
        "manager_cli_mixin": GoodManagerCliMixin,
    }

    package_registrar.register(self.mock_package)
    self.assertEqual(
        extensions.package_info, {
            _TEST_PACKAGE_NAME:
                immutabledict.immutabledict({
                    "version": self.mock_package.__version__,
                    "key_download_function": self.mock_package.download_key,
                    "import_path": _TEST_PACKAGE_IMPORT_PATH,
                })
        })
    self.assertEqual(extensions.auxiliary_devices, [GoodAuxiliaryDevice])
    self.assertEqual(extensions.primary_devices, [GoodPrimaryDevice])
    self.assertEqual(extensions.virtual_devices, [GoodVirtualDevice])
    self.assertEqual(extensions.communication_types,
                     {GoodCommunicationType.__name__: GoodCommunicationType})
    self.assertEqual(
        extensions.detect_criteria, {
            GoodCommunicationType.__name__: {
                GoodQueryKey.some_valid_query: good_detection_query
            }
        })
    self.assertEqual(extensions.capability_interfaces["good_capability_base"],
                     GoodCapabilityBase)
    self.assertEqual(extensions.capability_flavors["good_capability_default"],
                     GoodCapabilityDefault)
    self.assertEqual(extensions.capabilities["good_capability"],
                     "good_capability_base")
    self.assertEqual(extensions.keys, [GoodKey])

    # Test registering a different package which extends detect criteria for
    # communication type registered by the first package.
    self.mock_package.__name__ = "some_parent_package.another_extension_package"
    self.mock_package.export_extensions.return_value = {
        "detect_criteria": {
            GoodCommunicationType.__name__:
                immutabledict.immutabledict({
                    GoodQueryKey.another_valid_query:
                        another_good_detection_query,
                })
        }
    }
    package_registrar.register(self.mock_package)

    self.assertIn(_TEST_PACKAGE_NAME, extensions.package_info)
    self.assertIn("another_extension_package", extensions.package_info)
    self.assertEqual(
        extensions.detect_criteria, {
            GoodCommunicationType.__name__: {
                GoodQueryKey.some_valid_query: good_detection_query,
                GoodQueryKey.another_valid_query: another_good_detection_query,
            }
        })

  @mock.patch.object(package_registrar, "register")
  @mock.patch.object(
      importlib, "import_module", side_effect=ImportError("Package not found"))
  @mock.patch.object(package_registrar.logger, "warning")
  def test_import_and_register_import_failure(self, mock_warning, mock_import,
                                              mock_register):
    """Test import_and_register() on a nonexistent package."""
    return_value = package_registrar.import_and_register(
        "nonexistent-package", include_cli_instructions=True)
    self.assertFalse(return_value)
    self.assertEqual(mock_warning.call_count, 2)
    mock_import.assert_called_once_with("nonexistent-package")
    mock_register.assert_not_called()

  @mock.patch.object(
      package_registrar,
      "register",
      side_effect=errors.PackageRegistrationError("Something failed",
                                                  "some_package"))
  @mock.patch.object(importlib, "import_module")
  @mock.patch.object(package_registrar.logger, "warning")
  def test_import_and_register_registration_failure(self, mock_warning,
                                                    mock_import, mock_register):
    """Test import_and_register() on an invalid package."""
    return_value = package_registrar.import_and_register(
        "invalid-package", include_cli_instructions=True)
    self.assertFalse(return_value)
    self.assertEqual(mock_warning.call_count, 2)
    mock_import.assert_called_once_with("invalid-package")
    mock_register.assert_called_once()

  @mock.patch.object(package_registrar, "register")
  @mock.patch.object(importlib, "import_module")
  @mock.patch.object(package_registrar.logger, "warning")
  def test_import_and_register_success(self, mock_warning, mock_import,
                                       mock_register):
    """Test import_and_register() on a valid package."""
    return_value = package_registrar.import_and_register("valid-package")
    self.assertTrue(return_value)
    mock_warning.assert_not_called()
    mock_import.assert_called_once_with("valid-package")
    mock_register.assert_called_once()

  @mock.patch.object(json, "load", return_value={})
  @mock.patch.object(builtins, "open")
  @mock.patch.object(os.path, "exists", return_value=False)
  def test_get_cli_extension_packages_no_config_file(self, mock_exists,
                                                     mock_open, mock_load):
    """Test get_cli_extension_packages() when config file is missing."""
    self.assertFalse(package_registrar.get_cli_extension_packages())
    mock_exists.assert_called_once()
    mock_open.assert_not_called()
    mock_load.assert_not_called()

  @mock.patch.object(json, "load", return_value={})
  @mock.patch.object(builtins, "open")
  @mock.patch.object(os.path, "exists", return_value=True)
  def test_get_cli_extension_packages_no_config_entry(self, mock_exists,
                                                      mock_open, mock_load):
    """Test get_cli_extension_packages() when config doesn't have the entry."""
    self.assertFalse(package_registrar.get_cli_extension_packages())
    mock_exists.assert_called_once()
    mock_open.assert_called_once()
    mock_load.assert_called_once()

  @mock.patch.object(
      json,
      "load",
      return_value={
          "cli_extension_packages": ["package_one", "package_two"],
      })
  @mock.patch.object(builtins, "open")
  @mock.patch.object(os.path, "exists", return_value=True)
  def test_get_cli_extension_packages_success(self, mock_exists, mock_open,
                                              mock_load):
    """Test get_cli_extension_packages() with some registered CLI packages."""
    self.assertCountEqual(package_registrar.get_cli_extension_packages(),
                          ["package_one", "package_two"])
    mock_exists.assert_called_once()
    mock_open.assert_called_once()
    mock_load.assert_called_once()

  @mock.patch.object(
      package_registrar,
      "get_cli_extension_packages",
      return_value=["package_one", "package_two"])
  @mock.patch.object(package_registrar, "import_and_register")
  def test_import_and_register_cli_extension_packages(
      self, mock_import_and_register, mock_get_cli_extension_packages):
    """Test import_and_register_cli_extension_packages() with some packages."""
    package_registrar.import_and_register_cli_extension_packages()
    mock_get_cli_extension_packages.assert_called_once()
    mock_import_and_register.assert_has_calls([
        mock.call("package_one", include_cli_instructions=True),
        mock.call("package_two", include_cli_instructions=True)
    ],
                                              any_order=True)


if __name__ == "__main__":
  unit_test_case.main()
