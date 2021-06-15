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

"""Handles registration of device extension packages.

Registered extensions are stored in gazoo_device.extensions.
"""
import collections
import copy
import importlib
import inspect
import itertools
import json
import logging
import os.path
import types
from typing import Any, Callable, Collection, List, Mapping, Tuple, Type, Union

from gazoo_device import config
from gazoo_device import data_types
from gazoo_device import detect_criteria
from gazoo_device import errors
from gazoo_device import extensions
from gazoo_device import gdm_logger
from gazoo_device.base_classes import auxiliary_device
from gazoo_device.base_classes import gazoo_device_base
from gazoo_device.capabilities.interfaces import capability_base
from gazoo_device.capabilities.interfaces import switchboard_base
from gazoo_device.switchboard import communication_types
from gazoo_device.utility import common_utils
from gazoo_device.utility import conformance_utils
import immutabledict

# Temporary exceptions to the conformance checks
OVERRIDDEN_SIGNATURE_DEVICE_METHODS = (
)
PUBLIC_METHOD_EXCEPTIONS = (
)

_EXTENSION_DICT_DEFAULTS = immutabledict.immutabledict({
    "primary_devices": [],
    "auxiliary_devices": [],
    "virtual_devices": [],
    "communication_types": [],
    "detect_criteria": {},
    "capability_interfaces": [],
    "capability_flavors": [],
    "keys": [],
})
_EXPECTED_QUERY_ARGS = ("address", "detect_logger", "create_switchboard_func")
_MISMATCHING_SIGNATURE_TEMPLATE = (
    "Method {!r}, child signature {}, inherited signature(s) {}.")
_DetectQueryType = Callable[
    [str, logging.Logger, Callable[..., switchboard_base.SwitchboardBase]],
    Union[str, bool]
]
_DetectQueryMapping = Mapping[detect_criteria.QueryEnum, _DetectQueryType]
_VIRTUAL_ENV_PIP_PATH = os.path.join(config.VIRTUAL_ENV_DIRECTORY, "bin", "pip")

_AuxiliaryDeviceBase = auxiliary_device.AuxiliaryDevice
_PrimaryDeviceBase = gazoo_device_base.GazooDeviceBase
# Virtual devices currently do not have a dedicated base class.
_VirtualDeviceBase = gazoo_device_base.GazooDeviceBase
_CommunicationTypeBase = communication_types.CommunicationType
_CapabilityBase = capability_base.CapabilityBase
_DeviceClassType = Union[_AuxiliaryDeviceBase, _PrimaryDeviceBase,
                         _VirtualDeviceBase]

logger = gdm_logger.get_logger()


def register(package: types.ModuleType) -> None:
  """Registers the given extension package with GDM architecture.

  The provided module must define:
  * a "download_key" function;
  * a __version__ attribute (must be a string);
  * an "export_extensions" function.

  The download_key function must have the following signature:
  download_key(key_info: data_types.KeyInfo, local_key_path: str) -> None.
  It will be called if one of the SSH keys registered by the package is missing
  on the host. The function must obtain the key and write it to local_key_path.
  key_info is guaranteed to be one of the keys registered by the package.
  Directory containing local_key_path is guaranteed to exist. Key permissions
  for SSH keys will be set by GDM automatically.

  The export_extensions function must have the following signature:
  export_extensions() -> Dict[str, Any].
  The return dictionary must contain all extensions the package wishes to
  register with the GDM architecture. The dictionary format must be:
  {
      "primary_devices": [  # list of GazooDeviceBase subclasses
          <PrimaryDeviceClass1>, <...>
      ],
      "auxiliary_devices": [  # list of AuxiliaryDevice subclasses
          <AuxiliaryDeviceClass1>, <...>
      ],
      "virtual_devices": [  # list of GazooDeviceBase subclasses
          <VirtualDeviceClass1>, <...>
      ],
      "communication_types": [  # list of CommunicationType subclasses
          <CommunicationTypeClass1>, <...>
      ],
      "detect_criteria": {  # CommTypeName -> {QueryEnum -> Callable} entries
          "CommunicationTypeName1": {
              <DetectionQueryName1>: <detection_query_1_function>,
              <DetectionQueryName2>: <detection_query_2_function>,
              <...>
          },
          "CommunicationTypeName2": {
              <...>
          }
      },
      "capability_interfaces": [  # CapabilityBase subclasses (usually abstract)
          <Capability1Base>, <Capability2Base>, <...>
      ],
      "capability_flavors": [  # concrete CapabilityBase subclasses
          <Capability1Foo>, <Capability1Bar>, <Capability2Default>, <...>
      ],
      "keys": [  # data_types.KeyInfo instances
          <KeyInfoSsh1>, <KeyInfoSsh2>, <KeyInfoApiToken1>, <...>
      ]
  }

  Args:
    package: Extension package to register (typically its __init__ module).

  Raises:
    PackageRegistrationError: The extensions provided by
      package.export_extensions() are invalid, or package.__version__ is not
      defined.
  """
  package_name = package.__name__.split(".")[-1]
  _validate_extension_package(package, package_name)

  new_extensions = dict(copy.deepcopy(_EXTENSION_DICT_DEFAULTS))
  new_extensions.update(package.export_extensions())
  extensions_backup = _copy_extensions()

  try:
    _register(new_extensions, package_name,
              package.__version__,  # pytype: disable=attribute-error
              package.download_key)
  except errors.PackageRegistrationError:
    # Registration failed: revert all changes to the extensions to avoid
    # leaving them in an inconsistent state.
    _restore_extensions(extensions_backup)
    raise


