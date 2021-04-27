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

"""Switch power capability interface.

This class defines the required API all flavors of the switch_power capability.
"""
import abc
from gazoo_device.capabilities.interfaces import capability_base


class SwitchPowerBase(capability_base.CapabilityBase):
  """Abstract base class defining the API for the switch_power capability."""

  @abc.abstractproperty
  def supported_modes(self):
    """Get auxiliary device supported power modes."""

  @abc.abstractmethod
  def power_on(self, port):
    """This command powers on the port specified.

    Args:
        port (int): Identifies which auxiliary device port to power on.
    """

  @abc.abstractmethod
  def power_off(self, port):
    """This command powers off the port specified.

    Args:
        port (int): Identifies which auxiliary device port to power off.
    """

  @abc.abstractmethod
  def set_mode(self, mode, port):
    """Sets the given auxiliary device port to the mode specified.

    Args:
        mode (str): auxiliary device mode to set.
        port (int): The port to set.

    Raises:
        DeviceError: invalid port, or mode.
    """

  @abc.abstractmethod
  def get_mode(self, port):
    """Gets the auxiliary device mode for the specified port.

    Args:
        port (int): Use this port to get the mode.

    Returns:
        str: auxiliary device port mode settings

    Raises:
        DeviceError: invalid port.
    """
