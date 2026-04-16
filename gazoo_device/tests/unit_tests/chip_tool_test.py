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

"""Unit tests for the raspberry_pi_matter_controller module."""
from unittest import mock

from gazoo_device import errors
from gazoo_device import package_registrar
from gazoo_device.auxiliary_devices import chip_tool
from gazoo_device.capabilities import matter_controller_chip_tool
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.tests.unit_tests.utils import matter_controller_device_logs
from gazoo_device.utility import host_utils


class ChipToolTests(fake_device_test_case.FakeDeviceTestCase):
  """Test for CHIP tool on x86 host."""

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    package_registrar.register(chip_tool)

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements("chip_tool-0000")
    self.device_config["options"]["matter_node_id"] = 1234
    self.fake_responder.behavior_dict = {
        **matter_controller_device_logs.LINUX_BEHAVIOR.copy()
    }

    self.uut = chip_tool.ChipTool(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory,
    )

  def test_create_chip_tool_object(self):
    """Verifies the successful creation of a CHIP tool object."""
    self.assertIsNotNone(self.uut)
    self.assertIsInstance(self.uut, chip_tool.ChipTool)

  def test_has_chip_tool_command(self):
    self.assertTrue(self.uut.shell_capability.has_command("chip-tool"))

  def test_initialize_matter_controller_capability(self):
    self.assertIsNotNone(self.uut.matter_controller)

  def test_initialize_matter_endpoints_accessor_capability(self):
    self.assertIsNotNone(self.uut.matter_endpoints)

  def test_initialize_matter_endpoints_with_no_matter_node_id(self):
    """Tests matter_endpoints throws DeviceError with no commissioned device."""
    del self.device_config["options"]["matter_node_id"]
    with self.assertRaises(errors.DeviceError):
      _ = self.uut.matter_endpoints

  @mock.patch.object(
      matter_controller_chip_tool.MatterControllerChipTool, "factory_reset"
  )
  def test_factory_reset(self, mock_factory_reset):
    self.uut.factory_reset()
    mock_factory_reset.assert_called_once()

  @mock.patch.object(
      host_utils,
      "get_command_path",
      return_value="/usr/local/bin/chip-tool",
      autospec=True,
  )
  def test_check_chip_tool_available_with_path(self, mock_get_command_path):
    self.uut.check_chip_tool_available()
    mock_get_command_path.assert_called_once()

  @mock.patch.object(
      host_utils, "get_command_path", return_value="", autospec=True
  )
  def test_check_chip_tool_available_without_path(self, _):
    with self.assertRaises(errors.DependencyUnavailableError):
      self.uut.check_chip_tool_available()

  @mock.patch.object(
      host_utils,
      "get_command_path",
      return_value="/usr/local/bin/chip-tool",
      autospec=True,
  )
  def test_check_chip_tool_executable_return_code_zero(self, _):
    self.uut.check_chip_tool_available()
    self.uut.check_chip_tool_executable()

  @mock.patch.object(
      host_utils,
      "get_command_path",
      return_value="/usr/local/bin/chip-tool",
      autospec=True,
  )
  def test_check_chip_tool_executable_return_code_nonzero(self, _):
    self.uut.check_chip_tool_available()
    self.fake_responder.behavior_dict.update(
        matter_controller_device_logs.make_device_responses((
            {
                "cmd": "/usr/local/bin/chip-tool",
                "resp": (
                    "-bash: /usr/local/bin/chip-tool: No such file or directory"
                ),
                "code": -127,
            },
        ))
    )
    with self.assertRaises(errors.DependencyUnavailableError):
      self.uut.check_chip_tool_executable()

  def test_get_console_configuration(self):
    self.uut.get_console_configuration()


if __name__ == "__main__":
  fake_device_test_case.main()