def import_and_register(package_name: str,
                        include_cli_instructions: bool = False) -> bool:
  """Attempts to import and register the extension package.

  Args:
    package_name: Name of the package to import. For example,
      "foo_extension_package" or "my_package.bar_devices".
    include_cli_instructions: Whether to include CLI-specific instructions to
      resolve the error.

  Returns:
    True if operation succeeded, False otherwise.
  """
  try:
    package = importlib.import_module(package_name)
  except ImportError:
    logger.warning(
        f"Import of GDM extension package {package_name!r} failed. "
        "GDM will not be able to use the package. Error:",
        exc_info=True)
    if include_cli_instructions:
      logger.warning(
          "\nInstall the package in the GDM CLI virtual environment via "
          f"`{_VIRTUAL_ENV_PIP_PATH} install <package>` or unregister the "
          f"package from GDM CLI via `gdm unregister {package_name}`\n")
    return False
  try:
    register(package)
  except errors.PackageRegistrationError:
    logger.warning(
        f"Registration of GDM extension package {package_name!r} failed. "
        "GDM will not be able to use the package. Error:",
        exc_info=True)
    if include_cli_instructions:
      logger.warning(
          "\nUpdate the package and install the new version in the GDM CLI "
          "virtual environment via "
          f"`{_VIRTUAL_ENV_PIP_PATH} install <package>` or unregister the "
          f"package from GDM CLI via `gdm unregister {package_name}`\n")
    return False
  return True


def get_cli_extension_packages() -> List[str]:
  """Returns names of extension packages registered with the CLI."""
  if os.path.exists(config.DEFAULT_GDM_CONFIG_FILE):
    with open(config.DEFAULT_GDM_CONFIG_FILE) as gdm_config_file:
      gdm_config = json.load(gdm_config_file)
    return gdm_config.get("cli_extension_packages", [])
  return []


def import_and_register_cli_extension_packages() -> None:
  """Attempts to import and register all packages registered with the CLI."""
  cli_extension_packages = get_cli_extension_packages()
  for package_name in cli_extension_packages:
    import_and_register(package_name, include_cli_instructions=True)


def _validate_extension_package(package: types.ModuleType,
                                package_name: str) -> None:
  """Checks that the extension package is valid.

  Args:
    package: Extension package to check.
    package_name: Name of the extension package.

  Raises:
    PackageRegistrationError: Package has already been registered, or a required
      attribute is missing or invalid.
  """
  if package_name in extensions.package_info:
    raise errors.PackageRegistrationError(
        f"Package {package_name!r} has already been registered.",
        package_name=package_name)

  package_version = getattr(package, "__version__", None)
  if not package_version or not isinstance(package_version, str):
    raise errors.PackageRegistrationError(
        f"Expected __version__ to be a string, found {package_version}.",
        package_name=package_name)

  missing_functions = [
      func for func in ("download_key", "export_extensions")
      if not hasattr(package, func) or not callable(getattr(package, func))
  ]
  if missing_functions:
    raise errors.PackageRegistrationError(
        f"Package must define functions {missing_functions}.",
        package_name=package_name)


