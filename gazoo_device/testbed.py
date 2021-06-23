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

"""Testbed module.

Usage:

To enable a testbed health check, you will need to...

1. Add a health check method to the Testbed class below. This method should
follow the naming convention 'check_<description>', be decorated with
'@decorators.health_check', and accept 1 argument which will be the testing
value of the property used to trigger the check (detailed in 2. below). You will
have access to the devices in your testbed via self.devices within the health
check method. If you'd like to issue a shell command to the device within the
method, add the shell command to the global COMMANDS dictionary below and use it
in the method via self.commands.

2. Add an entry to the 'self._prop_to_health_check' dictionary in
Testbed.__init__() below. The entry should follow the format
{
  <testing property>: <health check method>
}
The testing property should be the name of the property used to trigger the
health check, and the health check method should be the newly added Testbed
method. This will tell GDM to execute the method when the property exists in the
testbed config (detailed in 3. below).

3. Add the testing property from 2. above to the testbed configs of the testbeds
you'd like to execute the health check on.

Note that the property value will be passed to the corresponding health check
method as an argument. If no property value is necessary, use 'true'.
"""
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger

logger = gdm_logger.get_logger()

COMMANDS = {"FILE_SYSTEMS": "df"}


class Testbed(object):
  """Class for testbed interaction."""

  def __init__(self, devices, testing_props, name="testbed"):
    """Initialize a Testbed object.

    Args:
        devices (list): list of device instances.
        testing_props (dict): properties of the testbed used for testing.
        name (str): optional name of the testbed, defaulted to "testbed".
    """
    self.name = name
    self.devices = devices
    self.testing_props = testing_props
    self.commands = COMMANDS

    # map from testing prop to corresponding testbed health check method
    # e.g. if { "external_storage": self.check_external_storage_mounted }, then
    #      the check_external_storage_mounted method will be executed as a
    #      health check if the "external_storage" prop is provided during
    #      Testbed initialization.
    self._prop_to_health_check = {
        "external_storage": self.check_external_storage_mounted,
    }

  @decorators.health_check
  def check_external_storage_mounted(self, enabled):
    """Check if external USB storage is mounted on devices in the testbed.

    Args:
        enabled (str): whether to run this health check, "true" or "false".

    Raises:
        TestbedMissingExternalStorageError: if devices are missing external
        USB storage.
    """
    if enabled.lower() == "false":
      return

    file_system_cmd = self.commands["FILE_SYSTEMS"]
    usb_storage_location = "/data/usb"
    devices_missing_external_storage = []
    for device in self.devices:
      file_system_output = device.shell(file_system_cmd)
      file_system_mounts = self._get_filesystem_mounts(file_system_output)
      if usb_storage_location not in file_system_mounts:
        devices_missing_external_storage.append(device.name)

    if devices_missing_external_storage:
      raise errors.TestbedMissingExternalStorageError(
          device_names=devices_missing_external_storage,
          details=(
              f"command {file_system_cmd!r} did not display any filesystems "
              f"mounted on {usb_storage_location!r}"),
          recovery="mount external USB storage")

  @decorators.LogDecorator(logger)
  def check_testbed_ready(self):
    """Checks if the testbed is healthy by executing a series of health check methods."""
    health_check_call = []  # list of tuples: (health check method, prop value)
    for prop in self.testing_props:
      if prop in self._prop_to_health_check:
        health_check_call.append(
            (self._prop_to_health_check[prop], self.testing_props[prop]))
    self._execute_health_check_methods(health_check_call)

  @decorators.LogDecorator(logger)
  def make_testbed_ready(self, setting="on"):
    """Check testbed readiness and attempt recovery if allowed.

    Args:
        setting (str): 'on'|'off'|'check_only'.

    Raises:
        DeviceError: if testbed health checks fail.
    """
    if setting not in ["on", "off", "check_only"]:
      raise errors.DeviceError(
          "{} failed make_testbed_ready. Setting '{}' is invalid.".format(
              self.name, setting))
    elif setting == "off":
      return

    # check testbed health
    try:
      self.check_testbed_ready()
    except errors.DeviceError as err:
      if setting == "check_only":
        logger.info("{} skipping recovery".format(self.name))
        raise

      logger.info("{} failed check_testbed_ready with {}".format(
          self.name, repr(err)))

      # attempt to recover the testbed
      self.recover(err)
      logger.info("{} re-checking readiness after recovery attempt".format(
          self.name))
      self.check_testbed_ready()
      logger.info("{} successfully recovered to ready state".format(self.name))

  @decorators.LogDecorator(logger)
  def recover(self, error):
    """Attempts to recover testbed based on the type of error specified.

    Args:
        error (CheckTestbedReadyError): The exception thrown that will be
          used to identify a possible recovery solution to use.

    Raises:
        CheckTestbedReadyError: If recovery fails.
    """
    raise error

  def _execute_health_check_methods(self, health_check_calls):
    """Execute health checks on the testbed.

    Args:
        health_check_calls (list): list of tuples as (health check method,
          argument) to execute as health checks.

    Raises:
        CheckTestbedReadyError: if health check fails.

    Notes:
        - The value of the property that triggered the health check is
        passed to the health
        check method as an argument; therefore, health check methods will
        accept a single
        argument (unlike device health checks). All property values will be
        strings.
        - Some health checks will have "true" / "false" argument values. The
        health check
        should be skipped when the argument is "false".
        - Order of health check methods matter. Health check execution will
        stop at the first
        failing health check.
    """
    checks_passed = []
    for step, health_check_call in enumerate(health_check_calls):
      health_check_method, arg = health_check_call
      method_name = health_check_method.__name__
      health_check_name = method_name.replace("_", " ").strip().capitalize()

      try:
        health_check_method(arg)
      except errors.CheckTestbedReadyError as err:
        logger.info("testbed health check {}/{} failed: {}.".format(
            step + 1, len(health_check_calls), health_check_name))
        err.checks_passed = checks_passed
        err.properties = self.testing_props.copy()
        raise

      checks_passed.append("{}.{}".format(type(self).__name__, method_name))
      logger.info("testbed health check {}/{} succeeded: {}.".format(
          step + 1, len(health_check_calls), health_check_name))

  def _get_filesystem_mounts(self, file_system_output):
    """Parse locations that file systems are mounted on from command output.

    Args:
        file_system_output (str): output of command listing device file
          systems.

    Returns:
        list: locations that file systems are mounted on on the device.
    """
    file_system_mounts = []
    for file_system in file_system_output.splitlines():
      if not file_system:
        continue
      file_system_info = file_system.split()

      # 6 columns of information
      # Filesystem,1K-blocks,Used,Available,Use%,Mounted on
      if len(file_system_info) == 6:
        file_system_mounts.append(file_system_info[5])

    return file_system_mounts
