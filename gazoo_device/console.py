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

"""Interactive console to replace direct device I/O such as ADB, SSH, Kermit."""
import asyncio
import collections
import re
from typing import Optional, Sequence, Tuple

from gazoo_device import console_config
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import switchboard_base
from prompt_toolkit import application
from prompt_toolkit import buffer
from prompt_toolkit import document
from prompt_toolkit import enums
from prompt_toolkit import filters
from prompt_toolkit import input as prompt_toolkit_input
from prompt_toolkit import key_binding
from prompt_toolkit import output
from prompt_toolkit import styles
from prompt_toolkit import widgets
from prompt_toolkit.application import current as application_current
from prompt_toolkit.eventloop import inputhook
from prompt_toolkit.key_binding.bindings import focus
from prompt_toolkit.layout import containers
from prompt_toolkit.layout import layout

logger = gdm_logger.get_logger()

_HELP_TEXT = """Application-level controls:
  Tab: move focus to the next window.
  Shift-Tab: move focus to the previous window.
  Mouse selection: select text to copy.
  Cmd-C/Win-C: copy selected text to the system clipboard.

Menu navigation controls:
  Use arrow keys to move between menu items.
  Use Enter to select the current menu item.

To close the console:
  Select the "Exit" menu button.

Command input window keys:
  Enter: send the contents of the input window to the device.
  Ctrl-C: clear the input window and interrupt the currently running command.
  Up/down arrow: select a command from history.
  Cmd-V/Win-V: paste system clipboard contents.
  Other keys (Left/Right Arrow, Page Up/Down, Backspace, Delete, characters):
    same as a typical text editor.

Command response and log window keys:
  Cursor controls:
    Arrow keys: move the cursor.
    vi-style key bindings can also be used to move the cursor. For example:
      gg: go to the beginning of text.
      G: go to the end of text.
    TODO(b/194440944): add an option for Emacs key bindings.

  Search controls:
    /: open forward search prompt.
    ?: open backward search prompt.
    Enter: perform the search.
    Esc: close the search prompt.
    n: go to the next match.
    N: go to the previous match.

Press Enter to close this window."""
_HELP_TEXT_WIDTH = 80
_MAX_TEXT_AREA_LINES = 100000


def _do_exit() -> None:
  application_current.get_app().exit()


class _AppendableTextArea(widgets.TextArea):
  """TextArea which allows appending text and automatically scrolls down."""

  def append_text(self, text_to_append: str) -> None:
    """Appends text_to_append to the text area."""
    new_text = self.text + text_to_append
    if not self.document.on_last_line:
      # Do not scroll down to latest log line if user is searching through logs.
      new_cursor_position = self.document.cursor_position
    else:
      new_cursor_position = len(new_text)
    self.document = document.Document(new_text, new_cursor_position)
    self.truncate_text()

  def truncate_text(self) -> None:
    """Drops the least recent lines if text size exceeds the maximum limit."""
    if self.document.line_count > _MAX_TEXT_AREA_LINES:
      num_lines_to_drop = self.document.line_count - _MAX_TEXT_AREA_LINES
      new_text = "\n".join(self.document.lines[num_lines_to_drop:])
      cursor_offset = (
          sum(len(line) for line in self.document.lines[:num_lines_to_drop])
          + num_lines_to_drop)  # To account for newline characters.
      if self.document.cursor_position >= cursor_offset:
        new_cursor_position = self.document.cursor_position - cursor_offset
      else:
        # If dropping lines at the current cursor position, imitate cursor
        # motion from pressing "down" several times.
        num_down_presses = num_lines_to_drop - self.document.cursor_position_row
        new_cursor_position = (
            self.document.cursor_position
            + self.document.get_cursor_down_position(num_down_presses)
            - cursor_offset)
      self.document = document.Document(new_text, new_cursor_position)


class _HelpWindowVisibility:
  """Controls for help window visibility."""

  def __init__(
      self,
      focus_element_on_show: Optional[containers.AnyContainer] = None,
      focus_element_on_hide: Optional[containers.AnyContainer] = None) -> None:
    self._visible = False
    self.focus_element_on_show = focus_element_on_show
    self.focus_element_on_hide = focus_element_on_hide

  def show(self) -> None:
    self._visible = True
    if self.focus_element_on_show:
      application_current.get_app().layout.focus(self.focus_element_on_show)

  def hide(self) -> None:
    self._visible = False
    if self.focus_element_on_hide:
      application_current.get_app().layout.focus(self.focus_element_on_hide)

  def is_visible(self) -> bool:
    return self._visible


