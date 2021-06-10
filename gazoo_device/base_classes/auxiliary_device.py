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

"""Base class for all auxiliary devices."""
import difflib
import functools
import inspect
import os
import re
import time
from typing import List, Set, Type
import weakref

from gazoo_device import config
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import extensions
from gazoo_device import gdm_logger
from gazoo_device.base_classes import auxiliary_device_base
from gazoo_device.capabilities.interfaces import capability_base
from gazoo_device.switchboard import log_process
from gazoo_device.utility import common_utils
from gazoo_device.utility import deprecation_utils

logger = gdm_logger.get_logger()

ERROR_PREFIX = "Exception_"
TIMEOUTS = {"CONNECTED": 3, "SHELL": 60}


def get_log_filename(log_directory, device_name, name_prefix=""):
  """Returns the full path of log filename using the information provided.

  Args:
      log_directory (path): to where the log file should be created.
      device_name (str): to use in the log filename
      name_prefix (str): string to prepend to the start of the log file.

  Returns:
      str: Path to log filename using the information provided.
  """

  log_timestamp = time.strftime("%Y%m%d-%H%M%S")
  if name_prefix:
    log_file_name = "{}-{}-{}.txt".format(name_prefix, device_name,
                                          log_timestamp)
  else:
    log_file_name = "{}-{}.txt".format(device_name, log_timestamp)
  return os.path.join(log_directory, log_file_name)


