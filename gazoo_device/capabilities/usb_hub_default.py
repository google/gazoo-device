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

"""The default implementation of the usb_hub capability.

The usb_hub capability is intended to be used by primary devices that require
the ability to
get or change the USB power mode for a configured port on a USB hub.

The configured USB hub must support the switch_power capability.
"""

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import usb_hub_base

logger = gdm_logger.get_logger()


class UsbHubDefault(usb_hub_base.UsbHubBase):
  """Base class for usb_hub."""

  def __init__(self,
               device_name,
               get_manager,
               hub_name,
               device_port,
               get_switchboard_if_initialized,
               change_triggers_reboot=False,
               wait_for_bootup_complete_fn=None,
               settable=False):
    """Create an instance of the usb_hub capability.

    Args:
        device_name (str): name of the device this capability is attached
          to.
        get_manager (method): A method which returns the Manager instance.
        hub_name (str): name of the hub this device is attached to.
        device_port (int): usb hub port number used by the device.
        get_switchboard_if_initialized (callable): function which returns
          a Switchboard instance or None if Switchboard hasn't been initialized.
        change_triggers_reboot (bool): Set change_triggers_reboot to TRUE if
          changing the USB power mode for the device causes a reboot.
        wait_for_bootup_complete_fn (func): A method that the capability can
          call to wait for a reboot to complete if triggered by a change.
        settable (bool): whether or not the properties are settable.
    """
    super(UsbHubDefault, self).__init__(device_name=device_name)
    self._hub_name = hub_name
    self._device_port = device_port
    self._get_switchboard_if_initialized = get_switchboard_if_initialized
    self._change_triggers_reboot = change_triggers_reboot
    self._wait_for_bootup_complete_fn = wait_for_bootup_complete_fn
    self._usb_hub = None
    self._settable = settable
    self._get_manager = get_manager

  @decorators.CapabilityLogDecorator(logger, level=decorators.DEBUG)
  def health_check(self):
    """Checks that the capability is ready to use.

    Raises:
        CapabilityNotReadyError: if unable to create auxiliary device for
        power switching.
    """
    unset_props = []
    if self.name is None:
      unset_props.append("device_usb_hub_name")
    if self.device_port is None:
      unset_props.append("device_usb_port")
    if unset_props:
      if self._settable:
        msg_format = ("If device is connected to Cambrionix, "
                      "set them via 'gdm set-prop {} <property> <value>'")
      else:
        msg_format = ("If device is connected to Cambrionix, "
                      "set them via 'gdm redetect {}")
      msg = msg_format.format(self._device_name)
      error_msg = "properties {} are unset. ".format(
          " and ".join(unset_props)) + msg
      raise errors.CapabilityNotReadyError(
          msg=error_msg, device_name=self._device_name)
    try:
      self._usb_hub = self._get_manager().create_device(self.name)
    except (errors.DeviceError, RuntimeError) as err:
      raise errors.CapabilityNotReadyError(
          msg=repr(err), device_name=self._device_name)
    self._healthy = True

  @decorators.CapabilityLogDecorator(logger, level=decorators.DEBUG)
  def close(self):
    """Closes the USB hub device instance."""
    if self._usb_hub:
      self._usb_hub.close()
    super().close()

  @decorators.PersistentProperty
  def name(self):
    """The name of the usb hub.

    Returns:
        str: usb hub name.

    Raises:
        DeviceError: usb hub name retrieval failed
    """
    return self._hub_name

  @decorators.DynamicProperty
  def supported_modes(self):
    """Get the USB power modes supported by the USB hub."""
    if not self.healthy:
      self.health_check()
    return self._usb_hub.switch_power.supported_modes

  @decorators.PersistentProperty
  def device_port(self):
    """The usb hub port number used by device.

    Returns:
        int: port number on usb hub.

    Raises:
        DeviceError: usb hub port number retrieval failed
    """
    return self._device_port

  @decorators.CapabilityLogDecorator(logger)
  def check_device_ready(self):
    self.health_check()

  @decorators.CapabilityLogDecorator(logger, level=decorators.DEBUG)
  def get_device_power(self):
    """Gets usb port mode if set.

    Returns:
        str: 'sync', 'charge', or 'off'

    Raises:
        DeviceError: if key 'mode' doesn't exist
    """
    if not self.healthy:
      self.health_check()
    return self._usb_hub.switch_power.get_mode(self._device_port)

  @decorators.CapabilityLogDecorator(logger)
  def set_device_power(self, mode, no_wait=False):
    """Turns associated powered usb hub port, if available, power state to sync, off, charge.

    Args:
        mode (str): power mode to set USB hub port to ("sync", "off",
          "charge")
        no_wait (bool): return before boot up is complete. Default: False.

    Raises:
        DeviceError: if invalid mode provided

    Notes:
        'sync' is data and power on, 'charge' is power only on, 'off' is
        both off.
    """
    self._set_port_mode(mode, self.device_port, no_wait)

  @decorators.CapabilityLogDecorator(logger)
  def power_off(self, port, no_wait=False):
    """This command powers off the port specified or all ports if port is None.

    Args:
        port (int): identifies which hub port to power off
        no_wait (bool): Return before boot up is complete. Default: False.

    Raises:
         DeviceError: port number invalid.
    """
    self._set_port_mode("off", port, no_wait)

  @decorators.CapabilityLogDecorator(logger)
  def power_on(self, port, data_sync=True, no_wait=False):
    """This command powers on the port specified or all ports if port is None.

    Args:
        port (int): identifying which hub port to power on
        data_sync (bool): True if data should be enabled, false for power
          only
        no_wait (bool): Return before boot up is complete. Default: False.

    Raises:
         DeviceError: port number invalid.
    """
    mode = "sync"
    if not data_sync:
      mode = "charge"
    self._set_port_mode(mode, port, no_wait)

  def _set_port_mode(self, mode, port, no_wait):
    """Set the USB power mode fort the specified port.

    Args:
        mode (str): power mode to set USB hub port to
        port (int): identifies which hub port to set the mode on.
        no_wait (bool): Return before boot up is complete. Default: False.

    Raises:
        DeviceError: mode or port is invalid.
    """
    if not self.healthy:
      self.health_check()
    if self._verify_power_change_needed(mode, self.device_port):
      logger.debug(
          "{} setting device USB power to '{}' for hub: {} and port: {}".format(
              self._device_name, mode, self._hub_name, port))
      switchboard = self._get_switchboard_if_initialized()
      if switchboard:
        switchboard.add_log_note(
            "Setting device USB power to '{}' for hub {} and port {}".format(
                mode, self._hub_name, port))
        if self._change_triggers_reboot:
          switchboard.add_log_note(
              "GDM triggered reboot via USB power change.")
      self._usb_hub.switch_power.set_mode(mode, port)
      if self._change_triggers_reboot and not no_wait:
        self._wait_for_bootup_complete_fn()

  def _verify_power_change_needed(self, mode, port):
    """Returns whether or not port power change needed.

    Args:
        mode (str): power mode to set USB hub port to.
        port (int): Identifies which port to check the power mode.

    Returns:
        bool: if current mode is not the same as expected mode.

    Raises:
        DeviceError: if mode provided or usb_hub management is not a valid
        option
    """
    mode = mode.lower()
    if mode not in list(self.supported_modes):
      raise errors.DeviceError("{} USB power mode must be in "
                               "supported_modes".format(self._device_name))
    if not self.healthy:
      self.health_check()
    current_mode = self._usb_hub.switch_power.get_mode(port)
    return current_mode != mode
