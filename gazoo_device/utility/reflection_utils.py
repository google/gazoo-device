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

"""Utilities for analyzing GDM code at runtime (reflection)."""
import importlib
import inspect
import os
import types
from typing import Any, Callable, Collection, Dict, List, Optional, Set, Type

from gazoo_device import config
from gazoo_device import gdm_logger

logger = gdm_logger.get_logger()

_PACKAGE_DIR = "gazoo_device/"


def get_all_subclasses_in_module(
    parent_class: Type[Any],
    module: types.ModuleType,
    exclude_private: bool = True,
    exclude_abstract: bool = False) -> List[Type[Any]]:
  """Returns all classes derived from parent_class in the module.

  Args:
    parent_class: Class object from which the subclasses must be derived.
    module: Module to scan for subclasses.
    exclude_private: If True, do not include private classes.
    exclude_abstract: If True, do not include abstract classes.

  Returns:
    Subclasses of parent_class defined in the module.
  """
  subclasses = []
  for name, member in inspect.getmembers(module):
    if (inspect.isclass(member)
        and (not exclude_abstract or not inspect.isabstract(member))
        and (not exclude_private or not name.startswith("_"))
        and issubclass(member, parent_class)):
      subclasses.append(member)
  return subclasses


def _get_module_path(module: types.ModuleType) -> str:
  """Returns the module path."""
  return module.__file__


def get_all_subclasses_in_package(
    parent_class: Type[Any],
    package: types.ModuleType,
    excluded_modules: Optional[Collection[types.ModuleType]] = None,
    exclude_private: bool = True,
    exclude_abstract: bool = False,
    module_path_getter: Callable[[types.ModuleType], str] = _get_module_path
) -> Dict[types.ModuleType, Set[Type[Any]]]:
  """Returns classes derived from parent_class in modules within the package.

  Does not recurse into subpackages (subdirectories are not scanned).

  Args:
    parent_class: Class object from which the subclasses must be derived.
    package: __init__.py module of the package to scan.
    excluded_modules: Modules to exclude from the scan.
    exclude_private: If True, do not include private classes.
    exclude_abstract: If True, do not include abstract classes.
    module_path_getter: Function to retrieve the file path of a module.

  Returns:
    Mapping from module to set of classes derived from parent_class defined in
    that module.
  """
  if excluded_modules is None:
    excluded_modules = set()

  modules = [
      module for module in _list_package_modules(package, module_path_getter)
      if module not in excluded_modules
  ]

  module_to_classes = {}
  for module in modules:
    subclasses = get_all_subclasses_in_module(parent_class=parent_class,
                                              module=module,
                                              exclude_private=exclude_private,
                                              exclude_abstract=exclude_abstract)
    if subclasses:
      module_to_classes[module] = set(subclasses)
  return module_to_classes


def _list_package_modules(
    package: types.ModuleType,
    module_path_getter: Callable[[types.ModuleType], str] = _get_module_path
) -> List[types.ModuleType]:
  """Returns a list of all modules defined in the package.

  Subpackages (subdirectories) are not scanned.

  Args:
    package: __init__.py module of the package to scan. For example,
      gazoo_device.capabilities.
    module_path_getter: Function to retrieve the file path of a module.
  """
  suffix = ".py"
  suffix_len = len(suffix)

  package_path = module_path_getter(package)
  package_dir = os.path.dirname(package_path)
  files_in_package = os.listdir(package_dir)

  module_names = [
      a_file[:-suffix_len]
      for a_file in files_in_package
      if a_file.endswith(suffix) and a_file != "__init__.py"
  ]

  modules = []
  for module_name in module_names:
    modules.append(
        importlib.import_module(
            ".{}".format(module_name), package=package.__name__))
  return modules
