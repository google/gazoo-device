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

"""Interface containing required GDM APIs for primary devices.

Some of these APIs are implemented in GazooDeviceBase and don't need to be
re-implemented in derived device classes. Device classes should inherit from
GazooDeviceBase, not from this class.
"""
import abc


class PrimaryDeviceBase(abc.ABC):
  """Interface containing required GDM APIs for primary devices."""
  COMMUNICATION_TYPE = None  # Override
  DETECT_MATCH_CRITERIA = None  # Overrride
  DEVICE_TYPE = None  # Override
  _COMMUNICATION_KWARGS = {}
  _OWNER_EMAIL = ""  # override in child classes
  # Maximum number of attempts for recovery from health check failures.
  _RECOVERY_ATTEMPTS = 1

  @abc.abstractproperty
  def alias(self):
    """Returns the user-defined device alias (string)."""

  @abc.abstractproperty
  def commands(self):
    """Dictionary of commands issued to the device via shell."""

  @abc.abstractproperty
  def communication_address(self):
    """Returns the name of the main communication port (for example, ip address)."""

  @abc.abstractproperty
  def connected(self):
    """Returns whether the device is connected or not."""

  @abc.abstractproperty
  def firmware_version(self):
    """Returns the firmware version installed on the device."""

  @abc.abstractproperty
  def health_checks(self):
    """Returns list of methods to execute as health checks."""

  @abc.abstractproperty
  def model(self):
    """Returns the device model."""

  @abc.abstractproperty
  def name(self):
    """Returns the unique identifier for the device (like cambrionix-a3b4)."""

  @abc.abstractproperty
  def os(self):
    """Operating system of the device (like Android or Linux)."""

  @abc.abstractproperty
  def platform(self):
    """Platform of the device."""

  @abc.abstractproperty
  def regexes(self):
    """Regular expressions used to retrieve properties, events, states from device output."""

  @abc.abstractproperty
  def serial_number(self):
    """Returns the serial number of the device."""

  @abc.abstractproperty
  def timeouts(self):
    """Dictionary of default timeouts to use when expecting certain actions."""

  @abc.abstractmethod
  def check_device_ready(self):
    """Checks if the device is ready for testing.

    If not, raises a CheckDeviceReadyError.

    This is typically implemented by checking if device responds to shell
    commands and if it's streaming logs. There can be additional device-specific
    checks as well.
    """

  @abc.abstractmethod
  def close(self):
    """Calls close on the communication ports and resets anything needed.

    Note:
        Resets the buttons and terminates the child processes.
    """

  @abc.abstractmethod
  def get_detection_info(self):
    """Gets the persistent and optional attributes of a device during setup.

    Returns:
      tuple: (dict, dict) dictionary of persistent attributes,
             dictionary of optional attributes (set to None).
    """

  @abc.abstractmethod
  def get_dynamic_properties(self):
    """Returns dictionary of dynamic properties."""

  @abc.abstractmethod
  def get_optional_properties(self):
    """Returns dictionary of optional properties."""

  @abc.abstractmethod
  def get_persistent_properties(self):
    """Returns dictionary of persistent properties."""

  @abc.abstractmethod
  def get_property_names(self):
    """Returns a list of all property names."""

  @abc.abstractmethod
  def factory_reset(self):
    """Places the device back in an out-of-box state.

    Note:
        It unpairs the device as necessary.
    """

  @abc.abstractmethod
  def is_connected(cls, device_config):  # pylint: disable=no-self-argument
    """Determines if the device is connected (reachable).

    Note:
        This method is used during device detection.
        This should be a class or static method, not an instance method.

    Args:
        device_config (dict): contains "persistent" dict

    Returns:
        bool: True if the device is connected (i.e. pingable), False otherwise.
    """

  @abc.abstractmethod
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

  @abc.abstractmethod
  def reboot(self, no_wait=False, method="shell"):
    """Issues a soft reboot command.

    Args:
        no_wait (bool): flag indicating whether reboot verification should be
          skipped. If False, blocks until reboot completion.
        method (str): reboot technique to use.
    """

  @abc.abstractmethod
  def recover(self, error):
    """Attempts to recover device based on the type of error specified.

    Note: The check_device_ready method can raise a number of separate
    exceptions which are passed to this method as exception objects. The recovery
    method is chosen based on the type of the error. See subclasses of
    CheckDeviceError in errors.py for a list of errors raised by
    check_device_ready.

    Args:
        error (CheckDeviceReadyError): A subclass of CheckDeviceReadyError
        that will be used to identify a possible recovery solution to use.

    Raises:
        DeviceError: If device recovery fails while attempting to perform
        recovery steps.
        CheckDeviceReadyError: If there are no recovery steps available for
        the error argument, it will be re-raised directly.
    """

  @abc.abstractmethod
  def shell(self,
            command,
            command_name="shell",
            timeout=None,
            port=0,
            searchwindowsize=2000,
            include_return_code=False):
    """Sends command and returns response.

    Args:
        command (str): Command to send to the device.
        command_name (str): Optional identifier to use in logs for this
          command.
        timeout (float or None): Seconds to wait for pattern after command sent.
          If None, the default shell timeout is used.
        port (int): Which port to send on, 0 or 1. Default: 0.
        searchwindowsize (int): Number of the last bytes to look at
        include_return_code (bool): flag indicating return code should be
          returned

    Returns:
        str or tuple: response or (response, return_code) if
        include_return_code is True.
    """

  @abc.abstractmethod
  def wait_for_bootup_complete(self, timeout=None):
    """Wait until the device finishes booting up and is ready for testing.

    Args:
        timeout (int): max time to wait for the device to finish booting up.

    Raises:
        DeviceNotBootupCompleteError: device failed to finish booting up
        before the timeout.
    """
