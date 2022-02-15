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

"""Implementation of the switch_power_ethernet."""
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import switch_power_base
from gazoo_device.utility import retry

logger = gdm_logger.get_logger()

ON = "on"
OFF = "off"

TIMEOUTS = {"STATE_CHANGE": 5}


class SwitchPowerEthernet(switch_power_base.SwitchPowerBase):
  """Switch power flavor for ethernet switches."""

  def __init__(self, device_name, get_port_status_func, turn_on_port_func,
               turn_off_port_func):
    """Create an instance of the switch power with ethernet capability.

    Args:
        device_name (str): name, usually the switch ip address.
        get_port_status_func (func): function to get port status.
        turn_on_port_func (func): function to turn on port.
        turn_off_port_func (func): function to turn off port.
    """
    super().__init__(device_name=device_name)
    self._get_port_status_func = get_port_status_func
    self._turn_on_port_func = turn_on_port_func
    self._turn_off_port_func = turn_off_port_func

  @decorators.PersistentProperty
  def supported_modes(self):
    """Get the power modes supported by the switch."""
    return [OFF, ON]

  def get_mode(self, port):
    """Gets the mode for the specified port.

    Args:
      port (int): Use this port to get the mode.

    Returns:
        str: port mode settings 'off', 'on'

    Raises:
      DeviceError: invalid port.
    """
    port_status = self._get_port_status_func(port)
    if port_status.lower() in ["on", "1", "enable"]:
      return ON
    return OFF

  @decorators.CapabilityLogDecorator(logger)
  def power_off(self, port):
    """This command powers off the port specified.

    Args:
        port (int): Identifies which hub port to power off.
    """
    self.set_mode(OFF, port)

  @decorators.CapabilityLogDecorator(logger)
  def power_on(self, port):
    """This command powers on the port specified.

    Args:
        port (int): Identifies which hub port to power on.
    """
    self.set_mode(ON, port)

  @decorators.CapabilityLogDecorator(logger)
  def set_mode(self, mode, port):
    """Sets the given port to the mode specified.

    Args:
      mode (str): mode to set. Options: 'off', 'on'
      port (int): The port to set.

    Raises:
      DeviceError: invalid port, or mode.
    """
    self._validate_mode(mode)
    logger.info("{} setting power mode to {} for port {}".format(
        self._device_name, mode, port))

    if mode == ON:
      self._turn_on_port_func(port)
    else:
      self._turn_off_port_func(port)
    try:
      retry.retry(
          func=self._verify_mode_change,
          func_args=[port, mode],
          timeout=TIMEOUTS["STATE_CHANGE"],
          is_successful=retry.is_true,
          interval=1,
          reraise=False)
    except errors.CommunicationTimeoutError:
      raise errors.DeviceError(
          "{} failed to verify that ethernet connection is {}".format(
              self._device_name, mode))

  def _validate_mode(self, mode):
    if mode not in list(self.supported_modes):
      raise errors.DeviceError(
          "Mode {} not found in supported modes {!r}".format(
              mode, self.supported_modes))

  def _verify_mode_change(self, port, expected_mode):
    return self.get_mode(port) == expected_mode
