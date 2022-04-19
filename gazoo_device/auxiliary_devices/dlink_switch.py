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
"""D-Link switch device controller."""
from typing import Any, Dict, Tuple

from gazoo_device import custom_types
from gazoo_device import decorators
from gazoo_device import detect_criteria
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.base_classes import auxiliary_device
from gazoo_device.capabilities import switch_power_snmp
from gazoo_device.utility import host_utils

logger = gdm_logger.get_logger()


class DLinkSwitch(auxiliary_device.AuxiliaryDevice):
  """Device class for a D-Link Switch."""
  COMMUNICATION_TYPE = "SnmpComms"
  DETECT_MATCH_CRITERIA = {detect_criteria.SnmpQuery.IS_DLINK: True}
  DEVICE_TYPE = "dlink_switch"
  _OWNER_EMAIL = "gdm-authors@google.com"

  @decorators.PersistentProperty
  def ip_address(self):
    """Global IP address."""
    return self.communication_address

  @decorators.LogDecorator(logger)
  def get_console_configuration(self) -> None:
    """Returns None. Console is not supported because there's no Switchboard."""
    del self  # Unused because console is not supported.
    return None

  @decorators.CapabilityDecorator(switch_power_snmp.SwitchPowerSnmp)
  def switch_power(self):
    """Capability to control switch power setting over SNMP."""
    return self.lazy_init(
        switch_power_snmp.SwitchPowerSnmp,
        device_name=self.name,
        ip_address=self.ip_address,
        total_ports=self.total_ports)

  @decorators.LogDecorator(logger)
  def get_detection_info(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Gets the persistent and optional attributes of a DLI Power Switch.

    Returns:
      Tuple of dictionaries containing persistent and optional attributes.
    """
    self.props["optional"] = {}
    self.props["persistent_identifiers"]["model"] = (
        detect_criteria.get_dlink_model_name(self.ip_address))
    # Cannot get serial number via snmp; no other known way for this device.
    # Using IP as a unique identifier instead.
    self.props["persistent_identifiers"]["serial_number"] = (
        self.ip_address.replace(".", ""))
    return self.props["persistent_identifiers"], self.props["optional"]

  @classmethod
  def is_connected(cls,
                   device_config: custom_types.ManagerDeviceConfigDict) -> bool:
    """Checks whether or not the D-Link Power Switch is connected.

    Args:
      device_config: Contains the persistent attributes.

    Returns:
      True if device responds to a ping. False if not.
    """
    return host_utils.is_pingable(
        device_config["persistent"]["console_port_name"])

  @decorators.DynamicProperty
  def total_ports(self) -> int:
    """Gets the number of ports for the attached unifi_switch.

    D-Link DGS-1100 gigabit ethernet switches will have either
    5 or 8 ports depending on their model name.

    Possible model names:
    DGS-1100-05 Gigabit Ethernet Switch
    DGS-1100-05L Gigabit Ethernet Switch
    DGS-1100-08 Gigabit Ethernet Switch
    DGS-1100-08L Gigabit Ethernet Switch

    Returns:
      Number of device ports.
    """
    if "-05" in str(self.model):
      return 5
    elif "-08" in str(self.model):
      return 8
    raise errors.DeviceError(
        f"{self.device_type} model name does not contain expected "
        f"port values -05 or -08. Model name is: {self.model}")
