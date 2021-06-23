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

"""Default implementation of the PwRPC (Pigweed RPC) button capability."""
from typing import Any, Callable, Dict
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
               expect_button_regexes: Dict[int, str],
               expect_timeout: int,
               switchboard_call_expect: Callable[..., Any]):
    """Creates an instance of the PwRPCButtonDefault capability.

    Args:
      device_name: Device name used for logging.
      expect_button_regexes: Dict of expected regexes for each button id.
      expect_timeout: Timeout (s) to wait for the expected regex.
      switchboard_call_expect: The switchboard.call_and_expect method.
    """
    super().__init__(device_name=device_name)
    self._expect_button_regexes = expect_button_regexes
    self._expect_timeout = expect_timeout
    self._switchboard_call_expect = switchboard_call_expect

  @decorators.CapabilityLogDecorator(logger)
  def push(self, button_id: int) -> None:
    """Push the button with the given id.

    Args:
      button_id: Button ID.

    Raises:
      DeviceError: When button_id is invalid or RPC ack value is not True.
    """
    if button_id not in self._expect_button_regexes:
      valid_ids = set(self._expect_button_regexes.keys())
      raise errors.DeviceError(f"Invalid button id {button_id}. Possible valid "
                               f"ids: {valid_ids}.")

    expect_regex = self._expect_button_regexes[button_id]
    _, (ack, _) = self._switchboard_call_expect(
        method=pigweed_rpc_transport.PigweedRPCTransport.rpc,
        pattern_list=[expect_regex],
        timeout=self._expect_timeout,
        method_args=("Button", "Event"),
        method_kwargs={"idx": button_id, "pushed": True},
        raise_for_timeout=True)

    if not ack:
      raise errors.DeviceError(f"Device {self._device_name} button {button_id} "
                               f"push failed.")
