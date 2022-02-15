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

"""Default implementation of the PwRPC (Pigweed RPC) button capability."""
from typing import Any, Callable, Tuple
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import pwrpc_button_base
from gazoo_device.switchboard.transports import pigweed_rpc_transport

logger = gdm_logger.get_logger()


class PwRPCButtonDefault(pwrpc_button_base.PwRPCButtonBase):
  """Pigweed RPC button capability for devices communicating over PwRPC."""

  def __init__(self,
               device_name: str,
               valid_button_ids: Tuple[int, ...],
               switchboard_call: Callable[..., Any],
               rpc_timeout_s: int):
    """Creates an instance of the PwRPCButtonDefault capability.

    Args:
      device_name: Device name used for logging.
      valid_button_ids: Button numbers as present on a device.
      switchboard_call: The switchboard.call method.
      rpc_timeout_s: Timeout (s) for RPC call.
    """
    super().__init__(device_name=device_name)
    self._valid_button_ids = valid_button_ids
    self._switchboard_call = switchboard_call
    self._rpc_timeout_s = rpc_timeout_s

  @decorators.CapabilityLogDecorator(logger)
  def push(self, button_id: int) -> None:
    """Push the button with the given id.

    Args:
      button_id: Button ID.

    Raises:
      DeviceError: When button_id is invalid or RPC ack value is not True.
    """
    if button_id not in self._valid_button_ids:
      raise errors.DeviceError(f"Invalid button id {button_id}. Possible valid "
                               f"ids: {self._valid_button_ids}.")

    ack, _ = self._switchboard_call(
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
        method_args=("Button", "Event"),
        method_kwargs={"idx": button_id,
                       "pushed": True,
                       "pw_rpc_timeout_s": self._rpc_timeout_s})

    if not ack:
      raise errors.DeviceError(f"Device {self._device_name} button {button_id} "
                               f"push failed.")
