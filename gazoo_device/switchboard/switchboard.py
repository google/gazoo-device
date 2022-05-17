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
"""Switchboard capability implementation.

Switchboard is the backbone of all device interaction.
It provides the ability to interact with devices using standardized transport,
button, and expect APIs.

By separating these standardized APIs we can more easily test the logic and
eventually unit test device classes independent of hardware.
"""
import io
import os
import queue
import re
import signal
import subprocess
import time
import types
import typing
from typing import Any, Callable, Dict, List, Mapping, MutableSequence, Optional, Sequence, Tuple, Union

from gazoo_device import config
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device import log_parser
from gazoo_device.capabilities.interfaces import switchboard_base
from gazoo_device.switchboard import data_framer
from gazoo_device.switchboard import expect_response
from gazoo_device.switchboard import line_identifier
from gazoo_device.switchboard import log_process
from gazoo_device.switchboard import switchboard_process
from gazoo_device.switchboard import transport_process
from gazoo_device.switchboard import transport_properties
from gazoo_device.switchboard.transports import jlink_transport
from gazoo_device.switchboard.transports import serial_transport
from gazoo_device.switchboard.transports import tcp_transport
from gazoo_device.switchboard.transports import transport_base
from gazoo_device.utility import multiprocessing_utils
from gazoo_device.utility import usb_utils
from typing_extensions import Protocol
import xmodem

logger = gdm_logger.get_logger("core")

MODE_TYPE_ALL = switchboard_base.MODE_TYPE_ALL
MODE_TYPE_ANY = switchboard_base.MODE_TYPE_ANY
MODE_TYPE_SEQUENTIAL = switchboard_base.MODE_TYPE_SEQUENTIAL
VERIFY_METHOD_MD5SUM = switchboard_base.VERIFY_METHOD_MD5SUM
_VALID_EXPECT_TYPES = [
    line_identifier.LINE_TYPE_ALL, line_identifier.LINE_TYPE_LOG,
    line_identifier.LINE_TYPE_RESPONSE
]
_VALID_EXPECT_MODES = [MODE_TYPE_ALL, MODE_TYPE_ANY, MODE_TYPE_SEQUENTIAL]
_VERIFY_METHODS = [VERIFY_METHOD_MD5SUM]


class ButtonInterface(Protocol):
  """Interface for buttons."""

  def close(self):
    """Release any held buttons on close."""

  def is_valid(self, button: str) -> bool:
    """Return True if button specified is in the list of valid buttons."""

  def press(self, button: str, wait: float = 0.0) -> None:
    """Presses button and waits for the time specified."""

  def click(self, button: str, duration: float = .5) -> None:
    """Presses the button specified and holds it for the specified duration."""

  def release(self, button: str) -> None:
    """Releases the button specified if it was previously pressed."""

  def valid_buttons(self) -> List[str]:
    """Returns a list of valid button names."""


def _ensure_has_newline(cmd: str,
                        add_newline: bool = True,
                        newline: str = "\n") -> str:
  """Ensure command ends with a newline (if add_newline is True)."""
  if add_newline and not cmd.endswith(("\n", "\x00", r"\0", newline)):
    cmd += newline
  return cmd


def _get_pattern_index(compiled_list: Sequence[re.Pattern],
                       match_list: Sequence[re.Match],
                       mode: str) -> Optional[int]:
  """Return index of compiled regex pattern that matches the match provided.

  Args:
      compiled_list: of regular expression patterns to match
      match_list: of Match objects previously found
      mode: type of expect to use ("any", "all", or "sequential")

  Returns:
      The index to a matching compile regex pattern in compiled_list
      that matches the last entry added to match_list or None if no
      match was found.
  """
  if match_list:
    if mode == MODE_TYPE_SEQUENTIAL:
      return len(match_list) - 1
    else:
      for index, pattern in enumerate(compiled_list):
        if pattern == match_list[-1].re:
          return index
  return None


def _get_pattern_list(compiled_list: Sequence[re.Pattern],
                      match_list: Sequence[re.Match],
                      mode: str) -> Sequence[re.Pattern]:
  """Returns pattern_list to be used in expect search using information provided.

  Args:
      compiled_list: of regular expression patterns
      match_list: of Match objects previously found
      mode: type of expect to use ("any", "all", or "sequential")

  Returns:
      A list of compiled regular expression patterns from compiled_list
      to use for the next round of pattern searches according to the
      mode specified.

  Note:
      The primary difference between expect type modes is what pattern list
      should be used. For any, the whole list should be returned every time
      until one match is found. For all, only the remaining unmatched
      patterns should be returned. For sequential, only the first of the
      remaining unmatched patterns should be returned.
  """

  if mode == MODE_TYPE_ANY:
    return compiled_list
  missing_patterns = _get_missing_patterns(compiled_list, match_list, mode)
  if mode == MODE_TYPE_ALL:
    return missing_patterns
  return [missing_patterns[0]]


def _get_missing_patterns(compiled_list: Sequence[re.Pattern],
                          match_list: Sequence[re.Match],
                          mode: str) -> Sequence[re.Pattern]:
  """Returns compiled regex patterns from compiled_list that are not in match_list.

  Args:
      compiled_list: of regular expression patterns
      match_list: of Match objects previously found
      mode: type of expect to use ("any", "all", or "sequential")

  Returns:
      list: A list of compiled regex patterns from compiled_list that are not
            in match_list.
  """
  if mode == MODE_TYPE_SEQUENTIAL:
    return compiled_list[len(match_list):]
  else:
    matched_patterns = [match.re for match in match_list]
    return [
        pattern for pattern in compiled_list if pattern not in matched_patterns
    ]


def _get_pattern_strings(compiled_list: Sequence[re.Pattern]) -> List[str]:
  """Returns regex pattern strings from a list of compiled regex pattern objects.

  Args:
      compiled_list: of regular expression patterns to extract strings from

  Returns:
      A list of regex pattern strings extracted from compiled list of
      regex pattern objects.
  """
  return [str(pattern.pattern) for pattern in compiled_list]