def _register(
    new_extensions: Mapping[str, Any],
    package_name: str,
    package_version: str,
    download_key: Callable[[data_types.KeyInfo, str], None]) -> None:
  """Registers the given extensions with GDM architecture.

  Args:
    new_extensions: Extensions to register with GDM architecture. See the
      register() docstring for format details.
    package_name: Name of the package being registered.
    package_version: Version of the package being registered.
    download_key: download_key function of the package.

  Raises:
    PackageRegistrationError: The provided extensions are invalid.
  """
  _validate_capability_interfaces(
      ext_capability_interfaces=new_extensions["capability_interfaces"],
      package_name=package_name)
  new_capability_interfaces = {
      common_utils.generate_name(interface): interface
      for interface in new_extensions["capability_interfaces"]
  }
  # Capability interfaces have to be registered before validating flavors.
  extensions.capability_interfaces.update(new_capability_interfaces)
  new_capabilities = {
      interface.get_capability_name(): if_name
      for if_name, interface in new_capability_interfaces.items()
  }
  extensions.capabilities.update(new_capabilities)

  _validate_capability_flavors(
      ext_capability_flavors=new_extensions["capability_flavors"],
      package_name=package_name)
  new_capability_flavors = {
      common_utils.generate_name(flavor): flavor
      for flavor in new_extensions["capability_flavors"]
  }
  # Capability flavors have to be registered before validating device classes.
  extensions.capability_flavors.update(new_capability_flavors)

  _validate_device_classes(
      ext_auxiliary_devices=new_extensions["auxiliary_devices"],
      ext_primary_devices=new_extensions["primary_devices"],
      ext_virtual_devices=new_extensions["virtual_devices"],
      package_name=package_name)
  _validate_comm_type_classes(
      ext_communication_types=new_extensions["communication_types"],
      package_name=package_name)
  _validate_detect_criteria(
      ext_detect_criteria=new_extensions["detect_criteria"],
      ext_communication_types=new_extensions["communication_types"],
      package_name=package_name)
  _validate_keys(new_extensions["keys"], package_name=package_name)

  extensions.auxiliary_devices = list(set(
      extensions.auxiliary_devices
      + new_extensions["auxiliary_devices"]))
  extensions.primary_devices = list(set(
      extensions.primary_devices
      + new_extensions["primary_devices"]))
  extensions.virtual_devices = list(set(
      extensions.virtual_devices
      + new_extensions["virtual_devices"]))
  extensions.communication_types.update({
      comm_type.__name__: comm_type
      for comm_type in new_extensions["communication_types"]
  })
  for comm_type_name, query_dict in new_extensions["detect_criteria"].items():
    if comm_type_name not in extensions.detect_criteria:
      extensions.detect_criteria[comm_type_name] = dict(query_dict)
    else:
      extensions.detect_criteria[comm_type_name].update(query_dict)
  extensions.keys.extend(new_extensions["keys"])

  extensions.package_info[package_name] = immutabledict.immutabledict({
      "version": package_version,
      "key_download_function": download_key,
  })


def _validate_device_classes(ext_auxiliary_devices: Collection[Type[Any]],
                             ext_primary_devices: Collection[Type[Any]],
                             ext_virtual_devices: Collection[Type[Any]],
                             package_name: str) -> None:
  """Validates the extension device classes.

  Args:
    ext_auxiliary_devices: Auxiliary device classes to validate.
    ext_primary_devices: Primary device classes to validate.
    ext_virtual_devices: Virtual device classes to validate.
    package_name: Name of the package providing the extension classes.

  Raises:
    PackageRegistrationError: Device classes are invalid.
  """
  _assert_subclasses(ext_auxiliary_devices, _AuxiliaryDeviceBase, package_name,
                     "auxiliary device")
  _assert_subclasses(ext_primary_devices, _PrimaryDeviceBase, package_name,
                     "primary device")
  _assert_subclasses(ext_virtual_devices, _VirtualDeviceBase, package_name,
                     "virtual device")

  new_device_classes = tuple(itertools.chain(
      ext_auxiliary_devices, ext_primary_devices, ext_virtual_devices))
  known_device_classes = (extensions.auxiliary_devices
                          + extensions.primary_devices
                          + extensions.virtual_devices)
  new_device_types = tuple(device_class.DEVICE_TYPE
                           for device_class in new_device_classes)
  _assert_unique(new_device_types,
                 names_description="Device types",
                 classes_description="device classes",
                 package_name=package_name)
  redefined_device_types = set.intersection(
      {device_class.DEVICE_TYPE for device_class in new_device_classes},
      {device_class.DEVICE_TYPE for device_class in known_device_classes})
  if redefined_device_types:
    raise errors.PackageRegistrationError(
        f"Device types {redefined_device_types} are already defined in GDM.",
        package_name=package_name)

  conformance_issues = _get_device_class_conformance_issues(new_device_classes)
  if conformance_issues:
    issue_messages = []
    for cls, issues in conformance_issues:
      issue_message = "".join(f"\n\t{issue}" for issue in issues)
      issue_messages.append(f"{cls}{issue_message}")
    raise errors.PackageRegistrationError(
        "The following device class(es) are incompliant with GDM "
        "architecture:\n{}".format("\n".join(issue_messages)),
        package_name=package_name)


