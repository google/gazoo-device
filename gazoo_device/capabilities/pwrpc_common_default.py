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
from typing import Any, Callable
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device.capabilities.interfaces import pwrpc_common_base
from gazoo_device.switchboard.transports import pigweed_rpc_transport
try:
  # pylint: disable=g-import-not-at-top
  from device_service import device_service_pb2
except ImportError:
  device_service_pb2 = None


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
