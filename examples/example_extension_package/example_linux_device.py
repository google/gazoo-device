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

"""Example of a primary device controller.

This example targets a generic Linux device accessible over SSH.
Assumptions for this device controller to work:
- The target device is running Linux.
- The device responds to ping and can be SSHed into.
- SSH does not require a password. You may need to set up passwordless
  SSH access via ssh-copy-id or uncomment "key_info" communication argument and
  generate an SSH key.
- The SSH username is "root". If not, change the value of _SSH_USERNAME.

The few modifications you may need to perform to make this example controller
work with your device are marked with # TODO(user) comments.
"""
import os.path
from typing import Dict, NoReturn, Tuple

from gazoo_device import data_types
from gazoo_device import decorators
from gazoo_device import detect_criteria
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.base_classes import ssh_device
import immutabledict

logger = gdm_logger.get_logger()

_COMMANDS = immutabledict.immutabledict({
    "FIRMWARE_VERSION": "uname -r",
    # Commands prefixed with "INFO_" will run during detection.
    # Their return values will be stored in the persistent config file.
    # The values will be available in
    # self.props["persistent_identifiers"][<property>].
    # In this case, the property name will be "hardware_architecture".
    "INFO_HARDWARE_ARCHITECTURE": "uname -m",
    "REBOOT": "sudo reboot",
})
_REGEXES = immutabledict.immutabledict({})
_TIMEOUTS = immutabledict.immutabledict({})
# TODO(user): You may need to change the value of _SSH_USERNAME for your device.
_SSH_USERNAME = "root"

_EXTENSION_PACKAGE_DIR = os.path.abspath(os.path.dirname(__file__))
_LOG_EVENT_FILTER_DIR = os.path.join(_EXTENSION_PACKAGE_DIR,
                                     "log_event_filters")

# _PACKAGE_NAME must match the name of the package.
_PACKAGE_NAME = "example_extension_package"
SSH_KEY_INFO = data_types.KeyInfo(
    file_name="linuxexample_ssh_key",
    type=data_types.KeyType.SSH,
    package=_PACKAGE_NAME)


class ExampleLinuxDevice(ssh_device.SshDevice):
  """Example primary device controller for a generic Linux device."""
  # Device controllers must correspond to a single device type.
  # Therefore, detect criteria must uniquely identify a single device
  # type. A generic Linux device controller doesn't satisfy this property,
  # but we'll cheat a bit for the purpose of this example.
  # GenericQuery.ALWAYS_TRUE query below will cause all devices GDM can SSH into
  # to be identified as ExampleLinuxDevice.
  DETECT_MATCH_CRITERIA = {
      detect_criteria.GenericQuery.ALWAYS_TRUE: True,
      # Real detection queries look like this:
      # detect_criteria.SshQuery.SOME_QUERY_FUNCTION: "regex"
      # detect_criteria.SshQuery.ANOTHER_QUERY_FUNCTION: True
  }
  DEVICE_TYPE = "linuxexample"
  _COMMUNICATION_KWARGS = {
      **ssh_device.SshDevice._COMMUNICATION_KWARGS,
      "username": _SSH_USERNAME,
      # TODO(user): Uncomment the key below if your device needs a password to
      # connect via SSH and you want to use a controller-specific key.
      # "key_info": SSH_KEY_INFO,
  }
  _DEFAULT_FILTERS = (
      os.path.join(_LOG_EVENT_FILTER_DIR, "basic.json"),
      os.path.join(_LOG_EVENT_FILTER_DIR, "crashes.json"),
  )
  _OWNER_EMAIL = "gdm-authors@google.com"

  def __init__(self,
               manager,
               device_config,
               log_file_name=None,
               log_directory=None):
    """Initializes an ExampleLinuxDevice."""
    super().__init__(manager,
                     device_config,
                     log_file_name=log_file_name,
                     log_directory=log_directory)
    self._commands.update(_COMMANDS)
    self._regexes.update(_REGEXES)
    self._timeouts.update(_TIMEOUTS)

  @decorators.LogDecorator(logger)
  def factory_reset(self) -> NoReturn:
    """Resets the device to its factory default settings.

    Raises:
      NotImplementedError: There's no command to factory reset a generic Linux
        device.
    """
    # A typical factory_reset implementation clears persistent settings (for
    # example, user settings) and reboots the device to clear settings stored
    # in memory.
    raise NotImplementedError("Not implemented for a generic Linux device.")

  @decorators.DynamicProperty
  def firmware_version(self) -> str:
    """Firmware version of the device."""
    return self.shell(self.commands["FIRMWARE_VERSION"])

  @decorators.LogDecorator(logger)
  def get_detection_info(self) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Returns the persistent and optional properties of a device."""
    persistent_props, optional_props = super().get_detection_info()
    # Note that setting the "serial_number" persistent property is
    # required to generate the GDM name for the device.
    # If the device doesn't expose the serial number, set
    # self.props["persistent_identifiers"]["serial_number"] to any
    # persistent unique identifier such as a MAC address of an interface.
    if not persistent_props.get("serial_number"):
      persistent_props["serial_number"] = "56781234"
    # Setting the "model" persistent property is also required.
    # This refers to the hardware model of the device.
    # Typical values are "Production", "Development", "Prototype".
    if not persistent_props.get("model"):
      persistent_props["model"] = "Production"
    # Initialize an example optional property.
    optional_props["my_optional_prop"] = "A default value"

    return persistent_props, optional_props

  @decorators.PersistentProperty
  def hardware_architecture(self) -> str:
    """Hardware architecture of the device (such as "x86_64").

    Returns:
      Hardware architecture of the device.

    This property is not required by GDM. It's an example of a persistent
    property which is populated during detection.
    """
    return self.props["persistent_identifiers"]["hardware_architecture"]

  @decorators.OptionalProperty
  def my_optional_prop(self) -> str:
    """Example of an optional property which can be set by users."""
    return self.props["optional"]["my_optional_prop"]

  @my_optional_prop.setter
  def my_optional_prop(self, new_value: str) -> None:
    """Example of an optional property which can be set by users."""
    self.props["optional"]["my_optional_prop"] = new_value

  @decorators.PersistentProperty
  def platform(self) -> str:
    """Software platform."""
    return "new_top_secret_platform"

  @decorators.LogDecorator(logger)
  def reboot(self, no_wait: bool = False, method: str = "shell") -> None:
    """Issues a soft reboot command.

    Args:
      no_wait: Flag indicating whether reboot verification should be skipped.
        If False, blocks until reboot completion.
      method: Reboot technique to use. Only "shell" is supported.

    Raises:
      DeviceError: If the provided reboot method is not supported.
    """
    if method not in ["shell"]:
      raise errors.DeviceError(
          "{} reboot failed. Unsupported reboot method {!r} requested."
          .format(self.name, method))

    self._inject_log_marker()
    self.switchboard.add_log_note("GDM triggered reboot")
    # Devices typically go offline before responding to the command.
    # Use switchboard.send() directly instead of shell() to avoid waiting for a
    # response.
    self.switchboard.send(self.commands["REBOOT"])
    if not no_wait:
      self._verify_reboot()
