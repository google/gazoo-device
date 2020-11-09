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

"""Communication Power Cambrionix Capability."""
import time
from gazoo_device import decorators
from gazoo_device import gdm_logger

from gazoo_device.capabilities.interfaces import comm_power_base

logger = gdm_logger.get_gdm_logger()


class CommPowerCambrionix(comm_power_base.CommPowerBase):
    """Base class for comm_power_cambrionix capability."""

    def __init__(self,
                 device_name,
                 manager,
                 data_usb_hub_name,
                 data_usb_port,
                 close_all_transports_fn,
                 open_all_transports_fn,
                 add_log_note_fn,
                 power_and_data_share_cable=False):
        """Create an instance of the comm_power_cambrionix capability.

        Args:
            device_name (str): name of the device this capability is attached to.
            manager (Manager): the manager used to create a device.
            data_usb_hub_name (str): name of the Cambrionix the device data line is connected to.
            data_usb_port (int): Cambrionix port number the device data line is connected to.
            close_all_transports_fn (func): switchboard method to close all transports.
            open_all_transports_fn (func): switchboard method to open all transports.
            add_log_note_fn (func): The method used to send a log note to the device log.
            power_and_data_share_cable (bool): set power_and_data_share_cable to TRUE if device
                                               shares a common USB cable for its power and data.
        Raises:
            ValueError: If the capability cannot be created.
        """
        super().__init__(device_name=device_name)
        if not data_usb_hub_name or not data_usb_port:
            msg = (f"{device_name} the data_usb_hub_name and data_usb_port are unset. "
                   "If the device is plugged into a Cambrionix, issue "
                   "'gdm redetect {device_name}' to set them.")
            logger.debug(msg)
            raise ValueError(msg)
        if not manager:
            msg = (f"{device_name} failed to create comm_power_cambrionix capability."
                   " Device class must not be closed when initiating the capability.")
            logger.debug(msg)
            raise ValueError(msg)

        self._data_usb_hub_name = data_usb_hub_name
        self._data_usb_port = int(data_usb_port)
        self._cambrionix = manager.create_device(data_usb_hub_name)
        self._power_and_data_share_cable = power_and_data_share_cable
        self._add_log_note_fn = add_log_note_fn
        self._close_all_transports_fn = close_all_transports_fn
        self._open_all_transports_fn = open_all_transports_fn

    @decorators.CapabilityLogDecorator(logger)
    def off(self):
        """Turn off power to the device communications port."""
        if self._power_and_data_share_cable:
            if self._add_log_note_fn:
                self._add_log_note_fn(
                    f"comm_power.off() called on {self._device_name} set communication port "
                    f"{self._data_usb_port} to charge as device has a single USB cable "
                    "for data and power.")
            self._close_all_transports_fn()
            self._cambrionix.switch_power.power_on(self._data_usb_port, data_sync=False)
        else:
            self._close_all_transports_fn()
            self._cambrionix.switch_power.power_off(self._data_usb_port)

    @decorators.CapabilityLogDecorator(logger)
    def on(self):
        """Turn on power to the device communication port."""
        self._cambrionix.switch_power.power_on(self._data_usb_port)
        time.sleep(5)  # Small delay to give time for 'dev/tty' to populate
        self._open_all_transports_fn()
