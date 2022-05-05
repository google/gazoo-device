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

"""Cambrionix unit tests."""
import fcntl
import os
from typing import List
from unittest import mock

from gazoo_device import errors
from gazoo_device.auxiliary_devices import cambrionix
from gazoo_device.tests.unit_tests.utils import cambrionix_logs
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
import immutabledict
import serial


_CAMBRIONIX_CMD_DICT = immutabledict.immutabledict({
    "state": [],
    "state 1": "1, 0000, D O, 0, 0, x, 0.00",
    "state 4": "4, 0175, e A S, 0, 0, x, 0.00",
    "system": cambrionix_logs.CAMBRIONIX_SYSTEM,
    "reboot watchdog": [],
    "reboot": [],
    "mode sync 2": [],  # mode and port
    "cef": [],  # clears system error flags
    "crf": [],  # clears the system reboot flag
    "limits": cambrionix_logs.CAMBRIONIX_LIMITS,
})

_PP15S_EXPECTED_TOTAL_PORTS = 15
_PP8S_EXPECTED_TOTAL_PORTS = 8
_U16S_EXPECTED_TOTAL_PORTS = 16

_PERSISTENT_PROPERTIES = immutabledict.immutabledict({
    "model": "PP15S",
    "serial_number": "FT2BSR6O",
    "total_ports": 15,
    "port_extension_map": {
        "1.1": 4,
        "1.2": 5,
        "1.3": 6,
        "1.4": 7,
        "2.1": 15,
        "2.2": 14,
        "2.3": 13,
        "2.4": 12,
        "3.1": 11,
        "3.2": 10,
        "3.3": 9,
        "3.4": 8,
        "4.2": 1,
        "4.3": 2,
        "4.4": 3,
    },
})
_SERIAL_PORT_PATH = (
    "/dev/serial/by-id/usb-FTDI_FT230X_Basic_UART_DN00I41W-if00-port0")


def _mock_shell(cmd: str, close_delay: float = 0.0) -> List[str]:
  """Returns mock Cambrionix shell response lines.

  Args:
    cmd: A valid Cambrionix command.
    close_delay: Seconds to delay between command and closing control port.

  Returns:
    Lines with which a real Cambrionix would respond to the command.
  """
  del close_delay  # Unused by the mock.
  return _CAMBRIONIX_CMD_DICT[cmd]


