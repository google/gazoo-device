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

"""The default implementation of the usb_hub capability.

The usb_hub capability is intended to be used by primary devices that require the ability to
get or change the USB power mode for a configured port on a USB hub.

The configured USB hub must support the switch_power capability.
"""
from __future__ import absolute_import

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import usb_hub_base

logger = gdm_logger.get_gdm_logger()


class UsbHubDefault(usb_hub_base.UsbHubBase):
    """Base class for usb_hub."""

    def __init__(self,
                 device_name,
                 manager,
                 hub_name,
                 device_port,
                 add_log_note_fn=None,
                 change_triggers_reboot=False,
                 wait_for_bootup_complete_fn=None):
        """Create an instance of the usb_hub capability.

        Args:
            device_name (str): name of the device this capability is attached to.
            manager (Manager): The manager used to create a device.
            hub_name (str): name of the hub this device is attached to.
            device_port (int): usb hub port number used by the device.
            add_log_note_fn (func): The method used to send a log note to the device log.
            change_triggers_reboot (bool): Set change_triggers_reboot to TRUE if changing the
                                           USB power mode for the device causes a reboot.
            wait_for_bootup_complete_fn (func): A method that the capability can call to wait for
                                                a reboot to complete if triggered by a change.

        Raises:
            ValueError: If the hub device cannot be created.
        """
        super(UsbHubDefault, self).__init__(device_name=device_name)
        if not hub_name or not device_port:
            msg = ("{name} `device_usb_hub_name` and `device_usb_port` properties are unset. "
                   "If the device is plugged into a Cambrionix, issue "
                   "'gdm redetect {name}' or 'gdm set-prop {name} <property> <value>' to set them."
                   .format(name=device_name))
            logger.debug(msg)
            raise ValueError(msg)
        if not manager:
            msg = ("{} failed to created usb_hub capability. Device class must not "
                   "be closed when initiating the capability.").format(device_name)
            logger.debug(msg)
            raise ValueError(msg)

        self._hub_name = hub_name
        self._device_port = device_port
        self._usb_hub = manager.create_device(hub_name)
        self._add_log_note_fn = add_log_note_fn
        self._change_triggers_reboot = change_triggers_reboot
        self._wait_for_bootup_complete_fn = wait_for_bootup_complete_fn

    @property
    def name(self):
        """The name of the usb hub.

        Returns:
            str: usb hub name.

        Raises:
            GazooDeviceError: usb hub name retrieval failed
        """
        return self._hub_name

    @property
    def supported_modes(self):
        """Get the USB power modes supported by the USB hub."""
        return self._usb_hub.switch_power.supported_modes

    @property
    def device_port(self):
        """The usb hub port number used by device.

        Returns:
            int: port number on usb hub.

        Raises:
            GazooDeviceError: usb hub port number retrieval failed
        """
        return self._device_port

    @decorators.CapabilityLogDecorator(logger)
    def check_device_ready(self):
        return self._usb_hub.check_device_ready()

    @decorators.CapabilityLogDecorator(logger, level=decorators.DEBUG)
    def get_device_power(self):
        """Gets usb port mode if set.

        Returns:
            str: 'sync', 'charge', or 'off'

        Raises:
            GazooDeviceError: if key 'mode' doesn't exist
        """
        return self._usb_hub.switch_power.get_mode(self._device_port)

    @decorators.CapabilityLogDecorator(logger)
    def set_device_power(self, mode, no_wait=False):
        """Turns associated powered usb hub port, if available, power state to sync, off, charge.

        Args:
            mode (str): power mode to set USB hub port to ("sync", "off", "charge")
            no_wait (bool): return before boot up is complete. Default: False.

        Raises:
            GazooDeviceError: if invalid mode provided

        Notes:
            'sync' is data and power on, 'charge' is power only on, 'off' is both off.
        """
        self._set_port_mode(mode, self.device_port, no_wait)

    @decorators.CapabilityLogDecorator(logger)
    def power_off(self, port, no_wait=False):
        """This command powers off the port specified or all ports if port is None.

        Args:
            port (int): identifies which hub port to power off
            no_wait (bool): Return before boot up is complete. Default: False.

        Raises:
             GazooDeviceError: port number invalid.
        """
        self._set_port_mode("off", port, no_wait)

    @decorators.CapabilityLogDecorator(logger)
    def power_on(self, port, data_sync=True, no_wait=False):
        """This command powers on the port specified or all ports if port is None.

        Args:
            port (int): identifying which hub port to power on
            data_sync (bool): True if data should be enabled, false for power only
            no_wait (bool): Return before boot up is complete. Default: False.

        Raises:
             GazooDeviceError: port number invalid.
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
            GazooDeviceError: mode or port is invalid.
        """
        if self._verify_power_change_needed(mode, self.device_port):
            logger.debug("{} setting device USB power to '{}' for hub: {} and port: {}".
                         format(self._device_name, mode, self._hub_name, port))
            if self._add_log_note_fn:
                self._add_log_note_fn("Setting device USB power to '{}' for hub {} and port {}".
                                      format(mode, self._hub_name, port))
                if self._change_triggers_reboot:
                    self._add_log_note_fn("GDM triggered reboot via USB power change.")
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
            GazooDeviceError: if mode provided or usb_hub management is not a valid option
        """
        mode = mode.lower()
        if mode not in self.supported_modes:
            raise errors.GazooDeviceError("{} USB power mode must be in "
                                          "supported_modes".format(self._device_name))

        current_mode = self._usb_hub.switch_power.get_mode(port)
        return current_mode != mode
