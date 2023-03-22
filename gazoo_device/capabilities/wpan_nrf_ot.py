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
"""The wpan OpenThread CLI capability for NRF platform."""

from typing import Callable, List, Optional

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities import wpan_ot_base
from gazoo_device.switchboard import expect_response

logger = gdm_logger.get_logger()

_COMMAND_RESPONSE_END = r"(.*\n)?(Done|Error \d+:.*)\n"


class WpanNrfOt(wpan_ot_base.WpanOtBase):
  """The wpan OpenThread CLI capability for NRF platform."""

  def __init__(self, device_name: str, send: Callable[..., None],
               send_and_expect: Callable[..., expect_response.ExpectResponse]):
    """Initializes an instance of WpanNrfOt capability.

    Args:
      device_name: Name of device using this capability.
      send: Switchboard.send method.
      send_and_expect: Switchboard.send_and_expect method.
    """
    super().__init__(device_name=device_name)
    self._send = send
    self._send_and_expect = send_and_expect

  @decorators.CapabilityLogDecorator(logger)
  def factory_reset(self) -> None:
    """Factory resets the Thread board.

    Raises:
      DeviceError: when something wrong happens during the factory reset.

    Note:
      factory reset command resets the board so it does not output a "DONE"
      string.
    """
    self._send(wpan_ot_base.Commands.FACTORY_RESET.value)
    self.wait_for_state({"disabled"})

  @decorators.DynamicProperty
  def csl_period(self) -> int:
    """Returns the csl period for the device in unit of 10 symbols.

    Symbol means symbol duration time in radio transmission, which equals to
    (1 / symbol rate). The symbol rate for Thread (IEEE 802.15.4, 2450MHz) is
    62.5k symbol/s. Thus 10 symbols equals to 0.00016s.
    """
    return int(self.call_command(wpan_ot_base.Commands.CSL_PERIOD.value)[0])

  @decorators.CapabilityLogDecorator(logger)
  def set_csl_period(self, csl_period: int) -> None:
    """Sets the csl period for the device in unit of 10 symbols.

    Args:
      csl_period: The csl period in unit of 10 symbols.  Symbol means symbol
        duration time in radio transmission, which equals to (1 / symbol rate).
        The symbol rate for Thread (IEEE 802.15.4, 2450MHz) is 62.5k symbol/s.
        Thus 10 symbols equals to 0.00016s.
    """
    self.call_command(f"{wpan_ot_base.Commands.CSL_PERIOD.value} {csl_period}")

  @decorators.DynamicProperty
  def csl_timeout(self) -> int:
    """Gets the csl timeout for the device.

    Returns:
      The csl timeout in unit of seconds.
    """
    return int(self.call_command(wpan_ot_base.Commands.CSL_TIMEOUT.value)[0])

  @decorators.CapabilityLogDecorator(logger)
  def set_csl_timeout(self, csl_timeout: int) -> None:
    """Sets the csl timeout for the device.

    Args:
      csl_timeout: The csl timeout in unit of seconds.
    """
    self.call_command(
        f"{wpan_ot_base.Commands.CSL_TIMEOUT.value} {csl_timeout}"
    )

  def call_command(self,
                   command: str,
                   timeout: Optional[float] = None) -> List[str]:
    """Helper method to send OTCLI command, check and return the responses."""
    if timeout is None:
      timeout = 5.0

    response = self._send_and_expect(
        command=command, pattern_list=[_COMMAND_RESPONSE_END], timeout=timeout)
    if response.timedout:
      error_message = response.before
      if "InvalidCommand" in response.before:
        raise errors.DeviceError(
            f"{self._device_name} Invalid command {command}: {error_message}")
      else:
        raise errors.DeviceError(
            f"{self._device_name} timed out responding to command {command}"
            f"after {timeout} seconds: {error_message}")
    lines = response.after.split("\n")[:-1]  # Strip the final empty line.
    if lines[-1] == "Done":
      # Command returns successfully
      return lines[1:-1]  # Strip echo back command and the status line.
    else:
      # Command returns an error
      raise errors.DeviceError(f"{self._device_name} command {command} failed. "
                               f"Response: {response.after}")
