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

"""Default implementation of the PwRPC (Pigweed RPC) wifi capability."""

import time
from typing import Any, Callable, Optional

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import pwrpc_wifi_base
from gazoo_device.protos import wifi_service_pb2
from gazoo_device.utility import pwrpc_utils
from gazoo_device.utility import retry


_LOGGER = gdm_logger.get_logger()
_WIFI_RPC = "WiFi"
_ASCII_NULL_BYTES = b"\x00"
_GET_STATE_RPC_TIMEOUT_SEC = 5
_POLL_INTERVAL_SEC = 1


class PwRPCWifiDefault(pwrpc_wifi_base.PwRPCWifiBase):
  """Pigweed RPC wifi capability."""

  def __init__(self,
               device_name: str,
               switchboard_call: Callable[..., Any]):
    """Initializes an instance of the PwRPCWifiDefault capability.

    Args:
      device_name: Device name used for logging.
      switchboard_call: The switchboard.call method.
    """
    super().__init__(device_name=device_name)
    self._switchboard_call = switchboard_call

  @decorators.DynamicProperty
  def channel(self) -> int:
    """Wifi channel used with current ssid connection."""
    channel_bytes = self._wifi_rpc_call("GetChannel")
    return wifi_service_pb2.Channel.FromString(channel_bytes).channel

  @decorators.DynamicProperty
  def ssid(self) -> str:
    """Name of the SSID to which device is connected."""
    ssid_bytes = self._wifi_rpc_call("GetSsid")
    ssid = wifi_service_pb2.Ssid.FromString(ssid_bytes).ssid
    # b/212183946: Remove any null characters from ssid name.
    return ssid.rstrip(_ASCII_NULL_BYTES).decode()

  @decorators.DynamicProperty
  def state(self) -> bool:
    """Returns if the device is connected to wifi."""
    try:
      state_bytes = self._wifi_rpc_call("GetState")
      return wifi_service_pb2.State.FromString(state_bytes).connected
    except errors.DeviceError as e:
      if "Error code: 9" in str(e):
        # TODO(gdm-authors) Remove error handling when the RPC is fixed.
        _LOGGER.warning(
            f"GetState doesn't work when the {self._device_name} is not "
            "connected to WiFi.")
        return False
      else:
        raise

  @decorators.DynamicProperty
  def ipv6_address(self) -> str:
    """IPv6 address for wifi interface."""
    try:
      ip6_address_bytes = self._wifi_rpc_call("GetIP6Address")
      return wifi_service_pb2.IP6Address.FromString(ip6_address_bytes).address
    except errors.DeviceError as e:
      if "Error code: 13" in str(e):
        # TODO(gdm-authors) Remove error handling when the RPC is fixed.
        _LOGGER.warning(
            f"GetIP6Address doesn't work when the {self._device_name} is not "
            "connected to WiFi.")
        return ""
      else:
        raise e

  @decorators.DynamicProperty
  def mac_address(self) -> str:
    """MAC address for the wifi interface.

    Returns:
      String representation of mac_address in lower case hexadecimal digits
      separated by colon (:). e.g. 24:0a:c4:f8:6c:d4
    """
    mac_address_bytes = self._wifi_rpc_call("GetMacAddress")
    return wifi_service_pb2.MacAddress.FromString(mac_address_bytes).mac_address

  @decorators.DynamicProperty
  def wifi_interface(self) -> str:
    """Name of the interface used for wifi connection."""
    wifi_interface_bytes = self._wifi_rpc_call("GetWiFiInterface")
    return wifi_service_pb2.WiFiInterface.FromString(
        wifi_interface_bytes).interface

  @decorators.DynamicProperty
  def ipv4_address(self) -> str:
    """IPv4 address for wifi interface."""
    ip4_address_bytes = self._wifi_rpc_call("GetIP4Address")
    return wifi_service_pb2.IP4Address.FromString(ip4_address_bytes).address

  @decorators.CapabilityLogDecorator(_LOGGER)
  def connect(self,
              ssid: str,
              security_type: str,
              secret: Optional[str] = None,
              verify: bool = True,
              timeout: int = _GET_STATE_RPC_TIMEOUT_SEC,
              interval: int = _POLL_INTERVAL_SEC) -> None:
    """Establishes wifi conection with given ssid.

    Args:
      ssid: Name of the wifi ssid.
      security_type: Wifi encryption protocol as defined in
        wifi_service_pb2.WIFI_SECURITY_TYPE.
      secret: Wifi passphrase.
      verify: Verifies if the device is connected to wifi.
      timeout: Timeout in seconds to verify the connection.
      interval: Interval in seconds between verification tries.

    Raises:
      DeviceError with appropriate error code if connection failed.
    """
    connect_kwargs = {
        "ssid":
            ssid.encode(),
        "security_type":
            wifi_service_pb2.WIFI_SECURITY_TYPE.Value(security_type)
    }
    if secret is not None:
      connect_kwargs.update({"secret": secret.encode()})

    connection_result_bytes = self._wifi_rpc_call("Connect", connect_kwargs)
    connection_result = wifi_service_pb2.ConnectionResult.FromString(
        connection_result_bytes)
    result = connection_result.error

    # Wait for the Connect RPC to take effect
    if verify:
      if result != wifi_service_pb2.CONNECTION_ERROR.OK:
        raise errors.DeviceError(
            f"{self._device_name} failed to connect to wifi with {result}")
      retry.retry(
          func=lambda: self.state,
          is_successful=lambda state: state,
          timeout=timeout,
          interval=interval,
          reraise=False)

  @decorators.CapabilityLogDecorator(_LOGGER)
  def disconnect(self, verify: bool = True) -> None:
    """Disconnects from current wifi connection."""
    self._wifi_rpc_call("Disconnect")
    if verify and self.state:
      raise errors.DeviceError(
          f"{self._device_name} failed to disconnect from wifi.")

  def _wifi_rpc_call(
      self,
      service_name: str,
      service_kwargs: Optional[dict[str, Any]] = None) -> bytes:
    """Helper method for WiFi RPC call."""
    if service_kwargs is None:
      service_kwargs = {}
    payload = self._switchboard_call(
        method_name=pwrpc_utils.RPC_METHOD_NAME,
        method_args=(_WIFI_RPC, service_name),
        method_kwargs=service_kwargs)
    # b/281957128#comment2 Temporary solution to fix WiFi RPC timeout issue.
    time.sleep(0.5)
    return payload
