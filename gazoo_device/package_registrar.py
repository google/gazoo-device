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

"""Handles registration of device extension packages.

Registered extensions are stored in gazoo_device.extensions.
"""
import abc
import collections
import copy
import importlib
import inspect
import itertools
import json
import os.path
import types
import typing
from typing import Any, Callable, Collection, Mapping, MutableMapping, Optional, Union
from gazoo_device import config
from gazoo_device import data_types
from gazoo_device import errors
from gazoo_device import extensions
from gazoo_device import gdm_logger
from gazoo_device.base_classes import auxiliary_device
from gazoo_device.base_classes import gazoo_device_base
from gazoo_device.capabilities.interfaces import capability_base
from gazoo_device.detect_criteria import base_detect_criteria
from gazoo_device.switchboard.communication_types import base_comms
from gazoo_device.utility import common_utils
from gazoo_device.utility import conformance_utils
from gazoo_device.utility import host_utils
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
    "manager_cli_mixin": None,
})
_EXPECTED_QUERY_ARGS = ("address", "detect_logger", "create_switchboard_func")
_MISMATCHING_SIGNATURE_TEMPLATE = (
    "Method {!r}, child signature {}, inherited signature(s) {}.")
_VIRTUAL_ENV_PIP_PATH = os.path.join(config.VIRTUAL_ENV_DIRECTORY, "bin", "pip")

_AuxiliaryDeviceBase = auxiliary_device.AuxiliaryDevice
_PrimaryDeviceBase = gazoo_device_base.GazooDeviceBase
# Virtual devices currently do not have a dedicated base class.
_VirtualDeviceBase = gazoo_device_base.GazooDeviceBase
_CommunicationTypeBase = base_comms.CommunicationType
_CapabilityBase = capability_base.CapabilityBase
_DeviceClassType = Union[_AuxiliaryDeviceBase, _PrimaryDeviceBase,
                         _VirtualDeviceBase]

logger = gdm_logger.get_logger()