def _get_device_class_conformance_issues(
    device_classes: Collection[Type[_DeviceClassType]]
) -> List[Tuple[Type[_DeviceClassType], List[str]]]:
  """Returns conformance issues identified in the device classes.

  Args:
    device_classes: Device classes to check for conformance with architecture.

  Returns:
    List of (device class, list of conformance issues) tuples.
    If there are no issues for a device class, it will not be present in the
    return list.
  """
  all_issues = []
  for device_class in device_classes:
    issues = []
    no_log_decorator_methods = conformance_utils.get_log_decorator_violators(
        device_class)
    if no_log_decorator_methods:
      issues.append(
          "Public methods without return values must be decorated with "
          "@decorators.LogDecorator(<logger>). Incompliant methods: "
          f"{no_log_decorator_methods}.")
    mismatching_signatures = conformance_utils.get_mismatching_signatures(
        device_class, excluded_methods=OVERRIDDEN_SIGNATURE_DEVICE_METHODS)
    if mismatching_signatures:
      mismatching_signature_messages = [
          _MISMATCHING_SIGNATURE_TEMPLATE.format(method, child_sig, parent_sigs)
          for method, child_sig, parent_sigs in mismatching_signatures]
      issues.append(
          "Methods may not fully override signatures inherited from parents. "
          "Only extending the argument list is allowed. "
          f"Incompliant method signatures: {mismatching_signature_messages}.")
    invalid_public_methods = conformance_utils.get_invalid_public_methods(
        device_class, excluded_methods=PUBLIC_METHOD_EXCEPTIONS)
    if invalid_public_methods:
      issues.append(
          "New public methods are not allowed, except for health checks. "
          "Methods must either be private or, if public, moved into "
          f"capabilities. Incompliant methods: {invalid_public_methods}.")
    uncategorized_properties = conformance_utils.get_uncategorized_properties(
        device_class)
    if uncategorized_properties:
      issues.append(
          "Public properties must be categorized as either @decorators"
          ".DynamicProperty, .PersistentProperty, .OptionalProperty, or "
          ".CapabilityDecorator. Incompliant properties: "
          f"{uncategorized_properties}.")
    unset_class_constants = conformance_utils.get_unset_constants(device_class)
    if unset_class_constants:
      issues.append(f"Class constants {unset_class_constants} are not set.")
    invalid_health_checks = conformance_utils.get_invalid_health_check_names(
        device_class)
    if invalid_health_checks:
      issues.append(
          "Health checks must follow the <check_...> naming convention. "
          f"Incompliant health checks: {invalid_health_checks}.")
    invalid_definitions = conformance_utils.get_invalid_capability_definitions(
        device_class)
    if invalid_definitions:
      issues.append("Capability definition(s) are invalid. {}".format(
          ", ".join(f"Capability {cap!r}: {err}"
                    for cap, err in invalid_definitions)))
    if issues:
      all_issues.append((device_class, issues))

  return all_issues


def _validate_comm_type_classes(
    ext_communication_types: Collection[Type[Any]],
    package_name: str) -> None:
  """Validates the extension communication types.

  Args:
    ext_communication_types: Communication type classes to validate.
    package_name: Name of the package providing the extension classes.

  Raises:
    PackageRegistrationError: Communication type classes are invalid.
  """
  _assert_subclasses(ext_communication_types, _CommunicationTypeBase,
                     package_name, "communication type")
  new_comm_types = {
      comm_type.__name__: comm_type
      for comm_type in ext_communication_types
  }
  _raise_if_redefined(new_classes=new_comm_types,
                      old_classes=extensions.communication_types,
                      classes_description="communication types",
                      package_name=package_name)


