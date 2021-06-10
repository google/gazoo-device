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

"""Helper methods for validating architecture conformance."""
import inspect
import re
from typing import Any, Callable, Collection, List, NoReturn, Optional, Tuple
from typing import Type, Union
from gazoo_device import decorators
from gazoo_device import manager
from gazoo_device.base_classes import auxiliary_device
from gazoo_device.base_classes import auxiliary_device_base
from gazoo_device.base_classes import gazoo_device_base
from gazoo_device.base_classes import primary_device_base
from gazoo_device.capabilities.interfaces import capability_base

_ALLOWED_PROPERTY_TYPES_CAPABILITY = (decorators.PersistentProperty,
                                      decorators.DynamicProperty,
                                      decorators.OptionalProperty)
_ALLOWED_PROPERTY_TYPES_DEVICE = (decorators.PersistentProperty,
                                  decorators.DynamicProperty,
                                  decorators.OptionalProperty,
                                  decorators.CapabilityProperty)
_LOG_DECORATOR_BASE_CLASSES = (auxiliary_device.AuxiliaryDevice,
                               gazoo_device_base.GazooDeviceBase,
                               capability_base.CapabilityBase)
_PUBLIC_METHOD_BASE_CLASSES = (primary_device_base.PrimaryDeviceBase,
                               gazoo_device_base.GazooDeviceBase,
                               auxiliary_device.AuxiliaryDevice,
                               auxiliary_device_base.AuxiliaryDeviceBase)
_REQUIRED_DEVICE_CLASS_CONSTANTS = ("DEVICE_TYPE",
                                    "COMMUNICATION_TYPE",
                                    "DETECT_MATCH_CRITERIA",
                                    "_OWNER_EMAIL")
_RETURN_SECTION_MULTILINE = r"\n\s*Returns:\s*\n"
_RETURN_SECTION_ONELINE = r"\b(R|r)eturn(s)?\b"
_MISMATCHING_SIGNATURE_TEMPLATE = """\tMethod: {}
\t\tInherited signature:
\t\t{}
\t\tConflicting signature(s) inherited from:
\t\t{}."""

_LogDecoratorType = Union[Type[auxiliary_device.AuxiliaryDevice],
                          Type[gazoo_device_base.GazooDeviceBase],
                          Type[capability_base.CapabilityBase]]


def get_invalid_capability_definitions(
    device_class: Type[Any]) -> List[Tuple[str, str]]:
  """Returns all invalid capability definitions in the device class."""
  invalid_definitions = []
  for attr_name, attr in inspect.getmembers(device_class):
    if isinstance(attr, decorators.CapabilityProperty):
      try:
        _validate_capability_definition(attr)
      except (TypeError, ValueError, RuntimeError) as e:
        invalid_definitions.append((attr_name, repr(e)))
  return invalid_definitions


def get_invalid_health_check_names(device_class: Type[Any]) -> List[str]:
  """Returns names of health checks which do not start with "check_<...>"."""
  incompliant_attrs = []
  for attr_name, attr in inspect.getmembers(device_class):
    if (callable(attr)
        and hasattr(attr, "__health_check__") and
        not attr_name.startswith("check_")):
      incompliant_attrs.append(attr_name)
  return incompliant_attrs


def get_invalid_public_methods(
    device_class: Type[Any],
    excluded_methods: Optional[Collection[str]] = None) -> List[str]:
  """Returns names of public methods which are not allowed.

  The only allowed public methods are:
    * the ones required by base_classes/primary_device_base.py;
    * the ones added in base_classes/gazoo_device_base.py;
    * health checks;
    * deprecated aliases.
  All other public functionality in device classes must be implemented as
  capabilities.

  Args:
    device_class: Device class to check.
    excluded_methods: Names of methods to exclude from this check.

  Returns:
    Names of incompliant attribute names.
  """
  excluded_methods = excluded_methods or []
  incompliant_attrs = []
  base_attrs = set()
  for base_class in _PUBLIC_METHOD_BASE_CLASSES:
    base_attrs |= set(vars(base_class))

  for attr_name, attr in inspect.getmembers(device_class):
    if (not attr_name.startswith("_")
        and callable(attr)
        and not hasattr(attr, "__deprecated__")
        and not hasattr(attr, "__health_check__")
        and attr_name not in base_attrs
        and attr_name not in excluded_methods):
      incompliant_attrs.append(attr_name)
  return incompliant_attrs


