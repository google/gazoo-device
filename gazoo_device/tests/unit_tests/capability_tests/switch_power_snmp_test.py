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
"""Tests for switch_power_snmp capability."""
import subprocess
from unittest import mock

from gazoo_device import errors
from gazoo_device.capabilities import switch_power_snmp
from gazoo_device.tests.unit_tests.utils import unit_test_case

_DEVICE_NAME = "DLINK_SWITCH"
_IP_ADDRESS = "0.0.0.0"
_TOTAL_PORTS = 5
_PORT = 1
_GET = "snmpget -v 2c -c private 0.0.0.0:161 1.3.6.1.2.1.2.2.1.7.1"
_SET_ON = "snmpset -v 2c -c private 0.0.0.0:161 1.3.6.1.2.1.2.2.1.7.1 i 1"
_SET_OFF = "snmpset -v 2c -c private 0.0.0.0:161 1.3.6.1.2.1.2.2.1.7.1 i 2"
_ON_STATUS = "iso.3.6.1.2.1.2.2.1.7.1 = INTEGER: 1"
_OFF_STATUS = "iso.3.6.1.2.1.2.2.1.7.1 = INTEGER: 2"
_RETURNCODE = 0


class SwitchPowerSnmpTests(unit_test_case.UnitTestCase):
  """Test class to verify the behavior of the switch_power_snmp capability."""

  def setUp(self):
    super().setUp()
    self.uut = switch_power_snmp.SwitchPowerSnmp(_DEVICE_NAME, _IP_ADDRESS,
                                                 _TOTAL_PORTS)

  def test_supported_modes(self):
    self.assertEqual(
        self.uut.supported_modes,
        [switch_power_snmp._ON, switch_power_snmp._OFF],
    )

  def test_get_mode__invalid_port(self):
    """Test that get_mode recognizes an invalid port."""
    with self.assertRaises(errors.DeviceError):
      self.uut.get_mode(0)

  @mock.patch.object(subprocess, "check_output", return_value=_ON_STATUS)
  def test_get_mode__port_on(self, mock_check_output):
    """Test get_mode recognizes an ON status."""
    self.assertEqual(self.uut.get_mode(_PORT), switch_power_snmp._ON)
    mock_check_output.assert_called_once_with(
        _GET.split(), text=True, timeout=switch_power_snmp._SNMP_TIMEOUT_S)

  @mock.patch.object(subprocess, "check_output", return_value=_OFF_STATUS)
  def test_get_mode__port_off(self, mock_check_output):
    """Test get_mode recognizes an OFF status."""
    self.assertEqual(self.uut.get_mode(_PORT), switch_power_snmp._OFF)
    mock_check_output.assert_called_once_with(
        _GET.split(), text=True, timeout=switch_power_snmp._SNMP_TIMEOUT_S)

  def test_set_mode__invalid_port(self):
    """Test that set_mode recognizes an invalid port."""
    with self.assertRaises(errors.DeviceError):
      self.uut.set_mode(switch_power_snmp._ON, _TOTAL_PORTS + 1)

  @mock.patch.object(subprocess, "check_output", return_value=_ON_STATUS)
  def test_set_mode_on__pass(self, mock_check_output):
    """Test set_mode successfully sets port ON."""
    self.uut.set_mode(switch_power_snmp._ON, _PORT)
    mock_check_output.assert_called_once_with(
        _SET_ON.split(), text=True, timeout=switch_power_snmp._SNMP_TIMEOUT_S)

  @mock.patch.object(subprocess, "check_output", return_value=_OFF_STATUS)
  def test_set_mode_on__fail(self, mock_check_output):
    """Test set_mode fails to set port ON."""
    with self.assertRaises(errors.DeviceError):
      self.uut.set_mode(switch_power_snmp._ON, _PORT)
    mock_check_output.assert_called_once_with(
        _SET_ON.split(), text=True, timeout=switch_power_snmp._SNMP_TIMEOUT_S)

  @mock.patch.object(subprocess, "check_output", return_value=_OFF_STATUS)
  def test_set_mode_off__pass(self, mock_check_output):
    """Test set_mode successfully sets port OFF."""
    self.uut.set_mode(switch_power_snmp._OFF, _PORT)
    mock_check_output.assert_called_once_with(
        _SET_OFF.split(), text=True, timeout=switch_power_snmp._SNMP_TIMEOUT_S)

  @mock.patch.object(subprocess, "check_output", return_value=_ON_STATUS)
  def test_set_mode_off__fail(self, mock_check_output):
    """Test set_mode fails to set port OFF."""
    with self.assertRaises(errors.DeviceError):
      self.uut.set_mode(switch_power_snmp._OFF, _PORT)
    mock_check_output.assert_called_once_with(
        _SET_OFF.split(), text=True, timeout=switch_power_snmp._SNMP_TIMEOUT_S)

  @mock.patch.object(switch_power_snmp.SwitchPowerSnmp, "set_mode")
  def test_power_off(self, mock_set_mode):
    self.uut.power_off(_PORT)
    mock_set_mode.assert_called_once_with(switch_power_snmp._OFF, _PORT)

  @mock.patch.object(switch_power_snmp.SwitchPowerSnmp, "set_mode")
  def test_power_on(self, mock_set_mode):
    self.uut.power_on(_PORT)
    mock_set_mode.assert_called_once_with(switch_power_snmp._ON, _PORT)


if __name__ == "__main__":
  unit_test_case.main()