def register(package: types.ModuleType) -> None:
  """Registers the given extension package with GDM architecture.

  The provided module must define:
  * a __version__ attribute (must be a string);
  * an "export_extensions" function;
  * a "download_key" function if the package exports any keys.

  The download_key function must have the following signature:
  download_key(key_info: data_types.KeyInfo, local_key_path: str) -> None.
  It will be called if one of the SSH keys registered by the package is missing
  on the host. The function must obtain the key and write it to local_key_path.
  key_info is guaranteed to be one of the keys registered by the package.
  Directory containing local_key_path is guaranteed to exist. Key permissions
  for SSH keys will be set by GDM automatically.

  The export_extensions function must have the following signature:
  export_extensions() -> dict[str, Any].
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
      ],
      # Manager mixins are used to expose package-defined CLI commands.
      "manager_cli_mixin": <class object inheriting from FireManager> or None,
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
              package.__name__,
              getattr(package, "download_key", None))
  except errors.PackageRegistrationError:
    # Registration failed: revert all changes to the extensions to avoid
    # leaving them in an inconsistent state.
    _restore_extensions(extensions_backup)
    raise


def is_extension_package(package: types.ModuleType) -> bool:
  """Returns whether the module is a GDM extension package."""
  return hasattr(package, "export_extensions")


def is_registered(package: types.ModuleType) -> bool:
  """Returns whether the package has been registered.

  Args:
    package: Extension package to register (typically its __init__ module). For
      package specification, see the 'register' function docstring.
  """
  package_name = package.__name__.split(".")[-1]
  return package_name in extensions.package_info


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


def get_cli_extension_packages() -> list[str]:
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

  if (not hasattr(package, "export_extensions") or
      not callable(package.export_extensions)):
    raise errors.PackageRegistrationError(
        "Package must define an 'export_extensions' function.",
        package_name=package_name)


def _register(
    new_extensions: MutableMapping[str, Any],
    package_name: str,
    package_version: str,
    package_import_path: str,
    download_key: Optional[Callable[[data_types.KeyInfo, str], None]]) -> None:
  """Registers the given extensions with GDM architecture.

  Args:
    new_extensions: Extensions to register with GDM architecture. See the
      register() docstring for format details.
    package_name: Name of the package being registered.
    package_version: Version of the package being registered.
    package_import_path: Import path of the package.
    download_key: download_key function of the package. Allowed to be None if
      the package doesn't export and keys.

  Raises:
    PackageRegistrationError: The provided extensions are invalid.
  """
  _validate_device_class_type_and_uniqueness(
      ext_auxiliary_devices=new_extensions["auxiliary_devices"],
      ext_primary_devices=new_extensions["primary_devices"],
      ext_virtual_devices=new_extensions["virtual_devices"],
      package_name=package_name)

  (ext_capability_interfaces,
   ext_capability_flavors,
   ext_communication_types,
   ext_extra_aux_device_classes,
   aux_extra_primary_device_classes) = (
       _implicit_export(
           device_classes=tuple(
               itertools.chain(new_extensions["auxiliary_devices"],
                               new_extensions["primary_devices"],
                               new_extensions["virtual_devices"])),
           additional_capability_interfaces=new_extensions[
               "capability_interfaces"])
       )
  # Most interfaces and flavors can be exported implicitly. These unions are
  # only needed for corner cases where the implicit export logic doesn't work.
  # Most device classes are exported explicitly. For additional device classes
  # exported implicitly, attributes not visible via reflection (detection
  # criteria and keys) are not registered.
  new_extensions["capability_interfaces"] = list(
      set(new_extensions["capability_interfaces"])
      | ext_capability_interfaces)
  new_extensions["capability_flavors"] = list(
      set(new_extensions["capability_flavors"])
      | ext_capability_flavors)
  new_extensions["communication_types"] = list(
      set(new_extensions["communication_types"])
      | ext_communication_types)
  new_extensions["auxiliary_devices"] = list(
      set(new_extensions["auxiliary_devices"])
      | ext_extra_aux_device_classes)
  new_extensions["primary_devices"] = list(
      set(new_extensions["primary_devices"])
      | aux_extra_primary_device_classes)
  _validate_device_class_type_and_uniqueness(
      ext_auxiliary_devices=new_extensions["auxiliary_devices"],
      ext_primary_devices=new_extensions["primary_devices"],
      ext_virtual_devices=new_extensions["virtual_devices"],
      package_name=package_name)

  _validate_capability_interfaces(
      ext_capability_interfaces=new_extensions["capability_interfaces"],
      package_name=package_name)
  new_capability_interfaces = {
      common_utils.generate_name(interface): interface
      for interface in new_extensions["capability_interfaces"]
  }
  # Capability interfaces have to be registered before validating flavors.
  extensions.capability_interfaces.update(new_capability_interfaces)
  new_capabilities = collections.defaultdict(set)
  # A capability name can map to several interfaces (and interface names).
  for if_name, interface in new_capability_interfaces.items():
    new_capabilities[interface.get_capability_name()].add(if_name)
  # Merge with existing capabilities.
  for capability_name, interface_names in new_capabilities.items():
    extensions.capabilities[capability_name] = interface_names.union(
        extensions.capabilities.get(capability_name, set()))

  _validate_capability_flavors(
      ext_capability_flavors=new_extensions["capability_flavors"],
      package_name=package_name)
  new_capability_flavors = {
      common_utils.generate_name(flavor): flavor
      for flavor in new_extensions["capability_flavors"]
  }
  # Capability flavors have to be registered before validating device classes.
  extensions.capability_flavors.update(new_capability_flavors)

  # Device class conformance can only be checked after capabilities have been
  # registered.
  _validate_device_class_conformance(
      tuple(itertools.chain(
          new_extensions["auxiliary_devices"],
          new_extensions["primary_devices"],
          new_extensions["virtual_devices"])),
      package_name=package_name)
  _validate_comm_type_classes(
      ext_communication_types=new_extensions["communication_types"],
      package_name=package_name)
  _validate_detect_criteria(
      ext_detect_criteria=new_extensions["detect_criteria"],
      ext_communication_types=new_extensions["communication_types"],
      package_name=package_name)
  _validate_keys(new_extensions["keys"], package_name=package_name)
  _validate_manager_cli_mixin(new_extensions["manager_cli_mixin"],
                              package_name=package_name)

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

  if (new_extensions["keys"] and
      (download_key is None or not callable(download_key))):
    raise errors.PackageRegistrationError(
        ("Package must define a 'download_key' function because it exports "
         "keys."),
        package_name=package_name)
  extensions.key_to_download_function.update({
      key_info: download_key for key_info in new_extensions["keys"]
  })
  if new_extensions["manager_cli_mixin"]:
    extensions.manager_cli_mixins.append(new_extensions["manager_cli_mixin"])

  extensions.package_info[package_name] = immutabledict.immutabledict({
      "version": package_version,
      "import_path": package_import_path,
  })


def _implicit_export(
    device_classes: Collection[type[_DeviceClassType]],
    additional_capability_interfaces: Collection[type[_CapabilityBase]],
) -> tuple[
    set[type[Any]],
    set[type[_CapabilityBase]],
    set[type[base_comms.CommunicationType]],
    set[type[_AuxiliaryDeviceBase]],
    set[type[_PrimaryDeviceBase]],
]:
  """Finds package contents by examining device classes.

  Args:
    device_classes: Device classes to examine to find all other extensions.
    additional_capability_interfaces: Capability interfaces explicitly exported
      by the package. This can be used to override the default logic finding
      capability interfaces.

  Returns:
    Package contents found via reflection: capability interfaces, capability
    flavors, communication types, additional (not present in device_classes)
    auxiliary device classes, and additional primary device classes. Additional
    virtual device classes are returned along with primary because they share
    the same interface.
  """
  # Finding all supported capabilities and device classes is an iterative
  # process. Device classes can export capability flavors and interfaces.
  # Capabilities can export device classes (typically auxiliary devices), which
  # can in turn export more capabilities, interfaces, and device classes.
  # Once we have a complete set of device classes and capabilities, we can find
  # all communication types and capability interfaces.
  all_new_capability_flavors = set()
  all_new_capability_interfaces: set[type[Any]] = set()
  unprocessed_device_classes = set(device_classes)
  all_new_device_classes = set()
  capability_device_classes = set()
  while unprocessed_device_classes:
    for new_device_class in unprocessed_device_classes:
      all_new_device_classes.add(new_device_class)
      new_capability_flavors = (
          new_device_class.get_supported_capability_flavors())
      all_new_capability_flavors.update(new_capability_flavors)
      new_capability_sub_flavors = set()
      for flavor in new_capability_flavors:
        new_capability_sub_flavors.update(flavor.get_sub_capability_flavors())
      all_new_capability_flavors.update(new_capability_sub_flavors)
      for flavor in new_capability_flavors | new_capability_sub_flavors:
        capability_device_classes |= flavor.get_used_device_classes()
    unprocessed_device_classes = (
        capability_device_classes - all_new_device_classes)

  for flavor in all_new_capability_flavors:
    for parent_class in flavor.__mro__[1:]:
      if parent_class in (object, abc.ABC, capability_base.CapabilityBase):
        continue  # Not an interface.
      # Interface is either an abstract class or a concrete class which
      # doesn't define any public methods.
      elif (inspect.isabstract(parent_class) or
            not([attr for attr in parent_class.__dict__.keys()
                 if not attr.startswith("_")]) or
            # Allow overriding the implicit export logic via explicit exports.
            parent_class in additional_capability_interfaces):
        all_new_capability_interfaces.add(parent_class)

  all_new_communication_types = {
      device_class.COMMUNICATION_TYPE
      for device_class in all_new_device_classes
      if device_class.COMMUNICATION_TYPE is not None
  }
  all_new_auxiliary_device_classes = {
      device_class
      for device_class in all_new_device_classes - set(device_classes)
      if issubclass(device_class, _AuxiliaryDeviceBase)
  }
  all_new_primary_device_classes = {
      device_class
      for device_class in all_new_device_classes - set(device_classes)
      if issubclass(device_class, _PrimaryDeviceBase)
  }

  return (
      all_new_capability_interfaces,
      all_new_capability_flavors,
      typing.cast(  # pytype doesn't understand these cannot be None.
          set[type[base_comms.CommunicationType]],
          all_new_communication_types),
      all_new_auxiliary_device_classes,
      all_new_primary_device_classes,
  )


def _validate_device_class_type_and_uniqueness(
    ext_auxiliary_devices: Collection[type[Any]],
    ext_primary_devices: Collection[type[Any]],
    ext_virtual_devices: Collection[type[Any]],
    package_name: str) -> None:
  """Validates extension device class type and uniqueness.

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

  exported_device_classes = set(itertools.chain(
      ext_auxiliary_devices, ext_primary_devices, ext_virtual_devices))
  known_device_classes = (
      set(extensions.auxiliary_devices) |
      set(extensions.primary_devices) |
      set(extensions.virtual_devices))
  exported_device_types = tuple(device_class.DEVICE_TYPE
                                for device_class in exported_device_classes)
  _assert_unique(exported_device_types,
                 names_description="Device types",
                 classes_description="device classes",
                 package_name=package_name)
  # Ignore identical device classes already registered by another package.
  new_device_classes = exported_device_classes.difference(known_device_classes)
  redefined_device_types = set.intersection(
      {device_class.DEVICE_TYPE for device_class in new_device_classes},
      {device_class.DEVICE_TYPE for device_class in known_device_classes})
  if redefined_device_types:
    raise errors.PackageRegistrationError(
        f"Device types {redefined_device_types} are already defined in GDM.",
        package_name=package_name)


