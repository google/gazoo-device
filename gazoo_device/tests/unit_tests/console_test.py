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

"""Unit tests for the interactive console (console.py)."""
import asyncio
import builtins
from unittest import mock

from absl.testing import parameterized
from gazoo_device import console
from gazoo_device import console_config
from gazoo_device.switchboard import ftdi_buttons
from gazoo_device.switchboard import line_identifier
from gazoo_device.switchboard import switchboard
from gazoo_device.tests.unit_tests.utils import unit_test_case
from prompt_toolkit import document
from prompt_toolkit.application import current as application_current
from prompt_toolkit.eventloop import inputhook

_BATCH_1_NUM_LINES = 10
_BATCH_2_NUM_LINES = 10
_TOTAL_NUM_LINES = _BATCH_1_NUM_LINES + _BATCH_2_NUM_LINES
_WINDOW_HEIGHT = 10


class ConsoleTests(unit_test_case.UnitTestCase):

  def setUp(self):
    super().setUp()

    self.switchboard = mock.MagicMock(spec=switchboard.SwitchboardDefault)
    self.button_map = {"a_button": {"interface": 1, "pin": 3},
                       "b_button": {"interface": 2, "pin": 5}}
    with mock.patch.object(ftdi_buttons.FtdiButtons, "bitbang_device_init"):
      self.switchboard.button_list = [
          ftdi_buttons.FtdiButtons(
              ftdi_serial_number="12345678",
              button_map=self.button_map)]
    self.device_log_file = "some_file.txt"
    self.config = console_config.get_log_response_separate_port_configuration(
        line_identifier.PortLogIdentifier())

    self.uut = console.ConsoleApp(
        self.switchboard,
        self.device_log_file,
        self.config)

  @parameterized.named_parameters(
      # Appending additional log lines when the cursor is at the end should move
      # the cursor to the end of the text area.
      ("scroll_to_bottom_no_truncate", False, _BATCH_1_NUM_LINES,
       "", _TOTAL_NUM_LINES, "", console._MAX_TEXT_AREA_LINES),
      # Appending additional log lines when cursor is not at the end should not
      # move the cursor. Note: only 9 lines actually fit when _WINDOW_HEIGHT is
      # 10. The last line is always empty.
      ("no_scroll_to_bottom_no_truncate",
       True, 0, "Line 0", 0, "Line 0", console._MAX_TEXT_AREA_LINES),
      ("scroll_to_bottom_truncate", False,
       _WINDOW_HEIGHT - 1, "", _WINDOW_HEIGHT - 1, "", _WINDOW_HEIGHT),
      # If the current line under the cursor is truncated, cursor should move.
      ("no_scroll_to_buttom_truncate", True,
       0, f"Line {_BATCH_1_NUM_LINES - (_WINDOW_HEIGHT - 1)}",  # "Line 1"
       0, f"Line {_TOTAL_NUM_LINES - (_WINDOW_HEIGHT - 1)}",  # "Line 11"
       _WINDOW_HEIGHT))
  def test_text_area_append_text(
      self, move_cursor: bool,
      row_after_batch_1: int, line_after_batch_1: str,
      row_after_batch_2: int, line_after_batch_2: str,
      max_size: int):
    """Tests appending text and the resulting cursor motion.

    Writes a batch of log lines, optionally moves the cursor to the first line,
    and writes another batch of log lines. Asserts that the line under the
    cursor matches the expectation after each batch.

    Args:
      move_cursor: Whether to move the cursor to the first line after writing
        the first batch of log lines.
      row_after_batch_1: Expected cursor row after the first batch of logs is
        written and (optionally) the cursor is moved.
      line_after_batch_1: Expected line under the cursor after the first batch.
      row_after_batch_2: Expected cursor row after the second batch of logs is
        written.
      line_after_batch_2: Expected line under the cursor after the second batch.
      max_size: Maximum number of lines the text area can contain.
    """
    with mock.patch.object(console, "_MAX_TEXT_AREA_LINES", new=max_size):
      textarea = console._AppendableTextArea(
          text="",
          focusable=True,
          read_only=True,
          line_numbers=True,
          scrollbar=True,
          width=80,  # Wide enough for log lines to fit without wrapping.
          height=_WINDOW_HEIGHT,  # Not tall enough to display all log lines.
      )
      line_template = "Line {}\n"

      for i in range(_BATCH_1_NUM_LINES):
        textarea.append_text(line_template.format(i))
      if move_cursor:
        textarea.document = document.Document(textarea.text, 0)
      self.assertEqual(textarea.document.cursor_position_row, row_after_batch_1)
      self.assertEqual(textarea.document.current_line, line_after_batch_1)

      for i in range(_BATCH_1_NUM_LINES, _TOTAL_NUM_LINES):
        textarea.append_text(line_template.format(i))
      self.assertEqual(textarea.document.cursor_position_row, row_after_batch_2)
      self.assertEqual(textarea.document.current_line, line_after_batch_2)

      if max_size < _TOTAL_NUM_LINES:  # Check that lines get truncated.
        for i in range(_TOTAL_NUM_LINES - max_size):
          self.assertNotIn(line_template.format(i), textarea.text)

  def test_help_window_visibility(self):
    """Tests _HelpWindowVisibility controls."""
    focus_element_on_show = mock.MagicMock()
    focus_element_on_hide = mock.MagicMock()
    window_visibility = console._HelpWindowVisibility(
        focus_element_on_show=focus_element_on_show,
        focus_element_on_hide=focus_element_on_hide)
    with mock.patch.object(application_current, "get_app") as mock_get_app:
      focus = mock_get_app.return_value.layout.focus
      self.assertFalse(
          window_visibility.is_visible(),
          "Help window should not be visible at the start.")
      focus.assert_not_called()

      window_visibility.show()
      focus.assert_called_with(focus_element_on_show)
      self.assertTrue(
          window_visibility.is_visible(),
          "Help window should be visible after .show() is called.")

      window_visibility.hide()
      focus.assert_called_with(focus_element_on_hide)
      self.assertFalse(
          window_visibility.is_visible(),
          "Help window should not be visible after .hide() is called.")

  def test_process_logs(self):
    """Tests that log lines are transformed and added to appropriate windows."""
    raw_logs = [
        ("<2021-07-27 07:13:32.123456> GDM-M: Note: device-1234 switchboard "
         "successfully started.\n"),
        ("<2021-07-27 07:13:32.885288> GDM-M: Note: wrote command "
         "'which curl;echo Return Code: $?\n' to port 0\n"),
        "<2021-07-27 07:13:32.882359> GDM-1: Some log line\n",
        "<2021-07-27 07:13:32.882359> GDM-8: Unknown transport line\n",
        "<2021-07-27 07:13:32.919486> GDM-0: /bin/curl\n",
        "<2021-07-27 07:13:32.875740> GDM-0: Return Code: 0\n",
        "which curl;echo Return Code: $?\n",
    ]
    manager_log = (  # "GDM-M" should get replaced with "GDM".
        "<2021-07-27 07:13:32.123456> GDM: device-1234 switchboard "
        "successfully started.\n"
        "<2021-07-27 07:13:32.885288> GDM: wrote command "
        "'which curl;echo Return Code: $?\n' to port 0\n"
    )
    device_response = (  # "GDM-0: " should get stripped.
        "<2021-07-27 07:13:32.919486> /bin/curl\n"
        "<2021-07-27 07:13:32.875740> Return Code: 0\n"
    )
    device_log = (  # "GDM-1: " should get stripped.
        "<2021-07-27 07:13:32.882359> Some log line\n"
    )
    unknown_transport_log = (
        "<2021-07-27 07:13:32.882359> Unknown transport line\n")
    echoed_inputs = (  # Some devices echo back the received characters.
        "which curl;echo Return Code: $?\n"
    )
    text_areas = list(self.uut._window_id_to_text_area.values())
    input_area, response_area, log_area = text_areas
    self.assertFalse(input_area.text)
    self.assertFalse(response_area.text)
    self.assertFalse(log_area.text)

    with mock.patch.object(console.logger, "debug") as mock_debug:
      self.uut._process_device_logs(raw_logs)

    self.assertFalse(input_area.text)

    # The "GDM-8" log line should be dropped and go to logger.debug() instead.
    mock_debug.assert_called()
    debug_log_line = mock_debug.call_args[0][0]
    self.assertIn("Unable to display text", debug_log_line)
    self.assertIn(repr(unknown_transport_log), debug_log_line)

    self.assertIn(manager_log, response_area.text)
    self.assertIn(device_response, response_area.text)
    self.assertNotIn(device_log, response_area.text)
    self.assertIn(echoed_inputs, response_area.text)
    self.assertNotIn(unknown_transport_log, response_area.text)

    self.assertNotIn(manager_log, log_area.text)
    self.assertNotIn(device_response, log_area.text)
    self.assertIn(device_log, log_area.text)
    self.assertNotIn(echoed_inputs, log_area.text)
    self.assertNotIn(unknown_transport_log, log_area.text)

  @mock.patch.object(builtins, "open")
  @mock.patch.object(asyncio, "get_event_loop")
  @mock.patch.object(asyncio, "set_event_loop")
  @mock.patch.object(inputhook, "set_eventloop_with_inputhook")
  def test_run(
      self, mock_set_inputhook, mock_set_loop, mock_get_loop, mock_open):
    """Tests that running the console adds and removes the input hook."""
    with mock.patch.object(self.uut._application, "run") as mock_app_run:
      self.uut.run()
    mock_open.assert_called_once_with(self.device_log_file)
    mock_get_loop.assert_called()
    mock_set_inputhook.assert_called_once_with(self.uut._input_hook)
    mock_app_run.assert_called_once()
    mock_set_loop.assert_called_with(mock_get_loop.return_value)

  def test_switchboard_buttons(self):
    """Tests that Switchboard buttons are added to the menu."""
    self.assertIsNotNone(self.uut._button_dropdown)
    button_names = [menu_item.text
                    for menu_item in self.uut._button_dropdown.children]
    self.assertCountEqual(button_names, self.button_map.keys())

  def test_no_switchboard_buttons(self):
    """Tests that there's no button menu when there are no buttons."""
    self.switchboard.button_list = []
    uut = console.ConsoleApp(
        self.switchboard,
        self.device_log_file,
        self.config)
    self.assertIsNone(uut._button_dropdown)


if __name__ == "__main__":
  unit_test_case.main()
