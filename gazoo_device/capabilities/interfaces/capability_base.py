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

"""Capability base class. All capabilities must inherit from this class.

Serves two purposes:
- Enforce all capabilities to have a device_name attribute.
  This is a requirement for informative log and error messages in multi-device testing.
- Dynamically identify all capabilities supported by GDM.
  This is accomplished by scanning the capabilities folder and identifying all classes
  which subclass CapabilityBase.
"""
from __future__ import absolute_import
import abc
import six
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.utility import common_utils
from gazoo_device.utility import supported_classes

logger = gdm_logger.get_gdm_logger()
_CAPABILITY_INTERFACE_SUFFIX = "_base"
_capability_name_cache = {}


class CapabilityBase(six.with_metaclass(abc.ABCMeta), object):
    """Abstract base class for all capabilities."""

    def __init__(self, device_name):
        """Set the device_name attribute of the capability.

        Args:
            device_name (str): name of the device instance the capability is attached to.

        Note:
            All capabilities need to include the device name attribute to support error and log
            messages in multi-device testing.
        """
        self._device_name = device_name
        self._healthy = False

    @property
    def healthy(self):
        """Whether or not the capability has passed a health_check."""
        return self._healthy

    @decorators.CapabilityLogDecorator(logger, level=decorators.DEBUG)
    def health_check(self):
        """Overridden. Checks capability readiness."""
        self._healthy = True

    @classmethod
    def get_capability_interface(cls):
        """Returns the capability interface class of the given capability flavor or interface.

        Returns:
            type: capability interface class of this capability flavor.

        Note:
            If called on a flavor class, the nearest parent interface will be returned.
                KeypadDefault.get_capability_interface() -> <class keypad_base.KeypadBase>
            If called on an interface class, the same interface class will be returned.
                KeypadBase.get_capability_interface() -> <class keypad_base.KeypadBase>
            If called on CapabilityBase class, returns CapabilityBase (special case).

        Raises:
            GazooDeviceError: if the capability flavor does not inherit from any capability
                             interface.
        """
        if cls is CapabilityBase:
            return CapabilityBase
        for parent_class in cls.__mro__:
            if parent_class in supported_classes.SUPPORTED_CAPABILITY_INTERFACES.values():
                return parent_class
        raise errors.GazooDeviceError(
            "Capability {} does not inherit from a capability interface.".format(cls))

    @classmethod
    def get_capability_name(cls):
        """Generate the name under which a capability is accessible in a device class.

        Returns:
            str: capability name to use in device class capability definitions.

        Note:
            This is the default implementation. Override if necessary.

        Raises:
            GazooDeviceError: if unable to generate the name because the capability interface does
                             not follow the standard naming convention (<some_capability>Base).

        Examples:
            KeypadBase.get_capability_name() -> "keypad"
            KeypadDefault.get_capability_name() -> "keypad"
            COEventsBase.get_capability_name() -> "co_events"
        """
        interface = cls.get_capability_interface()
        snake_case_name = common_utils.title_to_snake_case(interface.__name__)
        if not snake_case_name.endswith(_CAPABILITY_INTERFACE_SUFFIX):
            raise errors.GazooDeviceError(
                "Unable to automatically generate the capability name for capability {} "
                "from interface {}. Interface snake case name {} does not end with '{}'"
                .format(cls, interface, snake_case_name, _CAPABILITY_INTERFACE_SUFFIX))
        return snake_case_name[:-len(_CAPABILITY_INTERFACE_SUFFIX)]

    @decorators.CapabilityLogDecorator(logger, level=None)
    def validate_required_keys(self, key_list, dictionary, dictionary_name):
        """Verify that the required keys are present in the provided dictionary.

        Args:
            key_list (list): list of required keys (string) for the provided dictionary.
            dictionary (dict): dictionary to check for all the required keys.
            dictionary_name (str): name (or purpose) of the dictionary.
                                   Only used in the error message. For example, "Commands".

        Raises:
            GazooDeviceError: if a required key is missing from the dictionary.
            GazooDeviceError: if "dictionary" argument is not a dictionary instance.

        Note:
            self._device_name must be set before calling this method (by CapabilityBase.__init__).
        """
        base_msg = "{} failed to create {!r} capability.".format(self._device_name,
                                                                 self.get_capability_name())
        if not isinstance(dictionary, dict):
            extra_msg = " Expected {!r} to be a dict, found {}".format(dictionary_name, dictionary)
            raise errors.GazooDeviceError(base_msg + extra_msg)

        missing_keys = [key for key in key_list if key not in dictionary]
        if missing_keys:
            extra_msg = " Dictionary {!r} is missing the following keys: {}".format(
                dictionary_name, missing_keys)
            raise errors.GazooDeviceError(base_msg + extra_msg)

    @classmethod
    def _get_capability_name(cls):
        """Add error checking and caching to capability name generation.

        Returns:
            str: capability name to use in device class capability definitions.

        Raises:
            GazooDeviceError: if cls is CapabilityBase.
        """
        if cls is CapabilityBase:
            raise errors.GazooDeviceError(
                "Cannot generate a capability name for CapabilityBase interface.")

        if cls not in _capability_name_cache:
            _capability_name_cache[cls] = cls.get_capability_name()
        return _capability_name_cache[cls]