def get_log_decorator_violators(cls: _LogDecoratorType,
                                check_inherited: bool = True) -> List[str]:
  """Returns method names which do not comply with the log decorator.

  Every public method without a return value must be decorated with
  @decorators.LogDecorator(<logger>).

  Args:
    cls: Class inheriting from AuxiliaryDevice, GazooDeviceBase, or
      CapabilityBase.
    check_inherited: Whether inherited methods need to be checked for
      compliance.

  Returns:
    Names of incompliant methods.

  Raises:
    TypeError: Invalid class provided.
  """
  if not issubclass(cls, _LOG_DECORATOR_BASE_CLASSES):
    raise TypeError(
        "Can only check log decorator API compliance for instances of "
        "{}. Found type: {}.".format(_LOG_DECORATOR_BASE_CLASSES, cls))

  incompliant_methods = []
  if check_inherited:
    attribute_names = dir(cls)
  else:
    attribute_names = vars(cls).keys()

  for attribute_name in attribute_names:
    attribute = getattr(cls, attribute_name)
    if _is_decoration_required(attribute):
      incompliant_methods.append(attribute_name)
  return incompliant_methods


def get_mismatching_signatures(
    cls: Type[Any],
    excluded_methods: Optional[Collection[str]] = None
) -> List[Tuple[str, str, List[str]]]:
  """Returns methods that do not include same args as the parent method.

  In other words, if a parent defines a method 'some_method' and the given
  class (cls) also defines the same method, add 'some_method' to list of
  mismatching signatures if cls.some_method signature does not start with the
  parent.some_method signature. Ignores __init__ and __new__ signatures.

  Args:
    cls: Class object to check methods signatures of.
    excluded_methods: Method names for which to ignore mismatched signatures.

  Returns:
    List of tuples, where each entry is
    (method name,
     class with method definition and method signature,
     [list of parents with different method signatures and signatures]).
  """
  excluded_methods = excluded_methods or []
  parents = cls.__mro__[1:]
  mismatches = []

  for attr_name, attr in inspect.getmembers(cls):
    if (inspect.isfunction(attr) or inspect.ismethod(attr)):
      if attr_name in ["__init__", "__new__"]:
        continue
      child_method = decorators.unwrap(attr)
      child_signature = inspect.getfullargspec(child_method).args

      parents_with_method = [
          parent for parent in parents if attr_name in parent.__dict__
      ]
      if attr_name in cls.__dict__:
        signature_defined_in = cls
      else:
        signature_defined_in = parents_with_method[0]

      parents_with_conflicting_signature = []
      for parent in parents_with_method:
        parent_method = decorators.unwrap(getattr(parent, attr_name))
        parent_signature = inspect.getfullargspec(parent_method).args

        len_parent = len(parent_signature)
        if child_signature[:len_parent] != parent_signature:
          parents_with_conflicting_signature.append("{}.{}.{}({})".format(
              parent.__module__, parent.__name__, attr_name,
              ", ".join(parent_signature)))

      if (parents_with_conflicting_signature
          and attr_name not in excluded_methods):
        mismatches.append(
            (attr_name,
             "{}.{}.{}({})".format(signature_defined_in.__module__,
                                   signature_defined_in.__name__,
                                   attr_name,
                                   ", ".join(child_signature)),
             parents_with_conflicting_signature))
  return mismatches


def get_mismatching_signature_err_strs(
    classes: Collection[Type[Any]],
    excluded_methods: Optional[Collection[str]] = None) -> List[str]:
  """Returns a list of the errors for the mismatched signatures on the classes.

  Looks for class signatures that don't match their parent's signatures.
  Unlike normal linting, it allows for children to add additional args as long
  as they start with the parent's args.

  Args:
    classes: Classes to look for mismatching signatures in their methods.
    excluded_methods: Method names for which to ignore mismatched signatures.

  Returns:
    Error messages identifying classes and their methods with mismatched
    signatures.
  """
  mismatches_strs = []
  for cls in classes:
    mismatching_signatures = get_mismatching_signatures(cls, excluded_methods)
    if mismatching_signatures:
      mismatching_signatures_str = "\n".join(
          _MISMATCHING_SIGNATURE_TEMPLATE.format(
              method, child_sig, "\n\t\t".join(parent_sigs))
          for method, child_sig, parent_sigs in mismatching_signatures)
      mismatches_strs.append("Class {}:\n{}".format(cls,
                                                    mismatching_signatures_str))
  return mismatches_strs


def get_uncategorized_properties(
    cls: Type[Any],
    excluded_properties: Optional[Collection[str]] = None) -> List[str]:
  """Returns names of public properties which do not fall into a known category.

  Allowed categories: persistent, dynamic, optional properties.
  Device classes can also define capabilities.

  Args:
    cls: Class object to check.
    excluded_properties: Names of properties to exclude from this check.

  Returns:
    Names of incompliant properties.
  """
  excluded_properties = excluded_properties or []
  if issubclass(cls, capability_base.CapabilityBase):
    allowed_property_types = _ALLOWED_PROPERTY_TYPES_CAPABILITY
  else:
    allowed_property_types = _ALLOWED_PROPERTY_TYPES_DEVICE
  incompliant_properties = []
  for attr_name, attr in inspect.getmembers(cls):
    if (not attr_name.startswith("_")
        and isinstance(attr, property)
        and attr_name not in excluded_properties
        and not hasattr(attr.fget, "__deprecated__")
        and not isinstance(attr, allowed_property_types)):
      incompliant_properties.append(attr_name)
  return incompliant_properties


