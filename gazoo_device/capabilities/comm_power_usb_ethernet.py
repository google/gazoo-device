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

"""Communication Power Cambrionix Capability.

Note: this should be refactored to be multi communication ports capability
if/when another device starts needing it.
"""
import time
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger

from gazoo_device.capabilities.interfaces import comm_power_base
from gazoo_device.capabilities.interfaces import switch_power_base
from gazoo_device.utility import deprecation_utils

logger = gdm_logger.get_logger()


class CommPowerUsbEthernet(comm_power_base.CommPowerBase):
  """Base class for comm_power  capability."""

  def __init__(self,
               device_name,
               create_device_func,
               props,
               hub_name_prop,
               primary_port_prop,
               secondary_port_prop,
               ethernet_switch_prop,
               ethernet_port_prop,
               get_switchboard_if_initialized,
               power_and_data_share_cable=False,
               pre_off_func=None):
    """Create an instance of the comm_power_cambrionix capability.

    Args:
      device_name (str): name of the device this capability is attached
        to.
      create_device_func (func): create_device method.
      props (dict): dictionary of device props from configuration file.
      hub_name_prop (str):  name of the hub name property. Should be in
        optional.
      primary_port_prop (str): name of the hub port property. Should be in
        optional.
      secondary_port_prop (str): name of the secondary port property in
        persistent.
      ethernet_switch_prop (str): ip address of the ethernet_switch prop.
        Optional.
      ethernet_port_prop (str): port number of the ethernet_switch port.
        Optional.
      get_switchboard_if_initialized (callable): function which returns
        a Switchboard instance or None if Switchboard hasn't been initialized.
      power_and_data_share_cable (bool): set power_and_data_share_cable to
        TRUE if device shares a common USB cable for its power and data.
      pre_off_func (func): a method to call before turning power off.

    Raises:
      ValueError: If the capability cannot be created.
    """
    super().__init__(device_name=device_name)

    self._create_device_func = create_device_func
    self._hub_name_prop = hub_name_prop
    self._primary_port_prop = primary_port_prop
    self._secondary_port_prop = secondary_port_prop
    self._props = props
    self._ethernet_switch = None

    # Set the properties
    self._get_switchboard_if_initialized = get_switchboard_if_initialized
    self._power_and_data_share_cable = power_and_data_share_cable
    self._pre_off_func = pre_off_func
    self._ethernet_switch_prop = ethernet_switch_prop
    self._ethernet_port_prop = ethernet_port_prop

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
      unset_props.append(self._primary_port_prop)
    if unset_props:
      msg_format = ("If device is connected to {}, "
                    "set them via 'gdm redetect {}'")
      msg = msg_format.format(self.hub_type, self._device_name)
      error_msg = "properties {} are unset. ".format(
          " and ".join(unset_props)) + msg
      raise errors.CapabilityNotReadyError(
          msg=error_msg, device_name=self._device_name)

    try:
      self._hub = self._create_device_func(self.hub_name)
      # Set up ethernet
      if self.ethernet_switch_address is not None:
        self._ethernet_switch = self._create_device_func(
            self.ethernet_switch_address)

    except errors.DeviceError as err:
      raise errors.CapabilityNotReadyError(
          msg=str(err), device_name=self._device_name)
    if self.ethernet_switch_address is not None:
      self._verify_switch_created(self._ethernet_switch)
    self._healthy = True

  @decorators.OptionalProperty
  def hub_name(self):
    """Name of the hub the device is attached to."""
    return self._props["persistent_identifiers"].get(self._hub_name_prop)

  @decorators.DynamicProperty
  def port_mode(self):
    """port mode."""
    if not self.healthy:
      self.health_check()
    return self._hub.switch_power.get_mode(self.port_number)

  @decorators.OptionalProperty
  def port_number(self):
    """Port number the device is attached to."""
    return self._props["persistent_identifiers"].get(self._primary_port_prop)

  @decorators.OptionalProperty
  def secondary_port_number(self):
    """Secondary usb port number that the device is attached to."""
    return self._props["persistent_identifiers"].get(self._secondary_port_prop)

  @decorators.OptionalProperty
  def ethernet_switch_address(self):
    """Address for ethernet switch."""
    return self._props["optional"].get(self._ethernet_switch_prop)

  @decorators.OptionalProperty
  def ethernet_port_number(self):
    """Port number for ethernet switch."""
    return self._props["optional"].get(self._ethernet_port_prop)

  @decorators.PersistentProperty
  def hub_type(self):
    """Type of hub the check is attached to."""
    return "cambrionix"

  @decorators.CapabilityLogDecorator(logger)
  def cycle(self, include_ethernet=False):
    """Power off then power on the communication port."""
    if not self.healthy:
      self.health_check()
    self.off()
    time.sleep(2)  # Small delay before calling power_on
    self.on()

  @decorators.CapabilityLogDecorator(logger)
  def off(self, include_ethernet=False):
    """Turn off power to the device communications port."""
    if not self.healthy:
      self.health_check()
    if self._pre_off_func:
      self._pre_off_func()
    switchboard = self._get_switchboard_if_initialized()
    if self._power_and_data_share_cable:
      if switchboard:
        switchboard.add_log_note(
            f"comm_power.off() called on {self._device_name} set communication "
            f"port {self.port_number} to charge as device has a single USB "
            "cable for data and power.")
        switchboard.close_all_transports()
      self._hub.switch_power.power_on(self.port_number, data_sync=False)
      if self.secondary_port_number is not None:
        self._hub.switch_power.power_on(
            self.secondary_port_number, data_sync=False)
    else:
      if switchboard:
        switchboard.close_all_transports()
      self._hub.switch_power.power_off(self.port_number)
      if self.secondary_port_number is not None:
        self._hub.switch_power.power_off(self.secondary_port_number)
    if include_ethernet:
      self.ethernet_off()

  @decorators.CapabilityLogDecorator(logger)
  def on(self, include_ethernet=False):
    """Turn on power to the device communication port."""
    if not self.healthy:
      self.health_check()
    self._hub.switch_power.power_on(self.port_number)
    if self.secondary_port_number is not None:
      self._hub.switch_power.power_on(self.secondary_port_number)
    if include_ethernet:
      self.ethernet_on()
    time.sleep(5)  # Small delay to give time for 'dev/tty' to populate
    switchboard = self._get_switchboard_if_initialized()
    if switchboard:
      switchboard.open_all_transports()

  @decorators.CapabilityLogDecorator(logger)
  def ethernet_off(self):
    """Turn off ethernet port.

    Raises:
      CapabilityNotReadyError: if unable to initiate ethernet_switch.
    """
    if not self.healthy:
      self.health_check()
    if not self._ethernet_switch:
      raise errors.CapabilityNotReadyError(
          device_name=self._device_name,
          msg="Not set up for ethernet switching.")
    self._ethernet_switch.switch_power.power_off(self.ethernet_port_number)

  @decorators.CapabilityLogDecorator(logger)
  def ethernet_on(self):
    """Turn on ethernet port.

    Raises:
      CapabilityNotReadyError: if unable to initiate ethernet_switch.
    """
    if not self.healthy:
      self.health_check()
    if not self._ethernet_switch:
      raise errors.CapabilityNotReadyError(
          device_name=self._device_name,
          msg="Not set up for ethernet switching.")
    self._ethernet_switch.switch_power.power_on(self.ethernet_port_number)

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


deprecation_utils.add_deprecated_attributes(
    CommPowerUsbEthernet, [("enable", "ethernet_on", True),
                           ("disable", "ethernet_off", True),
                           ("address", "ethernet_switch_address", False),
                           ("port", "ethernet_port_number", False),
                           ("power_cycle", "cycle", True)])