def _validate_detect_criteria(
    ext_detect_criteria: Mapping[str, _DetectQueryMapping],
    ext_communication_types: Collection[Type[Any]],
    package_name: str) -> None:
  """Validates the extension detection criteria.

  Args:
    ext_detect_criteria: Detection criteria to validate, where mapping keys are
      communication type names, and values are detection query mappings for each
      communication type.
    ext_communication_types: Communication types exported by the package.
    package_name: Name of the package providing the extensions.

  Raises:
    PackageRegistrationError: Detection criteria are invalid.
  """
  extension_comm_type_names = [comm_type.__name__
                               for comm_type in ext_communication_types]
  for comm_type_name, query_dict in ext_detect_criteria.items():
    for query_name, query in query_dict.items():
      base_error = ("Unable to register query {} for communication type {!r}. "
                    .format(query_name, comm_type_name))
      if not isinstance(query_name, detect_criteria.QueryEnum):
        raise errors.PackageRegistrationError(
            base_error + "Detection query keys must be {} instances.".format(
                detect_criteria.QueryEnum.__name__),
            package_name=package_name)
      if (not callable(query)
          or tuple(inspect.getfullargspec(query).args) != _EXPECTED_QUERY_ARGS):
        extra_error = ("Detection queries must be callable functions which "
                       "accept {} arguments: {}."
                       .format(len(_EXPECTED_QUERY_ARGS), _EXPECTED_QUERY_ARGS))
        raise errors.PackageRegistrationError(base_error + extra_error,
                                              package_name=package_name)

    if comm_type_name not in extensions.detect_criteria:
      if comm_type_name not in extension_comm_type_names:
        raise errors.PackageRegistrationError(
            "Unable to register detection criteria for communication type "
            f"{comm_type_name!r} as it has not been exported by the package.",
            package_name=package_name)
    else:
      redefined_queries = list(
          extensions.detect_criteria[comm_type_name].keys()
          & query_dict.keys())
      if redefined_queries:
        raise errors.PackageRegistrationError(
            f"Detection queries {redefined_queries} for communication type "
            f"{comm_type_name!r} are already defined in GDM.",
            package_name=package_name)


def _validate_capability_interfaces(
    ext_capability_interfaces: Collection[Type[Any]],
    package_name: str) -> None:
  """Validates the extension capability interfaces.

  Args:
    ext_capability_interfaces: Capability interface classes to validate.
    package_name: Name of the package providing the extension classes.

  Raises:
    PackageRegistrationError: Capability interface classes are invalid.
  """
  _assert_subclasses(ext_capability_interfaces, _CapabilityBase, package_name,
                     "capability interface", allow_abstract=True)
  new_capability_interfaces = {
      common_utils.generate_name(interface): interface
      for interface in ext_capability_interfaces
  }
  _assert_unique(new_capability_interfaces.keys(),
                 names_description="Capability interface names",
                 classes_description="capability interfaces",
                 package_name=package_name)
  _raise_if_redefined(new_classes=new_capability_interfaces,
                      old_classes=extensions.capability_interfaces,
                      classes_description="capability interfaces",
                      package_name=package_name)

  new_capability_names_list = []  # Entries are (interface name, interface)
  for interface in ext_capability_interfaces:
    try:
      interface_name = interface.get_capability_name()
    except TypeError:
      # Interface did not override name generation logic and isn't recognized
      # by GDM yet.
      interface_name = capability_base.get_default_capability_name(interface)
    new_capability_names_list.append((interface_name, interface))

  _assert_unique(tuple(name for name, _ in new_capability_names_list),
                 names_description="Capability names",
                 classes_description="capabilities",
                 package_name=package_name)
  new_capability_names = dict(new_capability_names_list)
  existing_capability_names = {
      cap_name: extensions.capability_interfaces[if_name]
      for cap_name, if_name in extensions.capabilities.items()
  }
  _raise_if_redefined(new_classes=new_capability_names,
                      old_classes=existing_capability_names,
                      classes_description="capabilities",
                      package_name=package_name)
  _assert_unique((list(new_capability_interfaces.keys())
                  + list(new_capability_names.keys())),
                 names_description="Capability interface and capability names",
                 classes_description="capability interfaces and capabilities",
                 package_name=package_name)