def get_unset_constants(device_class: Type[Any]) -> List[str]:
  """Returns names of unset required class constants."""
  return [attr for attr in _REQUIRED_DEVICE_CLASS_CONSTANTS
          if not getattr(device_class, attr, None)]


def _validate_capability_definition(
    capability_property: decorators.CapabilityProperty) -> None:
  """Raises an error if the capability definition is invalid."""
  flavor_classes = list(capability_property.capability_classes)
  all_flavors = manager.Manager.get_all_supported_capability_flavors().values()
  for flavor_class in flavor_classes:
    if not inspect.isclass(flavor_class):
      raise TypeError("Object {} is not a class object.".format(flavor_class))
    if not issubclass(flavor_class, capability_base.CapabilityBase):
      raise TypeError(
          "Object {} is not a subclass of CapabilityBase.".format(flavor_class))
    if flavor_class not in all_flavors:
      raise ValueError(
          "Capability class {} is not supported. "
          "Supported capability classes: {}.".format(flavor_class, all_flavors))

  expected_capability_interface = flavor_classes[0].get_capability_interface()
  for flavor_class in flavor_classes[1:]:
    capability_interface = flavor_class.get_capability_interface()
    if capability_interface != expected_capability_interface:
      raise RuntimeError(
          "Not all capability flavors share the same capability interface. "
          "Differing interfaces: {}, {}."
          .format(expected_capability_interface, capability_interface))

  expected_name = expected_capability_interface.get_capability_name()
  if capability_property.fget.__name__ != expected_name:
    raise RuntimeError(
        "Attempting to define capability flavor(s) {} under invalid name {}. "
        "Capability interface: {}, expected name: {}.".format(
            flavor_classes, capability_property.fget.__name__,
            expected_capability_interface, expected_name))


def _is_instance_method(obj: Any) -> bool:
  """Returns True if obj is an instance method (bound or unbound)."""
  # "Unbound" methods are considered functions in Python 3
  is_method_or_func = inspect.ismethod(obj) or inspect.isfunction(obj)

  if is_method_or_func:
    unwrapped_func = decorators.unwrap(obj)
    args = inspect.getfullargspec(unwrapped_func).args
    return bool(args) and args[0] == "self"

  return False


def _is_decoration_required(attr: Any) -> bool:
  """Check if log decorator is required for this attribute.

  Methods that need to be decorated are public class instance methods which do
  not return a value.

  Args:
    attr: Attribute to check.

  Returns:
    Whether the attribute should be decorated with the log decorator.
  """
  return (_is_instance_method(attr)  # Bound or unbound instance method
          and not attr.__name__.startswith("_")  # Public
          and not getattr(attr, "__isabstractmethod__", False)  # Not abstract
          and not _has_return_value(attr)  # Has a return other than None
          and decorators.WRAPS_ATTR_NAME not in attr.__dict__)  # Not decorated


def _has_return_value(method: Callable[..., Any]) -> Optional[bool]:
  """Returns True if the method returns anything other than None.

  Args:
    method: Method to check.

  Returns:
    bool: True if the method has a return value, False otherwise.
    None: If it's not possible to tell (no docstring and no type annotation).
  """
  has_return_value = _has_return_value_from_type_annotation(method)
  if has_return_value is None:  # No return type annotation
    has_return_value = _has_return_value_from_docstring(method)
  return has_return_value


def _has_return_value_from_docstring(
    method: Callable[..., Any]) -> Optional[bool]:
  """Parses the docstring to determine if the method returns a value.

  Args:
    method: Method to check.

  Returns:
    bool: True if the method has a return value, False otherwise.
    None: If it's not possible to tell (no docstring).
  """
  docstring = method.__doc__
  if docstring is None:
    return None
  if len(docstring.splitlines()) > 1:  # Multi-line docstring
    return re.search(_RETURN_SECTION_MULTILINE, docstring) is not None
  else:
    return re.search(_RETURN_SECTION_ONELINE, docstring) is not None


def _has_return_value_from_type_annotation(
    method: Callable[..., Any]) -> Optional[bool]:
  """Examines the type annotation to determine if method returns.

  Args:
    method: method to check.

  Returns:
    bool: True if the method has a return value, False otherwise.
    None: If it's not possible to tell (no return value type annotation).
  """
  type_annotations = inspect.getfullargspec(method).annotations
  if "return" not in type_annotations:
    return None
  return type_annotations["return"] not in [None, NoReturn]
