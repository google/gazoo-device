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

"""Capability base class.

All capabilities must inherit from this class.

Serves two purposes:
- Enforce all capabilities to have a device_name attribute.
  This is a requirement for informative log and error messages in multi-device
  testing.
- Dynamically identify all capabilities supported by GDM.
  This is accomplished by scanning the capabilities folder and identifying all
  classes
  which subclass CapabilityBase.
"""
import abc
import functools
from typing import Any, Collection, Dict, Type
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import extensions
from gazoo_device import gdm_logger
from gazoo_device.utility import common_utils

logger = gdm_logger.get_logger()
_CAPABILITY_INTERFACE_SUFFIX = "_base"


class CapabilityBase(abc.ABC):
  """Abstract base class for all capabilities."""

  def __init__(self, device_name):
    """Set the device_name attribute of the capability.

    Args:
      device_name (str): name of the device instance the capability is attached
        to. Used for error and log messages in multi-device tests.
    """
    self._device_name = device_name
    self._healthy = None

  @decorators.CapabilityLogDecorator(logger, level=decorators.DEBUG)
  def close(self):
    """Performs cleanup and releases capability resources."""

  @decorators.DynamicProperty
  def healthy(self):
    """Whether or not the capability has passed a health_check."""
    if self._healthy is None:
      try:
        self.health_check()
        self._healthy = True
      except errors.CapabilityNotReadyError:
        self._healthy = False
    return self._healthy

  @decorators.CapabilityLogDecorator(logger, level=decorators.DEBUG)
  def health_check(self):
    """Overridden. Checks capability readiness."""
    self._healthy = True

  @classmethod
  def get_capability_interface(cls):
    """Returns the capability interface class.

    If called on a flavor class, the nearest parent interface will be
    returned: FileTransferScp.get_capability_interface() ->
      <class file_transfer_base.FileTransferBase>.

    If called on an interface class, the same interface class will be
    returned: FileTransferBase.get_capability_interface() ->
      <class file_transfer_base.FileTransferBase>.

    If called on CapabilityBase class, returns CapabilityBase (special case):
      CapabilityBase.get_capability_interface() -> <class CapabilityBase>.

    Returns:
      type: capability interface class of this capability flavor.

    Raises:
      TypeError: if the capability flavor does not inherit from any
        capability interface.
    """
    if cls is CapabilityBase:
      return CapabilityBase
    for parent_class in cls.__mro__:
      if parent_class in extensions.capability_interfaces.values():
        return parent_class
    raise TypeError(
        "Capability {} does not inherit from a capability interface.".format(
            cls))

  @classmethod
  @functools.lru_cache(maxsize=None)
  def get_capability_name(cls) -> str:
    """Returns the name under which capability is accessible in device class.

    This default implementation can be overridden in special cases.
    Examples:
      FileTransferBase.get_capability_name() -> "file_transfer"
      FileTransferScp.get_capability_name() -> "file_transfer"
      ABCDEventsBase.get_capability_name() -> "abcd_events"
    """
    return get_default_capability_name(cls.get_capability_interface())

  @decorators.CapabilityLogDecorator(logger, level=None)
  def validate_required_keys(self,
                             key_list: Collection[str],
                             dictionary: Dict[str, Any],
                             dictionary_name: str):
    """Verify that the required keys are present in the provided dictionary.

    self._device_name must be set before calling this method (by
    CapabilityBase.__init__). All raised errors are converted to DeviceError by
    the log decorator.

    Args:
      key_list: keys that are required in the dictionary.
      dictionary: to check for presence of all required keys.
      dictionary_name: name (or purpose) of the dictionary. Only
        used in the error message. For example, "Commands".

    Raises:
      KeyError: if a required key is missing from the dictionary.
    """
    missing_keys = [key for key in key_list if key not in dictionary]
    if missing_keys:
      raise KeyError(
          "{} failed to create {!r} capability. Dictionary {!r} is missing the "
          "following keys: {}".format(self._device_name,
                                      self.get_capability_name(),
                                      dictionary_name, missing_keys))


def get_default_capability_name(interface: Type[CapabilityBase]) -> str:
  """Generates the name under which a capability is accessible in device class.

  This is the default name generation logic.
  Examples:
    FileTransferBase -> "file_transfer"
    ABCDEventsBase -> "abcd_events"

  Args:
    interface (type): capability interface (a CapabilityBase subclass).

  Returns:
    str: capability name to use in device class capability definitions.

  Raises:
    RuntimeError: if unable to generate the name because the capability
      interface does not follow the standard naming convention
      (<some_capability>Base).
    ValueError: if the interface is CapabilityBase.
  """
  if interface is CapabilityBase:
    raise ValueError("Cannot generate a capability name for the CapabilityBase "
                     "interface.")
  snake_case_name = common_utils.title_to_snake_case(interface.__name__)
  if not snake_case_name.endswith(_CAPABILITY_INTERFACE_SUFFIX):
    raise RuntimeError(
        "Unable to automatically generate the capability name from "
        "capability interface {}. Interface snake case name {!r} does not "
        "end in {!r}. Either rename the interface or override "
        "get_capability_name() in the interface."
        .format(interface, snake_case_name, _CAPABILITY_INTERFACE_SUFFIX))
  return snake_case_name[:-len(_CAPABILITY_INTERFACE_SUFFIX)]
