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

"""Communication Power Ethernet Switch Capability."""
from gazoo_device import decorators
from gazoo_device import gdm_logger

from gazoo_device.capabilities.interfaces import comm_power_base

logger = gdm_logger.get_gdm_logger()


class CommPowerEthernetSwitch(comm_power_base.CommPowerBase):
    """Base class for comm_power_ethernet_switch capability."""

    def __init__(self,
                 device_name,
                 ethernet_switch_disable_fn,
                 ethernet_switch_enable_fn):
        """Create an instance of the comm_power_ethernet_switch capability.

        Args:
            device_name (str): name of the device this capability is attached to.
            ethernet_switch_disable_fn (func): disables ethernet_switch port for device's
                                               ethernet connection.
            ethernet_switch_enable_fn (func): enables ethernet_switch port for device's
                                              ethernet connection.
        """
        super().__init__(device_name=device_name)
        self._ethernet_switch_disable_fn = ethernet_switch_disable_fn
        self._ethernet_switch_enable_fn = ethernet_switch_enable_fn

    @decorators.CapabilityLogDecorator(logger)
    def off(self):
        """Turn off power to the device communications port."""
        self._ethernet_switch_disable_fn()

    @decorators.CapabilityLogDecorator(logger)
    def on(self):
        """Turn on power to the device communication port."""
        self._ethernet_switch_enable_fn()
