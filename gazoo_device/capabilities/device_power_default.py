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
"""Device Power Default Capability."""

import time
from typing import Any, Callable, Dict, Optional

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import device_power_base
from gazoo_device.utility import deprecation_utils
import immutabledict

logger = gdm_logger.get_logger()

_HUB_TYPE_PROPERTY = "device_power_hub_type"
_HUB_TYPE_CAMBRIONIX = "cambrionix"
_HUB_TYPE_POWERSWITCH = "powerswitch"
_HUB_TYPE_UNIFI_SWITCH = "unifi_switch"

SUPPORTED_HUB_TYPES = (
    _HUB_TYPE_CAMBRIONIX,
    _HUB_TYPE_POWERSWITCH,
    _HUB_TYPE_UNIFI_SWITCH,
)

_HUB_TYPE_PROPS = immutabledict.immutabledict({
    _HUB_TYPE_CAMBRIONIX: ("device_usb_hub_name", "device_usb_port"),
    _HUB_TYPE_POWERSWITCH: ("powerswitch_name", "powerswitch_port"),
    _HUB_TYPE_UNIFI_SWITCH: ("unifi_switch_name", "unifi_switch_port"),
})


class DevicePowerDefault(device_power_base.DevicePowerBase):
  """Base class for device_power."""

  def __init__(
      self,
      device_name: str,
      create_device_func: Callable[..., Any],
      default_hub_type: str,
      props: Dict[str, Any],
      usb_ports_discovered: bool,
      wait_for_bootup_complete_fn: Callable[[], None],
      switchboard_inst: Any,
      change_triggers_reboot: bool = False,
      usb_hub_name_prop: str = "device_usb_hub_name",
      usb_port_prop: str = "device_usb_port",
      wait_for_connection_fn: Optional[Callable[[], None]] = None,
  ):
    """Create an instance of the device_power capability.

    The power switch type can be changed by setting the 'device_power_hub_type'
    property. The valid hub types are 'cambrionix', 'powerswitch', and
    'unifi_switch'.

    Each hub type also requires a corresponding hub_name and hub_port property
    to be set.

    Cambrionix requires 'device_usb_hub_name' and 'device_usb_port' to be set.
      (These names can be changed by passing in the different property names)

    Powerswitch requires 'powerswitch_name' and 'powerswitch_port' to be set.

    Unifi_switch requires 'unifi_switch_name' and 'unifi_switch_port' to be set.

    Args:
      device_name: Name of the device this capability is attached to.
      create_device_func: A method to create device of hub_type.
      default_hub_type: Type of switch for power cycling.
      props: Dictionary of device props from configuration file.
      usb_ports_discovered: True if the USB ports are discovered by gdm detect.
      wait_for_bootup_complete_fn: A method that the capability can call to wait
        for a reboot to complete if triggered by a change.
      switchboard_inst: Instance of switchboard capability
      change_triggers_reboot: Set change_triggers_reboot to TRUE if changing the
        power mode for the device causes a reboot.
      usb_hub_name_prop: Name of the hub name property.
      usb_port_prop: Name of the hub port property.
      wait_for_connection_fn: a method to wait for the device to become
        reachable.

    Raises:
      ValueError: If hub type is not a known type.
    """
    super().__init__(device_name=device_name)

    self._hub = None
    self._create_device_func = create_device_func
    self._usb_ports_discovered = usb_ports_discovered
    self._props = props
    hub_type = self._props["optional"].get(_HUB_TYPE_PROPERTY, default_hub_type)
    if hub_type not in SUPPORTED_HUB_TYPES:
      raise ValueError("Hub type {} is not supported. Valid types: {}".format(
          hub_type, SUPPORTED_HUB_TYPES))
    self._hub_type = hub_type
    self._hub_name_prop, self._port_prop = _HUB_TYPE_PROPS[self._hub_type]
    if self._hub_type == _HUB_TYPE_CAMBRIONIX:
      self._hub_name_prop = usb_hub_name_prop
      self._port_prop = usb_port_prop

    # Set where the hub/port propeties are in _props.
    if self._hub_type == _HUB_TYPE_CAMBRIONIX and self._usb_ports_discovered:
      self._dict_name = "persistent_identifiers"
    else:
      self._dict_name = "optional"

    self._wait_for_bootup_complete_fn = wait_for_bootup_complete_fn
    self._switchboard = switchboard_inst
    self._change_triggers_reboot = change_triggers_reboot
    self._wait_for_connection_fn = wait_for_connection_fn

  @decorators.CapabilityLogDecorator(logger, level=decorators.DEBUG)
  def health_check(self):
    """Checks that the capability is ready to use.

    Raises:
      CapabilityNotReadyError: If expected properties are not set or
        unable to create auxiliary device for power switching.
    """
    unset_props = []
    if self.hub_name is None:
      unset_props.append(self._hub_name_prop)
    if self.port_number is None:
      unset_props.append(self._port_prop)
    if unset_props:
      if self._hub_type == _HUB_TYPE_CAMBRIONIX and self._usb_ports_discovered:
        msg_format = ("If device is connected to {}, "
                      "set them via 'gdm redetect {}'")
      else:
        msg_format = ("If device is connected to {}, "
                      "set them via 'gdm set-prop {} <property> <value>'")
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
    self._healthy = True

  @decorators.CapabilityLogDecorator(logger, level=decorators.DEBUG)
  def close(self):
    """Closes the hub device instance."""
    if self._hub:
      self._hub.close()
    super().close()

  @decorators.OptionalProperty
  def hub_name(self):
    """Name of the hub the device is attached to."""
    return self._props[self._dict_name].get(self._hub_name_prop)

  @decorators.OptionalProperty
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
  def off(self, close_transports=True):
    """Turn off power to the device.

    Args:
      close_transports (bool): Whether to close transports when powering off.
    """
    if not self.healthy:
      self.health_check()
    # No-op if port is already off.
    status = self._hub.switch_power.get_mode(self.port_number)
    if status == "off":
      return
    if self._change_triggers_reboot:
      self._switchboard.add_log_note(
          f"GDM triggered reboot via {self.hub_type} power change.")
      self._hub.switch_power.power_off(self.port_number)
      self._wait_for_bootup_complete_fn()
    else:
      if close_transports:
        self._switchboard.close_all_transports()
      self._hub.switch_power.power_off(self.port_number)

  @decorators.CapabilityLogDecorator(logger)
  def on(self, no_wait=False):
    """Turn on power to the device.

    If Switchboard hasn't been initialized then transports won't be opened
    and GDM triggered reboot won't be logged to avoid initializing the
    switchboard. Note that if no_wait=False then Switchboard will be initialized
    at the end.

    Args:
        no_wait (bool):  Return before verifying boot up.
    """
    if not self.healthy:
      self.health_check()
    # No-op if port is already on.
    status = self._hub.switch_power.get_mode(self.port_number)
    if status in ["sync", "charge", "on"]:
      return
    if self._change_triggers_reboot:
      if self._switchboard.health_checked:
        self._switchboard.add_log_note(
            f"GDM triggered reboot via {self.hub_type} power change.")
    self._hub.switch_power.power_on(self.port_number)
    if not self._change_triggers_reboot:
      if self._wait_for_connection_fn is not None:
        self._wait_for_connection_fn()
      else:
        time.sleep(2)  # Small delay to give time for 'dev/tty' to populate
      if self._switchboard.health_checked:
        self._switchboard.open_all_transports()

    if not no_wait:
      self._wait_for_bootup_complete_fn()


deprecation_utils.add_deprecated_attributes(DevicePowerDefault,
                                            [("power_off", "off", True),
                                             ("power_on", "on", True),
                                             ("power_cycle", "cycle", True)])