class AuxiliaryDevice(auxiliary_device_base.AuxiliaryDeviceBase):
  """Interface containing required GDM APIs for auxiliary devices."""
  _OWNER_EMAIL = ""  # override in child classes

  def __init__(self,
               manager,
               device_config,
               log_file_name=None,
               log_directory=None):
    """Initialize a device class with the serial port information provided.

    Args:
        manager(manager.Manager): Manager object for this device instance.
        device_config (dict): dict of two dicts, 'optional' device
          parameters and 'persistent' device parameters.
        log_file_name (str): file name in the log directory for device logs.
        log_directory (str): directory in which the controller will create
          the log file.
    """
    self.manager_weakref = weakref.ref(manager)

    # Create a dictionary to store "properties".  For now keep the
    # classification of "persistent" and "optional".
    self.props = {
        "persistent_identifiers": device_config["persistent"],
        "optional": device_config["options"]
    }

    self._regexes = {}
    self._commands = {}
    self._timeouts = TIMEOUTS.copy()
    # Initialize log files
    self.log_directory = log_directory
    if log_file_name:
      self._log_file_name = os.path.join(log_directory, log_file_name)
    else:
      log_name_prefix = device_config["log_name_prefix"]
      self._log_file_name = get_log_filename(
          log_directory, self.name, name_prefix=log_name_prefix)
    self.device_type = self.DEVICE_TYPE

  @decorators.OptionalProperty
  def alias(self):
    """Returns the user-defined device alias (string)."""
    return self.props["optional"]["alias"]

  @decorators.PersistentProperty
  def communication_address(self):
    """Returns the name of the main communication port.

    (e.g. ip address).

    Returns:
        str: path or address of main communication port.
    """
    return self.props["persistent_identifiers"].get("console_port_name")

  @decorators.PersistentProperty
  def commands(self):
    """Dictionary of commands issued to the device via shell."""
    return self._commands

  @decorators.DynamicProperty
  def connected(self):
    """Returns whether or not device is connected."""
    device_config = {"persistent": self.props["persistent_identifiers"]}
    return self.is_connected(device_config)

  @classmethod
  def get_dynamic_property_names(cls):
    """Returns a list of dynamic property names including capability ones."""
    return cls._get_property_names(decorators.DynamicProperty)

  @classmethod
  def get_persistent_property_names(cls):
    """Returns a list of persistent property names including capability ones."""
    names = cls._get_property_names(decorators.PersistentProperty)
    for property_value in config.CLASS_PROPERTY_TYPES:
      names += cls._get_property_names(property_value)
    return sorted(names)

  @classmethod
  def get_optional_property_names(cls):
    """Returns a list of optional property names including capability ones."""
    return cls._get_property_names(decorators.OptionalProperty)

  @decorators.PersistentProperty
  def health_checks(self):
    """Returns list of methods to execute as health checks."""
    return [self.check_device_connected]

  @decorators.DynamicProperty
  def log_file_name(self) -> str:
    """Current device log file name in use.

    Returns:
      Path to current device log file name.

    When the device has been recently created it might be possible that the log
    file path does not yet exist, but will be created very soon. The caller is
    expected to check if the file path returned exists. The caller should refer
    to this property often because log rotation might cause the log path to
    change depending on the max_log_size value currently in use.
    """
    current_log_filename = self._log_file_name

    # Check if log file has rotated to next log filename
    next_log_filename = log_process.get_next_log_filename(current_log_filename)
    while os.path.exists(next_log_filename):
      current_log_filename = next_log_filename
      next_log_filename = log_process.get_next_log_filename(
          current_log_filename)
    return current_log_filename

  @decorators.PersistentProperty
  def regexes(self):
    """Regular expressions used to retrieve properties, events and states from device output.

    Returns:
        dict: mapping of name to regular expression.
    """
    return self._regexes

  @decorators.PersistentProperty
  def model(self):
    """Returns the device model."""
    return self.props["persistent_identifiers"]["model"]

  @decorators.PersistentProperty
  def name(self):
    return self.props["persistent_identifiers"]["name"]

  @decorators.PersistentProperty
  def serial_number(self):
    return self.props["persistent_identifiers"]["serial_number"]

  @decorators.PersistentProperty
  def timeouts(self):
    """Dictionary of default timeouts to use when expecting certain actions."""
    return self._timeouts

  @decorators.health_check
  def check_create_switchboard(self):
    """Checks switchboard can be successfully created."""
    self.switchboard.add_log_note("{} switchboard successfully started.".format(
        self.name))

  @decorators.LogDecorator(logger)
  def check_device_ready(self):
    """Check device readiness by executing a series of health check methods."""
    self._execute_health_check_methods(self.health_checks)

  @decorators.LogDecorator(logger, decorators.DEBUG)
  def close(self):
    """Calls close on the communication ports and resets anything needed.

    Note:
        Resets the buttons and terminates the child processes.
    """
    self.reset_all_capabilities()

    if hasattr(self, "manager_weakref"):
      manager_instance = self.manager_weakref()
      if manager_instance is not None:
        if self.name in manager_instance._open_devices:
          self._log_object_lifecycle_event("close")
          del manager_instance._open_devices[self.name]
      del manager_instance

  @decorators.health_check
  def check_device_connected(self):
    """Checks that device shows up as a connection on the host machine.

    Raises:
       DeviceNotConnectedError: if device is not connected.
    """
    device_config = {"persistent": self.props["persistent_identifiers"]}
    try:
      common_utils.retry(
          func=self.is_connected,
          func_args=(device_config,),
          is_successful=bool,
          timeout=self.timeouts["CONNECTED"])
    except errors.CommunicationTimeoutError:
      raise errors.DeviceNotConnectedError(
          self.name, msg="device not reachable from host machine.")

  def get_capability_classes(
      self, capability_name: str) -> List[Type[capability_base.CapabilityBase]]:
    """Returns possible capability classes (flavors) for the capability.

    Args:
        capability_name (str): name of the capability, such as "switchboard"
          or "file_transfer".

    Returns:
        list[type]: capability classes that can be used for the capability.

    Raises:
        DeviceError: if the capability is not supported by the device.

    Note:
        For a given device class, most capabilities are implemented by just 1
        flavor. In a few cases, there are several flavors. Which flavor is used
        depends on the firmware version and is determined at runtime.
    """
    if not self.has_capabilities([capability_name]):
      raise errors.DeviceError(
          "{} get_capability_classes failed. "
          "Capability {} is not supported by {}."
          .format(self.name, capability_name, self.device_type))
    capability_property = getattr(type(self), capability_name)
    return list(capability_property.capability_classes)

  def get_dynamic_properties(self):
    """Returns a dictionary of prop, value for each dynamic property."""
    names = self.get_dynamic_property_names()
    return self._get_properties(names)

  def get_persistent_properties(self):
    """Returns a dictionary of prop, value for each persistent property."""
    names = self.get_persistent_property_names()
    return self._get_properties(names)

  def get_property(self, name, raise_error=False):
    """Retrieves a property value (can be nested).

    Args:
        name (str): name of a single property to fetch.
        raise_error (bool): raise error if unable to retrieve property

    Returns:
        object: value of the specified dynamic property.

    Raises:
        DeviceError: property value is not a plain data object.
        AttributeError: property doesn't exist.
        Exception: property is not retrieveable for arbitrary reason.

    Note:
        Expects property value to be a plain data object.
        Returns a string when property doesn't exist or property raises an
        error.
        Able to process both device properties (firmware_version) and
        capability properties (usb_hub.device_port)
    """
    instance = self
    try:
      if "." in name:  # capability property
        instance = getattr(self, name.split(".")[0])
        name = name.split(".")[1]

      value = getattr(instance, name)
      if callable(value):
        raise errors.DeviceError("{}'s {} is a method".format(self.name, name))
      return value
    except AttributeError:
      if name in self.props["optional"]:
        return self.props["optional"][name]
      if raise_error:
        raise
      close_matches = difflib.get_close_matches(name, self.get_property_names())
      return "{} does not have a known property '{}'. Close matches: {}".format(
          self.name, name, " or ".join(close_matches))
    except Exception as err:
      if raise_error:
        raise
      error_type = type(err).__name__
      logger.info("{} for {}, exception: {}".format(error_type, name, str(err)))
      return ERROR_PREFIX + error_type

  def get_property_names(self):
    """Returns a list of all property names."""
    full_list = list(self.get_dynamic_property_names())
    full_list.extend(self.get_persistent_property_names())
    full_list.extend(self.get_optional_property_names())
    full_list.extend(self.props["optional"])
    return list(set(full_list))

  def get_optional_properties(self):
    """Returns a dictionary of prop, value for each optional property."""
    names = self.get_optional_property_names()
    return self._get_properties(names)

  @classmethod
  def get_supported_capabilities(cls):
    """Returns a list of names of capabilities supported by this device class."""
    # Deduplicate names: there may be several flavors which share the same interface
    capability_names = {
        capability_class.get_capability_name()
        for capability_class in cls.get_supported_capability_flavors()
    }
    return sorted(list(capability_names))

  @classmethod
  def get_supported_capability_flavors(
      cls) -> Set[Type[capability_base.CapabilityBase]]:
    """Returns all capability flavor classes supported by this device class."""
    capability_classes = [
        member.capability_classes
        for _, member in inspect.getmembers(cls)
        if isinstance(member, decorators.CapabilityProperty)
    ]
    return functools.reduce(set.union, capability_classes, set())

  @classmethod
  def has_capabilities(cls, capability_names):
    """Check whether this device class supports all of the given capabilities.

    Args:
        capability_names (list): names of capabilities to check for.

    Note:
        capability_names (list): list of capability names.
            Capability names are strings. They can be:
                - capability names ("file_transfer"),
                - capability interface names ("filetransferbase"),
                - capability flavor names ("filetransferscp").
            If an interface name or capability name is specified, the behavior
            is identical: any capability flavor which implements the given
            interface will match. If a flavor name is specified, only that
            capability flavor will match. Different kinds of capability names
            can be used together (["usb_hub", "filetransferscp"]).

    Returns:
        bool: True if all of the given capabilities are supported by this
        device class, False otherwise.

    Raises:
        DeviceError: invalid type of capability_names argument OR
                     one of the capability names provided isn't recognized
                     by GDM.
    """
    valid_capability_names_types = (list, tuple, set)
    if not isinstance(capability_names, valid_capability_names_types):
      raise errors.DeviceError(
          "Invalid type of capability_names. Expected one of: {}, found: {}."
          .format(valid_capability_names_types, type(capability_names)))
    if not all(isinstance(cap_name, str) for cap_name in capability_names):
      raise errors.DeviceError(
          "All capability names must be of string type. Found: {}.".format(
              capability_names))

    capabilities = []  # Interface or flavor classes
    for cap_name in capability_names:
      cap_name = cap_name.lower()
      if cap_name in extensions.capability_flavors:
        interface_or_flavor = extensions.capability_flavors[cap_name]
      elif cap_name in extensions.capability_interfaces:
        interface_or_flavor = extensions.capability_interfaces[cap_name]
      elif cap_name in extensions.capabilities:
        interface_name = extensions.capabilities[cap_name]
        interface_or_flavor = extensions.capability_interfaces[interface_name]
      else:
        msg = "\n".join([
            "Capability {} is not recognized.".format(cap_name),
            "Supported capability interfaces: {}".format(
                extensions.capability_interfaces.keys()),
            "Supported capability flavors: {}".format(
                extensions.capability_flavors.keys()),
            "Supported capabilities: {}".format(
                extensions.capabilities.keys())
        ])
        raise errors.DeviceError(msg)
      capabilities.append(interface_or_flavor)

    supported_capabilities = cls.get_supported_capability_flavors()
    for requested_capability in capabilities:
      if not any(
          issubclass(supported_capability, requested_capability)
          for supported_capability in supported_capabilities):
        return False
    return True

  def is_capability_initialized(self, capability_name: str) -> bool:
    """Returns whether the capability has been initialized.

    Args:
        capability_name (str): name of the capability, such as "switchboard"
          or "file_transfer".

    Returns:
        bool: True if capability has been initialized, False otherwise.
    """
    capability_class = self.get_capability_classes(capability_name)[0]
    return hasattr(self, self._get_private_capability_name(capability_class))

  @decorators.LogDecorator(logger, decorators.DEBUG)
  def make_device_ready(self, setting: str = "on") -> None:
    """Checks device readiness and attempts recovery if allowed.

    If setting is 'off': does nothing.
    If setting is 'check_only': only checks readiness (recovery is skipped).
    If setting is 'on': checks readiness and attempts recovery
    self._RECOVERY_ATTEMPTS times.
    If setting is 'flash_build': same as 'on', but will attempt reflashing the
    device if it's supported and if all other recovery methods fail.

    Args:
      setting: 'on', 'off', 'check_only', or 'flash_build'.

    Raises:
      CheckDeviceReadyError: Re-raises the device readiness check error if
        unable to recover from it.
      DeviceError: If the recovery process raises an error.
    """
    if setting == "off":
      return

    recoverable_error = None
    unrecoverable_error = None
    for attempt in range(self._RECOVERY_ATTEMPTS):
      logger.info(f"{self.name} checking device readiness: attempt "
                  f"{attempt + 1} of {self._RECOVERY_ATTEMPTS}")
      try:
        self.check_device_ready()
      except errors.CheckDeviceReadyError as err:
        if setting == "check_only":
          logger.info(f"{self.name} make_device_ready setting is {setting!r}. "
                      "Skipping device recovery")
          raise
        # pylint: disable=unidiomatic-typecheck
        if type(recoverable_error) == type(err):
          logger.info(
              f"{self.name} readiness check raised the same error type "
              f"{type(err).__name__!r} after a recovery attempt. "
              "Assuming that the device is unable to recover. "
              f"Previous error: {recoverable_error!r}. New error: {err!r}")
          unrecoverable_error = err
          break
        recoverable_error = err
      else:
        if attempt != 0:
          logger.info(f"{self.name} successfully recovered to a ready state "
                      f"after {attempt + 1} recovery attempts")
        return

      logger.info(f"{self.name} attempting recovery: attempt {attempt + 1} "
                  f"of {self._RECOVERY_ATTEMPTS}")
      try:
        self.recover(recoverable_error)
      except errors.DeviceError as err:
        logger.info(
            f"{self.name} recovery attempt {attempt + 1} raised an error. "
            f"Assuming that the device is unable to recover. Error: {err!r}")
        unrecoverable_error = err
        break
    else:
      logger.info(f"{self.name} ran out of recovery attempts. "
                  "Executing a final device readiness check.")
      try:
        self.check_device_ready()
      except errors.CheckDeviceReadyError as err:
        unrecoverable_error = err
      else:
        logger.info(f"{self.name} successfully recovered to a ready state "
                    f"after {self._RECOVERY_ATTEMPTS} recovery attempts")
        return

    # If execution gets here, either recovery failed due to an error during
    # recover() or due to seeing the same CheckDeviceReadyError after a
    # successful recover() call, or recovery ran out of attempts.
    if setting != "flash_build" or not self.has_capabilities(["flash_build"]):
      if setting == "flash_build":
        logger.warning(f"{self.name} make_device_ready setting is {setting!r}, "
                       "but device does not support 'flash_build' capability")
      logger.info(f"{self.name} was not able to recover from "
                  f"{unrecoverable_error!r}")
      raise unrecoverable_error

    logger.info(f"{self.name} re-flashing device with the default build")
    self.flash_build.upgrade(forced_upgrade=True)
    logger.info(f"{self.name} checking device readiness after reflashing")
    self.check_device_ready()
    logger.info(f"{self.name} successfully recovered to a ready state")

  @decorators.PersistentProperty
  def owner(self) -> str:
    """Email of the owner (maintainer) of this device class."""
    return self._OWNER_EMAIL

  @decorators.LogDecorator(logger)
  def recover(self, error: errors.CheckDeviceReadyError) -> None:
    """Attempts to recover device based on the type of error specified.

    Args:
      error: A subclass of CheckDeviceReadyError that will be used to identify
        a possible recovery solution to use.

    Raises:
      CheckDeviceReadyError: If there are no recovery steps available for
        the error argument, it will be re-raised directly.
    """
    raise error

  @decorators.LogDecorator(logger, decorators.DEBUG)
  def reset_all_capabilities(self):
    """Resets all capabilities which have been initialized by deleting them.

    Capabilities will be re-initialized on next use (when they're accessed).
    """
    for capability_name in self.get_supported_capabilities():
      self.reset_capability(capability_name)

  @decorators.LogDecorator(logger, decorators.DEBUG)
  def reset_capability(self, capability_name: str) -> None:
    """Resets the capability if it's already initialized by deleting it.

    Calls the "close" method of the capability before deleting it.
    The capability will be re-initialized on next capability use (when it's
    accessed).

    Args:
        capability_name (str): name of the capability, such as "switchboard"
        or "file_transfer".
    """
    capability_class = self.get_capability_classes(capability_name)[0]
    capability_name = self._get_private_capability_name(capability_class)
    if hasattr(self, capability_name):
      getattr(self, capability_name).close()
      delattr(self, capability_name)

  @decorators.LogDecorator(logger, decorators.DEBUG)
  def set_property(self, prop, value):
    """Set an optional property.

    Args:
        prop (str): property name
        value (object): value of the property name.

    Raises:
        ValueError: if property is persistent or dynamic with no setter.
    """
    if prop in self.get_persistent_property_names():
      raise ValueError("{}'s {} is a persistent property and not settable. "
                       "Redetect device if it's wrong.".format(self.name, prop))
    if prop in self.get_dynamic_property_names():
      if not self._property_has_setter(prop):
        raise ValueError(
            "{}'s {} is a dynamic property which is not settable.".format(
                self.name, prop))
      instance = self
      if "." in prop:  # capability property
        instance = getattr(self, prop.split(".")[0])
        prop = prop.split(".")[1]
      setattr(instance, prop, value)
      return
    self.props["optional"][prop] = value

  def command_with_regex(self,
                         command,
                         regex,
                         command_fn,
                         regex_group=1,
                         raise_error=False,
                         tries=1,
                         **command_fn_kwargs):
    """Sends a command, searches for a regex in the response, and returns a match group.

    Args:
        command (str): command to issue.
        regex (str): regular expression with one or more capturing groups.
        command_fn (func): the function used to send the command.
        regex_group (int): number of regex group to return.
        raise_error (bool): whether or not to raise error if unable to find
          a match.
        tries (int): how many times to try executing the command before
          failing.
        **command_fn_kwargs (dict): keyword arguments for the command_fn
          function.

    Returns:
        str: value of the capturing group with index 'regex_group' in the match.

    Raises:
        DeviceError: if command execution fails OR
                     couldn't find the requested group in any of the
                     responses.
    """
    for _ in range(tries):
      try:
        response = command_fn(command, **command_fn_kwargs)
      except errors.DeviceError:
        continue

      match = re.search(regex, response, re.MULTILINE | re.DOTALL)
      if match:
        max_group = match.lastindex
        if max_group is None:
          max_group = 0

        if regex_group > max_group:
          logger.warning(
              "{}: requested group index ({}) exceeds index of last matched group ({}). "
              "Matched groups: {}, response: {!r}, regex: {!r}.".format(
                  self.name, regex_group, max_group, match.groups(), response,
                  regex))
        else:
          return str(match.group(regex_group))

    msg = "{} unable to retrieve {} from {} after {} tries".format(
        self.name, regex, command, tries)

    if raise_error:
      raise errors.DeviceError(msg)
    else:
      logger.warning(msg)
      return ""

  @decorators.health_check
  def check_ping_responsiveness(self):
    """Check if the auxiliary device responds to pings.

    Raises:
        DeviceNotResponsiveError: if no response to ping before the timeout.
    """
    try:
      common_utils.retry(
          self._ping,
          is_successful=bool,
          timeout=self._PING_TIMEOUT,
          reraise=True)
    except Exception as err:
      raise errors.DeviceNotResponsiveError(
          self.name,
          "failed to respond to ping",
          timeout=self._PING_TIMEOUT,
          details=str(err))

  def _execute_health_check_methods(self, health_checks):
    """Execute health checks on the device.

    Args:
        health_checks (list): list of methods to execute as health checks.

    Raises:
        CheckDeviceReadyError: if a health check fails.

    Note:
        Order of health check methods matter. Health check execution will
        stop at the first failing health check.
    """
    for step, health_check_method in enumerate(health_checks):
      method_name = health_check_method.__name__
      health_check_name = method_name.replace("_", " ").strip().capitalize()

      try:
        health_check_method()
      except errors.CheckDeviceReadyError:
        logger.info("{} health check {}/{} failed: {}.".format(
            self.name, step + 1, len(health_checks), health_check_name))
        raise

      logger.info("{} health check {}/{} succeeded: {}.".format(
          self.name, step + 1, len(health_checks), health_check_name))

  def lazy_init(self, capability_class, *args, **kwargs):
    """Provides a lazy instantiation mechanism for capabilities.

    The capability instance will not be created until it is accessed for the
    first time.
    Subsequent accesses will return the same capability instance.
    In other words, no more than one capability instance will be created.
    If a capability is not accessed, the capability instance is not created.

    Args:
        capability_class (class): capability class to instantiate.
        *args (tuple): positional args to the capability's __init__.
        **kwargs (dict): keyword arguments to the capability's __init__.

    Returns:
        CapabilityBase: initialized capability instance.
    """
    capability_name = self._get_private_capability_name(capability_class)
    if not hasattr(self, capability_name):
      capability_inst = capability_class(*args, **kwargs)
      setattr(self, capability_name, capability_inst)
    return getattr(self, capability_name)

  @classmethod
  def _get_private_capability_name(cls, capability_class):
    """Returns the name of the private attribute to use for a given capability class.

    Args:
        capability_class(class): capability class object.

    Returns:
        str: name of the private capability attribute to be used.
    """
    return "_{}".format(capability_class.get_capability_name())

  @classmethod
  def _get_property_names(cls, property_type):
    """Returns the property names for all public properties of the type."""
    classes = cls.get_supported_capability_flavors().copy()
    classes.add(cls)
    property_names = []
    for a_class in classes:
      # pytype: disable=attribute-error
      prefix = "" if a_class == cls else a_class.get_capability_name() + "."
      # pytype: enable=attribute-error
      for name, member in inspect.getmembers(a_class):
        if isinstance(member, property_type) and not name.startswith("_"):
          property_names.append("{}{}".format(prefix, name))
    return list(set(property_names))

  def _get_properties(self, property_names):
    """Returns a dictionary of prop, value for each property."""
    property_dict = {}
    for name in property_names:
      value = self.get_property(name)
      if isinstance(value, str) and "does not have a known property" in value:
        continue  # property not supported in current flavor
      property_dict[name] = value

    return property_dict

  def _get_switchboard_if_initialized(self):
    """Returns self.switchboard if it's initialized, None otherwise."""
    if self.is_capability_initialized("switchboard"):
      return self.switchboard  # pytype: disable=attribute-error
    return None

  def _list_properties_dynamic_auxiliary_device(self):
    """Returns a set of dynamic properties.

    Returns:
        set: dynamic properties that can be queried during get-prop CLI/API
        operation.
    """
    return set(["connected"])

  def _log_object_lifecycle_event(self, method_name):
    """Logs a message about a lifecycle event of a python object.

    Args:
        method_name (str): name of the method called on the object.
    """
    logger.debug("{} called on {} (id = {}) in process {}.".format(
        method_name, self, id(self), os.getpid()))

  def _property_has_setter(self, property_name):
    """Checks whether a property has a setter.

    Args:
        property_name (str): name of the property. If property is a
          capability property then the string should be
          <capability_name>.<property_name>

    Raises:
        AttributeError: if property doesn't exist

    Returns:
        bool: True if property has a setter, else False
    """
    target_class = type(self)
    # Get the class that holds the property
    if "." in property_name:
      capability_name = property_name.split(".")[0]
      capability_instance = getattr(self, capability_name)
      target_class = type(capability_instance)
      property_name = property_name.split(".")[1]
    # Check whether the property has a setter
    attr = getattr(target_class, property_name)
    return attr.fset is not None


deprecation_utils.add_deprecated_attributes(AuxiliaryDevice, [
    ("console_port_name", "communication_address", False),
])
