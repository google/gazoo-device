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

"""Default implementation of the Pigweed RPC device common capability."""
import time
from typing import Any, Callable, Optional
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import pwrpc_common_base
from gazoo_device.switchboard.transports import pigweed_rpc_transport
try:
  # pylint: disable=g-import-not-at-top
  # pytype: disable=import-error
  from device_service import device_service_pb2
  # pytype: enable=import-error
except ImportError:
  device_service_pb2 = None

logger = gdm_logger.get_logger()
_RPC_TIMEOUT = 10


class PwRPCCommonDefault(pwrpc_common_base.PwRPCCommonBase):
  """Pigweed RPC common capability for devices communicating over PwRPC."""

  def __init__(self,
               device_name: str,
               switchboard_call: Callable[..., Any],
               switchboard_call_expect: Callable[..., Any]):
    """Create an instance of the PwRPCCommonDefault capability.

    Args:
      device_name: Device name used for logging.
      switchboard_call: The switchboard.call method which calls to the endpoint.
        See more examples in nrf_pigweed_lighting.py.
      switchboard_call_expect: The switchboard.call_and_expect method.
    """
    super().__init__(device_name=device_name)
    self._switchboard_call = switchboard_call
    self._switchboard_call_expect = switchboard_call_expect

  @decorators.DynamicProperty
  def vendor_id(self) -> str:
    """The vendor id of the device."""
    return self._get_static_info("vendor_id")

  @decorators.DynamicProperty
  def product_id(self) -> str:
    """The product id of the device."""
    return self._get_static_info("product_id")

  @decorators.DynamicProperty
  def software_version(self) -> str:
    """The software version of the device."""
    return self._get_static_info("software_version")

  @decorators.CapabilityLogDecorator(logger)
  def reboot(self,
             no_wait: bool = False,
             rpc_timeout_s: int = _RPC_TIMEOUT,
             bootup_logline_regex: Optional[str] = None,
             bootup_timeout: Optional[int] = None):
    """Reboots the device.

    Args:
      no_wait: Return before reboot completes.
      rpc_timeout_s: Timeout (s) for RPC call.
      bootup_logline_regex: Device logline indicating booting up, not applicable
        if no_wait is True.
      bootup_timeout: Timeout (s) to wait for the bootup message, not applicable
        if no_wait is True.
    """
    if no_wait:
      self._trigger_device_action(action="Reboot",
                                  rpc_timeout_s=rpc_timeout_s)
    else:
      self._trigger_device_action(action="Reboot",
                                  rpc_timeout_s=rpc_timeout_s,
                                  expect_regex=bootup_logline_regex,
                                  expect_timeout_s=bootup_timeout)
      self._wait_for_bootup_complete(bootup_timeout)

  @decorators.CapabilityLogDecorator(logger)
  def factory_reset(self,
                    no_wait: bool = False,
                    rpc_timeout_s: int = _RPC_TIMEOUT,
                    bootup_logline_regex: Optional[str] = None,
                    bootup_timeout: Optional[int] = None):
    """Factory resets the device.

    Args:
      no_wait: Return before factory-reset completes.
      rpc_timeout_s: Timeout (s) for RPC call.
      bootup_logline_regex: Device logline indicating booting up, not applicable
      if no_wait is True.
      bootup_timeout: Timeout (s) to wait for the bootup message, not applicable
      if no_wait is True.
    """
    if no_wait:
      self._trigger_device_action(action="FactoryReset",
                                  rpc_timeout_s=rpc_timeout_s)
    else:
      self._trigger_device_action(action="FactoryReset",
                                  rpc_timeout_s=rpc_timeout_s,
                                  expect_regex=bootup_logline_regex,
                                  expect_timeout_s=bootup_timeout)
      self._wait_for_bootup_complete(bootup_timeout)

  @decorators.CapabilityLogDecorator(logger)
  def ota(self):
    """Triggers OTA to the device."""
    self._trigger_device_action("TriggerOta")

  def _get_static_info(self, property_name: str) -> str:
    """Returns device static information.

    Args:
      property_name: Static property name which currently supports: vendor_id,
        product_id and software_version.

    Raises:
      DeviceError: The ack status is not true or an invalid property_name is
      given.
    """
    ack, payload_in_bytes = self._switchboard_call(
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
        method_args=("Device", "GetDeviceInfo"),
        method_kwargs={})
    if not ack:
      raise errors.DeviceError(
          f"{self._device_name} getting static info failed.")
    payload = device_service_pb2.DeviceInfo.FromString(payload_in_bytes)
    device_property = getattr(payload, property_name, None)
    if device_property is None:
      raise errors.DeviceError(f"{property_name} doesn't exist in static info.")
    return device_property

  def _trigger_device_action(
      self,
      action: str,
      rpc_timeout_s: int = _RPC_TIMEOUT,
      expect_regex: Optional[str] = None,
      expect_timeout_s: Optional[int] = None) -> None:
    """Triggers specific device action.

    Args:
      action: Device actions including reboot, factory-reset and OTA.
      rpc_timeout_s: Timeout (s) for RPC call.
      expect_regex: Expected device logline regex.
      expect_timeout_s: Timeout (s) to wait for the expected regex.

    Raises:
      DeviceError: The ack status is not true.
    """
    if expect_regex is None and expect_timeout_s is None:
      ack, _ = self._switchboard_call(
          method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
          method_args=("Device", action),
          method_kwargs={"pw_rpc_timeout_s": rpc_timeout_s})
    elif expect_regex is not None and expect_timeout_s is not None:
      _, (ack, _) = self._switchboard_call_expect(
          method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
          pattern_list=[expect_regex],
          timeout=expect_timeout_s,
          method_args=("Device", action),
          method_kwargs={"pw_rpc_timeout_s": rpc_timeout_s},
          raise_for_timeout=True)
    else:
      raise ValueError("Only one of \"expect_regex\", \"expect_timeout_s\" "
                       "arguments was provided. Both or neither should be "
                       "provided.")
    if not ack:
      raise errors.DeviceError(f"{self._device_name} triggering {action} failed"
                               ": The action did not succeed")

  def _wait_for_bootup_complete(self, bootup_timeout: int):
    """Waits for device to boot up.

    Args:
      bootup_timeout: Max time to wait for bootup to complete (in seconds).

    Raises:
      DeviceError: If device did not boot up successfully in given timeout.
    """
    start_time = time.time()
    bootup_time = start_time + bootup_timeout
    while time.time() < bootup_time:
      try:
        logger.debug(f"{self._device_name} responded to the RPC call: "
                     f"{self.software_version}")
        logger.info(f"{self._device_name} booted up in "
                    f"{time.time() - start_time}s")
        return
      except errors.DeviceError:
        logger.debug(f"{self._device_name} hasn't booted up yet.")
      time.sleep(0.5)
    raise errors.DeviceError(f"Failed to boot up within {bootup_timeout}s.")
