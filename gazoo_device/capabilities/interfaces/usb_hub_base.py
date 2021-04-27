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

"""USB hub capability interface.

Abstract Base class for the usb_hub capability.

The usb_hub capability is intended to be used by primary devices that require
the ability to
get or change the USB power mode for a configured port on a USB hub.

The configured USB hub must support the switch_power capability.
"""
import abc
from gazoo_device.capabilities.interfaces import capability_base


class UsbHubBase(capability_base.CapabilityBase):
  """Abstract base class for USB hub capability."""

  @abc.abstractproperty
  def name(self):
    """The name of the usb hub.

    Returns:
        str: usb hub name.
    """

  @abc.abstractproperty
  def device_port(self):
    """The usb hub port number used by device.

    Returns:
        int: port number on usb hub.
    """

  @abc.abstractproperty
  def supported_modes(self):
    """Get the USB power modes supported by the USB hub."""

  @abc.abstractmethod
  def get_device_power(self):
    """Gets usb port mode if set.

    Returns:
        str: 'sync', 'charge', or 'off'

    Raises:
        DeviceError: if usb_hub and usb_port are not properly set.
    """

  @abc.abstractmethod
  def set_device_power(self, mode):
    """Turns associated powered usb hub port, if available, power state to sync, off, charge.

    Args:
        mode (str): power mode to set USB hub port to ("sync", "off",
          "charge")

    Raises:
        DeviceError: if invalid mode provided or usb_hub management is not a
        valid option

    Notes:
        'sync' is data and power on, 'charge' is power only on, 'off' is both
        off.
    """

  @abc.abstractmethod
  def power_off(self, port=None):
    """This command powers off the port specified or all ports if port is None.

    Args:
        port (int): identifies which hub port to power off

    Raises:
         DeviceError: port number invalid.
    """

  @abc.abstractmethod
  def power_on(self, port=None, data_sync=True):
    """This command powers on the port specified or all ports if port is None.

    Args:
        port (int): identifying which hub port to power on
        data_sync (bool): True if data should be enabled, false for power only

    Raises:
         DeviceError: port number invalid.
    """
