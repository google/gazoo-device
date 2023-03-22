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

"""Interface for Matter controller capability."""

import abc
import enum
from typing import Any, List, Optional, Sequence

from gazoo_device.capabilities.interfaces import capability_base


@enum.unique
class CommissionMethod(enum.Enum):
  BLE_WIFI = enum.auto()
  BLE_THREAD = enum.auto()
  ON_NETWORK = enum.auto()


class MatterControllerBase(capability_base.CapabilityBase):
  """Abstract base class for Matter controller capability."""

  @property
  @abc.abstractmethod
  def version(self) -> str:
    """Matter SDK version of the controller."""

  @abc.abstractmethod
  def commission(self,
                 node_id: int,
                 setup_code: str,
                 long_discriminator: Optional[int] = None,
                 ssid: Optional[str] = None,
                 password: Optional[str] = None,
                 operational_dataset: Optional[str] = None) -> None:
    """Commissions a device into the controller's fabric.

    Commissioning protocol is based on specified arguments:
      - When operational dataset is provided, pairs the device over ble-thread.
      - When Wi-Fi SSID and password are provided, pairs the device over
        ble-wifi.
      - Otherwise, discover the devices on the network and pairs with the first
        one that matches the setup code and long discriminator if one is
        specified.

    Args:
      node_id: Node ID to assign to the node being commissioned.
      setup_code: Set up PIN code of the remote device.
      long_discriminator: Discriminator of the remote device.
      ssid: Wi-Fi SSID either as a string, or in the form hex:XXXXXXXX where the
        bytes of the SSID are encoded as two-digit hex numbers.
      password: Wi-Fi password, either as a string or as hex data.
      operational_dataset: Thread dataset in base-64. This argument is mutually
        exclusive with ssid and password.
    """

  @abc.abstractmethod
  def decommission(self) -> None:
    """Forgets a commissioned device with the given node id."""

  @abc.abstractmethod
  def read(self, endpoint_id: int, cluster: str, attribute: str) -> Any:
    """Reads a cluster's attribute for the given node id and endpoint.

    Args:
      endpoint_id: Endpoint ID within the node to read attribute from.
      cluster: Name of the cluster to read the attribute value from.
      attribute: Name of the cluster attribute to read.

    Returns:
      Attribute value of the cluster.
    """

  @abc.abstractmethod
  def write(self, endpoint_id: int, cluster: str, attribute: str,
            value: Any) -> None:
    """Writes a cluster's attribute for the given node id and endpoint.

    Args:
      endpoint_id: Endpoint ID within the node to write attribute to.
      cluster: Name of the cluster to write the attribute value to (e.g. onoff).
      attribute: Name of the cluster attribute to write (e.g. on-time).
      value: New attribute value to update the cluster with.
    """

  @abc.abstractmethod
  def start_subscription(self, endpoint_id: int, cluster: str, attribute: str,
                         min_interval_s: int, max_interval_s: int) -> None:
    """Starts a subscription to a cluster's attribute.

    Args:
      endpoint_id: Endpoint ID within the node to write attribute to.
      cluster: Name of the cluster to write the attribute value to (e.g. onoff).
      attribute: Name of the cluster attribute to write (e.g. on-time).
      min_interval_s: Server should not send a new report if less than this
        number of seconds has elapsed since the last report.
      max_interval_s: Server must send a report if this number of seconds has
        elapsed since the last report.
    """

  @abc.abstractmethod
  def stop_subscription(self) -> List[Any]:
    """Stops existing subscription and returns subscribed values.

    Returns:
      Sequence of attribute values.
    """

  @abc.abstractmethod
  def subscribe(self,
                endpoint_id: int,
                cluster: str,
                attribute: str,
                min_interval_s: int,
                max_interval_s: int,
                timeout_s: int = 10) -> List[Any]:
    """Subscribes to a cluster's attribute and blocks until timeout.

    Args:
      endpoint_id: Endpoint ID within the node to write attribute to.
      cluster: Name of the cluster to write the attribute value to (e.g. onoff).
      attribute: Name of the cluster attribute to write (e.g. on-time).
      min_interval_s: Server should not send a new report if less than this
        number of seconds has elapsed since the last report.
      max_interval_s: Server must send a report if this number of seconds has
        elapsed since the last report.
      timeout_s: Number of seconds to subscribe to this attribute for.

    Returns:
      Sequence of attribute values.
    """

  @abc.abstractmethod
  def send(self, endpoint_id: int, cluster: str, command: str,
           arguments: Sequence[Any]) -> None:
    """Sends a command to a device with the given node id and endpoint.

    Args:
      endpoint_id: Endpoint ID within the node to read attribute from.
      cluster: Name of the cluster to send the command to (e.g. onoff).
      command: Name of the command to send (e.g. toggle).
      arguments: Command arguments.
    """

  @abc.abstractmethod
  def upgrade(self, build_file: str, build_id: str,
              paa_trust_store_path: str) -> None:
    """Installs chip-tool binary to the controller device and downloads matter certs.

    Args:
      build_file: Local path to build file.
      build_id: Commit SHA the controller is built at.
      paa_trust_store_path: Path where matter certs will be downloaded.
    """

  @abc.abstractmethod
  def factory_reset(self) -> None:
    """Factory resets all settings stored on controller's device."""

  @abc.abstractmethod
  def update_certs(self,
                   device_dest: str,
                   host_dest: Optional[str] = None) -> None:
    """Downloads certs from Matter SDK and to the device.

    Downloads certs and stores in the specified path in the host. Later, copies
    them to the specified path in the device.

    Args:
      device_dest: Directory path in the device to which the certs will be
        copied from the host machine.
      host_dest: Directory path in the host machine to store the certs. If not
        specified, a temporary directory will be used and cleaned up before
        exit.
    """