def _validate_capability_flavors(ext_capability_flavors: Collection[Type[Any]],
                                 package_name: str) -> None:
  """Validates the extension capability flavors.

  Args:
    ext_capability_flavors: Capability flavor classes to validate.
    package_name: Name of the package providing the extension classes.

  Raises:
    PackageRegistrationError: Capability flavor classes are invalid.
  """
  _assert_subclasses(ext_capability_flavors, _CapabilityBase, package_name,
                     "capability flavor")
  new_capability_flavors = {
      common_utils.generate_name(flavor): flavor
      for flavor in ext_capability_flavors
  }
  _assert_unique(new_capability_flavors.keys(),
                 names_description="Capability flavor names",
                 classes_description="capability flavors",
                 package_name=package_name)
  _raise_if_redefined(new_classes=new_capability_flavors,
                      old_classes=extensions.capability_flavors,
                      classes_description="capability flavors",
                      package_name=package_name)

  _assert_unique((list(new_capability_flavors.keys())
                  + list(extensions.capability_interfaces.keys())
                  + list(extensions.capabilities.keys())),
                 names_description="Capability flavor and (capability "
                                   "interface or capability) names",
                 classes_description="capability flavors and (capability "
                                     "interfaces or capabilities)",
                 package_name=package_name)

  conformance_issues = _get_capability_flavor_conformance_issues(
      ext_capability_flavors)
  if conformance_issues:
    issue_messages = []
    for cls, issues in conformance_issues:
      issue_message = "".join(f"\n\t{issue}" for issue in issues)
      issue_messages.append(f"{cls}{issue_message}")
    raise errors.PackageRegistrationError(
        "The following capability class(es) are incompliant with GDM "
        "architecture:\n{}".format("\n".join(issue_messages)),
        package_name=package_name)


def _get_capability_flavor_conformance_issues(
    capability_flavors: Collection[Type[_CapabilityBase]]
) -> List[Tuple[Type[_CapabilityBase], List[str]]]:
  """Returns conformance issues identified in the capability flavor classes.

  Args:
    capability_flavors: Capability flavor classes to check for conformance.

  Returns:
    List of (capability flavor class, list of conformance issues) tuples.
    If there are no issues for a capability flavor class, it will not be present
    in the return list.
  """
  all_issues = []
  for capability_flavor in capability_flavors:
    issues = []
    no_log_decorator_methods = conformance_utils.get_log_decorator_violators(
        capability_flavor)
    if no_log_decorator_methods:
      issues.append(
          "Public methods without return values must be decorated with "
          "@decorators.CapabilityLogDecorator(<logger>). "
          f"Incompliant methods: {no_log_decorator_methods}.")
    mismatching_signatures = conformance_utils.get_mismatching_signatures(
        capability_flavor)
    if mismatching_signatures:
      mismatching_signature_messages = [
          _MISMATCHING_SIGNATURE_TEMPLATE.format(method, child_sig, parent_sigs)
          for method, child_sig, parent_sigs in mismatching_signatures]
      issues.append(
          "Methods may not fully override signatures inherited from parents. "
          "Only extending the argument list is allowed. "
          f"Incompliant method signatures: {mismatching_signature_messages}.")
    uncategorized_properties = conformance_utils.get_uncategorized_properties(
        capability_flavor)
    if uncategorized_properties:
      issues.append(
          "Public properties must be categorized as either @decorators"
          ".DynamicProperty, .PersistentProperty, or .OptionalProperty. "
          f"Incompliant properties: {uncategorized_properties}.")
    if issues:
      all_issues.append((capability_flavor, issues))

  return all_issues


def _validate_keys(keys: Collection[data_types.KeyInfo],
                   package_name: str) -> None:
  """Validates the extension keys.

  Args:
    keys: Keys provided by the extension package.
    package_name: Name of the extension package.

  Raises:
    PackageRegistrationError: Provided keys are invalid.
  """
  if not all(isinstance(key, data_types.KeyInfo) for key in keys):
    raise errors.PackageRegistrationError(
        "Keys must be data_types.KeyInfo instances.",
        package_name=package_name)
  if not all(key.package == package_name for key in keys):
    raise errors.PackageRegistrationError(
        "KeyInfo.package attribute must match the name of the package "
        f"({package_name!r}).", package_name=package_name)