class SwitchboardDefault(switchboard_base.SwitchboardBase):
  """Manages device interactions and writes everything to a single file.

  This will spawn and manage 3 or more multiprocess subprocesses:
      Process 0 (Main)
          The primary process where the API/CLI/tests execute from;
          responsible for initializing this module for each device. Performs
          expect and Parser logic and closes subprocesses on shutdown or
          transport errors.

      Process 1..n (Transport)
          One or more subprocesses responsible for performing all device
          transport operations (e.g. open/close and read/write) and
          communicating results to other subprocesses as needed using
          queues.

      Process n+1 (Log writer)
          Performs all log writing operations received from log queue
          shared with Transport subprocess. Log lines are written only for
          completed log lines.

      Process n+2 (Log filter)
          Reads log lines from the log file written by the log writer
          subprocess. Filters each log line read for desired events and
          writes them to an event file. The main process can then use the
          event file to query for relevant events.
  """

  def __init__(
      self,
      device_name: str,
      exception_queue: queue.Queue,
      transport_list: List[transport_base.TransportBase],
      log_path: str,
      framer_list: Optional[List[data_framer.DataFramer]] = None,
      identifier: Optional[line_identifier.LineIdentifier] = None,
      button_list: Optional[ButtonInterface] = None,
      parser: Optional[log_parser.LogParser] = None,
      partial_line_timeout_list: Optional[List[int]] = None,
      force_slow: bool = False,
      max_log_size: int = 0,
  ):
    """Initialize the Switchboard with the parameters provided.

    Args:
      device_name: name of the device
      exception_queue: a single exception queue to share for all subprocesses to
        report exceptions into
      transport_list: of Transport type classes to use for this device.
      log_path: path/to/log/file to store device logs
      framer_list: list of DataFramer derived classes to use to frame incoming
        raw data into raw lines.
      identifier: LineIdentifier derived class to use to identify log and
        response lines from device for expect_type filtering.
      button_list: of Button type classes to use to click, press, release,
        is_valid, valid_buttons, and close methods defined for button
        instigation, button name verification and listing, and closing.
      parser: log filtering object
      partial_line_timeout_list: of seconds to wait before writing partial
        transport line received for each transport.
      force_slow: flag indicating all sends should assume slow=True.
      max_log_size: maximum size in bytes before performing log rotation.
        max_log_size of 0 means no log rotation should ever occur.
    """
    super().__init__(device_name=device_name)
    if framer_list is None:
      framer_list = []
    if partial_line_timeout_list is None:
      partial_line_timeout_list = []

    self.log_path = log_path
    self.button_list = button_list
    self._force_slow = force_slow
    self._identifier = identifier or line_identifier.AllUnknownIdentifier()
    time.sleep(.1)
    self._log_queue = multiprocessing_utils.get_context().Queue()
    self._call_result_queue = multiprocessing_utils.get_context().Queue()
    self._raw_data_queue = multiprocessing_utils.get_context().Queue()
    self._raw_data_queue_users = 0
    self._transport_process_id = 0
    self._exception_queue = exception_queue

    # Cache inputs for lazy initialization.
    self._transport_list = transport_list
    self._framer_list = framer_list
    self._partial_line_timeout_list = partial_line_timeout_list
    self._max_log_size = max_log_size
    self._parser = parser

    self._transport_processes_cache = []
    self._log_writer_process_cache = None
    self._log_filter_process_cache = None

    self._stored_health_check_error: Optional[Exception] = None

  def __del__(self):
    self.close()

  @decorators.CapabilityLogDecorator(logger, level=None)
  def add_log_note(self, note: str) -> None:
    """Adds given note to device log file.

    Args:
        note: to write to the log file
    """
    self.health_check()
    if note[-1] == "\n":
      log_message = "Note: {}".format(note)
    else:
      log_message = "Note: {}\n".format(note)
    try:
      log_process.log_message(self._log_queue, log_message, "M")
    except (AttributeError, IOError):  # manager shutdown or close called
      pass

  @decorators.CapabilityLogDecorator(logger, level=decorators.DEBUG)
  def add_new_filter(self, filter_path: str) -> None:
    """Adds new log filter at path specified to LogFilterProcess.

    Args:
        filter_path: filter file to add

    Raises:
        RuntimeError: if LogFilterProcess is not available or running.
        ValueError: if filter_path doesn't exist
    """
    if not os.path.exists(filter_path):
      raise ValueError("Filter path {} doesn't exist.".format(filter_path))

    if (not self._log_filter_process or
        not self._log_filter_process.is_running()):
      raise RuntimeError("Log filter process is not currently running.")

    self._log_filter_process.send_command(log_process.CMD_ADD_NEW_FILTER,
                                          filter_path)
    while (self._log_filter_process.is_running() and
           not self._log_filter_process.is_command_consumed()):
      time.sleep(0.001)

  def call(self,
           method: types.MethodType,
           method_args: Tuple[Any, ...] = (),
           method_kwargs: Optional[Dict[str, Any]] = None,
           port: int = 0) -> Any:
    """Calls a transport method in a transport process and returns the response.

    Args:
      method: the transport method to execute.
      method_args: positional arguments for the call.
      method_kwargs: keyword arguments for the call.
      port: number of the transport to call the method in.

    Raises:
      DeviceError: mismatching transport type.
      Exception: exceptions encountered in the transport process are reraised.

    Returns:
      object: return value of the transport method.

    Note that the call is executed in a different process. Therefore all
    transport method arguments and the return value must be serializable.
    """
    method_kwargs = method_kwargs or {}
    self._validate_port(port, self.call.__name__)
    class_name = method.__qualname__.split(".")[-2]
    method_name = method.__qualname__.split(".")[-1]
    transport_class_name = type(
        self._transport_processes[port].transport).__name__
    if (class_name != transport_base.TransportBase.__name__
        # All transports inherit from TransportBase
        and class_name != transport_class_name):
      raise errors.DeviceError(
          f"{self._device_name} Switchboard.call failed. "
          f"Requested method {method.__qualname__!r}, but transport {port} "
          f"is of type {transport_class_name!r}.")
    self.add_log_note("Executing {!r} in transport {}".format(
        method.__qualname__, port))
    self._transport_processes[port].send_command(
        transport_process.CMD_TRANSPORT_CALL,
        (method_name, method_args, method_kwargs))
    success, response = self._call_result_queue.get()
    if success:
      return response
    raise errors.DeviceError(
        f"{self._device_name} switchboard.call of method {method.__qualname__} "
        f"in transport {port} failed. {response}")

  def call_and_expect(
      self,
      method: types.MethodType,
      pattern_list: List[str],
      timeout: float = 30.0,
      searchwindowsize: int = config.SEARCHWINDOWSIZE,
      expect_type: str = line_identifier.LINE_TYPE_ALL,
      mode: str = MODE_TYPE_ANY,
      method_args: Tuple[Any, ...] = (),
      method_kwargs: Optional[Dict[str, Any]] = None,
      port: int = 0,
      raise_for_timeout: bool = False
  ) -> Tuple[expect_response.ExpectResponse, Any]:
    """Calls a transport method and expects on the patterns provided.

    Args:
        method: The transport method to execute.
        pattern_list: List of regex expressions to look for in the lines.
        timeout: Seconds to look for the patterns.
        searchwindowsize: Number of the last bytes to look at.
        expect_type: 'log', 'response', or 'all'.
        mode: Type of expect to run ("any", "all" or "sequential").
        method_args: Positional arguments for the call.
        method_kwargs: Keyword arguments for the call.
        port: Number of the transport to call the method in.
        raise_for_timeout: Raise an exception if the expect times out.

    Raises:
        DeviceError: if port specified or other expect arguments are
                     invalid, or timed out.

    Returns:
        (ExpectResponse, Returned value of the transport method)
    """
    expect_ret, func_ret = typing.cast(
        Tuple[expect_response.ExpectResponse, Any],
        self.do_and_expect(
            self.call, [method], {
                "method_args": method_args,
                "method_kwargs": method_kwargs,
                "port": port
            },
            pattern_list,
            timeout=timeout,
            searchwindowsize=searchwindowsize,
            expect_type=expect_type,
            mode=mode,
            include_func_response=True))
    if expect_ret and expect_ret.timedout and raise_for_timeout:
      raise errors.DeviceError(
          "Device {} call_and_expect timed out for method {} in {}s".format(
              self._device_name, method.__name__, timeout))
    return expect_ret, func_ret

  @decorators.CapabilityLogDecorator(logger)
  def click(self, button: str, duration: float = 0.5, port: int = 0) -> None:
    """Press and release the button for the duration and port specified.

    Args:
        button: button to press and release
        duration: seconds to wait before releasing button
        port: which port to click on, 0 or 1.

    Raises:
        DeviceError: If buttons are not supported on the device or
                     button, duration, or port values are invalid
    """
    self._check_button_args("click", button, port, duration=duration)

    log_message = "click button {} on port {} for duration {} - begin".format(
        button, port, duration)
    self.add_log_note(log_message)
    self.button_list[port].click(button, duration)
    log_message = "click button {} on port {} for duration {} - end".format(
        button, port, duration)
    self.add_log_note(log_message)

  def click_and_expect(
      self,
      button: str,
      pattern_list: List[str],
      duration: float = 0.5,
      timeout: float = 30.0,
      searchwindowsize: int = config.SEARCHWINDOWSIZE,
      expect_type: str = line_identifier.LINE_TYPE_ALL,
      port: int = 0,
      mode: str = MODE_TYPE_ANY,
      raise_for_timeout: bool = False) -> expect_response.ExpectResponse:
    """Press and release button, log lines matching patterns are returned.

    Flushes the expect queue before and after an expect. Starts up
    expect queue right before clicking button to catch fast responses.

    Args:
        button: button to press and release
        pattern_list: list of regex expressions to look for in the lines
        duration: seconds to press button before releasing it
        timeout: seconds to look for the patterns
        searchwindowsize: number of the last bytes to look at
        expect_type: 'log', 'response', or 'all'
        port: which port to send on, 0 or 1
        mode: type of expect to run ("any", "all" or "sequential")
        raise_for_timeout: Raise an exception if the expect times out

    Raises:
        DeviceError: If buttons are not supported on the device or
                     other arguments are invalid.

    Returns:
        ExpectResponse
    """
    return typing.cast(
        expect_response.ExpectResponse,
        self.do_and_expect(
            self.click, [button], {
                "duration": duration,
                "port": port
            },
            pattern_list,
            timeout=timeout,
            searchwindowsize=searchwindowsize,
            expect_type=expect_type,
            mode=mode,
            raise_for_timeout=raise_for_timeout))

  @decorators.CapabilityLogDecorator(logger, level=None)
  def close(self) -> None:
    """Shuts down child processes and closes the transports.

    All variables touched by this function should be the _cache type to avoid
    attempting to re-run health_checks.

    This is to support the case where switchboard health_check failed and a
    user wants to close/reset the switchboard and try again.
    """
    comms_addresses = [
        proc.transport.comms_address for proc in self._transport_processes_cache
    ]
    self._stop_processes()
    if hasattr(self, "button_list") and self.button_list:
      for button in self.button_list:
        button.close()
      self.button_list = []
    # Delete queues to release shared memory file descriptors.
    if hasattr(self, "_call_result_queue") and self._call_result_queue:
      delattr(self, "_call_result_queue")
    if hasattr(self, "_raw_data_queue") and self._raw_data_queue:
      delattr(self, "_raw_data_queue")
    if hasattr(self, "_log_queue") and self._log_queue:
      delattr(self, "_log_queue")
    if hasattr(self, "_exception_queue") and self._exception_queue:
      delattr(self, "_exception_queue")
    self.ensure_serial_paths_unlocked(comms_addresses)
    # Prevent switchboard from re-running health check after it's closed.
    self._healthy = False
    super().close()

  @decorators.CapabilityLogDecorator(logger)
  def close_all_transports(self) -> None:
    """Leaves the switchboard architecture intact but closes the communication FDs.

    This is used prior to the connections being closed,
    such as disconnecting an ethernet or a serial connection.
    Only closes the ones open so if device.close has already occurred,
    nothing will be closed.
    """
    for port in range(self.number_transports):
      self.close_transport(port=port)

  @decorators.CapabilityLogDecorator(logger, level=decorators.DEBUG)
  def close_transport(self, port=0):
    """Closes the transport specified.

    Args:
        port (int or str): the transport port to close

    Raises:
        DeviceError: If port value is invalid or out of range.
    """
    self._validate_port(port, self.close_transport.__name__)

    log_message = "closing transport for port {}".format(port)
    self.add_log_note(log_message)
    try:
      if self.button_list:
        button = self.button_list[port]
        button.close()
    except IndexError:
      # If button_list does not have an entry for [port], there is nothing to
      # close.
      pass

    start_time = time.time()
    transport_proc = self._transport_processes[port]
    transport_proc.send_command(transport_process.CMD_TRANSPORT_CLOSE)
    while transport_proc.is_open():
      time.sleep(0.01)
    log_message = "closed transport for port {} in {}s".format(
        port,
        time.time() - start_time)
    self.add_log_note(log_message)

  def do_and_expect(
      self,
      func: Callable[..., Any],
      func_args: Union[List[Any], Tuple[Any, ...]],
      func_kwargs: Mapping[str, Any],
      pattern_list: List[str],
      timeout: float = 30.0,
      searchwindowsize: int = config.SEARCHWINDOWSIZE,
      expect_type: str = line_identifier.LINE_TYPE_ALL,
      mode: str = MODE_TYPE_ANY,
      raise_for_timeout: bool = False,
      include_func_response: bool = False
  ) -> Union[Tuple[expect_response.ExpectResponse, Any],
             expect_response.ExpectResponse]:
    """Executes function with given args, blocks until expect matches or timeout occurs.

    Args:
        func: name of function to be called
        func_args: positional arguments specified to be passed to function.
          Input parameter "func" MUST NOT call "shell" nor another
          "core.xxx_expect" method so as to avoid the nested "flush" problem
          described in 'NEP-2343'.
        func_kwargs: keyword arguments specified to be passed to function
        pattern_list: list of regex expressions to look for in the lines
        timeout: seconds to look for the patterns
        searchwindowsize: number of the last bytes to look at
        expect_type: 'log', 'response', or 'all'
        mode: type of expect to run ("any", "all" or "sequential")
        raise_for_timeout: Raise an exception if the expect times out
        include_func_response: If True, also return func's return value.

    Returns:
        ExpectResponse or tuple: ExpectResponse or (ExpectResponse, object) if
        include_func_response is True.

    Raises:
        DeviceError: If func is not callable
                     If other arguments are invalid
    """
    if not callable(func):
      raise errors.DeviceError("Device {} do_and_expect failed. "
                               "Function: {} is not callable.".format(
                                   self._device_name, func))
    self._check_expect_args(pattern_list, timeout, searchwindowsize,
                            expect_type, mode)
    compiled_list = self._get_compiled_pattern_list(pattern_list)

    try:
      self._enable_raw_data_queue()
      func_ret = func(*func_args, **func_kwargs)
      expect_ret = self._expect(
          compiled_list,
          timeout,
          searchwindowsize,
          expect_type,
          mode,
          raise_for_timeout=raise_for_timeout)
      if include_func_response:
        return expect_ret, func_ret
      else:
        return expect_ret
    finally:
      self._disable_raw_data_queue()

  @decorators.CapabilityLogDecorator(logger)
  def echo_file_to_transport(self,
                             source_file: str,
                             destination_path: str,
                             port: int = 0,
                             bytes_per_echo: int = 50) -> None:
    r"""Transfers file to transport specified using echo commands.

    Args:
        source_file: path to the file to transfer
        destination_path: path to transfer file to on device
        port (int or str): the transport port to open
        bytes_per_echo (int): call to use during file transfer

    Raises:
        DeviceError: If source_file doesn't exist, can't be opened, or
                     the port or bytes_per_echo values are invalid or
                     out of range.

    Note:
        The caller is responsible for preparing the device to receive
        multiple echo commands to receive the file and only calling this
        method for devices that support the following commands::

            echo -ne > <destination_path>
            echo -ne "\\x{:02x}" >> <destination_path>
    """
    self._validate_port(port, self.echo_file_to_transport.__name__)

    if not os.path.exists(source_file):
      raise errors.DeviceError("Device {} echo file to transport failed. "
                               "Source file {} doesn't exist.".format(
                                   self._device_name, source_file))
    elif not isinstance(bytes_per_echo, int):
      raise errors.DeviceError(
          "Device {} echo file to transport failed. "
          "Expecting int for bytes_per_echo found {} instead.".format(
              self._device_name, type(bytes_per_echo)))
    elif bytes_per_echo <= 0:
      raise errors.DeviceError(
          "Device {} echo file to transport failed. "
          "Invalid bytes_per_echo value {} expected >0".format(
              self._device_name, bytes_per_echo))

    start_time = time.time()
    log_message = ("starting echo transfer of {} for port {} to {}".format(
        source_file, port, destination_path))
    self.add_log_note(log_message)

    # Read the data in from the file
    try:
      with io.open(source_file, "rb") as in_file:
        data = in_file.read()
    except IOError as err:
      raise errors.DeviceError("Device {} echo file to transport failed. "
                               "Unable to read {}. "
                               "Error: {!r}".format(self._device_name,
                                                    source_file, err))

    # Create and zero out the file
    cmd_string = "echo -ne > {}\n".format(destination_path)
    echo_pattern1 = r"echo -ne > [/\w.]+"
    result = self.send_and_expect(
        cmd_string, [echo_pattern1], port=port, expect_type="response")
    if result.timedout:
      raise errors.DeviceError("Device {} echo file to transport failed. "
                               "Unable to create/erase file {} on device. "
                               "Output: {!r}".format(self._device_name,
                                                     destination_path,
                                                     result.before))

    # Loop through the data at bytes_per_echo chunks at a time
    echo_pattern2 = r'echo -ne ".*"\s.*\s[/\w.]+'
    data_indexes = list(range(0, len(data), bytes_per_echo)) + [len(data)]
    for data_index in range(1, len(data_indexes)):
      start_index = data_indexes[data_index - 1]
      end_index = data_indexes[data_index]
      data_chunk = u"".join(
          [u"\\x%02x" % byte for byte in data[start_index:end_index]])
      cmd_string = "echo -ne \"{}\" >> {}\n".format(data_chunk,
                                                    destination_path)
      result = self.send_and_expect(
          cmd_string, [echo_pattern2], port=port, expect_type="response")
      if result.timedout:
        raise errors.DeviceError("Device {} echo file to transport failed. "
                                 "Unable to echo bytes {!r} to file {} "
                                 "Output: {!r}".format(self._device_name,
                                                       data_chunk,
                                                       destination_path,
                                                       result.before))
    log_message = ("finished echo transfer of {} for port {} in {}s".format(
        source_file, port,
        time.time() - start_time))
    self.add_log_note(log_message)

  @decorators.CapabilityLogDecorator(logger, level=decorators.DEBUG)
  def ensure_serial_paths_unlocked(self,
                                   communication_addresses: List[str]) -> None:
    """Ensures serial paths are longer locked by switchboard process after device is closed."""
    for comms_address in communication_addresses:
      if comms_address not in usb_utils.get_all_serial_connections():
        continue  # only active serial connections have locks

      try:
        output = subprocess.check_output(["lsof", comms_address],
                                         stderr=subprocess.STDOUT)
        output = output.decode("utf-8", "replace").splitlines()
      except (subprocess.CalledProcessError,
              ImportError):  # process does not exist
        continue

      process_number = output[-1].split()[1]  # process id
      try:
        number = int(process_number)
        logger.info(
            "{}'s communication process still exists. Killing process {}"
            .format(self._device_name, number))
        os.kill(int(process_number), signal.SIGTERM)
      except ValueError:
        logger.error(
            "{}'s communication process still exists "
            "but could not parse process number from lsof output correctly. "
            "Output: {}. Expected process number: {}".format(
                self._device_name, output, process_number))

  def expect(self,
             pattern_list: List[str],
             timeout: float = 30.0,
             searchwindowsize: int = config.SEARCHWINDOWSIZE,
             expect_type: str = line_identifier.LINE_TYPE_ALL,
             mode: str = MODE_TYPE_ANY,
             raise_for_timeout: bool = False) -> expect_response.ExpectResponse:
    """Block until a regex pattern is matched or until a timeout time has elapsed.

    Flushes the expect queue before and after an expect.

    Args:
        pattern_list: list of regex expressions to look for in the lines
        timeout: seconds to look for the patterns
        searchwindowsize: number of the last bytes to look at
        expect_type: 'log', 'response', or 'all'
        mode: type of expect to run ("any", "all" or "sequential")
        raise_for_timeout: Raise an exception if the expect times out

    Raises:
        DeviceError: if arguments are not valid.

    Returns:
        ExpectResponse object
    """
    self.health_check()
    self._check_expect_args(pattern_list, timeout, searchwindowsize,
                            expect_type, mode)
    compiled_list = self._get_compiled_pattern_list(pattern_list)

    try:
      self._enable_raw_data_queue()
      return self._expect(
          compiled_list,
          timeout,
          searchwindowsize,
          expect_type,
          mode,
          raise_for_timeout=raise_for_timeout)
    finally:
      self._disable_raw_data_queue()

  def get_line_identifier(self):
    """Returns the line identifier currently used by Switchboard."""
    return self._identifier

  @decorators.DynamicProperty
  def _transport_processes(
      self) -> MutableSequence[transport_base.TransportBase]:
    self.health_check()
    return self._transport_processes_cache

  @decorators.DynamicProperty
  def _log_writer_process(self) -> Optional[log_process.LogWriterProcess]:
    self.health_check()
    return self._log_writer_process_cache

  @decorators.DynamicProperty
  def _log_filter_process(self) -> Optional[log_process.LogFilterProcess]:
    self.health_check()
    return self._log_filter_process_cache

  @decorators.CapabilityLogDecorator(logger, level=decorators.DEBUG)
  def health_check(self) -> None:
    """Initializes Switchboard.

    This health check will affect the queues, but the queues are created in
    init and produce no side effects.

    This health check affects the following attributes:
    - self._transport_processes_cache
    - self._log_writer_process_cache
    - self._log_filter_process_cache

    Raises:
      errors.CapabilityNotReadyError: If switchboard has been closed.
      errors.CapabilityNotReadyError: If error occurs during health check.
    """
    if not self._healthy and self._healthy is not None:
      raise errors.CapabilityNotReadyError(
          msg="Switchboard has been closed or failed to start.",
          device_name=self._device_name) from self._stored_health_check_error
    elif self._healthy is None:
      try:
        # Populate self._transport_processes and set self._transport_process_id
        self._add_transport_processes(self._transport_list, self._framer_list,
                                      self._partial_line_timeout_list)
        # Set self._log_writer_process and self._log_filter_process
        self._add_log_writer_process(self.log_path, self._max_log_size)
        self._add_log_filter_process(self._parser, self.log_path)
        logger.info("%s logging to file %s", self._device_name, self.log_path)
        self._start_processes()
        self._healthy = True

      except Exception as err:
        self._healthy = False
        self._stored_health_check_error = err
        raise errors.CapabilityNotReadyError(
            msg=repr(err), device_name=self._device_name) from err

  @decorators.DynamicProperty
  def number_transports(self) -> int:
    """Returns the number of transport processes used by Switchboard."""
    return len(self._transport_processes)

  @decorators.CapabilityLogDecorator(logger)
  def open_all_transports(self) -> None:
    """Opens the communication FDs, assuming switchboard architecture is intact.

    This is used after a physical connection has been reopened,
    such as reconnecting an ethernet or a serial connection.
    Only opens the ones closed so if device.close has already occurred,
    nothing will be opened.
    """
    for port in range(self.number_transports):
      self.open_transport(port=port)

  @decorators.CapabilityLogDecorator(logger, level=decorators.DEBUG)
  def open_transport(self, port: int = 0, timeout: float = 30.0) -> None:
    """Opens the transport specified.

    Args:
        port: the transport port to open
        timeout: how long to wait for port to open.

    Raises:
        DeviceError: If port value is invalid or out of range.
    """
    self._validate_port(port, self.open_transport.__name__)

    log_message = "opening transport for port {}".format(port)
    self.add_log_note(log_message)
    transport_proc = self._transport_processes[port]
    start_time = time.time()
    transport_proc.send_command(transport_process.CMD_TRANSPORT_OPEN)
    start_time = time.time()
    elapsed_time = 0
    while not transport_proc.is_open():
      if elapsed_time < timeout:
        time.sleep(0.01)
        elapsed_time = time.time() - start_time
      else:
        return
    log_message = "opened transport for port {} in {}s".format(
        port,
        time.time() - start_time)
    self.add_log_note(log_message)

  @decorators.CapabilityLogDecorator(logger)
  def press(self, button: str, wait: float = 0.0, port: int = 0) -> None:
    """Presses the button for the port specified and waits the time specified.

    Args:
        button (str): button to press
        wait (float): seconds to wait before returning
        port (int): which port to click on, 0 or 1

    Raises:
        DeviceError: If buttons are not supported on the device or
                     button, wait, or port values are invalid
    """
    self._check_button_args("press", button, port, wait=wait)

    log_message = "pressing button {} on port {} and waiting {}s - begin".format(
        button, port, wait)
    self.add_log_note(log_message)
    self.button_list[port].press(button, wait)
    log_message = "pressing button {} on port {} and waiting {}s - end".format(
        button, port, wait)
    self.add_log_note(log_message)

  def press_and_expect(
      self,
      button: str,
      pattern_list: List[str],
      wait: float = 0.0,
      timeout: float = 30.0,
      searchwindowsize: int = config.SEARCHWINDOWSIZE,
      expect_type: str = line_identifier.LINE_TYPE_ALL,
      port: int = 0,
      mode: str = MODE_TYPE_ANY) -> expect_response.ExpectResponse:
    """Press button and expect for pattern_list and other arguments provided.

    Flushes the expect queue before and after an expect. Starts up
    expect queue right before pressing button to catch fast responses.

    Args:
        button: button to press
        pattern_list: list of regex expressions to look for in the lines
        wait: seconds to wait
        timeout: Seconds to look for the patterns
        searchwindowsize: Number of the last bytes to look at
        expect_type: 'log', 'response', or 'all'
        port: Which port to send on, 0 or 1
        mode: type of expect to run ("any", "all" or "sequential")

    Raises:
        DeviceError: If buttons are not supported on the device or
                     button, wait, port, or expect values are invalid

    Returns:
        ExpectResponse
    """
    return typing.cast(
        expect_response.ExpectResponse,
        self.do_and_expect(
            self.press, [button], {
                "wait": wait,
                "port": port
            },
            pattern_list,
            timeout=timeout,
            searchwindowsize=searchwindowsize,
            expect_type=expect_type,
            mode=mode))

  @decorators.CapabilityLogDecorator(logger)
  def release(self, button: str, port: int = 0) -> None:
    """Release the button for the port specified.

    Args:
        button: button to release
        port: Which port to release button on, 0 or 1

    Raises:
        DeviceError: If buttons are not supported on the device or
                     button or port values are invalid
    """
    self._check_button_args("release", button, port)

    self.button_list[port].release(button)
    log_message = "released button {}".format(button)
    self.add_log_note(log_message)

  def release_and_expect(self,
                         button: str,
                         pattern_list: List[str],
                         timeout: float = 30.0,
                         searchwindowsize: int = config.SEARCHWINDOWSIZE,
                         expect_type: str = line_identifier.LINE_TYPE_ALL,
                         port: int = 0,
                         mode: str = "any"):
    """Release button, matches pattern_list in loglines as specified by expect_type.

    Flushes the expect queue before and after an expect. Starts up
    expect queue right before releasing button to catch fast responses.

    Args:
        button (str): button to release
        pattern_list (list): list of regex expressions to look for in the lines
        timeout (float): seconds to look for the patterns
        searchwindowsize (int): number of the last bytes to look at
        expect_type (str): 'log', 'response', or 'all'
        port (int): which port to send on, 0 or 1
        mode (str): type of expect to run ("any", "all" or "sequential")

    Raises:
        DeviceError: If buttons are not supported on the device or
                     button, port, or expect values are invalid

    Returns:
        ExpectResponse
    """
    return self.do_and_expect(
        self.release, [button], {"port": port},
        pattern_list,
        timeout=timeout,
        searchwindowsize=searchwindowsize,
        expect_type=expect_type,
        mode=mode)

  @decorators.CapabilityLogDecorator(logger, level=None)
  def send(self,
           command: str,
           port: int = 0,
           slow: bool = False,
           add_newline: bool = True,
           newline: str = "\n") -> None:
    """Sends the command to the device on the port (transport) specified.

    Args:
        command: to send to the device
        port: or transport to send command to
        slow: flag indicating command should be sent byte-by-byte
        add_newline: flag indicating newline should be added to command if
          missing
        newline: character to check for and add if missing at the end of the
          command

    Raises:
        DeviceError: if port specified is an invalid value or out of
                     range of the available ports
    """
    self._validate_port(port, self.send.__name__)

    self.add_log_note("wrote command {!r} to port {}".format(command, port))
    command = _ensure_has_newline(command, add_newline, newline)
    if slow or self._force_slow:
      for cmd_byte in command:
        self._send_command_to_device(cmd_byte, port=port)
    else:
      self._send_command_to_device(command, port=port)

  def send_and_expect(
      self,
      command: str,
      pattern_list: List[str],
      timeout: float = 30.0,
      searchwindowsize: int = config.SEARCHWINDOWSIZE,
      expect_type: str = line_identifier.LINE_TYPE_ALL,
      mode: str = MODE_TYPE_ANY,
      port: int = 0,
      slow: bool = False,
      add_newline: int = True,
      newline: str = "\n",
      command_tries: int = 1,
      raise_for_timeout: bool = False) -> expect_response.ExpectResponse:
    r"""Sends the command and expects on the patterns provided.

    Note: this method does not prepend the command with a wakeup character which
    some devices require. The reason this may be needed is because some devices
    go into a sleep state to save energy and will wakeup on receiving the first
    character sent to it which means the character won't get registered into the
    command buffer. This can be dealt with by prepending the command with a nop
    character that won't affect the command being executed in the case that the
    device has already woken up. If there is an issue with this method, try
    adding "\n" in front of the command. E.g. "\nsome_command"

    Flushes the expect queue before and after an send.

    Args:
        command: command to send to the device
        pattern_list: list of regex expressions to look for in the lines
        timeout: Seconds to look for the patterns
        searchwindowsize: Number of the last bytes to look at
        expect_type: 'log', 'response', or 'all'
        mode: type of expect to run ("any", "all" or "sequential")
        port: Which port to send on, 0 or 1
        slow: flag indicating command should be sent byte-by-byte
        add_newline: flag indicating newline should be added to command if
          missing
        newline: character to check for and add if missing at the end of the
          command
        command_tries: The number of tries to send the command if it times out.
        raise_for_timeout: Raise an exception if the expect times out

    Raises:
        DeviceError: if port specified or other expect arguments are
                     invalid, or timed out and raise_for_timeout was True.

    Returns:
        ExpectResponse
    """
    for _ in range(command_tries):
      result = typing.cast(
          expect_response.ExpectResponse,
          self.do_and_expect(
              self.send, [command], {
                  "port": port,
                  "slow": slow,
                  "add_newline": add_newline,
                  "newline": newline
              },
              pattern_list,
              timeout=timeout,
              searchwindowsize=searchwindowsize,
              expect_type=expect_type,
              mode=mode))
      if result.timedout:
        continue
      return result

    if result.timedout and raise_for_timeout:
      raise errors.DeviceError(
          "Device {} send_and_expect timed out for command {}".format(
              self._device_name, command))
    return result

  @decorators.CapabilityLogDecorator(logger)
  def set_max_log_size(self, max_log_size: int) -> None:
    """Sets the max_log_size value to the value provided.

    Args:
        max_log_size: the max log size to use for log rotation.

    Raises:
        ValueError: if max_log_size is not an integer value
        RuntimeError: if log writer process is not running

    Note:
        A max_log_size of 0 means no log rotation should ever occur.
    """
    if (not self._log_writer_process or
        not self._log_writer_process.is_running()):
      raise RuntimeError("Log writer process is not currently running.")
    elif not isinstance(max_log_size, int):
      raise ValueError("Expected 'type<int>' found {}".format(
          type(max_log_size)))

    self._log_writer_process.send_command(log_process.CMD_MAX_LOG_SIZE,
                                          max_log_size)
    while (self._log_writer_process.is_running() and
           not self._log_writer_process.is_command_consumed()):
      time.sleep(0.001)

  @decorators.CapabilityLogDecorator(logger)
  def start_new_log(self, log_path: str) -> None:
    """Changes log filter and writer to use a new log path provided.

    Args:
        log_path: to log file to switch to

    Raises:
        RuntimeError: if LogWriterProcess is not available or running.
    """
    if (not self._log_writer_process or
        not self._log_writer_process.is_running()):
      raise RuntimeError("Log writer process is not currently running.")

    if self._log_filter_process:  # pylint: disable=using-constant-test
      self._log_filter_process.send_command(log_process.CMD_NEW_LOG_FILE,
                                            log_path)
      while (self._log_filter_process.is_running() and
             not self._log_filter_process.is_command_consumed()):
        time.sleep(0.001)

    self._log_writer_process.send_command(log_process.CMD_NEW_LOG_FILE,
                                          log_path)
    while (self._log_writer_process.is_running() and
           not self._log_writer_process.is_command_consumed()):
      time.sleep(0.001)

    # Wait for new log file to appear
    while self._log_writer_process.is_running(
    ) and not os.path.exists(log_path):
      time.sleep(0.1)

  @decorators.CapabilityLogDecorator(logger)
  def transport_jlink_flash(self, image_path: str, port: int = 0) -> None:
    """Calls the J-Link flash method in the transport.

    Args:
      image_path: path to the image file to be flashed onto the device.
      port: number of the transport to execute the method in.
    """
    self.call(
        method=jlink_transport.JLinkTransport.flash,
        method_args=(image_path,),
        port=port)

  @decorators.CapabilityLogDecorator(logger)
  def transport_jlink_reset(self, port: int = 0) -> None:
    """Calls the J-Link reset method in the transport."""
    self.call(method=jlink_transport.JLinkTransport.reset, port=port)

  @decorators.CapabilityLogDecorator(logger)
  def transport_serial_set_baudrate(self,
                                    new_baudrate: int,
                                    port: int = 0) -> None:
    """Sets the serial transport baudrate to a different baudrate.

    Args:
      new_baudrate: new baudrate to be set, generally 115200 or 921600.
      port: number of the transport to set the baudrate for.
    """
    self.call(method=serial_transport.SerialTransport.flush_buffers, port=port)
    self.call(
        method=serial_transport.SerialTransport.set_property,
        method_args=(transport_properties.BAUDRATE, new_baudrate),
        port=port)
    self.call(method=serial_transport.SerialTransport.flush_buffers, port=port)

  @decorators.CapabilityLogDecorator(logger, level=decorators.DEBUG)
  def transport_serial_send_xon(self, port: int = 0) -> None:
    """Sends the XON control character to the serial transport."""
    self.call(method=serial_transport.SerialTransport.send_xon, port=port)

  @decorators.CapabilityLogDecorator(logger, level=decorators.DEBUG)
  def transport_serial_send_xoff(self, port: int = 0) -> None:
    """Sends the XOFF control character to the serial transport."""
    self.call(method=serial_transport.SerialTransport.send_xoff, port=port)

  @decorators.CapabilityLogDecorator(logger, level=decorators.DEBUG)
  def transport_serial_send_break_byte(self, port: int = 0) -> None:
    """Sends the break control character (Ctrl+C) to the serial transport."""
    self.call(
        method=serial_transport.SerialTransport.send_break_byte, port=port)

  def verify_file_on_transport(self,
                               source_file: str,
                               destination_path: str,
                               port: int = 0,
                               method: str = VERIFY_METHOD_MD5SUM) -> bool:
    """Verifies source file contents matches destination_path on transport using method.

    Args:
        source_file: to compare content to on transport
        destination_path: to file to verify on transport
        port: the transport port to open
        method: the method to use to verify destination_path

    Raises:
        DeviceError: If source_file doesn't exist, can't be opened, or
                     the port or method values are invalid or out of range.

    Returns:
        A boolean status indicating verification was successful.

    Note:
        The caller is responsible for preparing the device to receive one
        of the following verification commands::

            md5sum < destination_path >
    """
    self._validate_port(port, self.verify_file_on_transport.__name__)

    if not os.path.exists(source_file):
      raise errors.DeviceError("Device {} verify file on transport failed. "
                               "Source file {} doesn't exist.".format(
                                   self._device_name, source_file))
    elif not isinstance(method, str):
      raise errors.DeviceError(
          "Device {} verify file on transport failed. "
          "Expecting string for method found {} instead.".format(
              self._device_name, type(method)))
    elif method not in _VERIFY_METHODS:
      raise errors.DeviceError("Device {} verify file on transport failed. "
                               "Unknown method value {} expected: {}".format(
                                   self._device_name, method,
                                   ",".join(_VERIFY_METHODS)))

    # Verify md5sum is available on the host computer
    host_md5sum_path = subprocess.check_output(["which", "md5sum"],
                                               stderr=subprocess.PIPE).decode(
                                                   "utf-8", "replace")
    if "md5sum" not in host_md5sum_path:
      raise errors.DeviceError(
          "Device {} echo file to transport failed. "
          "md5sum is not installed on host. "
          "Unable to verify successful file transfer".format(self._device_name))

    try:
      md5sum_results = subprocess.check_output(
          [host_md5sum_path.rstrip(), source_file]).decode("utf-8", "replace")
    except subprocess.CalledProcessError as err:
      raise errors.DeviceError("Device {} echo file to transport failed. "
                               "Unable to retrieve md5sum of {}. "
                               "Error: {!r}".format(self._device_name,
                                                    source_file, err))
    else:
      host_checksum = md5sum_results.split()[0]

    # Get md5sum of destination_path
    checksum_pattern = r"(\w{32})\s+" + destination_path
    missing_pattern = "can't open '" + destination_path + ("': No such file or "
                                                           "directory")
    result = self.send_and_expect(
        "md5sum {}\n".format(destination_path),
        [checksum_pattern, missing_pattern],
        expect_type="response",
        port=port)
    if result.timedout:
      raise errors.DeviceError(
          "Device {} echo file to transport failed. "
          "Unable to verify {} using the md5sum command".format(
              self._device_name, destination_path))
    elif result.index == 0:  # checksum returned for file pattern
      device_checksum = result.match.group(1)
    elif result.index == 1:  # missing file pattern
      device_checksum = "No such file or directory"
    success = host_checksum == device_checksum
    if success:
      log_message = ("verification of {} for port {} was successful".format(
          destination_path, port))
    else:
      log_message = ("verification of {} for port {} failed. "
                     "The host md5sum {!r} != device md5sum {!r}".format(
                         destination_path, port, host_checksum,
                         device_checksum))
    self.add_log_note(log_message)
    return success

  @decorators.CapabilityLogDecorator(logger)
  def xmodem_file_to_transport(self, source_file: str, port: int = 0) -> bool:
    """Transfers file to transport specified using the XModem protocol.

    Args:
        source_file: to the file to transfer
        port: the transport port to open

    Raises:
        DeviceError: If source_file doesn't exist, can't be opened, or
                     the port value provided is invalid or out of range.

    Returns:
        bool: A boolean status indicating xmodem transfer was successful.

    Note:
        The caller is responsible for putting the transport into XModem
        transfer mode before calling this method.
    """
    self._validate_port(port, self.xmodem_file_to_transport.__name__)

    if not os.path.exists(source_file):
      raise errors.DeviceError("Device {} xmodem file to transport failed. "
                               "Source file {} doesn't exist.".format(
                                   self._device_name, source_file))

    try:
      stream = io.open(source_file, "rb")
    except IOError as err:
      raise errors.DeviceError("Device {} xmodem file to transport failed. "
                               "Unable to open source file {}. "
                               "Error: {!r}".format(self._device_name,
                                                    source_file, err))
    success = False
    transport = self._transport_processes[port].transport
    modem = xmodem.XMODEM(transport.read, transport.write)
    start_time = time.time()
    try:
      self.close_transport(port=port)
      log_message = "starting xmodem transfer of {} for port {}".format(
          source_file, port)
      self.add_log_note(log_message)
      transport.open()
      success = modem.send(stream)
    finally:
      stream.close()
      log_message = (
          "finished xmodem transfer of {} for port {} in {}s success={}".format(
              source_file, port,
              time.time() - start_time, success))
      self.add_log_note(log_message)
      transport.close()
      self.open_transport(port=port)
    return success

  def add_transport_process(self, transport: transport_base.TransportBase,
                            **transport_process_kwargs: Any) -> int:
    """Add a new transport process to the list of transport processes.

    Args:
        transport: transport to the device for this process
        **transport_process_kwargs: keyword arguments to the transport process
    transport_process_kwargs can be:
        framer(DataFramer): DataFramer derived classes to use to frame incoming
          raw data into raw lines. Defaults to None.
        partial_line_timeout(float): time in seconds to wait before adding
          partial lines to raw_data_queue and log_queue. Defaults to
          transport_process.PARTIAL_LINE_TIMEOUT.
        read_timeout(float): time to wait in seconds for transport reads.
          Defaults to to transport_process._READ_TIMEOUT
        max_read_bytes(int): to attempt to read on each transport read call.
          Defaults to transport_process._MAX_READ_BYTES
        max_write_bytes(int): to attempt to write on each transport write call.
          Defaults to transport_process._MAX_WRITE_BYTES

    Returns:
        int: position of newly added transport process in list of transport
        processes("port")
    """
    self._transport_processes_cache.append(
        transport_process.TransportProcess(
            self._device_name,
            self._exception_queue,
            multiprocessing_utils.get_context().Queue(),
            self._log_queue,
            transport,
            call_result_queue=self._call_result_queue,
            raw_data_queue=self._raw_data_queue,
            raw_data_id=self._transport_process_id,
            **transport_process_kwargs))
    self._transport_process_id += 1
    return len(
        self._transport_processes_cache) - 1  # The added process is always last

  def _add_transport_processes(self, transport_list, framer_list,
                               partial_line_timeout_list):
    """Create transport processes which handle the given transports.

    Args:
      transport_list(list): list of transports.
      framer_list(list): list of data framers, one per transport.
      partial_line_timeout_list(list): list of float to delay before adding a
        partial line.
    """
    for idx, transport in enumerate(transport_list):
      kwargs = {}
      if idx < len(framer_list):
        kwargs["framer"] = framer_list[idx]
      if idx < len(partial_line_timeout_list):
        kwargs["partial_line_timeout"] = partial_line_timeout_list[idx]
      self.add_transport_process(transport, **kwargs)

  def _add_log_writer_process(self, log_path, max_log_size):
    """Creates log writer process. Should only be called from health_check()."""
    self._log_writer_process_cache = log_process.LogWriterProcess(
        self._device_name,
        self._exception_queue,
        multiprocessing_utils.get_context().Queue(),
        self._log_queue,
        log_path,
        max_log_size=max_log_size)

  def _add_log_filter_process(self, parser, log_path):
    """Creates log filter process. Should only be called from health_check()."""
    if parser is not None:
      self._log_filter_process_cache = log_process.LogFilterProcess(
          self._device_name, self._exception_queue,
          multiprocessing_utils.get_context().Queue(), parser, log_path)

  def _check_button_args(self,
                         func_name: str,
                         button: str,
                         port: int,
                         duration: float = 0.0,
                         wait: float = 0.0) -> None:
    """Checks that button arguments are valid.

    Args:
        func_name: name of the calling function (to include in the error
          message).
        button: button name.
        port: which port to click on, 0 or 1.
        duration: seconds to wait before releasing button.
        wait: seconds to wait before returning after pressing the button.

    Raises:
        DeviceError: provided button arguments are invalid.
    """
    self._validate_port(port, func_name)

    if not self.button_list:
      raise errors.DeviceError(
          "Device {} {} failed. "
          "Buttons are not supported for this device.".format(
              self._device_name, func_name))
    elif not isinstance(button, str):
      raise errors.DeviceError(
          "Device {} {} failed. "
          "Expecting str for button found {} instead.".format(
              self._device_name, func_name, type(button)))
    elif not isinstance(duration, (int, float)):
      raise errors.DeviceError(
          "Device {} {} failed. "
          "Expecting int or float for duration found {} instead.".format(
              self._device_name, func_name, type(duration)))
    elif not isinstance(wait, (int, float)):
      raise errors.DeviceError(
          "Device {} {} failed. "
          "Expecting int or float for wait found {} instead.".format(
              self._device_name, func_name, type(wait)))
    elif duration < 0.0:
      raise errors.DeviceError(
          "Device {} {} failed. "
          "Invalid duration value {} expected >=0.0".format(
              self._device_name, func_name, duration))
    elif wait < 0.0:
      raise errors.DeviceError("Device {} {} failed. "
                               "Invalid wait value {} expected >=0.0".format(
                                   self._device_name, func_name, wait))
    elif not self.button_list[port].is_valid(button):
      raise errors.DeviceError(
          "Device {} {} failed. "
          "Invalid button {} for port {} expected {}.".format(
              self._device_name, func_name, button, port,
              self.button_list[port].valid_buttons()))

  def _check_expect_args(self, pattern_list: List[str], timeout: float,
                         searchwindowsize: int, expect_type: str,
                         mode: str) -> None:
    """Check that expect arguments are valid.

    Args:
        pattern_list: list of regex expressions to look for in the lines
        timeout: seconds to look for the patterns
        searchwindowsize: number of the last bytes to look at
        expect_type: 'log', 'response', or 'all'
        mode: type of expect to run ("any", "all" or "sequential")

    Raises:
        DeviceError: provided expect arguments are invalid.
    """
    if not isinstance(pattern_list, list):
      raise errors.DeviceError(
          "Device {} expect failed. "
          "Expecting list for pattern_list ({}) found {} instead.".format(
              self._device_name, repr(pattern_list), type(pattern_list)))
    elif not isinstance(timeout, (int, float)):
      raise errors.DeviceError(
          "Device {} expect failed. "
          "Expecting int or float for timeout found {} instead.".format(
              self._device_name, type(timeout)))
    elif not isinstance(searchwindowsize, int):
      raise errors.DeviceError(
          "Device {} expect failed. "
          "Expecting int for searchwindowsize found {} instead.".format(
              self._device_name, type(searchwindowsize)))
    elif not isinstance(expect_type, str):
      raise errors.DeviceError(
          "Device {} expect failed. "
          "Expecting str for expect_type found {} instead.".format(
              self._device_name, type(expect_type)))
    elif not isinstance(mode, str):
      raise errors.DeviceError(
          "Device {} expect failed. "
          "Expecting str for mode found {} instead.".format(
              self._device_name, type(mode)))
    elif expect_type not in _VALID_EXPECT_TYPES:
      raise errors.DeviceError(
          "Device {} expect failed. "
          "Invalid input for expect_type found {} expecting one of {}.".format(
              self._device_name, expect_type, _VALID_EXPECT_TYPES))
    elif mode not in _VALID_EXPECT_MODES:
      raise errors.DeviceError(
          "Device {} expect failed. "
          "Invalid input for mode found {} expecting one of {}.".format(
              self._device_name, mode, _VALID_EXPECT_MODES))
    elif not pattern_list:
      raise errors.DeviceError(
          "Device {} expect failed. "
          "Expecting at least one pattern in list, found none.".format(
              self._device_name))
    log_message = ("expecting {} patterns from {!r} using "
                   "{} lines and {} search window in {}s".format(
                       mode, pattern_list, expect_type, searchwindowsize,
                       timeout))
    self.add_log_note(log_message)

  def _disable_raw_data_queue(self) -> None:
    """Decrement the raw_data_queue user count and disable and flush the raw_data_queue."""
    if self._raw_data_queue_users:
      self._raw_data_queue_users -= 1
    if self._raw_data_queue_users == 0:
      self._toggle_raw_data()
      self._flush_raw_data_queue()

  def _enable_raw_data_queue(self) -> None:
    """Increment the raw_data_queue user count and flush and enable the raw_data_queue."""
    self._raw_data_queue_users += 1
    if self._raw_data_queue_users == 1:
      self._flush_raw_data_queue()
      self._toggle_raw_data()

  def _expect(
      self,
      compiled_list: Sequence[re.Pattern],
      timeout: float,
      searchwindowsize: int,
      expect_type: str,
      mode: str,
      raise_for_timeout: bool = False) -> expect_response.ExpectResponse:
    """Wait until a message matching the regexps in the list arrives on the data queue.

    Args:
        compiled_list: The list of patterns
        timeout: seconds to look for the patterns
        searchwindowsize: number of the last bytes to look at
        expect_type: 'log', 'response', or 'all'
        mode: type of expect to run ("any", "all" or "sequential")
        raise_for_timeout: Raise an exception if the expect times out

    Returns:
         ExpectResponse: an expect response

    Raises:
        DeviceError: for a timeout if raise_for_timeout is True.
    """
    actual_searchwindowsize = searchwindowsize * 2
    captured_index = 0
    captured_lines = []
    expected_matches = 1 if mode == "any" else len(compiled_list)
    found_matches = 0
    match_list = []
    window = u""

    start_time = time.time()
    end_time = start_time + timeout
    while time.time() < end_time:
      # Stage 1/4: get next raw line to add to search window
      time_left = end_time - time.time()
      try:
        message = switchboard_process.get_message(
            self._raw_data_queue, timeout=0 if time_left < 0 else time_left)
      except (AttributeError, IOError, queue.Empty, ValueError):
        # manager shutdown or close called
        break

      if message is None:
        continue

      port, line = message
      if not self._identifier.accept(port, line, expect_type):
        continue

      # Stage 2/4: add raw line to search window in searchwindowsize chunks
      captured_lines.append(line)
      line_split_indexes = list(range(0, len(line),
                                      searchwindowsize)) + [len(line)]
      for line_index in range(1, len(line_split_indexes)):
        start_index = line_split_indexes[line_index - 1]
        end_index = line_split_indexes[line_index]
        partial_line = line[start_index:end_index]
        captured_index += len(partial_line)
        window += partial_line
        window = window[-actual_searchwindowsize:]

        # Break if timeout was exceeded
        if time.time() >= end_time:
          break

        # Stage 3/4: find matching pattern from pattern_list in search window
        pattern_list = _get_pattern_list(compiled_list, match_list, mode)
        for pattern in pattern_list:
          match = pattern.search(window)
          if not match:
            continue
          found_matches += 1
          match_list.append(match)

          index = _get_pattern_index(compiled_list, match_list, mode)
          log_message = "found pattern {!r} at index {}".format(
              pattern.pattern, index)
          self.add_log_note(log_message)
          if found_matches != expected_matches:
            # Remove content from window up to match end for next pattern search
            window = window[match.end():]
            break

          # Stage 4/4: expect pattern success, return results
          time_elapsed = time.time() - start_time

          # Compute index into captured_string where match was found
          i = captured_index - len(window) + match.start()

          captured_string = u"".join(captured_lines)
          before = captured_string[:i]
          after = captured_string[i:]

          missing_patterns = _get_missing_patterns(compiled_list, match_list,
                                                   mode)
          remaining_list = _get_pattern_strings(missing_patterns)
          log_message = (
              "mode {} expect completed with {!r} remaining patterns in {}s"
              .format(mode, u", ".join(remaining_list), time_elapsed))
          self.add_log_note(log_message)
          return expect_response.ExpectResponse(
              index,
              before,
              after,
              match,
              time_elapsed,
              match_list=match_list,
              remaining=remaining_list)

    # Stage 4/4: expect pattern timed out, return results
    time_elapsed = time.time() - start_time

    if match_list:
      match = match_list[-1]
      index = _get_pattern_index(compiled_list, match_list, mode)
    else:
      index = match = None
    before = u"".join(captured_lines)
    after = ""

    missing_patterns = _get_missing_patterns(compiled_list, match_list, mode)
    remaining_list = _get_pattern_strings(missing_patterns)
    log_message = (
        "expect timed out after waiting {}s for {!r} remaining patterns".format(
            time_elapsed, u", ".join(remaining_list)))
    self.add_log_note(log_message)

    if raise_for_timeout:
      raise errors.DeviceError(
          "{} expect timed out after waiting {}s for {!r} remaining patterns"
          .format(self._device_name, time_elapsed, ", ".join(remaining_list)))

    return expect_response.ExpectResponse(
        index,
        before,
        after,
        match,
        time_elapsed,
        timedout=True,
        remaining=remaining_list,
        match_list=match_list)

  def _flush_raw_data_queue(self) -> None:
    try:
      while not self._raw_data_queue.empty():
        self._raw_data_queue.get_nowait()
    except (AttributeError, IOError, queue.Empty):
      # manager shutdown or close called or queue empty
      pass

  def _get_compiled_pattern_list(self,
                                 pattern_list: List[str]) -> List[re.Pattern]:
    """Return compiled regexps objects for the given regex pattern list.

    Args:
        pattern_list: list of regular expressions to compile.

    Returns:
        list: compiled regular expressions.

    Raises:
        DeviceError: invalid regular expression provided.
    """
    compiled_list = []
    for pattern in pattern_list:
      try:
        compiled_pattern = re.compile(pattern, re.DOTALL | re.MULTILINE)
        compiled_list.append(compiled_pattern)
      except re.error as err:
        raise errors.DeviceError("Device {} expect failed. "
                                 "Invalid regex pattern {}. Error {!r}".format(
                                     self._device_name, pattern, err))
    return compiled_list

  def _send_command_to_device(self, command: str, port: int = 0) -> None:
    """Send command to port (transport) specified.

    Args:
        command: to be sent to port(transport)
        port: selecting which transport to send command to
    """
    transport = self._transport_processes[port]
    transport.send_command(transport_process.CMD_TRANSPORT_WRITE, command)

  @decorators.CapabilityLogDecorator(logger, level=decorators.DEBUG)
  def delete_last_transport_process(self) -> None:
    """Stops and deletes the last transport process in self._transport_processes.

    Note:
        Just stopping a transport process does not delete it.
        All stopped processes are typically reopened after a device reboot.
        The process must be deleted to ensure it is not reopened after a
        device reboot.

    Since we're using process numbers to identify the transport, deleting
    any transport other than the last one will cause some other transports
    in the transport list to shift their transport number by 1, breaking
    their usage. To prevent this, allow deleting only the last process for
    now. The proper solution would be to use some other form of
    identification for processes.

    Raises:
        DeviceError: if there's no transport process to delete.
    """
    if self._transport_processes:  # pylint: disable=using-constant-test
      last_proc_num = len(self._transport_processes) - 1
      self.stop_transport_process(last_proc_num)
      del self._transport_processes[last_proc_num]
    else:
      raise errors.DeviceError("There are no transport processes.")

  @decorators.CapabilityLogDecorator(logger, level=decorators.DEBUG)
  def start_transport_process(self, process_num: int) -> None:
    """Start the transport process at position process_num in transport list.

    Args:
        process_num: position in self._transport_processes list. This position
          is returned by a prior self.add_transport_process() call.

    Raises:
        DeviceError: if process_num has an invalid value.
    """
    self._validate_port(process_num, self.start_transport_process.__name__)
    if not self._transport_processes[process_num].is_started():
      self._transport_processes[process_num].start()

  @decorators.CapabilityLogDecorator(logger, level=decorators.DEBUG)
  def stop_transport_process(self, process_num: int) -> None:
    """Stop the transport process.

    Args:
        process_num: number of transport to stop.
    """
    self._validate_port(process_num, self.stop_transport_process.__name__)
    process = self._transport_processes[process_num]
    if process.is_started():
      process.stop()

  def _start_processes(self) -> None:
    """Starts all Switchboard processes if not already started.

    Should only be called from health_check().
    """
    all_processes = self._transport_processes_cache + [
        self._log_writer_process_cache, self._log_filter_process_cache
    ]
    processes_to_start = [
        process for process in all_processes
        if process is not None and not process.is_started()
    ]
    for process in processes_to_start:
      process.start(wait_for_start=False)
    # b/207400270: with "spawn", each process takes ~1.5s to become responsive.
    # To speed up the combined process start time, start each process without
    # waiting for it to become responsive and then wait for all processes to
    # become responsive to parallelize process startup.
    try:
      for process in processes_to_start:
        process.wait_for_start()
    except RuntimeError:
      # If any process fails to start, terminate all of them to clean up.
      for process in processes_to_start:
        process.terminate()
      raise

  def _stop_processes(self) -> None:
    """Stop all Switchboard processes."""
    # Use _cache objects here because this function is touched by close().
    if self._transport_processes_cache:
      logger.info("{} closing switchboard processes".format(self._device_name))
      # Stop and delete all processes.
      # Public functions are avoided here to avoid hitting a non-cache object
      # which will trigger health_check.
      for process in self._transport_processes_cache:
        if process.is_started():
          process.stop()
      self._transport_processes_cache = []
    if self._log_writer_process_cache:
      if self._log_writer_process_cache.is_started():
        self._log_writer_process_cache.stop()
      self._log_writer_process_cache = None
    if self._log_filter_process_cache:
      if self._log_filter_process_cache.is_started():
        self._log_filter_process_cache.stop()
      self._log_filter_process_cache = None

  def _validate_port(self, port: int, function_name: str) -> None:
    """Validates the user input (port number).

    Args:
      port: port number(position of transport in transport list)
      function_name: name of function calling _validate_port

    Raises:
      DeviceError: if port number is not valid OR
    """
    basic_error = "Device {} {} failed. ".format(self._device_name,
                                                 function_name)
    if not isinstance(port, int):
      raise errors.DeviceError(basic_error +
                               "Invalid port type. Expected: int, found: {}."
                               .format(type(port).__name__))
    elif port < 0 or port >= len(self._transport_processes):
      raise errors.DeviceError(
          basic_error +
          "Invalid port number. Expected: [0..{}), found: {}.".format(
              len(self._transport_processes), port))

  def _toggle_raw_data(self):
    # pylint: disable=not-an-iterable
    for transport in self._transport_processes:
      transport.toggle_raw_data()
    # pylint: enable=not-an-iterable