def _validate_device_class_conformance(
    device_classes: Collection[type[_DeviceClassType]],
    package_name: str) -> None:
  """Validates conformance of extension device classes.

  This must be performed after capability interfaces and flavors have been
  implicitly exported and registered, because device class capability definition
  verification requires all capabilities to be known.

  Args:
    device_classes: Auxiliary, primary, and virtual device classes to validate.
    package_name: Name of the package providing the extension classes.

  Raises:
    PackageRegistrationError: Device classes are invalid.
  """
  conformance_issues = _get_device_class_conformance_issues(device_classes)
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
    device_classes: Collection[type[_DeviceClassType]]
) -> list[tuple[type[_DeviceClassType], list[str]]]:
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
    ext_communication_types: Collection[type[Any]],
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
    ext_detect_criteria: Mapping[str, base_detect_criteria.DetectQueryMapping],
    ext_communication_types: Collection[type[Any]],
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
      if not isinstance(query_name, base_detect_criteria.QueryEnum):
        raise errors.PackageRegistrationError(
            base_error + "Detection query keys must be {} instances.".format(
                base_detect_criteria.QueryEnum.__name__),
            package_name=package_name)
      if (not callable(query)
          or tuple(inspect.getfullargspec(query).args) != _EXPECTED_QUERY_ARGS):
        extra_error = ("Detection queries must be callable functions which "
                       "accept {} arguments: {}."
                       .format(len(_EXPECTED_QUERY_ARGS), _EXPECTED_QUERY_ARGS))
        raise errors.PackageRegistrationError(base_error + extra_error,
                                              package_name=package_name)

    if (comm_type_name not in extensions.detect_criteria and
        comm_type_name not in extension_comm_type_names):
      raise errors.PackageRegistrationError(
          "Unable to register detection criteria for communication type "
          f"{comm_type_name!r} as it has not been exported by the package.",
          package_name=package_name)