def _assert_subclasses(classes: Collection[Type[Any]],
                       parent: Type[Any],
                       package_name: str,
                       class_description: str,
                       allow_abstract: bool = False) -> None:
  """Raises an error if classes are not (concrete) subclasses of parent.

  Args:
    classes: Class objects to check.
    parent: The class object which should be the parent for all of classes.
    package_name: Name of the package being registered.
    class_description: Description of the classes being registered.
      For example, "primary device".
    allow_abstract: If False, all of classes must be concrete. Otherwise,
      abstract classes are allowed.

  Raises:
    PackageRegistrationError: One or more classes are invalid (not a class
      object, not a subclass of parent, or abstract when allow_abstract=False).
  """
  error_messages = []
  not_classes = [a_class for a_class in classes if not inspect.isclass(a_class)]
  if not_classes:
    error_messages.append(f"{not_classes} must be class objects.")

  not_subclasses = [  # issubclass() only works on class objects.
      a_class for a_class in classes
      if inspect.isclass(a_class) and not issubclass(a_class, parent)]
  if not_subclasses:
    error_messages.append(
        f"{not_subclasses} must be subclasses of {parent.__name__}.")

  if not allow_abstract:
    abstract_classes = [a_class for a_class in classes
                        if inspect.isabstract(a_class)]
    if abstract_classes:
      error_messages.append(f"{abstract_classes} must not be abstract.")

  if error_messages:
    raise errors.PackageRegistrationError(
        "Provided {} classes are invalid. {}".format(class_description,
                                                     " ".join(error_messages)),
        package_name=package_name)


def _assert_unique(names: Collection[str],
                   names_description: str,
                   classes_description: str,
                   package_name: str) -> None:
  """Raises an error if the names are not unique.

  Args:
    names: Class names to validate.
    names_description: Description of the class names.
    classes_description: Desciption of the classes.
    package_name: Name of the package being registered.

  Raises:
    PackageRegistrationError: Class names are not unique.
  """
  name_counts = collections.Counter(names)
  duplicate_names = [name for name, count in name_counts.items() if count > 1]
  if duplicate_names:
    raise errors.PackageRegistrationError(
        f"{names_description} {duplicate_names} are used by multiple "
        f"{classes_description}. {names_description} must be unique.",
        package_name=package_name)


def _raise_if_redefined(new_classes: Mapping[str, Type[Any]],
                        old_classes: Mapping[str, Type[Any]],
                        classes_description: str,
                        package_name: str) -> None:
  """Raises if the new class dictionary redefines items in the old one.

  Args:
    new_classes: New class name -> new class object mapping.
    old_classes: Known class name -> known class object mapping.
    classes_description: Human-readable description of the classes.
    package_name: Name of the package being registered.

  Raises:
    PackageRegistrationError: Some of the new classes share names with the
      already known classes.
  """
  redefined_names = list(set(old_classes.keys()) & set(new_classes.keys()))
  if redefined_names:
    offending = [new_classes[if_name] for if_name in redefined_names]
    redefined = [old_classes[if_name] for if_name in redefined_names]
    raise errors.PackageRegistrationError(
        f"New {classes_description} {offending} have same names "
        f"({redefined_names}) as existing {classes_description} {redefined}.",
        package_name=package_name)


def _copy_extensions():
  """Returns a backup copy of the current state of extensions."""
  return (extensions.capability_interfaces.copy(),
          extensions.capabilities.copy(),
          extensions.capability_flavors.copy(),
          extensions.auxiliary_devices.copy(),
          extensions.primary_devices.copy(),
          extensions.virtual_devices.copy(),
          extensions.communication_types.copy(),
          copy.deepcopy(extensions.detect_criteria),
          copy.deepcopy(extensions.package_info),
          extensions.keys.copy())


def _restore_extensions(backup_copy):
  """Restores the state of extensions from the backup copy."""
  (extensions.capability_interfaces,
   extensions.capabilities,
   extensions.capability_flavors,
   extensions.auxiliary_devices,
   extensions.primary_devices,
   extensions.virtual_devices,
   extensions.communication_types,
   extensions.detect_criteria,
   extensions.package_info,
   extensions.keys) = backup_copy
