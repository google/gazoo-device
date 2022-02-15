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

"""Fire Manager module.

Used for CLI-specific commands and flags.
Built to work with Python Fire: https://github.com/google/python-fire.
"""
import codecs
import enum
import fnmatch
import inspect
import json
import logging
import os.path
import pydoc
import re
import sys
import textwrap
import time
from typing import Any, Collection, List, Mapping, Optional, Sequence, Tuple, Type

from gazoo_device import config
from gazoo_device import console
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device import manager
from gazoo_device import package_registrar
from gazoo_device.utility import parallel_utils
from gazoo_device.utility import usb_utils

logger = gdm_logger.get_logger()


class AttributeClassification(enum.Enum):
  """Types of class attributes recognized by the "man" method."""
  CAPABILITY = "capability"
  DEPRECATED_METHOD = "deprecated method"
  DEPRECATED_PROPERTY = "deprecated property"
  HEALTH_CHECK = "health check"
  OTHER = "other"
  PRIVATE_METHOD = "private method"
  PROPERTY = "property"
  CLASS_PROPERTY = "class property"
  PUBLIC_METHOD = "public method"

MAX_TIME_TO_WAIT_FOR_INITATION = 5

_DOC_INDENT_SIZE = 4
# Capability attributes visible on device summary man page
# (e.g. "man cambrionix").
_VISIBLE_CAPABILITY_ATTRIBUTES = [
    AttributeClassification.PROPERTY, AttributeClassification.PUBLIC_METHOD
]
_FORMAT_DEF = "  {:22s}  {}"
_FORMAT_VAL = "\t\t\t  {}"
_FORMAT_DIC = "\t\t\t  {:25s} {!r}"


def _log_man_warning_for_multiple_flavors(
    capability_classes: Collection[Type[Any]],
    capability_name: str,
    device_type: str,
    capability_class: Type[Any]) -> None:
  """Logs 'gdm man' warning when multiple capability flavors are available.

  Args:
    capability_classes: All available capability flavors.
    capability_name: Name of the capability.
    device_type: Type of the device with this capability.
    capability_class: Capability flavor selected to print documentation for.

  Capabilities can have multiple flavors in one device class, although this is
  somewhat rare. The flavor used is determined based on device firmware at
  runtime. Since we don't know which flavor will be used without an attached
  device, log a warning and print documentation for any single flavor.
  """
  flavors = [a_cls.__name__ for a_cls in capability_classes]
  logger.warning(
      f"{len(flavors)} flavors ({flavors}) of capability {capability_name!r} "
      f"are available for {device_type}.\n"
      f"Showing documentation for flavor {capability_class}.\n")


def _run_device_action(
    manager_inst: manager.Manager, device_name: str, full_attribute_name: str,
    method_args: Tuple[Any, ...], method_kwargs: Mapping[str, Any]) -> Any:
  """Returns the result of a device method call or a property."""
  device = manager_inst.create_device(device_name)
  attribute = device
  try:
    for attribute_name in full_attribute_name.split("."):
      attribute = getattr(attribute, attribute_name)
    if callable(attribute):  # It's a method.
      return attribute(*method_args, **method_kwargs)
    else:  # It's a property.
      return attribute
  finally:
    device.close()


def pretty_print_props(props_dicts: Mapping[str, Mapping[str, Any]]):
  """Prettily logs the props dictionaries from manager.get_device_prop."""
  device_property_types = ["persistent", "optional", "dynamic"]
  manager_property_types = ["settable"]
  for property_type in device_property_types + manager_property_types:
    if property_type not in props_dicts:
      continue

    title = "{} Properties:".format(property_type.capitalize())
    logger.info("")
    logger.info(title)
    for prop_name in sorted(props_dicts[property_type]):
      prop_value = props_dicts[property_type][prop_name]
      if isinstance(prop_value, list) and len(prop_value) > 1:
        logger.info(_FORMAT_DEF.format(prop_name, ""))
        for value in prop_value:
          if callable(value):
            value = value.__name__
          logger.info(_FORMAT_VAL.format(str(value)))
        logger.info("")
      elif isinstance(prop_value, dict) and len(prop_value) > 1:
        logger.info(_FORMAT_DEF.format(prop_name, ""))
        for key in sorted(prop_value):
          logger.info(_FORMAT_DIC.format(key, prop_value[key]))
        logger.info("")

      else:
        logger.info(_FORMAT_DEF.format(prop_name, prop_value))


