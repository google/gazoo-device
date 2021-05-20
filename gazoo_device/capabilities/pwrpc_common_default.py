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
from typing import Any, Callable
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import pwrpc_common_base
from gazoo_device.switchboard.transports import pigweed_rpc_transport
try:
  # pylint: disable=g-import-not-at-top
  from device_service import device_service_pb2
except ImportError:
  device_service_pb2 = None

BOOTUP_TIMEOUT = 10  # seconds
logger = gdm_logger.get_logger()


class PwRPCCommonDefault(pwrpc_common_base.PwRPCCommonBase):
  """Pigweed RPC common capability for devices communicating over PwRPC."""

  def __init__(self,
               device_name: str,
               switchboard_call: Callable[..., Any]):
    """Create an instance of the PwRPCCommonDefault capability.

    Args:
      device_name: Device name used for logging.
      switchboard_call: The Switchboard.call method which calls to the endpoint.
        See more examples in nrf_pigweed_lighting.py.
    """
    super().__init__(device_name=device_name)
    self._switchboard_call = switchboard_call

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
             bootup_logline_regex: str,
             bootup_timeout: int,
             no_wait: bool = False):
    """Reboots the device.

    Args:
      bootup_logline_regex: Device logline indicating booting up.
      bootup_timeout: Timeout (s) to wait for the bootup message.
      no_wait: Return before reboot completes.
    """
    self._trigger_device_action("Reboot")
    if not no_wait:
      self._verify_reboot(bootup_logline_regex, bootup_timeout)

  @decorators.CapabilityLogDecorator(logger)
  def factory_reset(self,
                    bootup_logline_regex: str,
                    bootup_timeout: int,
                    no_wait: bool):
    """Factory resets the device.

    Args:
      bootup_logline_regex: Device logline indicating booting up.
      bootup_timeout: Timeout (s) to wait for the bootup message.
      no_wait: Return before factory reset completes.
    """
    self._trigger_device_action("FactoryReset")
    if not no_wait:
      self._verify_reboot(bootup_logline_regex, bootup_timeout)

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
      raise errors.DeviceError("{} getting static info failed.".format(
          self._device_name))
    payload = device_service_pb2.DeviceInfo.FromString(payload_in_bytes)
    device_property = getattr(payload, property_name, None)
    if device_property is None:
      raise errors.DeviceError(f"{property_name} doesn't exist in static info.")
    return device_property

  def _trigger_device_action(self, action: str, timeout_s: int = 10) -> None:
    """Triggers specific device action.

    Args:
      action: Device actions including reboot, factory-reset and OTA.
      timeout_s: Timeout in seconds.

    Raises:
      DeviceError: The ack status is not true.
    """
    ack, _ = self._switchboard_call(
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
        method_args=("Device", action),
        method_kwargs={"pw_rpc_timeout_s": timeout_s})
    if not ack:
      raise errors.DeviceError("{} triggering {} failed: The action did not"
                               " succeed".format(self._device_name, action))

  def _verify_reboot(self, bootup_logline_regex: str, bootup_timeout: int):
    """Verifies reboot actually occurred.

    Args:
      bootup_logline_regex: Device logline indicating booting up.
      bootup_timeout: Timeout (s) to wait for the bootup message.
    """
    self._verify_bootup_starting(bootup_logline_regex)
    self._verify_responding_to_rpc(bootup_timeout)

  def _verify_bootup_starting(self, bootup_logline_regex: str):
    """Verifies bootup actually occurred.

    Args:
      bootup_logline_regex: Device logline indicating booting up.
    """
    logger.info(f"Waiting for logline {bootup_logline_regex}.")
    # TODO(b/188378008): implement logline matching logic.

  def _verify_responding_to_rpc(self, bootup_timeout):
    """Verifies device starting responding to RPC.

    Args:
      bootup_timeout: Timeout (s) to wait for the bootup message.
    """
    start_time = time.time()
    bootup_time = start_time + bootup_timeout
    while time.time() < bootup_time:
      try:
        logger.debug("{} responded to the RPC call: {}".
                     format(self._device_name, self.software_version))
        logger.info("{} booted up in {}s".
                    format(self._device_name, time.time() - start_time))
        return
      except errors.DeviceError:
        logger.debug("{} hasn't booted up yet.".format(self._device_name))
      time.sleep(0.5)
    raise errors.DeviceError(f"Failed to boot up within {BOOTUP_TIMEOUT}s.")
