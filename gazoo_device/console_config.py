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

"""Configuration for the interactive console (console.py)."""
import dataclasses
import re
from typing import Callable, Sequence, Tuple, Type, Union

from gazoo_device.switchboard import line_identifier
from gazoo_device.switchboard import log_process


@dataclasses.dataclass(frozen=True)
class _Window:
  """Configuration for a single console window."""
  name: str  # Window title.
  window_id: int  # Unique ID.


@dataclasses.dataclass(frozen=True)
class CommandResponseWindow(_Window):
  """Configuration for a command & response console window."""


@dataclasses.dataclass(frozen=True)
class LogWindow(_Window):
  """Configuration for a log console window."""


@dataclasses.dataclass(frozen=True)
class CommandInputWindow(_Window):
  """Configuration for a command input console window."""
  # Transport number to send commands to.
  transport: int
  # If True, handle Ctrl-C by reopening the transport instead of sending Ctrl-C
  # to the device as a workaround for ADB and SSH ignoring Ctrl-C keystrokes in
  # non-interactive mode (b/194440950).
  reopen_transport_on_ctrl_c: bool = False

WindowType = Union[CommandResponseWindow, LogWindow, CommandInputWindow]

_DEFAULT_LINE_TRANSFORMS = (  # (Before_regex, replacement string) tuples.
    ("GDM-M: Note", "GDM"),
    (r"GDM-\d: ", ""),
)
_LOG_LINE_PREFIX_LENGTH = (
    log_process.LOG_LINE_HEADER_LENGTH + log_process.HOST_TIMESTAMP_LENGTH)


@dataclasses.dataclass(frozen=True)
class ConsoleConfiguration:
  """Interactive console configuration."""
  # Console window arrangement. Windows are stacked vertically with the first
  # sequence element rendered at the top.
  windows: Sequence[WindowType]
  # Function which accepts a log line and returns the ID of the console window
  # to which this log line should be appended.
  line_to_window_id: Callable[[str], int]
  # Transformations to apply to each line. Transformations are applied in order.
  # Each transformation is defined by a regex pattern and a corresponding
  # replacement string.
  window_line_transforms: Sequence[Tuple[str, str]] = _DEFAULT_LINE_TRANSFORMS

  def __post_init__(self) -> None:
    """Validates the provided window arrangement.

    Raises:
      ValueError: If window IDs are not unique.
    """
    ids = [window.window_id for window in self.windows]
    if len(set(ids)) != len(ids):
      raise ValueError(f"Window IDs {ids} are not unique")


def calculate_window_id(
    transport_num: int, window_class: Type[WindowType]) -> int:
  """Returns a unique window ID.

  window_id numbering scheme does not depend on the number of windows present.
  This allows us to reuse the same line_to_window_id logic for window
  configurations with different numbers of windows.

  Args:
    transport_num: Switchboard transport number.
    window_class: Type of the window, which determines its offset.
  """
  max_windows_per_transport = 3
  if window_class is CommandInputWindow:
    offset = 0
  elif window_class is CommandResponseWindow:
    offset = 1
  else:  # LogWindow
    offset = 2
  return max_windows_per_transport * transport_num + offset


def make_line_to_window_id(
    windows: Sequence[WindowType],
    device_line_identifier: line_identifier.LineIdentifier
) -> Callable[[str], int]:
  """Creates a line_to_window_id callable for the given configuration."""
  first_non_input_window_id = next(
      window.window_id for window in windows
      if not isinstance(window, CommandInputWindow))

  def line_to_window_id(log_or_command_line: str) -> int:
    """Returns the window ID of the window which should contain the line."""
    port_match = re.search(r" GDM-(\d): ", log_or_command_line)
    if not port_match:  # It's an "GDM-M" line.
      send_port_match = re.search(
          r"wrote command.*to port (\d)", log_or_command_line)
      if send_port_match:
        port = int(send_port_match.group(1))
        window_id = calculate_window_id(port, CommandResponseWindow)
      else:
        window_id = first_non_input_window_id
    else:
      port = int(port_match.group(1))
      line = log_or_command_line[_LOG_LINE_PREFIX_LENGTH:]
      is_response = device_line_identifier.accept(
          port, line, line_identifier.LINE_TYPE_RESPONSE)
      is_log = device_line_identifier.accept(
          port, line, line_identifier.LINE_TYPE_LOG)
      if is_response:
        window_type = CommandResponseWindow
      elif is_log:
        window_type = LogWindow
      else:  # Unidentified lines are typically echoed inputs.
        window_type = CommandResponseWindow
      window_id = calculate_window_id(port, window_type)
    return window_id

  return line_to_window_id


# Helper functions for creation of common console configurations.
def get_log_response_separate_port_configuration(
    device_line_identifier: line_identifier.LineIdentifier,
    input_window_name: str = "Command input",
    response_window_name: str = "Commands & responses",
    log_window_name: str = "Logs",
    reopen_command_transport_on_ctrl_c: bool = True) -> ConsoleConfiguration:
  """Returns a configuration where port 0 is for commands and 1 is for logs."""
  windows = (
      CommandInputWindow(
          name=input_window_name,
          window_id=calculate_window_id(0, CommandInputWindow),
          transport=0,
          reopen_transport_on_ctrl_c=reopen_command_transport_on_ctrl_c),
      CommandResponseWindow(
          name=response_window_name,
          window_id=calculate_window_id(0, CommandResponseWindow)),
      LogWindow(
          name=log_window_name,
          window_id=calculate_window_id(1, LogWindow)),
  )
  return ConsoleConfiguration(
      windows=windows,
      line_to_window_id=make_line_to_window_id(windows, device_line_identifier),
  )


def get_log_response_same_port_configuration(
    device_line_identifier: line_identifier.LineIdentifier,
    input_window_name: str = "Command input (port 0)",
    response_window_name: str = "Commands & responses (port 0)",
    log_window_name: str = "Logs (port 0)",
    enable_secondary: bool = False,
    secondary_input_window_name: str = "Command input (port 1)",
    secondary_response_window_name: str = "Commands & responses (port 1)",
    secondary_log_window_name: str = "Logs (port 1)") -> ConsoleConfiguration:
  """Returns a configuration where each port is used for logs and responses."""
  windows = (
      CommandInputWindow(
          name=input_window_name,
          window_id=calculate_window_id(0, CommandInputWindow),
          transport=0),
      CommandResponseWindow(
          name=response_window_name,
          window_id=calculate_window_id(0, CommandResponseWindow)),
      LogWindow(
          name=log_window_name,
          window_id=calculate_window_id(0, LogWindow)),
  )
  if enable_secondary:
    windows += (
        CommandInputWindow(
            name=secondary_input_window_name,
            window_id=calculate_window_id(1, CommandInputWindow),
            transport=1),
        CommandResponseWindow(
            name=secondary_response_window_name,
            window_id=calculate_window_id(1, CommandResponseWindow)),
        LogWindow(
            name=secondary_log_window_name,
            window_id=calculate_window_id(1, LogWindow)),
    )

  return ConsoleConfiguration(
      windows=windows,
      line_to_window_id=make_line_to_window_id(windows, device_line_identifier),
  )


def get_log_only_configuration(
    log_window_name: str = "Logs") -> ConsoleConfiguration:
  """Returns a configuration where only logs from port 0 are shown."""
  log_window_id = calculate_window_id(0, LogWindow)
  return ConsoleConfiguration(
      windows=(
          LogWindow(name=log_window_name, window_id=log_window_id),
      ),
      line_to_window_id=lambda line: log_window_id,  # There's only 1 window.
  )