def _make_button_menu_item(
    button_name: str,
    switchboard_inst: switchboard_base.SwitchboardBase,
    menu_container: widgets.MenuContainer) -> widgets.MenuItem:
  """Creates a menu item corresponding to a button."""
  button_menu_item = widgets.MenuItem(button_name)

  def button_handler() -> None:
    """Toggles the button and updates the button menu item text."""
    pressed_suffix = " (pressed)"
    is_pressed = button_menu_item.text.endswith(pressed_suffix)
    if is_pressed:
      switchboard_inst.release(button_name)
      button_menu_item.text = button_name
    else:
      switchboard_inst.press(button_name)
      button_menu_item.text = button_name + pressed_suffix
    # Clicking a menu item closes the menu by default and moves focus elsewhere.
    # Button press is a 2-step sequence (press & release), so don't close the
    # menu on button item clicks (by manually refocusing the menu container).
    application_current.get_app().layout.focus(menu_container.window)

  button_menu_item.handler = button_handler
  return button_menu_item


def _make_ui_window(
    window: console_config.WindowType,
    switchboard_inst: switchboard_base.SwitchboardBase
) -> Tuple[widgets.TextArea, widgets.Frame]:
  """Creates a text area and an enclosing frame.

  Args:
    window: Console window description.
    switchboard_inst: Switchboard capability instance.

  Returns:
    A tuple containing the window's text area and its enclosing UI frame.
  """
  if isinstance(window, console_config.CommandInputWindow):

    def handle_command_input(input_buffer: buffer.Buffer) -> None:
      command = input_buffer.text
      switchboard_inst.send(command, port=window.transport)

    command_input_area = widgets.TextArea(
        text="",
        multiline=False,
        accept_handler=handle_command_input,
        history=None,
        focusable=True,
        read_only=False,
        get_line_prefix=lambda line_num, wrap_count: " > "
    )
    command_input_area_bindings = key_binding.KeyBindings()

    @command_input_area_bindings.add("c-c")
    def _handle_control_c(event) -> None:  # pylint: disable=unused-variable
      del event  # Unused.
      command_input_area.text = ""
      if window.reopen_transport_on_ctrl_c:
        switchboard_inst.add_log_note(
            "The transport is running in non-interactive mode. "
            "Ctrl-C keystrokes are ignored by the device. "
            "Reopening the command transport as a workaround. "
            "Shell environment variables will be lost.")
        switchboard_inst.close_transport(port=window.transport)
        switchboard_inst.open_transport(port=window.transport)
      else:
        switchboard_inst.send(b"\x03", port=window.transport)

    command_input_area.control.key_bindings = command_input_area_bindings
    command_input_frame = widgets.Frame(
        body=command_input_area,
        title=window.name)
    return command_input_area, command_input_frame

  else:  # CommandResponseWindow or LogWindow
    search_toolbar = widgets.SearchToolbar()
    text_area = _AppendableTextArea(
        text="",
        focusable=True,
        read_only=True,
        line_numbers=True,
        scrollbar=True,
        search_field=search_toolbar,
    )
    text_area.window.ignore_content_height = lambda: True
    frame = widgets.Frame(
        body=containers.HSplit([
            text_area,
            search_toolbar,
        ]),
        title=window.name)
    return text_area, frame


