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

"""Mixin for comm_power_default capability."""
from unittest import mock

from gazoo_device.capabilities import comm_power_default

ETHERNET_SWITCH_NAME = "dlink_switch-4390"
ETHERNET_SWITCH_PORT = "2"


class CommPowerDefaultTestMixin:
  """Mixin for common device unit tests of communication power.

  Assumes self.uut is set.
  """

  def mixin_set_up(self):
    """Set up the ethernet switch ip and port for the mixin unit tests.

    Device unit tests that use this mixin should call this in setUp method.
    """
    self.uut.set_property("ethernet_switch_name", ETHERNET_SWITCH_NAME)
    self.uut.set_property("ethernet_switch_port", ETHERNET_SWITCH_PORT)

  @mock.patch.object(
      comm_power_default.CommPowerDefault, "_verify_switch_created")
  def test_power_off(self, _):
    """Test self.uut.communication_power.off is called."""
    self.uut.comm_power.off()
    if self.uut.comm_power._power_and_data_share_cable:
      self.uut.comm_power._hub.switch_power.power_on.assert_called_once_with(
          1, data_sync=False)
    else:
      self.uut.comm_power._hub.switch_power.power_off.assert_called_once()

  @mock.patch.object(
      comm_power_default.CommPowerDefault, "_verify_switch_created")
  def test_power_on(self, _):
    """Test self.uut.communication_power.on is called."""
    self.uut.comm_power._wait_for_bootup_complete_func = mock.Mock()
    self.uut.comm_power._wait_for_connection_func = mock.Mock()
    self.uut.comm_power.on()
    if self.uut.comm_power._power_and_data_share_cable:
      self.uut.comm_power._hub.switch_power.power_on.assert_called_once_with(
          1)
    else:
      self.uut.comm_power._hub.switch_power.power_on.assert_called_once()

  @mock.patch.object(
      comm_power_default.CommPowerDefault, "_verify_switch_created")
  def test_cycle(self, _):
    """Test calling cycle for the capability."""
    self.uut.comm_power._wait_for_bootup_complete_func = mock.Mock()
    self.uut.comm_power._wait_for_connection_func = mock.Mock()
    self.uut.comm_power.cycle()
    if self.uut.comm_power._power_and_data_share_cable:
      calls = [mock.call(1, data_sync=False), mock.call(1)]
      self.uut.comm_power._hub.switch_power.power_on.assert_has_calls(calls)
    else:
      self.uut.comm_power._hub.switch_power.power_on.assert_called_once()
      self.uut.comm_power._hub.switch_power.power_off.assert_called_once()
