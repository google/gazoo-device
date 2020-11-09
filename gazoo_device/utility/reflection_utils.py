# Copyright 2020 Google LLC
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

"""Utilities for analyzing GDM code at runtime (reflection)."""
import functools
import importlib
import inspect
import os

import gazoo_device

from gazoo_device import auxiliary_devices
from gazoo_device import config
from gazoo_device import gdm_logger
from gazoo_device import primary_devices
from gazoo_device import virtual_devices
from gazoo_device.base_classes import auxiliary_device
from gazoo_device.base_classes import gazoo_device_base
from gazoo_device.capabilities.interfaces import capability_base
from gazoo_device.utility import common_utils
from gazoo_device.utility import supported_classes


logger = gdm_logger.get_gdm_logger()

_PACKAGE_DIR = "gazoo_device/"


def identify_all_supported_classes():
    """Dynamically identify all device classes and capabilities supported by GDM.

    The results are stored in supported_classes.py to avoid circular imports.
    """
    if supported_classes.mappings_generated:
        return

    aux_classes = _get_all_device_classes(auxiliary_device.AuxiliaryDevice,
                                          auxiliary_devices)

    primary_classes = _get_all_device_classes(gazoo_device_base.GazooDeviceBase,
                                              primary_devices)

    virtual_classes = _get_all_device_classes(gazoo_device_base.GazooDeviceBase,
                                              virtual_devices)

    supported_classes.SUPPORTED_AUXILIARY_DEVICE_CLASSES = aux_classes
    supported_classes.SUPPORTED_PRIMARY_DEVICE_CLASSES = primary_classes
    supported_classes.SUPPORTED_VIRTUAL_DEVICE_CLASSES = virtual_classes

    supported_classes.SUPPORTED_CAPABILITY_INTERFACES = {
        common_utils.generate_name(interface): interface
        for interface in _get_all_supported_capability_interfaces()}

    supported_classes.SUPPORTED_CAPABILITY_FLAVORS = {
        common_utils.generate_name(flavor): flavor
        for flavor in _get_all_supported_capability_flavors()}

    supported_classes.SUPPORTED_CAPABILITIES = {
        interface.get_capability_name(): if_name
        for if_name, interface in supported_classes.SUPPORTED_CAPABILITY_INTERFACES.items()}

    supported_classes._mappings_generated = True


def get_all_subclasses_in_package(parent_class, package,
                                  excluded_modules=None, only_public=True):
    """Returns all classes derived from parent_class in any of the modules within the package.

    Does not recurse into subpackages (subdirectories will not be scanned).

    Args:
        parent_class (type): class object from which the subclasses must be derived.
        package (module): module (__init__.py) of package to scan.
        excluded_modules (list): list of modules to exclude from the scan.
        only_public (bool): whether to return only public or both public and private classes.

    Returns:
        dict: map from module to set of classes derived from parent_class defined in that module.
    """
    if excluded_modules is None:
        excluded_modules = set()

    modules = [module for module in _list_package_modules(package)
               if module not in excluded_modules]

    module_to_classes = {}
    for module in modules:
        public_classes = [member for name, member in inspect.getmembers(module)
                          if inspect.isclass(member) and
                          (not name.startswith("_") or not only_public)]
        derived_classes = [a_class for a_class in public_classes
                           if issubclass(a_class, parent_class)]
        if derived_classes:
            module_to_classes[module] = set(derived_classes)
    return module_to_classes


def _get_all_device_classes(base_class, package):
    """Dynamically identify all device classes using the base class in the package.

    Args:
       base_class (class): base class of device class
       package (module): package in which classes reside

    Note:
        - device classes must be in package folder;
        - all device classes must inherit from base class;
        - subdirectories of package folder will not be scanned.

    Returns:
        list: all device classes using the base class in the package.
    """
    device_class_list = []
    final_device_classes = []
    classes_superset = get_all_subclasses_in_package(base_class, package).values()
    for device_class_set in classes_superset:
        device_class_list += list(device_class_set)

    for device_class in device_class_list:
        class_name = _lowercase_object_name(device_class)
        if class_name.endswith("device") or class_name.endswith("base"):
            # remove any imported base classes
            continue
        else:
            final_device_classes.append(device_class)
    final_device_classes.sort(key=lambda x: x.DEVICE_TYPE)
    return final_device_classes


def _get_all_supported_capability_flavors():
    """Dynamically identify all capability flavors supported by GDM.

    Note:
        - capability flavors must be in gazoo_device/capabilities/ folder;
        - subdirectories of gazoo_device/capabilities/ will not be scanned.
          In other words, there must be no subfolders under gazoo_device/capabilities/.
        - capability flavors must (indirectly) inherit from CapabilityBase. Capability flavors
          should inherit from capability interfaces, which should inherit from CapabilityBase.

    Returns:
        set: all capability flavor classes supported by GDM.
    """
    flavor_module_to_classes = get_all_subclasses_in_package(
        capability_base.CapabilityBase, gazoo_device.capabilities)
    return functools.reduce(set.union, flavor_module_to_classes.values(), set())


def _get_all_supported_capability_interfaces():
    """Dynamically identify all capability interfaces supported by GDM.

    Note:
        - capability interfaces (abstract base classes) must be in
          gazoo_device/capabilities/interfaces/ folder;
        - subdirectories of gazoo_device/capabilities/interfaces/ will not be scanned.
          In other words, there must be no subfolders under gazoo_device/capabilities/interfaces/.
        - capability interfaces must inherit from CapabilityBase;
        - CapabilityBase class is excluded from the results.

    Returns:
        set: all capability interface classes supported by GDM.
    """
    interface_module_to_classes = get_all_subclasses_in_package(
        capability_base.CapabilityBase, gazoo_device.capabilities.interfaces,
        excluded_modules=[capability_base])
    return functools.reduce(set.union, interface_module_to_classes.values(), set())


def _get_module_path(module):
    """Return the module path.

    Args:
        module(module): python module object.

    Returns:
        str: path to the module.
    """
    module_path = module.__file__
    if module_path.startswith(config.PACKAGE_PATH):
        # No action necessary if root directories are the same
        return module_path
    else:
        if _PACKAGE_DIR in module_path:  # "<...path...>/gazoo_device/<...path remainder...>"
            path_remainder = module_path.split(_PACKAGE_DIR)[-1]
            return os.path.join(config.PACKAGE_PATH, path_remainder)
        else:  # Not a gazoo_device module.
            return module_path


def _list_package_modules(package):
    """List all modules defined in a package. Subpackages (subdirectories) are not scanned.

    Args:
        package(module): package to scan. For example, gazoo_device.capabilities.

    Returns:
        list: all modules that can be imported from the package.
    """
    suffix = ".py"
    suffix_len = len(suffix)

    package_path = _get_module_path(package)
    package_dir = os.path.dirname(package_path)
    files_in_package = os.listdir(package_dir)

    module_names = [a_file[:-suffix_len] for a_file in files_in_package
                    if a_file.endswith(suffix) and a_file != "__init__.py"]

    modules = []
    for module_name in module_names:
        try:
            modules.append(importlib.import_module(".{}".format(module_name),
                                                   package=package.__name__))
        except ImportError:
            logger.debug("Failed to import module {} from {}.".format(module_name,
                                                                      package.__name__))
    return modules


def _lowercase_object_name(a_object):
    return a_object.__name__.lower()
