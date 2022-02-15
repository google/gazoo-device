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

"""Unit tests for gdm_cli.py."""
import inspect
from typing import Dict
from unittest import mock

from absl.testing import parameterized
from gazoo_device import gdm_cli
from gazoo_device.auxiliary_devices import raspberry_pi
from gazoo_device.tests.unit_tests.utils import unit_test_case

_GOOD_COMMANDS = (
    "- devices",
    "detect --force_overwrite",
    "detect",
    "delete raspberrypi-0001",
    "redetect raspberrypi-0001",
    "detect --static_ips 12.34.56.78",
    "devices",
    "log raspberrypi-0001",
    "helpfull",
    "man",
    "man raspberrypi",
    "man raspberrypi reboot",
    "man raspberrypi file_transfer",
    "man raspberrypi console_port_name",
    "man raspberrypi communication_address",
    "port-map",
    "get-usb-hub-props raspberrypi-0001",
    "set-prop raspberrypi-0001 some_new_property 1",
    "get-prop raspberrypi-0001",
    "get-prop raspberrypi-0001 firmware_version",
    "get-device-prop raspberrypi-0001",
    "get-device-prop raspberrypi-0001 firmware_version",
    "update-gdm",
    "issue raspberrypi-0001",
    "issue raspberrypi-0001 - reboot",
    "issue raspberrypi-0001 - firmware_version",
    "issue raspberrypi-0001 - reboot --method=x",
    "exec raspberrypi-0001",
    "exec raspberrypi-0001 - reboot",
    "exec raspberrypi-0001 - reboot --method=x",
    "health-check raspberrypi-0001",
    "-v",
    "--debug - detect",
    "--dev_debug - detect",
    "--quiet - detect",
)


class CLITests(unit_test_case.UnitTestCase):
  """Unit tests for gdm_cli.py."""

  @parameterized.named_parameters(
      *(dict(testcase_name=command, command=command)
        for command in _GOOD_COMMANDS))
  def test_command(self, command: str):
    """Tests that CLI commands can be executed successfully."""
    manager_instance = gdm_cli._create_manager_for_cli({})
    with mock.patch.object(raspberry_pi.RaspberryPi, "__init__",
                           return_value=None):
      raspberry_pi_inst = raspberry_pi.RaspberryPi(manager_instance, {})
    manager_instance.close()

    raspberry_pi_mock = mock.NonCallableMagicMock(
        raspberry_pi_inst, autospec=True)
    manager_mock = mock.NonCallableMagicMock(
        manager_instance, autospec=True)

    # Set return value of all mocks to None to prevent Fire from iterating
    # infinitely. Fire stops at the first non-callable attribute.
    for _, attribute in inspect.getmembers(raspberry_pi_mock):
      if isinstance(attribute, mock.MagicMock):
        attribute.return_value = None
    raspberry_pi_mock.__str__.return_value = "Raspberry Pi (mock)"
    for _, attribute in inspect.getmembers(manager_mock):
      if isinstance(attribute, mock.MagicMock):
        attribute.return_value = None

    manager_mock.issue.return_value = raspberry_pi_mock
    manager_mock.exec.return_value = raspberry_pi_mock
    manager_mock.create_device.return_value = raspberry_pi_mock

    with mock.patch.object(
        gdm_cli, "_create_manager_for_cli", return_value=manager_mock):
      with mock.patch.object(
          raspberry_pi, "RaspberryPi",
          return_value=raspberry_pi_mock):

        with self.assertRaises(SystemExit) as assertion:
          gdm_cli.main(command)
        self.assertEqual(
            assertion.exception.code, 0,
            f"{command!r} failed with return code {assertion.exception.code}.")

  @parameterized.parameters(
      dict(command="--debug - detect", expected_flags={"debug": True}),
      dict(command="--dev_debug - detect", expected_flags={"dev_debug": True}),
      dict(command="--quiet - detect", expected_flags={"quiet": True}),
      dict(command="--help", expected_flags={}),
      dict(command="-- --help", expected_flags={}))
  def test_get_flag(self, command: str, expected_flags: Dict[str, bool]):
    """Tests that _get_flags() properly parses and returns flags."""
    flags = gdm_cli._get_flags(command.split())
    self.assertEqual(flags, expected_flags)


if __name__ == "__main__":
  unit_test_case.main()
