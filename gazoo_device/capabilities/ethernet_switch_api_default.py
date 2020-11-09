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

"""ethernet_switch_api_base default implementation."""
from __future__ import absolute_import

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import ethernet_switch_api_base
from gazoo_device.utility import common_utils

logger = gdm_logger.get_gdm_logger()

TIMEOUTS = {
    "ENABLE": 5,
    "DISABLE": 5,
}


class EthernetSwitchApiDefault(ethernet_switch_api_base.EthernetSwitchApiBase):
    """ethernet_switch_api_base default implementation."""

    def __init__(self,
                 device_name,
                 address, port,
                 disable_port_method, enable_port_method, get_port_status_method,
                 pre_enable_port_method=None, post_enable_port_method=None,
                 pre_disable_port_method=None, post_disable_port_method=None):
        """Creates an instance of the EthernetSwitchApiDefault capability.

        Args:
            device_name (str): name of the device with this capability. Used for log and error
                messages.

            address (str): Address of the ethernet switch

            port (str): Port number on ethernet switch where the device is connected

            disable_port_method (func): Function that takes port as input param and disables the
                port

            enable_port_method (func): Function that takes port as input param and enables
                the port

            get_port_status_method (func): Function that takes port as input param and returns
                a str variable refering to the port status

            pre_enable_port_method (func): Function that needs to be executed before enabling the
                port

            post_enable_port_method (func): Function that needs to be executed after enabling the
                port

            pre_disable_port_method (func): Function that needs to be executed before disabling the
                port

            post_disable_port_method (func): Function that needs to be executed after disabling the
                port
        """
        super(EthernetSwitchApiDefault, self).__init__(device_name=device_name)

        self._address = address
        self._port = port

        self.disable_port_method = disable_port_method
        self.pre_disable_port_method = pre_disable_port_method
        self.post_disable_port_method = post_disable_port_method

        self.enable_port_method = enable_port_method
        self.pre_enable_port_method = pre_enable_port_method
        self.post_enable_port_method = post_enable_port_method

        self.get_port_status_method = get_port_status_method

    @decorators.CapabilityLogDecorator(logger)
    def disable(self, no_wait=False):
        """Disables ethernet_switch port for device's ethernet connection.

        Args:
            no_wait (bool): If True, returns before verifying connection status.

        Raises:
          GazooDeviceError: if ethernet connection has not been disabled.
        """
        if not self.status:
            logger.debug("{} Ethernet connection is already disabled.".format(self._device_name))
            return

        if callable(self.pre_disable_port_method):
            self.pre_disable_port_method()

        logger.warn("{} Disabling the ethernet connection by turning off ethernet port# {!r} on "
                    "ethernet switch {!r}.".format(self._device_name, self.port, self.address))
        self.disable_port_method(self.port)

        if not no_wait:
            try:
                common_utils.retry(
                    func=getattr,
                    func_args=[self, "status"],
                    is_successful=common_utils.not_func,
                    timeout=TIMEOUTS["DISABLE"],
                    interval=1,
                    reraise=False
                )
            except errors.CommunicationTimeoutError:
                raise errors.GazooDeviceError(
                    "{} Failed to verify that ethernet connection is disabled".format(
                        self._device_name))

        if callable(self.post_disable_port_method):
            self.post_disable_port_method()

    @decorators.CapabilityLogDecorator(logger)
    def enable(self, no_wait=False):
        """Enables ethernet_switch port for devices ethernet connection.

        Args:
            no_wait (bool): If True, returns before verifying connection status.

        Raises:
            GazooDeviceError: if ethernet connection has not been enabled.
        """
        if self.status:
            logger.debug("{} Ethernet connection is already enabled.".format(self._device_name))
            return

        if callable(self.pre_enable_port_method):
            self.pre_enable_port_method()

        logger.warn("{} Enabling the ethernet connection by turning on ethernet port# {!r} on "
                    "ethernet switch {!r}.".format(self._device_name, self.port, self.address))
        self.enable_port_method(self.port)

        if not no_wait:
            try:
                common_utils.retry(
                    func=getattr,
                    func_args=[self, "status"],
                    is_successful=bool,
                    timeout=TIMEOUTS["ENABLE"],
                    interval=1,
                    reraise=False
                )
            except errors.CommunicationTimeoutError:
                raise errors.GazooDeviceError(
                    "{} Failed to verify that ethernet connection is enabled".format(
                        self._device_name))

        if callable(self.post_enable_port_method):
            self.post_enable_port_method()

    @property
    def address(self):
        """Returns the IP address of the ethernet switch where device is conneced.

        Returns:
            str: ethernet switch ip address
        """
        return self._address

    @property
    def port(self):
        """Returns the port number on the ethernet switch where device is conneced.

        Returns:
            str: ethernet switch ip address
        """
        return self._port

    @property
    def status(self):
        """Current status of the ethernet switch port.

        Returns:
            bool: True if ethernet ethernet switch port is enabled, otherwise False
        """
        port_status = self.get_port_status_method(self.port)
        return port_status.lower() in ["on", "1", "enable"]