class CambrionixTest(fake_device_test_case.FakeDeviceTestCase):
  """Cambrionix unit test class."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements("cambrionix-i41w")
    self.device_config["persistent"]["console_port_name"] = _SERIAL_PORT_PATH
    self.device_config["persistent"]["model"] = "PP15S"
    self.uut = cambrionix.Cambrionix(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory,
        log_file_name=None)

  def test_002_is_connected(self):
    with mock.patch.object(os.path, "exists", return_value=True):
      self.assertTrue(cambrionix.Cambrionix.is_connected(self.device_config))
      old_config = {"persistent": {"hub_port_name": "1234"}}
      self.assertTrue(cambrionix.Cambrionix.is_connected(old_config))

  @mock.patch.object(fcntl, "fcntl")
  @mock.patch.object(serial, "Serial", fd=1, is_open=False)
  def test_004_open(self, mock_fcntl, mock_serial):
    """Testing the '_open' function to ensure fd is assigned."""
    self.uut._serial_port = None
    mock_serial.fd = 1
    self.uut._open()
    self.assertTrue(
        mock_serial.called, "ERROR - the serial object {} was not "
        "mocked.".format("serial.Serial()"))
    self.uut._serial_port.is_open = False
    mock_serial.open.reset_mock()
    self.uut._open()
    self.uut._serial_port.open.assert_called()

  @mock.patch.object(
      serial,
      "Serial",
      autospec=True,
      side_effect=KeyError("Unexpected keyword arguments"))
  def test_005b_open_fails(self, mock_serial):
    """Test open fails when bad args are given."""
    self.uut._serial_port = None
    with self.assertRaisesRegex(errors.DeviceError,
                                "Unexpected keyword arguments"):
      self.uut._open()

  @mock.patch.object(cambrionix.Cambrionix, "_command", side_effect=_mock_shell)
  def test_006_check_device_ready(self, fake_command):
    """Verify check device ready successful on valid ping."""
    self.uut.check_device_ready()

  def test_013_recover_error(self):
    """Verify recover can process unknown errors."""
    with self.assertRaisesRegex(errors.DeviceError, "some error"):
      with mock.patch.object(self.uut, "reboot"):
        self.uut.recover(errors.DeviceError("some error"))

  def test_014_recover(self):
    """Verify recover can process known errors successfully."""
    with mock.patch.object(self.uut, "reboot"):
      self.uut.recover(
          errors.DeviceNotResponsiveError(self.uut.name, "some error"))
      self.assertTrue(self.uut.reboot.called, "Expected reboot to be called")

  @mock.patch.object(cambrionix.Cambrionix, "_command", side_effect=_mock_shell)
  def test_017_reboot(self, mock_command):
    """Verify a call to reboot is successful."""
    self.uut.reboot()
    self.assertIn("reboot", mock_command.call_args[0])

  @mock.patch.object(cambrionix.Cambrionix, "_command", side_effect=_mock_shell)
  def test_018_set_mode(self, mock_command):
    """Verify a call to set_mode is successful."""
    self.uut.switch_power.set_mode("sync", port=2)
    self.assertIn("mode sync 2", mock_command.call_args[0])

  def test_019_bad_mode(self):
    """Verify an invalid parameter in call to set_mode throws error."""
    with self.assertRaisesRegex(errors.DeviceError, "Mode dude not found"):
      self.uut.switch_power.set_mode("dude", port=2)

  @mock.patch.object(
      cambrionix.Cambrionix,
      "_command",
      side_effect=[(errors.DeviceError("some error"))])
  def test_020_bad_shell_with_return_code(self, mock_command):
    """Verify if bad shell command given -1 is returned and error thrown."""
    result, return_code = self.uut.shell("dude", include_return_code=True)
    self.assertEqual(result, "", "Expected '' instead found {}".format(result))
    self.assertEqual(
        return_code, -1,
        "Expected return_code -1 instead found {}".format(return_code))

  @mock.patch.object(cambrionix.Cambrionix, "_command", side_effect=_mock_shell)
  def test_021_shell_with_return_code(self, mock_command):
    """Verify if valid shell command is given a valid return code is seen."""
    result, return_code = self.uut.shell("cef", include_return_code=True)
    self.assertEqual(result, "",
                     "Expected '' result instead found {}".format(result))
    self.assertEqual(
        return_code, 0,
        "Expected return code 0 instead found {}".format(return_code))

  @mock.patch.object(cambrionix.Cambrionix, "_command", side_effect=_mock_shell)
  def test_021_shell(self, mock_command):
    """Verify if valid shell command is successful."""
    result = self.uut.shell("cef")
    self.assertEqual(result, "",
                     "Expected '' result instead found {}".format(result))

  @mock.patch.object(cambrionix.Cambrionix, "_command", side_effect=_mock_shell)
  def test_030_get_usb_mode(self, mock_command):
    """Get the usb mode using the switch_power capability."""
    self.assertEqual(self.uut.switch_power.get_mode(port=1), "off")

  @mock.patch.object(cambrionix.Cambrionix, "_command", side_effect=_mock_shell)
  def test_031_get_usb_mode_with_error_flag(self, mock_command):
    """Verify get_mode returns the correct state when error flag is set."""
    self.assertEqual(self.uut.switch_power.get_mode(port=4), "sync")

  @mock.patch.object(
      cambrionix.Cambrionix, "_command", return_value=_mock_shell("system"))
  def test_100_get_detection_info(self, mock_command):
    """Verify get detection info works correctly."""

    self._test_get_detection_info(
        self.device_config["persistent"]["console_port_name"],
        cambrionix.Cambrionix, _PERSISTENT_PROPERTIES.copy())

  @mock.patch.object(
      cambrionix.Cambrionix,
      "_command",
      return_value=[
          "cambrionix gobbly 5 Port USB Charge+Sync", "Hardware: gobbly",
          "Firmware: 1.68", "Compiled: Feb 14 2017 17:30:26", "Group: -",
          "Panel ID: Absent"
      ])
  def test_101_get_detection_info_bad_model(self, mock_command):
    """Verify get detection info works correctly."""

    with self.assertRaisesRegex(errors.DeviceError, "gobbly"):
      self.uut.get_detection_info()

  @mock.patch.object(
      cambrionix.Cambrionix, "_command", return_value=_mock_shell("system"))
  def test_150_check_pp15s_total_ports(self, mock_command):
    """Verify that for a PP15S that total_ports is correct."""
    # Verify the model is PP15S before checking for 15 ports.
    model = self.uut._get_system_hardware()
    self.assertEqual(model, "PP15S")
    self.assertEqual(self.uut.total_ports, _PP15S_EXPECTED_TOTAL_PORTS)

  def test_151_check_pp8s_total_ports(self):
    """Verify that for a PP8S that total_ports is correct."""
    self.uut.props["persistent_identifiers"]["model"] = "PP8S"
    self.assertEqual(self.uut.total_ports, _PP8S_EXPECTED_TOTAL_PORTS)

  @mock.patch.object(
      cambrionix.Cambrionix, "_get_system_hardware", return_value="U16S")
  @mock.patch.object(
      cambrionix.Cambrionix, "_command", return_value=_mock_shell("system"))
  def test_152_check_u16s_total_ports(self, mock_command, mock_system_hardware):
    """Verify that for a U16S that total_ports is correct."""
    self.uut.props["persistent_identifiers"]["model"] = "U16S"
    self.assertEqual(self.uut.total_ports, _U16S_EXPECTED_TOTAL_PORTS)

  def test_200_cambrionix_has_switch_power_capability(self):
    """Verify that has_capabilities returns true for switch_power capability."""
    self.assertTrue(self.uut.has_capabilities(["switch_power"]))

  def test_201_does_not_have_usb_hub_capability(self):
    """Verify that the usb_hub capability is not supported by Cambrionix."""
    self.assertFalse(self.uut.has_capabilities(["usb_hub"]))

  def test_210_switch_power_in_supported_capabilities(self):
    """Verify switch_power capability is supported by Cambrionix."""
    self.assertIn("switch_power", self.uut.get_supported_capabilities())


if __name__ == "__main__":
  fake_device_test_case.main()
