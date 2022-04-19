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

"""Default implementation of the PwRPC (Pigweed RPC) wifi capability."""

from typing import Any, Callable, Optional

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import pwrpc_wifi_base
from gazoo_device.protos import wifi_service_pb2
from gazoo_device.switchboard.transports import pigweed_rpc_transport


_LOGGER = gdm_logger.get_logger()
_WIFI_RPC = "WiFi"
_ASCII_NULL_BYTES = b"\x00"


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

  def _verify_rpc_ack(self, ack: bool) -> None:
    """Helper method to verify rpc was acknowledged by device successfully.

    Args:
      ack: RPC ack.ok() value.

    Raises:
      DeviceError if the device failed to acknowledge the RPC.
    """
    if not ack:
      raise errors.DeviceError(f"{self._device_name} did not acknowledge "
                               "the RPC.")

  @decorators.DynamicProperty
  def channel(self) -> int:
    """Wifi channel used with current ssid connection."""
    ack, channel_bytes = self._switchboard_call(
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
        method_args=(_WIFI_RPC, "GetChannel"),
        method_kwargs={})

    self._verify_rpc_ack(ack)
    return wifi_service_pb2.Channel.FromString(channel_bytes).channel

  @decorators.DynamicProperty
  def ssid(self) -> str:
    """Name of the SSID to which device is connected."""
    ack, ssid_bytes = self._switchboard_call(
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
        method_args=(_WIFI_RPC, "GetSsid"),
        method_kwargs={})

    self._verify_rpc_ack(ack)
    ssid = wifi_service_pb2.Ssid.FromString(ssid_bytes).ssid
    # b/212183946: Remove any null characters from ssid name.
    return ssid.rstrip(_ASCII_NULL_BYTES).decode()

  @decorators.DynamicProperty
  def mac_address(self) -> str:
    """MAC address for the wifi interface.

    Returns:
      String representation of mac_address in lower case hexadecimal digits
      separated by colon (:). e.g. 24:0a:c4:f8:6c:d4
    """
    ack, mac_address_bytes = self._switchboard_call(
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
        method_args=(_WIFI_RPC, "GetMacAddress"),
        method_kwargs={})

    self._verify_rpc_ack(ack)
    return wifi_service_pb2.MacAddress.FromString(mac_address_bytes).mac_address

  @decorators.DynamicProperty
  def wifi_interface(self) -> str:
    """Name of the interface used for wifi connection."""
    ack, wifi_interface_bytes = self._switchboard_call(
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
        method_args=(_WIFI_RPC, "GetWiFiInterface"),
        method_kwargs={})

    self._verify_rpc_ack(ack)
    return wifi_service_pb2.WiFiInterface.FromString(
        wifi_interface_bytes).interface

  @decorators.DynamicProperty
  def ipv4_address(self) -> str:
    """IPv4 address for wifi interface."""
    ack, ip4_address_bytes = self._switchboard_call(
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
        method_args=(_WIFI_RPC, "GetIP4Address"),
        method_kwargs={})

    self._verify_rpc_ack(ack)
    return wifi_service_pb2.IP4Address.FromString(ip4_address_bytes).address

  @decorators.CapabilityLogDecorator(_LOGGER)
  def connect(self,
              ssid: str,
              security_type: str,
              secret: Optional[str] = None) -> None:
    """Establishes wifi conection with given ssid.

    Args:
      ssid: Name of the wifi ssid.
      security_type: Wifi encryption protocol as defined in
        wifi_service_pb2.WIFI_SECURITY_TYPE.
      secret: Wifi passphrase.

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
    ack, connection_result_bytes = self._switchboard_call(
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
        method_args=(_WIFI_RPC, "Connect"),
        method_kwargs=connect_kwargs)

    self._verify_rpc_ack(ack)
    connection_result = wifi_service_pb2.ConnectionResult.FromString(
        connection_result_bytes)
    result = connection_result.error
    if result != wifi_service_pb2.CONNECTION_ERROR.OK:
      raise errors.DeviceError(f"{self._device_name} failed to connect to wifi "
                               f"with {result}")

  @decorators.CapabilityLogDecorator(_LOGGER)
  def disconnect(self) -> None:
    """Disconnects from current wifi connection."""
    ack, _ = self._switchboard_call(
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
        method_args=(_WIFI_RPC, "Disconnect"),
        method_kwargs={})
    self._verify_rpc_ack(ack)