class FireManager(manager.Manager):
  """Manages the setup and communication of smart devices."""

  def __init__(self, debug=False, dev_debug=False, quiet=False):
    stream_debug = debug or dev_debug
    debug_level = logging.WARNING if quiet else logging.DEBUG

    super().__init__(debug_level=debug_level, stream_debug=stream_debug)

  def console(self, device_name: str, health_check: bool = False) -> None:
    """Starts an interactive device console.

    Use Tab and Shift-Tab to navigate between console windows (next/previous).

    Args:
      device_name: Name of the device to start the console for.
      health_check: Whether to run health checks before starting the console.

    Raises:
      NotImplementedError: If the device does not have a Switchboard capability.
    """
    make_device_ready = "on" if health_check else "off"
    device = self.create_device(device_name,
                                make_device_ready=make_device_ready)

    try:
      if not device.has_capabilities(["switchboard"]):
        raise NotImplementedError(
            f"{device.name} does not have a Switchboard capability, which is "
            "required for the console.")
      console_configuration = device.get_console_configuration()
      device.switchboard.set_max_log_size(0)  # Disable log rotation.
      gdm_logger.silence_progress_messages()  # To avoid interference with GUI.
      console_app = console.ConsoleApp(
          device.switchboard, device.log_file_name, console_configuration)
      console_app.run()
    finally:
      gdm_logger.reenable_progress_messages()
      device.close()

  def exec(self, identifier):
    """Alias for create_device with health checks disabled.

    Important: ensure the device is in a healthy state before using "exec"
    by running health checks via `gdm health-check device-1234`.
    Usage from the CLI: `gdm exec device-1234 - shell "echo 'foo'"`.

    Args:
      identifier (str): The identifier string (name) which specifies the device.

    Returns:
      Object: The device found and created by the identifier specified.
    """
    return self.create_device(identifier, make_device_ready="off")

  def get_persistent_prop_devices(self, devices):
    """Gets persistent props of one or more devices and returns a json response.

    This assumes the provided devices are healthy. If properties are unable to
    be fetched, an empty json object will be returned for the device for which
    the properties could not be retrieved.

    Args:
      devices (list): Device identifiers to get properties of.

    Returns:
      str: json formatted persistent properties, e.g.
        {
          'device-1234': {
            'build_date': '180124',
            'ftdi_serial_number': '1f824023'
          },
          'device-5678': {},
          ...
        }
    """
    logger.setLevel(logging.ERROR)  # silence logging to reduce CLI output
    devices_props = {}
    if isinstance(devices, str):
      devices = devices.split(",")

    for device_name in devices:
      persistent_props = {}
      try:
        device_props = self.get_device_configuration(device_name)
        persistent_props = device_props.get("persistent", {})
      except errors.DeviceError:
        pass  # unhealthy devices will have empty props
      devices_props[device_name] = persistent_props

    return json.dumps(devices_props)

  def get_prop(self, device_name, prop=None):
    """Prints the device properties.

    Args:
      device_name (str): identifier for device.
      prop (str): identifier for property.
    """
    if prop is not None:  # If requested a single property...
      value = self.get_device_prop(device_name, prop)
      logger.info(_FORMAT_DEF.format(prop, str(value)))
    else:
      props_dicts = self.get_device_prop(device_name, prop)
      pretty_print_props(props_dicts)

  def health_check(self, identifier, recover=False):
    """CLI command for running device health checks.

    Usage from the CLI: `gdm health-check device-1234`.

    Args:
      identifier (str): The identifier string (name) which specifies the
        device.
      recover (bool): whether to automatically recover from health check
        failures.
    """
    make_device_ready_setting = "check_only"
    if recover:
      make_device_ready_setting = "on"
    device = self.create_device(identifier, make_device_ready="off")
    try:
      device.make_device_ready(setting=make_device_ready_setting)
    finally:
      device.close()

  @classmethod
  def helpfull(cls):
    """Prints a general overview of GDM's features.

    Invoked by 'man' without arguments.
    """
    description = textwrap.dedent("""
      Gazoo Device Manager (gdm) command line interface is a single utility for control of a
      variety of Gazoo hardware.

      Commands:
        The CLI is dynamic, meaning commands are generated from API methods (see
        https://github.com/google/python-fire).
        There are several groups of commands.
          "Manager" commands operate on local config files on the PC.
          These commands are generated from API methods in the Manager class.
            The command may talk to devices (detect), but they don't change the state of
            the device (i.e. read-only)
            The command may change the config files stored on the PC, to detect new
            devices, add an alias, etc.
            To see a list of available manager commands, run "gdm".
          "Device" commands talk to or modify a Gazoo device.
          These commands are generated from API methods in device classes.
              This includes upgrade, reboot, etc.
              In general you enter a device command as "gdm issue <device_name> - <command>"
              Examples::
              gdm issue raspberrypi-zdwm - reboot
              gdm issue raspberrypi-zdwm - shell "echo 'foo'"
              To see the list of device commands available for a device, run "gdm man <device_type>"
              For example:: gdm man cambrionix

          You can get more details on a particular command at the command line with:
          "gdm <command> -h"
          For example::  gdm detect -h

          You can pass in flags to the CLI with:
          "gdm --<flag> - <command>"
          For example:: gdm --debug - devices
          To see a list of available flags, run "gdm -h"

      Supported device types:
      Primary:
      {}

      Auxiliary:
      {}

      Virtual:
      {}

      To explore available device functionality through the dynamic CLI, you will need a device
      attached to your host.

      Use "gdm man" to access static documentation (no devices necessary, but has limitations):
          "gdm man <device_type>" to see all functionality supported by a device.
          "gdm man <device_type> --deprecated" to see just deprecated functionality for a device.
          "gdm man <device_type> <class_attribute>" for device attribute documentation.
          "gdm man <device_type> <capability> <capability_attribute>" for capability attribute documentation.
    """).format(
        cls._indent_doc_lines(cls.get_supported_primary_device_types()),
        cls._indent_doc_lines(cls.get_supported_auxiliary_device_types()),
        cls._indent_doc_lines(cls.get_supported_virtual_device_types()))[1:-1]
    logger.info(description)

  def issue(self, identifier, **kwargs):
    """Alias for create_device with health checks enabled by default.

    Usage from the CLI: `gdm issue device-1234 - shell "echo 'foo'"`.

    Args:
      identifier (str): The identifier string (name) which specifies the
        device.
      **kwargs (dict): keyword-only arguments passed on to create_device:
        "log_file_name" (str) -- a string log file name to use for log
        results. "log_directory" (str) -- a directory path to use for storing
        log file. "make_device_ready" (str) -- health check setting ("on",
        "check_only", "off", "flash_build").

    Returns:
      Object: The device found and created by the identifier specified.
    """
    return self.create_device(
        identifier,
        log_file_name=kwargs.get("log_file_name"),
        log_directory=kwargs.get("log_directory"),
        make_device_ready=kwargs.get("make_device_ready", "on"))

  def issue_devices(self,
                    devices: Sequence[str],
                    attribute_name: str,
                    *method_args: Any,
                    timeout: float = parallel_utils.TIMEOUT_PROCESS,
                    **method_kwargs: Any) -> List[Any]:
    """Executes a device method or property in parallel for multiple devices.

    For example: 'gdm issue-devices device-1234,device-3456 reboot'.

    Args:
      devices: Device identifiers.
      attribute_name: Name of device method or property to execute in parallel.
        Can be nested. For example: "shell", "wifi.ssid".
      *method_args: Positional arguments to the device method.
      timeout: Maximum amount of seconds to allow parallel methods to complete.
      **method_kwargs: Keyword arguments to the device method.

    Returns:
      Results from parallel calls.
    """
    if isinstance(devices, str):
      devices = devices.split(",")
    return self._issue_devices(
        devices, attribute_name, timeout, method_args, method_kwargs)

  def issue_devices_all(self,
                        attribute_name: str,
                        *method_args: Any,
                        timeout: float = parallel_utils.TIMEOUT_PROCESS,
                        **method_kwargs: Any) -> List[Any]:
    """Executes a device method or property in parallel for connected devices.

    For example: 'gdm issue-devices-all reboot --no_wait=True'.

    Args:
      attribute_name: Name of device method or property to execute in parallel.
        Can be nested. For example: "shell", "wifi.ssid".
      *method_args: Positional arguments to the device method.
      timeout: Maximum amount of seconds to allow parallel methods to complete.
      **method_kwargs: Keyword arguments to the device method.

    Returns:
      Results from parallel calls.

    Raises:
      DeviceError: if no devices are connected.
    """
    devices = self.get_connected_devices()
    if not devices:
      raise errors.DeviceError("No devices are connected.")
    return self._issue_devices(
        devices, attribute_name, timeout, method_args, method_kwargs)

  def issue_devices_match(self,
                          match: str,
                          attribute_name: str,
                          *method_args: Any,
                          timeout: float = parallel_utils.TIMEOUT_PROCESS,
                          **method_kwargs: Any) -> List[Any]:
    """Executes a device method or property in parallel for matching devices.

    For example: 'gdm issue-devices-match raspberrypi* reboot --no_wait=True'.

    Args:
      match: Wildcard-supported string to match against device names, i.e.
        "raspberrypi*" will call provided method on all connected Raspberry Pis.
      attribute_name: Name of device method or property to execute in parallel.
        Can be nested. For example: "shell", "wifi.ssid".
      *method_args: Positional arguments to the device method.
      timeout: Maximum amount of seconds to allow parallel methods to complete.
      **method_kwargs: Keyword arguments to the device method.

    Returns:
      Results from parallel calls.

    Raises:
      DeviceError: if provided wildcard does not match any connected devices.
    """
    devices = fnmatch.filter(self.get_connected_devices(), match)
    if not devices:
      raise errors.DeviceError(f"No devices match {match!r}.")
    return self._issue_devices(
        devices, attribute_name, timeout, method_args, method_kwargs)

  def log(self, device_name, log_file_name=None, duration=2000):
    """Streams device logs to stdout.

    Args:
      device_name (str): device identifier.
      log_file_name (str): log_file_name. Used for testing purposes.
      duration (float): how long to stream logs for.

    Raises:
      DeviceError: if unable to initiate log file to stream in 10 seconds.
    """
    logger.info("Streaming logs for max {}s".format(duration))
    device = self.create_device(device_name, log_file_name=log_file_name)
    # Disable log rotation feature
    if hasattr(type(device), "switchboard"):
      device.switchboard.set_max_log_size(0)

    try:
      # Wait up to 10 seconds for log file to be created
      end_time = time.time() + MAX_TIME_TO_WAIT_FOR_INITATION
      while time.time() < end_time:
        if os.path.exists(device.log_file_name):
          break
        time.sleep(0.001)
      else:
        raise errors.DeviceError(
            "Streaming logs for {} failed. "
            "Log file not created within {} seconds".format(
                device_name, MAX_TIME_TO_WAIT_FOR_INITATION))

      start_time = time.time()
      end_time = start_time + duration
      # Open log file and process log file
      with codecs.open(
          device.log_file_name, "r", encoding="utf-8",
          errors="replace") as log_file:

        while time.time() < end_time:
          line = log_file.readline()
          if line:
            sys.stdout.write(line)
            sys.stdout.flush()
          else:
            time.sleep(0.001)

    finally:
      sys.stdout.flush()
      device.close()

  @classmethod
  def man(cls,
          device_type: Optional[str] = None,
          class_attr_name: Optional[str] = None,
          capability_attr_name: Optional[str] = None,
          deprecated: bool = False) -> None:
    """Prints documentation without reliance on device instance creation.

    Dynamic device documentation ("gdm <command> --help") is more complete, but
    requires a device attached to the host to generate documentation.

    Args:
      device_type: Device type.
      class_attr_name: Name of the class attribute to display documentation for.
      capability_attr_name: Name of the capability attribute to display
        documentation for.
      deprecated: Display only deprecated methods and properties.

    Raises:
      AttributeError: Requested attribute does not exist.
      TypeError: Requested capability attribute documentation for a
        non-capability.
    """
    # Handle both space-separated and dot-separated inputs:
    # gdm man cambrionix switch_power power_on
    # gdm man cambrionix.switch_power.power_on
    args = " ".join(
        arg for arg in (device_type, class_attr_name, capability_attr_name)
        if arg)
    args = args.replace(".", " ")
    # Allow both dashes and underscores for names.
    args = args.replace("-", "_")
    args_list = args.split()
    device_type, class_attr_name, capability_attr_name = (
        args_list + [None] * (3 - len(args_list)))

    if not device_type:
      cls.helpfull()
    else:
      device_class = cls.get_supported_device_class(device_type)
      if not class_attr_name:
        cls._man_device(device_type, device_class, deprecated)
      else:
        if not hasattr(device_class, class_attr_name):
          raise AttributeError(f"{device_type} ({device_class}) does not have "
                               f"attribute {class_attr_name!r}")
        class_attribute = getattr(device_class, class_attr_name)
        classification = cls._classify_attribute(class_attribute)
        class_attr_description = classification.value

        if classification == AttributeClassification.CAPABILITY:
          capability_classes = list(class_attribute.capability_classes)
          class_attribute = capability_classes[0]
          class_attr_description += f"; flavor: {class_attribute.__name__}"
          if len(capability_classes) > 1:
            _log_man_warning_for_multiple_flavors(
                capability_classes, class_attr_name, device_type,
                class_attribute)

        if not capability_attr_name:
          cls._man_class_attribute(
              device_class, class_attr_name, class_attr_description,
              class_attribute)
        else:
          if classification != AttributeClassification.CAPABILITY:
            raise TypeError(
                f"{device_type}.{class_attr_name} ({class_attribute}) is not a "
                "capability.")
          if not hasattr(class_attribute, capability_attr_name):
            raise AttributeError(
                f"{device_type}.{class_attr_name} ({class_attribute}) "
                f"does not have attribute {capability_attr_name!r}")
          capability_attribute = getattr(class_attribute, capability_attr_name)
          capability_attr_description = cls._classify_attribute(
              capability_attribute).value + f" of {class_attribute.__name__}"
          cls._man_capability_attribute(
              device_class, class_attr_name, capability_attr_name,
              capability_attr_description, capability_attribute)

  def print_usb_info(self):
    """Prints the usb_info dictionary in a human readable form."""
    values = usb_utils.get_address_to_usb_info_dict().values()
    logger.info("{} USB connections found.".format(len(values)))
    for num, usb_info_dict in enumerate(values):
      keys = usb_info_dict.get_properties()
      logger.info("Connection {}:".format(num))
      for key in keys:
        logger.info("\t{:15} {:15}".format(key,
                                           str(getattr(usb_info_dict, key))))

  def register(self, package_name: str) -> None:
    """Registers the given package with GDM CLI.

    Args:
      package_name: Name of the package to register. For example,
        "foo_extension_package" or "my_package.bar_devices".

    Note that this only registers the package for CLI usage. Tests and Python
    interpreter users must use package_registrar.register() instead.
    """
    registered_cli_packages = self.config.get("cli_extension_packages", [])
    if package_name not in registered_cli_packages:
      if package_registrar.import_and_register(package_name,
                                               include_cli_instructions=True):
        self._set_config_prop("cli_extension_packages",
                              registered_cli_packages + [package_name])
        logger.info(f"Registered package {package_name!r} with GDM CLI.")
    else:
      logger.info(
          f"Package {package_name!r} is already registered with GDM CLI.")

  def unregister(self, package_name: str) -> None:
    """Removes the given package from GDM CLI.

    Args:
      package_name: Name of the package to unregister. For example,
        "foo_extension_package" or "my_package.bar_devices".

    Note that this only removes the package from the CLI.
    """
    registered_cli_packages = self.config.get("cli_extension_packages", [])
    if package_name in registered_cli_packages:
      updated_packages = registered_cli_packages.copy()
      updated_packages.remove(package_name)
      self._set_config_prop("cli_extension_packages", updated_packages)
      logger.info(f"Removed package {package_name!r} from GDM CLI.")
    else:
      logger.info(f"Package {package_name!r} is not registered with GDM CLI.")

  def update_gdm(self):
    """Update GDM in this virtual environment.

    To update GDM in this virtual environment, call the GDM launcher script
    by using the full path as shown above.

    If no version is specified then GDM will be updated to the latest
    version available otherwise the version specified will be installed instead.
    """
    logger.info(textwrap.dedent(f"""
      Unable to update Gazoo Device Manager using this tool.
      If you want to update GDM call the GDM launcher script directly like this:
      {config.LAUNCHER_PATH} update-gdm [version]

      If after doing the above you see this message again, then you probably did a
      'sudo pip install gazoo-device' and overwrote the GDM launcher script. Please
      reinstall GDM.
    """))

  @classmethod
  def _classify_attribute(cls, class_attr):
    """Classifies the class attribute."""
    class_attr = decorators.unwrap(class_attr)
    if isinstance(class_attr, decorators.CapabilityProperty):
      return AttributeClassification.CAPABILITY
    if (hasattr(class_attr, "__deprecated__") or
        hasattr(getattr(class_attr, "fget", None), "__deprecated__")):
      if inspect.isroutine(class_attr):
        return AttributeClassification.DEPRECATED_METHOD
      if isinstance(class_attr, property):
        return AttributeClassification.DEPRECATED_PROPERTY
    if isinstance(class_attr, config.CLASS_PROPERTY_TYPES):
      return AttributeClassification.CLASS_PROPERTY
    if isinstance(class_attr, property):
      return AttributeClassification.PROPERTY
    if inspect.isroutine(class_attr):
      if hasattr(class_attr, "__health_check__"):
        return AttributeClassification.HEALTH_CHECK
      if class_attr.__name__.startswith("_"):
        return AttributeClassification.PRIVATE_METHOD
      return AttributeClassification.PUBLIC_METHOD
    return AttributeClassification.OTHER

  @classmethod
  def _indent_doc_lines(cls, doc_lines, indent=_DOC_INDENT_SIZE):
    """Indents docstring lines."""
    indent_str = " " * indent
    return "\n".join(indent_str + line for line in doc_lines)

  def _issue_devices(self,
                     devices: Sequence[str],
                     attribute_name: str,
                     timeout: float,
                     method_args: Tuple[Any, ...],
                     method_kwargs: Mapping[str, Any]) -> List[Any]:
    """Executes a device method in parallel on multiple devices.

    Args:
      devices: Device identifiers to execute the method on.
      attribute_name: Name of device method or property to execute in parallel.
      timeout: Maximum amount of seconds to allow parallel methods to complete.
      method_args: Positional arguments to the method.
      method_kwargs: Keyword arguments to the method.

    Returns:
      Results from the parallel method calls.
    """
    call_specs = [
        parallel_utils.CallSpec(_run_device_action, device, attribute_name,
                                method_args, method_kwargs)
        for device in devices]
    results, _ = parallel_utils.execute_concurrently(
        call_specs=call_specs, timeout=timeout, raise_on_process_error=True)
    return results

  @classmethod
  def _man_capability_attribute(cls,
                                device_class: Type[Any],
                                capability_name: str,
                                capability_attr_name: str,
                                description: str,
                                attribute: Any) -> None:
    """Prints capability attribute documentation.

    Invoked by 'man' with 3 args (device, capability, attribute).

    Args:
      device_class: Device class which contains the capability.
      capability_name: Name of the capability containing the attribute.
      capability_attr_name: Capability attribute to print documentation for.
      description: Description of the capability attribute.
      attribute: The capability attribute to display documentation for.
    """
    doc_title = (
        f"Manual for "
        f"{device_class.__name__}.{capability_name}.{capability_attr_name} "
        f"({description})\n")
    pydoc_lines = pydoc.render_doc(attribute).splitlines()
    doc = doc_title + "\n".join(pydoc_lines[1:])  # Replace pydoc's title
    logger.info(doc)

  @classmethod
  def _man_class_attribute(cls,
                           device_class: Type[Any],
                           class_attr_name: str,
                           description: str,
                           attribute: Any) -> None:
    """Prints class attribute documentation.

    Invoked by 'man' with 2 args (device, attribute).

    Args:
      device_class: Device class which contains the attribute.
      class_attr_name: Name of the class attribute to display documentation for.
      description: Description of the class attribute.
      attribute: The attribute to display documentation for.
    """
    doc_title = (f"Manual for {device_class.__name__}.{class_attr_name} "
                 f"({description})\n")
    pydoc_lines = pydoc.render_doc(attribute).splitlines()
    doc = doc_title + "\n".join(pydoc_lines[1:])  # Replace pydoc's title
    logger.info(doc)

  @classmethod
  def _man_device(cls,
                  device_type: str,
                  device_class: Type[Any],
                  deprecated: bool) -> None:
    """Prints supported device features.

    Args:
      device_type: Type of device.
      device_class: Device class to show documentation for.
      deprecated: Whether to display manuals of deprecated attributes.

    Invoked by 'man' with 1 argument (device type).
    """
    # Group device class attributes into properties, health checks, methods,
    # and capabilities
    capability_name_to_classes = {}
    property_names = []
    class_properties = []
    public_methods_names = []
    health_check_names = []
    deprecated_methods = []
    deprecated_properties = []
    for name, attribute in inspect.getmembers(device_class):
      classification = cls._classify_attribute(attribute)
      if classification == AttributeClassification.PROPERTY:
        property_names.append(name)
      elif classification == AttributeClassification.CLASS_PROPERTY:
        if not name.startswith("_"):
          class_properties.append(f"{name}: {attribute}")
      elif classification == AttributeClassification.HEALTH_CHECK:
        health_check_names.append(name)
      elif classification == AttributeClassification.PUBLIC_METHOD:
        public_methods_names.append(name)
      elif classification == AttributeClassification.CAPABILITY:
        capability_name_to_classes[name] = list(attribute.capability_classes)
      elif classification == AttributeClassification.DEPRECATED_METHOD:
        deprecated_methods.append(f"{name} ({attribute.__deprecated__})")
      elif classification == AttributeClassification.DEPRECATED_PROPERTY:

        # Parse alias from deprecated property docstring
        match = re.search(r'See "(?P<alias>.*)".', attribute.__doc__)
        if match:
          alias = match.group("alias")
          deprecated_properties.append(f"{name} ({alias})")

    # Generate a summary of supported capability methods and properties for each
    # capability
    capability_lines = []
    for cap_name, cap_classes in capability_name_to_classes.items():
      # There may be several flavors of a capability for a device class.
      for cap_class in cap_classes:
        capability_lines.append("{} ({})".format(cap_name, cap_class.__name__))
        methods_and_props = [
            name for name, member in inspect.getmembers(cap_class)
            if cls._classify_attribute(member) in _VISIBLE_CAPABILITY_ATTRIBUTES
        ]
        indented_lines = [
            " " * _DOC_INDENT_SIZE + line for line in methods_and_props
        ]
        capability_lines.extend(indented_lines)

    docs_capabilities = cls._indent_doc_lines(capability_lines)
    docs_methods = cls._indent_doc_lines(public_methods_names)
    docs_health_checks = cls._indent_doc_lines(health_check_names)
    docs_properties = cls._indent_doc_lines(property_names)
    docs_class_properties = cls._indent_doc_lines(class_properties)
    docs_deprecated_methods = cls._indent_doc_lines(deprecated_methods)
    docs_deprecated_properties = cls._indent_doc_lines(deprecated_properties)

    if deprecated:
      template = textwrap.dedent("""
        Deprecated manual for device type '{device_type}' (class {device_class})

        Deprecated methods:
        {deprecated_methods}

        Deprecated properties:
        {deprecated_properties}

        Use "gdm man {device_type} <deprecated_attribute>" for device attribute documentation.
      """)[1:-1]

    else:
      template = textwrap.dedent("""
        Manual for device type '{device_type}' (class {device_class})

        Owned (maintained) by {device_class._OWNER_EMAIL}

        Supported capabilities:
        {capabilities}

        Supported methods:
        {methods}

        Supported health check methods:
        {health_checks}

        Supported properties:
        {properties}

        Class properties:
        {class_properties}

        Use:
          "gdm man <device_type> <class_attribute>" for device attribute documentation.
          "gdm man <device_type> <capability> <capability_attribute>" for capability attribute documentation.
      """)[1:-1]

    doc = template.format(
        device_type=device_type,
        device_class=device_class,
        capabilities=docs_capabilities,
        methods=docs_methods,
        health_checks=docs_health_checks,
        properties=docs_properties,
        class_properties=docs_class_properties,
        deprecated_methods=docs_deprecated_methods,
        deprecated_properties=docs_deprecated_properties)
    logger.info(doc)
