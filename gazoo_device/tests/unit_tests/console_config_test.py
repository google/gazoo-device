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

"""Unit tests for the interactive console configuration (console_config.py)."""
from typing import Any, Callable, Dict, Tuple
from unittest import mock

from absl.testing import parameterized
from gazoo_device import console_config
from gazoo_device.switchboard import line_identifier
from gazoo_device.tests.unit_tests.utils import unit_test_case


class ConsoleConfigTests(unit_test_case.UnitTestCase):

  @parameterized.named_parameters(
      ("log_only", console_config.get_log_only_configuration, (), {}),
      ("separate_port_ctrl_c_transport_reopen",
       console_config.get_log_response_separate_port_configuration,
       (mock.MagicMock(spec=line_identifier.LineIdentifier),),
       {"reopen_command_transport_on_ctrl_c": True}),
      ("separate_port_ctrl_c_send_to_device",
       console_config.get_log_response_separate_port_configuration,
       (mock.MagicMock(spec=line_identifier.LineIdentifier),),
       {"reopen_command_transport_on_ctrl_c": False}),
      ("same_port_no_secondary",
       console_config.get_log_response_same_port_configuration,
       (mock.MagicMock(spec=line_identifier.LineIdentifier),), {}),
      ("same_port_with_secondary",
       console_config.get_log_response_same_port_configuration,
       (mock.MagicMock(spec=line_identifier.LineIdentifier),),
       {"enable_secondary": True}))
  def test_console_configuration_valid_layout(
      self, config_maker: Callable[..., console_config.ConsoleConfiguration],
      args: Tuple[Any, ...], kwargs: Dict[str, Any]):
    """Tests initialization and validation of valid console configurations."""
    configuration = config_maker(*args, **kwargs)
    self.assertTrue(configuration)

  def test_console_configuration_invalid_layout_duplicate_ids(self):
    """Tests creating a ConsoleConfiguration with duplicate window IDs."""
    error_regex = r"Window IDs \[0, 0\] are not unique"
    with self.assertRaisesRegex(ValueError, error_regex):
      console_config.ConsoleConfiguration(
          windows=(
              console_config.CommandResponseWindow("Window 1", 0),
              console_config.CommandResponseWindow("Window 2", 0)),
          line_to_window_id=mock.MagicMock())


if __name__ == "__main__":
  unit_test_case.main()
