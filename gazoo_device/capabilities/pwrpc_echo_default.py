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

"""Default implementation of the Pigweed RPC echo capability."""
from typing import Any, Callable
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import pwrpc_echo_base
from gazoo_device.switchboard.transports import pigweed_rpc_transport

logger = gdm_logger.get_logger()


class PwRPCEchoDefault(pwrpc_echo_base.PwRPCEchoBase):
  """Pigweed RPC echo capability."""

  def __init__(self,
               device_name: str,
               switchboard_call: Callable[..., Any]):
    """Create an instance of the PwRPCEchoDefault capability.

    Args:
      device_name: Device name used for logging.
      switchboard_call: The Switchboard.call method.
    """
    super().__init__(device_name=device_name)
    self._switchboard_call = switchboard_call

  @decorators.CapabilityLogDecorator(logger)
  def echo(self, msg: str) -> str:
    """Sends a message to the echo endpoint and returns the response back.

    Args:
      msg: Echo message to send.

    Returns:
      Echo message.

    Raises:
      DeviceError: Raises when RPC ack value is not True.
    """
    ack, echo_msg = self._switchboard_call(
        method=pigweed_rpc_transport.PigweedRPCTransport.echo_rpc,
        method_args=(msg,))
    if not ack:
      raise errors.DeviceError(f"{self._device_name} echo failed.")
    return echo_msg
