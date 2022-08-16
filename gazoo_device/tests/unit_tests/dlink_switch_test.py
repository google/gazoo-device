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
"""Tests for dlink_switch."""
import subprocess
from unittest import mock

from gazoo_device import detect_criteria
from gazoo_device import errors
from gazoo_device.auxiliary_devices import dlink_switch
from gazoo_device.capabilities import switch_power_snmp
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.utility import host_utils
import immutabledict

_PORT = 1
_TOTAL_PORTS = 5
_IP_ADDRESS = "123.45.67.89"
_MODEL = "DGS-1100-05"
_TOTAL_PORTS_RESPONSE = "iso.3.6.1.2.1.2.1.0 = INTEGER: 5"
_EXPECTED_TOTAL_PORTS_CALL = (
    f"snmpget -v 2c -c private {_IP_ADDRESS}:161 1.3.6.1.2.1.2.1.0".split())
_EXPECTED_TOTAL_PORTS_CALL_TIMEOUT_S = 10

_PERSISTENT_PROPERTIES = immutabledict.immutabledict({
    "device_type": "dlink_switch",
    "console_port_name": _IP_ADDRESS,
    "model": _MODEL,
    "serial_number": _IP_ADDRESS.replace(".", ""),
    "total_ports": _TOTAL_PORTS,
})


class DLinkSwitchTests(fake_device_test_case.FakeDeviceTestCase):
  """Tests for D-Link switch auxiliary device class."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements("dlink-switch-1234")
    self.device_config["persistent"]["console_port_name"] = _IP_ADDRESS
    self.device_config["persistent"]["model"] = _MODEL
    self.device_config["persistent"]["total_ports"] = _TOTAL_PORTS
    mock.patch.object(
        detect_criteria, "get_dlink_model_name", return_value=_MODEL).start()
    self.mock_check_output = mock.patch.object(
        subprocess, "check_output", return_value=_TOTAL_PORTS_RESPONSE).start()
    self.uut = dlink_switch.DLinkSwitch(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory,
        log_file_name=None)

  @mock.patch.object(host_utils, "is_pingable", return_value=True)
  def test_is_connected_true(self, mock_ping):
    """Verify is_connected works as expected."""
    self.assertTrue(dlink_switch.DLinkSwitch.is_connected(self.device_config))

  def test_ip_address(self):
    self.assertTrue(self.uut.ip_address, _IP_ADDRESS)

  def test_total_ports(self):
    self.assertEqual(self.uut.total_ports, _TOTAL_PORTS)

  def test_get_detection_info_success(self):
    """Tests get_detection_info gathers all expected device properties."""
    self._test_get_detection_info(
        self.device_config["persistent"]["console_port_name"],
        dlink_switch.DLinkSwitch, _PERSISTENT_PROPERTIES)

    self.mock_check_output.assert_called_once_with(
        _EXPECTED_TOTAL_PORTS_CALL,
        text=True,
        timeout=_EXPECTED_TOTAL_PORTS_CALL_TIMEOUT_S)
    self.assertEqual(
        self.uut.props["persistent_identifiers"]["total_ports"], _TOTAL_PORTS)

  def test_get_detection_info_fails_to_identify_total_ports(self):
    """Tests get_detection_info fails when total ports OID is unrecognizable."""
    self.mock_check_output.return_value = "JUNK"

    with self.assertRaisesRegex(
        errors.DeviceError, "Unexpected response: JUNK"):
      self._test_get_detection_info(
          self.device_config["persistent"]["console_port_name"],
          dlink_switch.DLinkSwitch, _PERSISTENT_PROPERTIES)

  @mock.patch.object(
      switch_power_snmp.SwitchPowerSnmp,
      "get_mode",
      return_value=switch_power_snmp._ON)
  def test_switch_power_get_mode(self, mock_get_mode):
    """Test that get_mode reads that the port is ON."""
    self.assertEqual(self.uut.switch_power.get_mode(1), switch_power_snmp._ON)

  @mock.patch.object(
      switch_power_snmp.SwitchPowerSnmp,
      "set_mode",
  )
  def test_switch_power_off(self, mock_set_mode):
    """Test that power_off sets the port to OFF."""
    self.uut.switch_power.power_off(_PORT)
    mock_set_mode.assert_called_once_with(switch_power_snmp._OFF, _PORT)

  @mock.patch.object(
      switch_power_snmp.SwitchPowerSnmp,
      "set_mode",
  )
  def test_switch_power_on(self, mock_set_mode):
    """Test that power_off sets the port to ON."""
    self.uut.switch_power.power_on(_PORT)
    mock_set_mode.assert_called_once_with(switch_power_snmp._ON, _PORT)


if __name__ == "__main__":
  fake_device_test_case.main()
