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

"""NRF52840 DK OpenThread device controller.

The NRF DK device acts as a full thread device which uses OpenThread CLI to
create, get and manage the thread network.
See https://openthread.io/codelabs/openthread-hardware#0 for more details.
"""

from typing import Callable, List

from gazoo_device import decorators
from gazoo_device import detect_criteria
from gazoo_device import errors
from gazoo_device.base_classes import nrf_connect_sdk_device
from gazoo_device.capabilities import wpan_nrf_ot
from gazoo_device.switchboard import switchboard


class NrfOpenThread(nrf_connect_sdk_device.NRFConnectSDKDevice):
  """NRF OpenThread device controller."""

  COMMUNICATION_TYPE = "JlinkSerialComms"
  _COMMUNICATION_KWARGS = {"baudrate": 115200, "enable_jlink": False}
  DETECT_MATCH_CRITERIA = {
      detect_criteria.SerialQuery.IS_NRF_OPENTHREAD: True,
      detect_criteria.SerialQuery.PRODUCT_NAME: "j-link",
  }
  _OWNER_EMAIL = "gdm-authors@google.com"
  DEVICE_TYPE = "nrfopenthread"

  @decorators.PersistentProperty
  def health_checks(self)-> List[Callable[[], None]]:
    """Returns the list of methods to execute as health checks."""
    return super().health_checks + [self.check_otcli]

  @decorators.health_check
  def check_otcli(self) -> None:
    """Checks if the OpenThread CLI is working."""
    response = self.switchboard.send_and_expect(
        command="help", pattern_list=[".*Done"], timeout=3)
    if response.timedout:
      raise errors.DeviceBinaryMissingError(
          device_name=self.name,
          msg="The OpenThread CLI library is not working.")

  @decorators.CapabilityDecorator(switchboard.SwitchboardDefault)
  def switchboard(self) -> switchboard.SwitchboardDefault:
    """Switchboard instance for communicating with the device."""
    switchboard_name = self._get_private_capability_name(
        switchboard.SwitchboardDefault)
    if not hasattr(self, switchboard_name):
      switchboard_kwargs = self._COMMUNICATION_KWARGS.copy()
      switchboard_kwargs.update({
          "communication_address": self.communication_address,
          "communication_type": self.COMMUNICATION_TYPE,
          "log_path": self.log_file_name,
          "device_name": self.name,
          "event_parser": None})
      setattr(self, switchboard_name,
              self.get_manager().create_switchboard(**switchboard_kwargs))

    return getattr(self, switchboard_name)

  @decorators.CapabilityDecorator(wpan_nrf_ot.WpanNrfOt)
  def wpan(self) -> wpan_nrf_ot.WpanNrfOt:
    """Wpan instance for using OpenThreadCLI services."""
    return self.lazy_init(
        wpan_nrf_ot.WpanNrfOt,
        device_name=self.name,
        send=self.switchboard.send,
        send_and_expect=self.switchboard.send_and_expect)
