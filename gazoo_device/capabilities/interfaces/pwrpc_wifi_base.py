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

"""Interface for a PwRPC (Pigweed RPC) wifi capability."""
import abc
from typing import Optional

from gazoo_device.capabilities.interfaces import capability_base


class PwRPCWifiBase(capability_base.CapabilityBase):
  """Pigweed RPC Wi-Fi capability."""

  @property
  @abc.abstractmethod
  def channel(self) -> int:
    """Wifi channel used with current ssid connection."""

  @property
  @abc.abstractmethod
  def ssid(self) -> str:
    """Name of the SSID to which device is connected."""

  @property
  @abc.abstractmethod
  def mac_address(self) -> str:
    """MAC address for the wifi interface."""

  @property
  @abc.abstractmethod
  def wifi_interface(self) -> str:
    """Name of the interface used for wifi connection."""

  @property
  @abc.abstractmethod
  def ipv4_address(self) -> str:
    """IPv4 address for wifi interface."""

  @abc.abstractmethod
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

  @abc.abstractmethod
  def disconnect(self) -> None:
    """Disconnects from current wifi connection."""
