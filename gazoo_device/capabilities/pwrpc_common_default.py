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

"""Default implementation of the Pigweed RPC device common capability."""
import time
from typing import Any, Callable, List, Optional
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import pwrpc_common_base
from gazoo_device.protos import device_service_pb2
from gazoo_device.switchboard.transports import pigweed_rpc_transport
from gazoo_device.utility import retry


logger = gdm_logger.get_logger()
_POLL_INTERVAL_SEC = 0.5  # seconds
_DEFAULT_BOOTUP_TIMEOUT = 30  # seconds


class PwRPCCommonDefault(pwrpc_common_base.PwRPCCommonBase):
  """Pigweed RPC common capability for devices communicating over PwRPC."""

  def __init__(self,
               device_name: str,
               switchboard_call: Callable[..., Any],
               rpc_timeout_s: int):
    """Create an instance of the PwRPCCommonDefault capability.

    Args:
      device_name: Device name used for logging.
      switchboard_call: The switchboard.call method which calls to the endpoint.
      rpc_timeout_s: Timeout (s) for RPC call.
    """
    super().__init__(device_name=device_name)
    self._switchboard_call = switchboard_call
    self._rpc_timeout_s = rpc_timeout_s

  @decorators.DynamicProperty
  def vendor_id(self) -> int:
    """The vendor id of the device."""
    return self.get_device_info().vendor_id

  @decorators.DynamicProperty
  def product_id(self) -> int:
    """The product id of the device."""
    return self.get_device_info().product_id

  @decorators.DynamicProperty
  def software_version(self) -> int:
    """The software version of the device."""
    return self.get_device_info().software_version

  @decorators.DynamicProperty
  def qr_code(self) -> str:
    """The pairing QR code of the device."""
    return self.pairing_info.qr_code

  @decorators.DynamicProperty
  def qr_code_url(self) -> str:
    """The pairing QR code URL of the device."""
    return self.pairing_info.qr_code_url

  @decorators.DynamicProperty
  def pairing_state(self) -> bool:
    """The pairing state of the device.

    The device is paired if it has at least one fabric ID and the fabric
    contains a node ID.

    Returns:
      The pairing state.
    """
    return bool(self.fabric_info) and hasattr(self.fabric_info[0], "node_id")

  @decorators.DynamicProperty
  def pairing_info(self) -> device_service_pb2.PairingInfo:
    """The pairing information of the device."""
    return self.get_device_info().pairing_info

  @decorators.DynamicProperty
  def fabric_info(self) -> List[device_service_pb2.FabricInfo]:
    """The list of fabric information of the device."""
    repeated_fabric_info = self.get_device_state().fabric_info
    return list(repeated_fabric_info)

  @decorators.CapabilityLogDecorator(logger)
  def reboot(self,
             verify: bool = True,
             bootup_timeout_s: int = _DEFAULT_BOOTUP_TIMEOUT) -> None:
    """Reboots the device.

    Args:
      verify: If true, waits for device bootup completes before returning.
      bootup_timeout_s: Timeout (s) to wait for the device to boot up.
    """
    self._trigger_device_action(action="Reboot")
    if verify:
      self.wait_for_bootup_complete(bootup_timeout_s)

  @decorators.CapabilityLogDecorator(logger)
  def factory_reset(self,
                    verify: bool = True,
                    bootup_timeout_s: int = _DEFAULT_BOOTUP_TIMEOUT) -> None:
    """Factory resets the device.

    Args:
      verify: If true, waits for device bootup completes before returning.
      bootup_timeout_s: Timeout (s) to wait for the device to boot up.
    """
    self._trigger_device_action(action="FactoryReset")
    if verify:
      self.wait_for_bootup_complete(bootup_timeout_s)

  @decorators.CapabilityLogDecorator(logger)
  def ota(self) -> None:
    """Triggers OTA to the device."""
    self._trigger_device_action(action="TriggerOta")

  @decorators.CapabilityLogDecorator(logger)
  def wait_for_bootup_complete(self, bootup_timeout: int) -> None:
    """Waits for device to boot up.

    Args:
      bootup_timeout: Max time to wait for bootup to complete (in seconds).

    Raises:
      DeviceError: If device did not boot up successfully in given timeout.
    """
    try:
      start_time = time.time()
      retry.retry(
          func=self.get_device_info,
          timeout=bootup_timeout,
          interval=_POLL_INTERVAL_SEC,
          reraise=False)
      logger.info(
          f"{self._device_name} booted up in {time.time() - start_time}s.")
    except errors.CommunicationTimeoutError as bootup_error:
      raise errors.DeviceError(
          f"{self._device_name} failed to boot up within {bootup_timeout}s."
      ) from bootup_error

  @decorators.CapabilityLogDecorator(logger)
  def get_device_info(self) -> device_service_pb2.DeviceInfo:
    """Returns device static information.

    Raises:
      DeviceError: The ack status is not true.
    """
    payload_in_bytes = self._trigger_device_action(action="GetDeviceInfo")
    payload = device_service_pb2.DeviceInfo.FromString(payload_in_bytes)
    return payload

  @decorators.CapabilityLogDecorator(logger)
  def get_device_state(self) -> device_service_pb2.DeviceState:
    """Returns device state information.

    Raises:
      DeviceError: The ack status is not true.
    """
    payload_in_bytes = self._trigger_device_action(action="GetDeviceState")
    payload = device_service_pb2.DeviceState.FromString(payload_in_bytes)
    return payload

  @decorators.CapabilityLogDecorator(logger)
  def set_pairing_info(
      self, code: Optional[int] = None, discriminator: Optional[int] = None
    ) -> None:
    """Sets the pairing info of the device.

    Args:
      code: New pairing code to set.
      discriminator: New discriminator to set.
    """
    new_code = self.pairing_info.code if code is None else code
    new_discriminator = (
        self.pairing_info.discriminator if discriminator is None
        else discriminator)
    self._trigger_device_action(action="SetPairingInfo",
                                code=new_code,
                                discriminator=new_discriminator)

  def _trigger_device_action(self, action: str, **kwargs: Any) -> bytes:
    """Triggers specific device action.

    Args:
      action: Device actions including reboot, factory-reset,
        OTA and setting/getting device state and pairing state.
      **kwargs: Arguments for the device action.

    Returns:
      The payload in bytes format.

    Raises:
      DeviceError: The ack status is not true.
    """
    device_rpc_kwargs = {"pw_rpc_timeout_s": self._rpc_timeout_s}
    device_rpc_kwargs.update(kwargs)
    ack, payload_in_bytes = self._switchboard_call(
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
        method_args=("Device", action),
        method_kwargs=device_rpc_kwargs)

    if not ack:
      raise errors.DeviceError(f"{self._device_name} triggering {action} failed"
                               ": The action did not succeed")

    return payload_in_bytes
