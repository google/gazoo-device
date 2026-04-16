# Copyright 2023 Google LLC
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
import random
import time
from typing import Any, Callable, Optional
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import pwrpc_common_base
from gazoo_device.protos import device_service_pb2
from gazoo_device.utility import pwrpc_utils
from gazoo_device.utility import retry


logger = gdm_logger.get_logger()
_POLL_INTERVAL_SEC = 0.5
_REBOOT_POLL_INTERVAL_SEC = 1
_WAIT_FOR_DEVICE_READY_SEC = 1
_DEFAULT_BOOTUP_TIMEOUT = 30  # seconds
_GET_DEVICE_INFO_RPC_TIMEOUT = 10
# TODO(gdm-authors) Remove this once the sample app has a default fw version.
_DEFAULT_SW_VERSION = "0"
_MIN_DISCRIMINATOR = 0
_MAX_DISCRIMINATOR = 0xFFF
_REBOOT_DELAY_MS = 1500  # According to b/285848248#comment88

# Available discriminator pool
_AVAILABLE_DISCRIMINATORS = [
    value for value in range(_MIN_DISCRIMINATOR, _MAX_DISCRIMINATOR+1)]
random.shuffle(_AVAILABLE_DISCRIMINATORS)


class PwRPCCommonDefault(pwrpc_common_base.PwRPCCommonBase):
  """Pigweed RPC common capability for devices communicating over PwRPC."""

  def __init__(self,
               device_name: str,
               switchboard_call: Callable[..., Any],
               rpc_timeout_s: int,
               pigweed_port: int = 0):
    """Create an instance of the PwRPCCommonDefault capability.

    Args:
      device_name: Device name used for logging.
      switchboard_call: The switchboard.call method which calls to the endpoint.
      rpc_timeout_s: Timeout (s) for RPC call.
      pigweed_port: Pigweed RPC transport port number.
    """
    super().__init__(device_name=device_name)
    self._switchboard_call = switchboard_call
    self._rpc_timeout_s = rpc_timeout_s
    self._pigweed_port = pigweed_port

  @decorators.DynamicProperty
  def software_version(self) -> str:
    """The software version of the device."""
    version = self.get_device_info().software_version_string
    return version or _DEFAULT_SW_VERSION

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
  def fabric_info(self) -> list[device_service_pb2.FabricInfo]:
    """The list of fabric information of the device."""
    repeated_fabric_info = self.get_device_state().fabric_info
    return list(repeated_fabric_info)

  @decorators.DynamicProperty
  def time_since_boot_millis(self) -> int:
    """The elapsed time since the device boots up in milliseconds."""
    return self.get_device_state().time_since_boot_millis

  @decorators.CapabilityLogDecorator(logger)
  def call(self,
           method_name: str,
           method_args: tuple[Any, ...] = (),
           method_kwargs: Optional[dict[str, Any]] = None) -> Any:
    """Switchboard RPC call wrapper with specific port number."""
    return self._switchboard_call(
        method_name=method_name,
        method_args=method_args,
        method_kwargs=method_kwargs,
        port=self._pigweed_port)

  @decorators.CapabilityLogDecorator(logger)
  def reboot(self,
             verify: bool = True,
             bootup_timeout_s: int = _DEFAULT_BOOTUP_TIMEOUT) -> None:
    """Reboots the device.

    Args:
      verify: If true, waits for device bootup completes before returning.
      bootup_timeout_s: Timeout (s) to wait for the device to boot up.
    """
    self._action_with_bootup_verification(
        action="Reboot", verify=verify, bootup_timeout_s=bootup_timeout_s)

  @decorators.CapabilityLogDecorator(logger)
  def factory_reset(self,
                    verify: bool = True,
                    bootup_timeout_s: int = _DEFAULT_BOOTUP_TIMEOUT) -> None:
    """Factory resets the device.

    Args:
      verify: If true, waits for device bootup completes before returning.
      bootup_timeout_s: Timeout (s) to wait for the device to boot up.
    """
    self._action_with_bootup_verification(
        action="FactoryReset", verify=verify, bootup_timeout_s=bootup_timeout_s)

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
    # For b/272311935, devices will enter bad state (unresponsive to RPC) when
    # trying to send the RPC requests right after rebooting or FDR.
    # Adding 1 second to wait for the device to be in a ready state before
    # sending RPC for polling.
    time.sleep(_WAIT_FOR_DEVICE_READY_SEC)
    try:
      start_time = time.time()
      retry.retry(
          func=self._trigger_device_action,
          func_kwargs={"action": "GetDeviceInfo"},
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
    """Returns device static information."""
    # Various Matter tests (Mobile, LHP, GHP tests) are hitting the
    # GetDeviceInfo RPC timeout issue, adding a retry for avoding race condition
    # of sending RPC calls.
    payload_in_bytes = retry.retry(
        func=self._trigger_device_action,
        func_kwargs={"action": "GetDeviceInfo"},
        timeout=_GET_DEVICE_INFO_RPC_TIMEOUT,
        interval=_POLL_INTERVAL_SEC,
        reraise=False)
    return device_service_pb2.DeviceInfo.FromString(payload_in_bytes)

  @decorators.CapabilityLogDecorator(logger)
  def get_device_state(self) -> device_service_pb2.DeviceState:
    """Returns device state information."""
    payload_in_bytes = self._trigger_device_action(action="GetDeviceState")
    return device_service_pb2.DeviceState.FromString(payload_in_bytes)

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

  @decorators.CapabilityLogDecorator(logger)
  def get_spake_info(self) -> device_service_pb2.SpakeInfo:
    """Returns the device spake information."""
    payload_in_bytes = self._trigger_device_action(action="GetSpakeInfo")
    return device_service_pb2.SpakeInfo.FromString(payload_in_bytes)

  @decorators.CapabilityLogDecorator(logger)
  def set_spake_info(
      self,
      verifier: Optional[bytes] = None,
      salt: Optional[bytes] = None,
      iteration_count: Optional[int] = None) -> None:
    """Sets the device spake information."""
    current_spake_info = self.get_spake_info()
    new_verifier = current_spake_info.verifier if verifier is None else verifier
    new_salt = current_spake_info.salt if salt is None else salt
    new_iteration_count = (
        current_spake_info.iteration_count if iteration_count is None
        else iteration_count)
    self._trigger_device_action(action="SetSpakeInfo",
                                verifier=new_verifier,
                                salt=new_salt,
                                iteration_count=new_iteration_count)

  @decorators.DynamicProperty
  def is_advertising(self) -> bool:
    """Returns if the device is advertising for commissioning."""
    payload_in_bytes = self._trigger_device_action(action="GetPairingState")
    payload = device_service_pb2.PairingState.FromString(payload_in_bytes)
    return payload.pairing_enabled

  @decorators.CapabilityLogDecorator(logger)
  def start_advertising(self) -> None:
    """Starts advertising for commissioning.

    Noop if device is already paired or it's already advertising.
    """
    if self.pairing_state or self.is_advertising:
      return
    self._trigger_device_action(action="SetPairingState",
                                pairing_enabled=True)

  @decorators.CapabilityLogDecorator(logger)
  def stop_advertising(self) -> None:
    """Stops advertising for commissioning.

    Noop if device is not advertising.
    """
    if not self.is_advertising:
      return
    self._trigger_device_action(action="SetPairingState",
                                pairing_enabled=False)

  @decorators.CapabilityLogDecorator(logger)
  def set_ota_metadata(self, tlv_metadata: bytes) -> None:
    """Sets OTA metadata for OTA provider.

    Note that the value does not persist across reboot. Also the device needs
    to be commissioned to the OTA provider (hub) to set the value.

    Args:
      tlv_metadata:
        TLV OTA metadata generated via gazoo_device.utility.tlv_utils.
    """
    self._trigger_device_action(action="SetOtaMetadataForProvider",
                                tlv=tlv_metadata)

  def set_pairing_info_and_start_advertising(
      self, passcode: Optional[int] = None) -> int:
    """Sets a new random pairing discriminator, code and starts advertising.

    Args:
      passcode: Pairing code to set. None if the code doesn't need to be set.

    Returns:
      The new pairing discriminator.
    """
    self.stop_advertising()

    discriminator = self.pairing_info.discriminator
    if self._pigweed_port == 0:
      # Only SoC devices support set_pairing_info and need random discriminator.
      if not _AVAILABLE_DISCRIMINATORS:
        raise ValueError("All possible discriminators have been used.")
      discriminator = _AVAILABLE_DISCRIMINATORS.pop()
      self.set_pairing_info(code=passcode, discriminator=discriminator)

    # Restart advertising to make sure the device is advertising with the
    # updated passcode, discriminator, and verifier.
    self.start_advertising()

    # Check if the QR code is valid after advertising
    if not self.qr_code:
      raise errors.DeviceError(
          f"QR code fetched from {self._device_name} RPC is empty.")
    logger.info("%s QR code is now %s", self._device_name, self.qr_code)

    return discriminator

  @decorators.CapabilityLogDecorator(logger)
  def trigger_icd_checkin(self) -> None:
    self._trigger_device_action(action="TriggerIcdCheckin")

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
    return self.call(
        method_name=pwrpc_utils.RPC_METHOD_NAME,
        method_args=("Device", action),
        method_kwargs=device_rpc_kwargs)

  def _action_with_bootup_verification(
      self, action: str, verify: bool, bootup_timeout_s: int) -> None:
    """Triggers actions with device bootup verification."""
    start_time = time.time()
    if action == "Reboot":
      # To avoid reboot RPC timeout issue b/285848248
      # https://github.com/project-chip/connectedhomeip/pull/29550
      # Note that 0 delay is NOT allowed and we default set to 1.5 seconds.
      self._trigger_device_action(action=action, delay_ms=_REBOOT_DELAY_MS)
    else:
      self._trigger_device_action(action=action)
    if verify:
      # For b/272311935, devices will enter bad state (unresponsive to RPC) when
      # trying to send the RPC requests right after rebooting or FDR.
      # Adding 1 second to wait for the device to be in a ready state before
      # sending RPC for polling.
      time.sleep(_WAIT_FOR_DEVICE_READY_SEC)
      try:
        retry.retry(
            func=lambda: self.time_since_boot_millis,
            is_successful=(
                lambda time_since_boot_after:  # pylint: disable=g-long-lambda
                time_since_boot_after < (time.time() - start_time) * 1000),  # pylint: disable=comparison-with-callable
            timeout=bootup_timeout_s,
            interval=_REBOOT_POLL_INTERVAL_SEC,
            reraise=False,
        )
        logger.debug(
            "%s time_since_boot_millis reset in %ds",
            self._device_name, (time.time() - start_time))
      except errors.CommunicationTimeoutError as bootup_error:
        raise errors.DeviceError(
            f"{self._device_name} failed reboot verification. "
            "time_since_boot_millis did not reset after the reboot."
        ) from bootup_error