def _validate_capability_interfaces(
    ext_capability_interfaces: Collection[type[Any]],
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

  new_capabilities = collections.defaultdict(set)
  for interface in ext_capability_interfaces:
    try:
      capability_name = interface.get_capability_name()
    except TypeError:
      # Interface did not override name generation logic and isn't recognized
      # by GDM yet. CapabilityBase.get_capability_name() is based on
      # CapabilityBase.get_capability_interface(), which doesn't work until the
      # interface is registered with GDM. Fall back to the same name generation
      # logic without the call to get_capability_interface().
      capability_name = capability_base.get_default_capability_name(interface)
    new_capabilities[capability_name].add(interface)

  _assert_unique((list(new_capability_interfaces.keys())
                  + list(new_capabilities.keys())),
                 names_description="Capability interface and capability names",
                 classes_description="capability interfaces and capabilities",
                 package_name=package_name)

  capability_names_to_interfaces = copy.deepcopy(new_capabilities)
  for cap_name, if_names in extensions.capabilities.items():
    capability_names_to_interfaces[cap_name] |= {
        extensions.capability_interfaces[if_name] for if_name in if_names}

  # Check that all capability interfaces with an identical name share the same
  # interface.
  for capability_name, interfaces in capability_names_to_interfaces.items():
    try:
      conformance_utils.get_shared_capability_interface(interfaces)
    except ValueError as err:
      raise errors.PackageRegistrationError(
          f"Interfaces for capability {capability_name!r} do not inherit from "
          "a common interface class. If several capability interfaces share "
          "the same capability name, they must inherit from a shared "
          "interface.",
          package_name=package_name) from err


def _validate_capability_flavors(ext_capability_flavors: Collection[type[Any]],
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
    capability_flavors: Collection[type[_CapabilityBase]]
) -> list[tuple[type[_CapabilityBase], list[str]]]:
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
    PackageRegistrationError: Provided keys are invalid or have overlaps in key
      file paths.
  """
  if not all(isinstance(key, data_types.KeyInfo) for key in keys):
    raise errors.PackageRegistrationError(
        "Keys must be data_types.KeyInfo instances.",
        package_name=package_name)

  # Deduplicate keys by object ID. Allow multiple packages to register the same
  # key object ("<object1> is <object2>") to enable sharing of keys between
  # packages. Disallow registering equal keys (different objects) to prevent
  # keys from one package from overwriting another. Use id(<object>) to check
  # whether objects are the same. Dict keys are unique (with later values
  # overwriting earlier values in case of collisions), so we can use a dict to
  # deduplicate by object ID.
  id_to_key_info_old_and_new_keys = {
      id(key): key
      for key in list(extensions.key_to_download_function) + list(keys)}
  key_paths = [
      host_utils.get_key_path(key)
      for key in id_to_key_info_old_and_new_keys.values()]
  _assert_unique(key_paths, "Key file paths", "keys", package_name)


def _validate_manager_cli_mixin(manager_cli_mixin: Optional[type[Any]],
                                package_name: str) -> None:
  """Validates the provided FireManager mixin.

  Args:
    manager_cli_mixin: None or a class object inheriting from FireManager.
    package_name: Name of the extension package.

  Raises:
    PackageRegistrationError: The provided FireManager mixin is invalid.
  """
  if manager_cli_mixin is None:
    return

  if inspect.isclass(manager_cli_mixin):  # Non-classes don't have __mro__.
    # fire_manager is not imported for a subclass check to prevent a circular
    # import.
    mro_class_names = [
        a_class.__name__ for a_class in manager_cli_mixin.__mro__]
    is_invalid = (inspect.isabstract(manager_cli_mixin)
                  or "FireManager" not in mro_class_names)
  else:
    is_invalid = True

  if is_invalid:
    raise errors.PackageRegistrationError(
        "Provided FireManager mixin class is invalid. It must be None or a "
        "concrete class object which inherits from gazoo_device.FireManager.",
        package_name=package_name)


def _assert_subclasses(classes: Collection[type[Any]],
                       parent: type[Any],
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
    for cls in abstract_classes:
      cls_methods = [
          method for method in inspect.getmembers(cls, inspect.isfunction)
      ]
      abstract_methods = [
          method[0]
          for method in cls_methods
          if getattr(method[1], "__isabstractmethod__", False)
      ]
      error_messages.append(
          f"{cls.__name__} has unimplemented abstract methods:"
          f" {', '.join(abstract_methods)}."
      )

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
    classes_description: Description of the classes.
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


def _raise_if_redefined(new_classes: Mapping[str, type[Any]],
                        old_classes: Mapping[str, type[Any]],
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
  # Look for an intersection between old and new, but skip cases where a class
  # is being re-registered (same class already known from another package).
  redefined_names = [
      class_name
      for class_name in set(old_classes.keys()) & set(new_classes.keys())
      if new_classes[class_name] is not old_classes[class_name]
  ]
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
          copy.deepcopy(extensions.capabilities),
          extensions.capability_flavors.copy(),
          extensions.auxiliary_devices.copy(),
          extensions.primary_devices.copy(),
          extensions.virtual_devices.copy(),
          extensions.communication_types.copy(),
          copy.deepcopy(extensions.detect_criteria),
          copy.deepcopy(extensions.package_info),
          extensions.key_to_download_function.copy())


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
   extensions.key_to_download_function) = backup_copy
