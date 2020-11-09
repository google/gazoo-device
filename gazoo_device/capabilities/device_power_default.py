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

"""Device Power Default Capability."""
import time

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger

from gazoo_device.capabilities.interfaces import device_power_base

logger = gdm_logger.get_gdm_logger()

SUPPORTED_HUB_TYPES = ["cambrionix", "powerswitch", "unifi_switch", "ethernet_switch"]


class DevicePowerDefault(device_power_base.DevicePowerBase):
    """Base class for device_power."""

    def __init__(self,
                 device_name,
                 create_device_func,
                 hub_type,
                 props,
                 settable,
                 hub_name_prop,
                 port_prop,
                 wait_for_bootup_complete_fn,
                 switchboard_inst,
                 change_triggers_reboot=False):
        """Create an instance of the device_power capability.

        Args:
            device_name (str): name of the device this capability is attached to.
            create_device_func (func): create_device method.
            hub_type (str): type of switch for power cycling.
            props (dict): dictionary of device props from configuration file.
            settable (bool): whether or not the properties are settable.
            hub_name_prop (str):  name of the hub name property
            port_prop (str): name of the hub port property
            wait_for_bootup_complete_fn (func): a method that the capability can call to wait for
                                                a reboot to complete if triggered by a change.
            switchboard_inst (object): instance of switchboard capability
            change_triggers_reboot (bool): set change_triggers_reboot to TRUE if changing the
                                           power mode for the device causes a reboot.

        Raises:
            ValueError: if hub type not a known type.
        """
        super().__init__(device_name=device_name)

        self._hub = None
        self._create_device_func = create_device_func
        self._settable = settable
        self._hub_name_prop = hub_name_prop
        self._props = props
        self._port_prop = port_prop
        if hub_type not in SUPPORTED_HUB_TYPES:
            raise ValueError(
                "Hub Type {} not supported. Valid types: {}".format(
                    hub_type, SUPPORTED_HUB_TYPES))
        self._hub_type = hub_type

        # Set the properties
        self._dict_name = "optional" if self._settable else "persistent_identifiers"

        self._wait_for_bootup_complete_fn = wait_for_bootup_complete_fn
        self._switchboard = switchboard_inst
        self._change_triggers_reboot = change_triggers_reboot

    @decorators.CapabilityLogDecorator(logger, level=decorators.DEBUG)
    def health_check(self):
        """Checks that the capability is ready to use.

        Raises:
            CapabilityNotReadyError: if unable to create auxiliary device for power switching.
        """
        unset_props = []
        if self.hub_name is None:
            unset_props.append(self._hub_name_prop)
        if self.port_number is None:
            unset_props.append(self._port_prop)
        if unset_props:
            if self._settable:
                msg_format = ("If device is connected to {}, "
                              "set them via 'gdm set-prop {} <property> <value>'")
            else:
                msg_format = ("If device is connected to {}, "
                              "set them via 'gdm redetect {}")
            msg = msg_format.format(self._hub_type, self._device_name)
            error_msg = "properties {} are unset. ".format(" and ".join(unset_props)) + msg
            raise errors.CapabilityNotReadyError(msg=error_msg,
                                                 device_name=self._device_name)
        try:
            self._hub = self._create_device_func(self.hub_name)
        except errors.GazooDeviceError as err:
            raise errors.CapabilityNotReadyError(msg=str(err),
                                                 device_name=self._device_name)
        self._healthy = True

    @decorators.SettableProperty
    def hub_name(self):
        """Name of the hub the device is attached to."""
        return self._props[self._dict_name].get(self._hub_name_prop)

    @decorators.PersistentProperty
    def hub_type(self):
        """Device type of the hub."""
        return self._hub_type

    @decorators.DynamicProperty
    def port_mode(self):
        """port mode."""
        if not self.healthy:
            self.health_check()
        return self._hub.switch_power.get_mode(self.port_number)

    @decorators.SettableProperty
    def port_number(self):
        """Port number the device is attached to."""
        return self._props[self._dict_name].get(self._port_prop)

    @decorators.CapabilityLogDecorator(logger)
    def cycle(self, no_wait=False):
        """Power off then power on the device.

        Args:
            no_wait (bool):  Return before verifying boot up.
        """
        if not self.healthy:
            self.health_check()
        self.off()
        time.sleep(2)  # Small delay before calling power_on
        self.on(no_wait=no_wait)

    @decorators.CapabilityLogDecorator(logger)
    def off(self):
        """Turn off power to the device."""
        if not self.healthy:
            self.health_check()
        if self._change_triggers_reboot:
            self._switchboard.add_log_note(
                f"GDM triggered reboot via {self.hub_type} power change.")
            self._hub.switch_power.power_off(self.port_number)
            self._wait_for_bootup_complete_fn()
        else:
            self._switchboard.close_all_transports()
            self._hub.switch_power.power_off(self.port_number)

    @decorators.CapabilityLogDecorator(logger)
    def on(self, no_wait=False):
        """Turn on power to the device.

        Args:
            no_wait (bool):  Return before verifying boot up.
        """
        if not self.healthy:
            self.health_check()
        if self._change_triggers_reboot:
            self._switchboard.add_log_note(
                f"GDM triggered reboot via {self.hub_type} power change.")
        self._hub.switch_power.power_on(self.port_number)
        if not self._change_triggers_reboot:
            time.sleep(2)  # Small delay to give time for 'dev/tty' to populate
            self._switchboard.open_all_transports()

        if not no_wait:
            self._wait_for_bootup_complete_fn()
