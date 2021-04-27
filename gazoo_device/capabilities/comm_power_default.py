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

"""Communication Power Default Capability."""
import time
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger

from gazoo_device.capabilities.interfaces import comm_power_base
from gazoo_device.capabilities.interfaces import switch_power_base
from gazoo_device.utility import deprecation_utils

logger = gdm_logger.get_logger()

SUPPORTED_HUB_TYPES = ["cambrionix", "ethernet_switch"]


class CommPowerDefault(comm_power_base.CommPowerBase):
  """Default class for comm_power capability."""

  def __init__(self,
               device_name,
               create_device_func,
               hub_type,
               props,
               settable,
               hub_name_prop,
               port_prop,
               get_switchboard_if_initialized,
               power_and_data_share_cable=False,
               wait_for_connection_func=None,
               wait_for_bootup_complete_func=None,
               pre_off_func=None):
    """Create an instance of the comm_power_default capability.

    Args:
      device_name (str): name of the device this capability is attached
        to.
      create_device_func (func): create_device method.
      hub_type (str): type of power hub for power cycling.
      props (dict): dictionary of device props from configuration file.
      settable (bool): whether or not the properties are settable.
      hub_name_prop (str):  name of the hub name property
      port_prop (str): name of the hub port property
      get_switchboard_if_initialized (callable): function which returns
        a Switchboard instance or None if Switchboard hasn't been initialized.
      power_and_data_share_cable (bool): set power_and_data_share_cable to
        TRUE if device shares a common USB cable for its power and data.
      wait_for_connection_func (func): a method to wait for the device to
        become reachable.
      wait_for_bootup_complete_func (func): a method to call if power and
        data share cable.
      pre_off_func (func): a method to call before turning power off.

    Raises:
      ValueError: If hub_type unknown.
    """
    super().__init__(device_name=device_name)

    self._create_device_func = create_device_func
    self._settable = settable
    self._hub_name_prop = hub_name_prop
    self._port_prop = port_prop
    if hub_type not in SUPPORTED_HUB_TYPES:
      raise ValueError("Hub Type {} not supported. Valid types: {}".format(
          hub_type, SUPPORTED_HUB_TYPES))
    self._hub_type = hub_type

    # Set the properties
    self._dict_name = "optional" if self._settable else "persistent_identifiers"
    self._props = props
    self._get_switchboard_if_initialized = get_switchboard_if_initialized
    self._power_and_data_share_cable = power_and_data_share_cable
    self._pre_off_func = pre_off_func
    self._wait_for_connection_func = wait_for_connection_func
    self._wait_for_bootup_complete_func = wait_for_bootup_complete_func
    self._hub = None

  @decorators.CapabilityLogDecorator(logger, level=decorators.DEBUG)
  def health_check(self):
    """Checks that the capability is ready to use.

    Raises:
        CapabilityNotReadyError: if unable to create auxiliary device for
        power switching.
    """
    unset_props = []
    if not self.hub_name:
      unset_props.append(self._hub_name_prop)
    if not self.port_number:
      unset_props.append(self._port_prop)
    if unset_props:
      if self._settable:
        msg_format = ("If device is connected to {}, "
                      "set them via 'gdm set-prop {} <property> <value>'")

      else:
        msg_format = ("If device is connected to {}, "
                      "set them via 'gdm redetect {}")
      msg = msg_format.format(self._hub_type, self._device_name)
      error_msg = "properties {} are unset. ".format(
          " and ".join(unset_props)) + msg
      raise errors.CapabilityNotReadyError(
          msg=error_msg, device_name=self._device_name)

    try:
      self._hub = self._create_device_func(self.hub_name)
    except errors.DeviceError as err:
      raise errors.CapabilityNotReadyError(
          msg=str(err), device_name=self._device_name)
    self._verify_switch_created(self._hub)
    self._healthy = True

  @decorators.OptionalProperty
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

  @decorators.OptionalProperty
  def port_number(self):
    """Port number the device is attached to."""
    return self._props[self._dict_name].get(self._port_prop)

  @decorators.CapabilityLogDecorator(logger)
  def cycle(self):
    """Power off then power on the communication port."""
    if not self.healthy:
      self.health_check()
    self.off()
    time.sleep(2)  # Small delay before calling power_on
    self.on()

  @decorators.CapabilityLogDecorator(logger)
  def off(self):
    """Turn off power to the device communications port."""
    if not self.healthy:
      self.health_check()
    if self._pre_off_func:
      self._pre_off_func()
    switchboard = self._get_switchboard_if_initialized()
    if switchboard:
      switchboard.close_all_transports()
      if self._power_and_data_share_cable:
        switchboard.add_log_note(
            f"comm_power.off() called on {self._device_name} set communication "
            f"port {self.port_number} to charge as device has a single USB "
            "cable for data and power.")
    if self._power_and_data_share_cable:
      self._hub.switch_power.power_on(self.port_number, data_sync=False)
    else:
      self._hub.switch_power.power_off(self.port_number)

  @decorators.CapabilityLogDecorator(logger)
  def on(self):
    """Turn on power to the device communication port."""
    if not self.healthy:
      self.health_check()
    self._hub.switch_power.power_on(self.port_number)
    # Wait for 'dev/tty' to populate
    if self._wait_for_connection_func:
      self._wait_for_connection_func()
    else:
      time.sleep(5)
    switchboard = self._get_switchboard_if_initialized()
    if switchboard:
      switchboard.open_all_transports()
    if self._wait_for_bootup_complete_func:
      self._wait_for_bootup_complete_func()

  def _verify_switch_created(self, switch):
    """Verifies switch is created and has switch_power capability."""
    if not (
        hasattr(switch, "switch_power") and
        isinstance(switch.switch_power, switch_power_base.SwitchPowerBase)):
      raise errors.CapabilityNotReadyError(
          msg="'switch_power' capability is missing in hub device {} ({}),"
          " or is not an instance of SwitchPowerBase".format(
              self.hub_name,
              type(switch).__name__),
          device_name=self._device_name)


deprecation_utils.add_deprecated_attributes(CommPowerDefault,
                                            [("enable", "on", True),
                                             ("disable", "off", True),
                                             ("power_cycle", "cycle", True),
                                             ("port", "port_number", False),
                                             ("address", "hub_name", False)])
