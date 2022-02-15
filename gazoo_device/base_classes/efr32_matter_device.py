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

"""Matter device base class for EFR32 Silabs platform."""
import os
from typing import Dict, NoReturn, Optional, Tuple

from gazoo_device import console_config
from gazoo_device import custom_types
from gazoo_device import decorators
from gazoo_device import gdm_logger
from gazoo_device.base_classes import gazoo_device_base
from gazoo_device.capabilities import device_power_default
from gazoo_device.capabilities import flash_build_jlink
from gazoo_device.capabilities import matter_endpoints_accessor
from gazoo_device.capabilities import pwrpc_common_default
from gazoo_device.protos import device_service_pb2
from gazoo_device.utility import usb_utils


logger = gdm_logger.get_logger()
BAUDRATE = 115200
_RPC_TIMEOUT = 10  # seconds
_EFR32_RPC_TIMEOUT = 5  # seconds
_EFR32_JLINK_NAME = "EFR32MG12PXXXF1024"
_DEFAULT_BOOTUP_TIMEOUT_SECONDS = 30
_CONNECTION_TIMEOUT_SECONDS = 10
_REBOOT_METHODS = ("pw_rpc", "soft", "hard")


class Efr32MatterDevice(gazoo_device_base.GazooDeviceBase):
  """Matter device base class for EFR32 platform.

  EFR32 Matter devices run on FreeRTOS with Matter functionality.
  """
  COMMUNICATION_TYPE = "PigweedSerialComms"
  _COMMUNICATION_KWARGS = {
      "protobufs": (device_service_pb2,), "baudrate": BAUDRATE}

  def __init__(self,
               manager,
               device_config,
               log_file_name=None,
               log_directory=None):
    super().__init__(
        manager,
        device_config,
        log_file_name=log_file_name,
        log_directory=log_directory)
    self._timeouts.update({"CONNECTED": _CONNECTION_TIMEOUT_SECONDS})

  def get_console_configuration(self) -> console_config.ConsoleConfiguration:
    """Returns the interactive console configuration."""
    return console_config.get_log_only_configuration()

  @decorators.LogDecorator(logger)
  def get_detection_info(self) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Gets the persistent and optional attributes of a device during setup.

    Returns:
      Dictionary of persistent attributes and dictionary of
      optional attributes.
    """
    persistent_dict = self.props["persistent_identifiers"]
    address = persistent_dict["console_port_name"]
    persistent_dict["serial_number"] = (
        usb_utils.get_serial_number_from_path(address))
    persistent_dict["model"] = "PROTO"
    persistent_dict.update(
        usb_utils.get_usb_hub_info(self.communication_address))
    return persistent_dict, {}

  @classmethod
  def is_connected(cls,
                   device_config: custom_types.ManagerDeviceConfigDict) -> bool:
    """Returns True if the device is connected to the host."""
    return os.path.exists(device_config["persistent"]["console_port_name"])

  @decorators.PersistentProperty
  def os(self) -> str:
    return "FreeRTOS"

  @decorators.PersistentProperty
  def platform(self) -> str:
    return "EFR32MG"

  @decorators.DynamicProperty
  def firmware_version(self) -> str:
    """Firmware version of the device."""
    return str(self.pw_rpc_common.software_version)

  @decorators.PersistentProperty
  def vendor_id(self) -> int:
    """Vendor ID of the device."""
    return self.pw_rpc_common.vendor_id

  @decorators.PersistentProperty
  def product_id(self) -> int:
    """Product ID of the device."""
    return self.pw_rpc_common.product_id

  @decorators.PersistentProperty
  def device_usb_hub_name(self) -> Optional[str]:
    """The name of the USB hub for the device or None if not configured."""
    return self.props["persistent_identifiers"].get("device_usb_hub_name", None)

  @decorators.PersistentProperty
  def device_usb_port(self) -> Optional[str]:
    """The port number on the USB hub or None if not configured."""
    return self.props["persistent_identifiers"].get("device_usb_port", None)

  @decorators.DynamicProperty
  def pairing_code(self) -> int:
    """Pairing code of the device."""
    return self.pw_rpc_common.pairing_info.code

  @decorators.DynamicProperty
  def pairing_discriminator(self) -> int:
    """Pairing discriminator of the device."""
    return self.pw_rpc_common.pairing_info.discriminator

  @decorators.LogDecorator(logger)
  def reboot(self, no_wait: bool = False, method: str = "pw_rpc") -> None:
    """Reboots the device.

    Args:
      no_wait: Return before reboot completes.
      method: Reboot technique to use. Valid methods
       ["pw_rpc", "soft", "hard"].

    Raises:
      ValueError: If invalid reboot method is specified.
    """
    if method not in _REBOOT_METHODS:
      raise ValueError(
          f"Method {method} not recognized. Supported methods: "
          f"{_REBOOT_METHODS}"
      )
    if method == "hard":
      self.device_power.cycle(no_wait=no_wait)
    else:
      self.pw_rpc_common.reboot(verify=not no_wait)

  @decorators.LogDecorator(logger)
  def factory_reset(self, no_wait: bool = False) -> None:
    """Factory resets the device.

    Args:
      no_wait: Return before reboot completes.
    """
    self.pw_rpc_common.factory_reset(verify=not no_wait)

  @decorators.LogDecorator(logger)
  def shell(self,
            command: str,
            command_name: str = "shell",
            timeout: Optional[int] = None,
            port: int = 0,
            searchwindowsize: int = 2000,
            include_return_code: bool = False) -> NoReturn:
    """Sends command and returns response.

    Args:
      command: Command to send to the device.
      command_name: Optional identifier to use in logs for this command.
      timeout: Seconds to wait for pattern after command sent.
        If None, the default shell timeout is used.
      port: Which port to send on, 0 or 1. Default: 0.
      searchwindowsize: Number of the last bytes to look at
      include_return_code: Flag indicating return code should be returned

    Raises:
      NotImplementedError:
      shell method is not implemented for EFR32 Matter device.
    """
    raise NotImplementedError("shell not implemented for EFR32 Matter device.")

  @decorators.LogDecorator(logger)
  def wait_for_bootup_complete(
      self, timeout: int = _DEFAULT_BOOTUP_TIMEOUT_SECONDS) -> None:
    """Wait until the device finishes booting up and is ready for testing.

    Args:
      timeout: Max time to wait for the device to finish booting up.
    """
    self.pw_rpc_common.wait_for_bootup_complete(timeout)

  @decorators.CapabilityDecorator(pwrpc_common_default.PwRPCCommonDefault)
  def pw_rpc_common(self):
    """PwRPCCommonDefault capability to send RPC command."""
    return self.lazy_init(
        pwrpc_common_default.PwRPCCommonDefault,
        device_name=self.name,
        switchboard_call=self.switchboard.call,
        rpc_timeout_s=_RPC_TIMEOUT)

  @decorators.CapabilityDecorator(flash_build_jlink.FlashBuildJLink)
  def flash_build(self):
    """FlashBuildJLink capability to flash hex image."""
    return self.lazy_init(flash_build_jlink.FlashBuildJLink,
                          device_name=self.name,
                          serial_number=self.serial_number,
                          platform_name=_EFR32_JLINK_NAME)

  @decorators.CapabilityDecorator(
      matter_endpoints_accessor.MatterEndpointsAccessor)
  def matter_endpoints(self):
    """Generic Matter endpoint instance."""
    # TODO(b/209366650) Use discovery cluster and remove the hard-coded IDs.
    return self.lazy_init(
        matter_endpoints_accessor.MatterEndpointsAccessor,
        endpoint_id_to_class=self.ENDPOINT_ID_TO_CLASS,
        device_name=self.name,
        switchboard_call=self.switchboard.call,
        rpc_timeout_s=_EFR32_RPC_TIMEOUT
    )

  @decorators.CapabilityDecorator(device_power_default.DevicePowerDefault)
  def device_power(self):
    """Capability to manipulate device power through Cambrionix."""
    return self.lazy_init(
        device_power_default.DevicePowerDefault,
        device_name=self.name,
        create_device_func=self.get_manager().create_device,
        default_hub_type="cambrionix",
        props=self.props,
        usb_ports_discovered=True,
        switchboard_inst=self.switchboard,
        wait_for_bootup_complete_fn=self.wait_for_bootup_complete,
        wait_for_connection_fn=self.check_device_connected,
        usb_hub_name_prop="device_usb_hub_name",
        usb_port_prop="device_usb_port")