class ConsoleApp:
  """Prompt_toolkit console application."""

  def __init__(
      self,
      switchboard_inst: switchboard_base.SwitchboardBase,
      device_log_file_name: str,
      configuration: console_config.ConsoleConfiguration,
      console_input: Optional[prompt_toolkit_input.Input] = None,
      console_output: Optional[output.Output] = None) -> None:
    """Initializes a prompt_toolkit console application.

    Args:
      switchboard_inst: Switchboard capability instance.
      device_log_file_name: The device log file to read (stream) logs from.
      configuration: Console configuration.
      console_input: Console input. Defaults to stdin.
      console_output: Console output. Defaults to stdout.
    """
    self._device_log_file_name = device_log_file_name
    self._window_line_transforms = configuration.window_line_transforms
    self._line_to_window_id = configuration.line_to_window_id
    self._log_file = None  # Set by run().

    body_frames = []
    self._window_id_to_text_area = collections.OrderedDict()
    for window in configuration.windows:
      text_area, enclosing_frame = _make_ui_window(window, switchboard_inst)
      self._window_id_to_text_area[window.window_id] = text_area
      body_frames.append(enclosing_frame)

    self._menu_exit_item = widgets.MenuItem("Exit", handler=_do_exit)
    if body_frames:
      self._default_focused_element = body_frames[0]
    else:
      self._default_focused_element = self._menu_exit_item
    help_window_visibility = _HelpWindowVisibility(
        focus_element_on_hide=self._default_focused_element)
    close_help_button = widgets.Button(
        text="Ok",
        handler=help_window_visibility.hide)
    help_window_visibility.focus_element_on_show = close_help_button
    help_float_dialog = containers.Float(
        containers.ConditionalContainer(
            content=widgets.Dialog(
                title="Console help",
                body=widgets.TextArea(
                    text=_HELP_TEXT,
                    focusable=True,
                    read_only=True,
                    scrollbar=True,
                    width=_HELP_TEXT_WIDTH,
                ),
                buttons=[close_help_button],
            ),
            filter=filters.Condition(help_window_visibility.is_visible),
        ),
    )

    root_container = widgets.MenuContainer(
        body=containers.FloatContainer(
            content=containers.HSplit(body_frames),
            floats=[help_float_dialog],
        ),
        menu_items=[
            self._menu_exit_item,
            widgets.MenuItem("Help", handler=help_window_visibility.show),
        ],
    )

    button_list = switchboard_inst.button_list
    button_names = button_list[0].valid_buttons() if button_list else []
    if button_names:
      button_menu_items = [
          _make_button_menu_item(button_name, switchboard_inst, root_container)
          for button_name in button_names
      ]
      self._button_dropdown = widgets.MenuItem(
          "Buttons", children=button_menu_items)
      root_container.menu_items.append(self._button_dropdown)
    else:
      self._button_dropdown = None

    # Global key bindings.
    bindings = key_binding.KeyBindings()
    bindings.add("tab")(focus.focus_next)
    bindings.add("s-tab")(focus.focus_previous)

    style = styles.Style.from_dict({
        "menu-bar": "bg:#aaaaaa #888888",
    })

    self._application = application.Application(
        layout=layout.Layout(
            container=root_container,
            focused_element=self._default_focused_element,
        ),
        style=style,
        full_screen=True,
        key_bindings=bindings,
        editing_mode=enums.EditingMode.VI,
        input=console_input,
        output=console_output,
    )

  def run(self) -> None:
    """Runs the console application until completion."""
    with open(self._device_log_file_name) as log_file:
      self._log_file = log_file
      eventloop_before = asyncio.get_event_loop()
      try:
        inputhook.set_eventloop_with_inputhook(self._input_hook)
        self._application.run()
      finally:
        asyncio.set_event_loop(eventloop_before)  # Remove the input hook.
        self._log_file = None

  def _add_text_to_window(self, text: str, window_id: int) -> None:
    """Adds text to the specified console window.

    If there's no console window with the given window_id, the text is dropped.

    Args:
      text: Text to add.
      window_id: ID of the window to add the text to.
    """
    if window_id not in self._window_id_to_text_area:
      logger.debug(f"There is no console window with ID {window_id}. "
                   f"Unable to display text: {text!r}.")
      return

    text_area = self._window_id_to_text_area[window_id]
    if isinstance(text_area, _AppendableTextArea):
      text_area.append_text(text)
    else:
      new_text = text_area.text + text
      text_area.document = document.Document(new_text, len(new_text))

  def _input_hook(self, input_hook_context: inputhook.InputHookContext) -> None:
    """Connects external I/O (device log file) to prompt_toolkit.

    Args:
      input_hook_context: Input hook context passed from prompt_toolkit. Unused.
    """
    del input_hook_context  # Unused.
    # Input hooks are supposed to yield control to the GUI event loop whenever
    # the GUI event loop has something to process. However, it seems that
    # efficiently processing all available log lines whenever they are available
    # works better than trying to yield control (which is expensive due to
    # overhead?). This implementation has to run quickly so that the GUI event
    # loop is not blocked for long. Note that this input hook is only called
    # from the GUI event loop whenever the event loop is idle.
    new_logs = self._log_file.readlines()
    self._process_device_logs(new_logs)

  def _process_device_logs(self, lines: Sequence[str]) -> None:
    """Appends device log files lines to appropriate console windows.

    Updating text windows is expensive, likely O(current_window_size). We can
    speed up the process by processing all logs in a batch and calling update
    for each window only once. This only really matters during startup, where
    thousands of log lines can be read immediately, and an inefficient
    implementation could block the UI for a few seconds.

    Args:
      lines: Text lines read from the device log file.
    """
    window_to_lines = {}
    for log_or_command_line in lines:
      window_id = self._line_to_window_id(log_or_command_line)
      if window_id not in window_to_lines:
        window_to_lines[window_id] = []
      window_to_lines[window_id].append(log_or_command_line)
    for window_id, lines in window_to_lines.items():
      transformed_lines = []
      for line in lines:
        transformed_line = line
        for before_regex, replacement in self._window_line_transforms:
          transformed_line = re.sub(before_regex, replacement, transformed_line)
        transformed_lines.append(transformed_line)
      # Lines are assumed to end in newline characters.
      self._add_text_to_window("".join(transformed_lines), window_id)
