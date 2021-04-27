# Copyright 2021 Google LLC
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

"""Interface for the Switchboard capability.

Switchboard is the backbone of all device interaction.
It provides the ability to interact with devices using standardized transport,
button, and expect APIs.

By separating these standardized APIs we can more easily test the logic and
eventually unit test device classes independent of hardware.

Switchboard implementation resides in gazoo_device/switchboard/switchboard.py.
"""
import abc
from typing import List

from gazoo_device import config
from gazoo_device.capabilities.interfaces import capability_base
from gazoo_device.switchboard import line_identifier

MODE_TYPE_ALL = "all"
MODE_TYPE_ANY = "any"
MODE_TYPE_SEQUENTIAL = "sequential"
VERIFY_METHOD_MD5SUM = "md5sum"


class SwitchboardBase(capability_base.CapabilityBase):
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

  @abc.abstractmethod
  def add_log_note(self, note):
    """Adds given note to device log file.

    Args:
        note (str): to write to the log file
    """

  @abc.abstractmethod
  def add_new_filter(self, filter_path):
    """Adds new log filter at path specified to LogFilterProcess.

    Args:
        filter_path (str): filter file to add

    Raises:
        RuntimeError: if LogFilterProcess is not available or running.
        ValueError: if filter_path doesn't exist
    """

  @abc.abstractmethod
  def click(self, button, duration=0.5, port=0):
    """Press and release the button for the duration and port specified.

    Args:
        button (str): button to press and release
        duration (float): seconds to wait before releasing button
        port (int): which port to click on, 0 or 1.

    Raises:
        DeviceError: If buttons are not supported on the device or
                     button, duration, or port values are invalid
    """

  @abc.abstractmethod
  def click_and_expect(self,
                       button,
                       pattern_list,
                       duration=0.5,
                       timeout=30.0,
                       searchwindowsize=config.SEARCHWINDOWSIZE,
                       expect_type="log",
                       port=0,
                       mode="any",
                       raise_for_timeout=False):
    """Press and release button, log lines matching patterns are returned.

    Args:
        button (str): button to press and release
        pattern_list (list): list of regex expressions to look for in the
          lines
        duration (int): seconds to press button before releasing it
        timeout (float): seconds to look for the patterns
        searchwindowsize (int): number of the last bytes to look at
        expect_type (str): 'log', 'response', or 'all'
        port (int): which port to send on, 0 or 1
        mode (str): type of expect to run ("any", "all" or "sequential")
        raise_for_timeout (bool): Raise an exception if the expect times out

    Raises:
        DeviceError: If buttons are not supported on the device or
                     other arguments are invalid.

    Returns:
        ExpectResponse: Object with values for the following attributes:
           .index (int): the index of the expected pattern (None if
           timeout).
           .timedout (bool): indicating whether it timed out.
           .time_elapsed (int): number of seconds between start and finish.
           .match (str): re.group of pattern match.
           .before (str): all the characters looked at before the match.
           .after (str):  all the characters after the first matching
           character.
           .remaining (list): remaining patterns not matched
           .match_list (list): re.search pattern MatchObjects

    Note:
        Flushes the expect queue before and after an expect. Starts up
        expect queue right before clicking button to catch fast responses.
    """

  @abc.abstractmethod
  def close(self):
    """Shuts down the subprocesses and closes the transports.

    NOTE:
        The current implementation relies on queues being garbage collected.
        Instead of explicitly closing the queues, all queue references MUST
        be deleted to
        release the queues and prevent a memory leak!
    """

  @abc.abstractmethod
  def close_all_transports(self):
    """Leaves the switchboard architecture intact but closes the communication FDs.

    This is used prior to the connections being closed, such as disconnecting an
    ethernet or a serial connection. Only closes the ones open so if
    device.close has already occurred, nothing will be closed.
    """

  @abc.abstractmethod
  def close_transport(self, port=0):
    """Closes the transport specified.

    Args:
        port (int or str): the transport port to close

    Raises:
        DeviceError: If port value is invalid or out of range.
    """

  @abc.abstractmethod
  def do_and_expect(self,
                    func,
                    func_args,
                    func_kwargs,
                    pattern_list,
                    timeout=30.0,
                    searchwindowsize=config.SEARCHWINDOWSIZE,
                    expect_type=line_identifier.LINE_TYPE_LOG,
                    mode=MODE_TYPE_ANY,
                    raise_for_timeout=False):
    """Executes function with given args, blocks until expect matches or timeout occurs.

    Args:
        func (method): name of function to be called
        func_args (list): positional arguments specified to be passed to
          function
        func_kwargs (dict): keyword arguments specified to be passed to
          function
        pattern_list (list): list of regex expressions to look for in the
          lines
        timeout (float): seconds to look for the patterns
        searchwindowsize (int): number of the last bytes to look at
        expect_type (str): 'log', 'response', or 'all'
        mode (str): type of expect to run ("any", "all" or "sequential")
        raise_for_timeout (bool): Raise an exception if the expect times out

    Returns:
        ExpectResponse: Object with values for the following attributes:
           .index (int): the index of the expected pattern (None if
           timeout).
           .timedout (bool): indicating whether it timed out.
           .time_elapsed (int): number of seconds between start and finish.
           .match (str): re.group of pattern match.
           .before (str): all the characters looked at before the match.
           .after (str):  all the characters after the first matching
           character.
           .remaining (list): remaining patterns not matched
           .match_list (list): re.search pattern MatchObjects

    Raises:
        DeviceError: If func is not callable
                     If other arguments are invalid

    Note:
        Input parameter "func" MUST NOT call "shell" nor another
        "core.xxx_expect" method so as to avoid the nested "flush" problem
        described in 'NEP-2343'.
    """

  @abc.abstractmethod
  def echo_file_to_transport(self,
                             source_file,
                             destination_path,
                             port=0,
                             bytes_per_echo=50):
    r"""Transfers file to transport specified using echo commands.

    Args:
        source_file (path): to the file to transfer
        destination_path (path): to transfer file to on device
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

  @abc.abstractmethod
  def ensure_serial_paths_unlocked(self, communication_addresses: List[str]):
    """Ensures serial paths are longer locked by switchboard process after device is closed."""

  @abc.abstractmethod
  def expect(self,
             pattern_list,
             timeout=30.0,
             searchwindowsize=config.SEARCHWINDOWSIZE,
             expect_type=line_identifier.LINE_TYPE_ALL,
             mode=MODE_TYPE_ANY,
             raise_for_timeout=False):
    """Block until a regex pattern is matched or until a timeout time has elapsed.

    Args:
        pattern_list (list): list of regex expressions to look for in the
          lines
        timeout (float): seconds to look for the patterns
        searchwindowsize (int): number of the last bytes to look at
        expect_type (str): 'log', 'response', or 'all'
        mode (str): type of expect to run ("any", "all" or "sequential")
        raise_for_timeout (bool): Raise an exception if the expect times out

    Raises:
        DeviceError: if arguments are not valid.

    Returns:
        ExpectResponse: Object with values for the following attributes:
           .index (int): the index of the expected pattern (None if
           timeout).
           .timedout (bool): indicating whether it timed out.
           .time_elapsed (int): number of seconds between start and finish.
           .match (str): re.group of pattern match.
           .before (str): all the characters looked at before the match.
           .after (str):  all the characters after the first matching
           character.
           .remaining (list): remaining patterns not matched
           .match_list (list): re.search pattern MatchObjects

    Note:
        Flushes the expect queue before and after an expect.
    """

  @abc.abstractmethod
  def get_line_identifier(self):
    """Returns the line identifier currently used by Switchboard."""

  @property
  @abc.abstractmethod
  def number_transports(self) -> int:
    """Returns the number of transport processes used by Switchboard."""

  @abc.abstractmethod
  def open_all_transports(self):
    """Opens the communication FDs, assuming switchboard architecture is intact.

    This is used after a physical connection has been reopened, such as
    reconnecting an ethernet or a serial connection.
    Only opens the ones closed so if device.close has already occurred, nothing
    will be opened.
    """

  @abc.abstractmethod
  def open_transport(self, port=0, timeout=30.0):
    """Opens the transport specified.

    Args:
        port (int or str): the transport port to open
        timeout (float): how long to wait for port to open.

    Raises:
        DeviceError: If port value is invalid or out of range.
    """

  @abc.abstractmethod
  def press(self, button, wait=0.0, port=0):
    """Presses the button for the port specified and waits the time specified.

    Args:
        button (str): button to press
        wait (float): seconds to wait before returning
        port (int): which port to click on, 0 or 1

    Raises:
        DeviceError: If buttons are not supported on the device or
                     button, wait, or port values are invalid
    """

  @abc.abstractmethod
  def press_and_expect(self,
                       button,
                       pattern_list,
                       wait=0.0,
                       timeout=30.0,
                       searchwindowsize=config.SEARCHWINDOWSIZE,
                       expect_type="log",
                       port=0,
                       mode="any"):
    """Press button and expect for pattern_list and other arguments provided.

    Args:
        button (str): button to press
        pattern_list (list): list of regex expressions to look for in the
          lines
        wait (float): seconds to wait
        timeout (float): Seconds to look for the patterns
        searchwindowsize (int): Number of the last bytes to look at
        expect_type (str): 'log', 'response', or 'all'
        port (int): Which port to send on, 0 or 1
        mode (str): type of expect to run ("any", "all" or "sequential")

    Raises:
        DeviceError: If buttons are not supported on the device or
                     button, wait, port, or expect values are invalid

    Returns:
        ExpectResponse: Object with values for the following attributes:
           .index (int): the index of the expected pattern (None if
           timeout).
           .timedout (bool): indicating whether it timed out.
           .time_elapsed (int): number of seconds between start and finish.
           .match (str): re.group of pattern match.
           .before (str): all the characters looked at before the match.
           .after (str):  all the characters after the first matching
           character.
           .remaining (list): remaining patterns not matched
           .match_list (list): re.search pattern MatchObjects

    Note:
        Flushes the expect queue before and after an expect. Starts up
        expect queue right before pressing button to catch fast responses.
    """

  @abc.abstractmethod
  def release(self, button, port=0):
    """Release the button for the port specified.

    Args:
        button (str): button to release
        port (int): Which port to release button on, 0 or 1

    Raises:
        DeviceError: If buttons are not supported on the device or
                     button or port values are invalid
    """

  @abc.abstractmethod
  def release_and_expect(self,
                         button,
                         pattern_list,
                         timeout=30.0,
                         searchwindowsize=config.SEARCHWINDOWSIZE,
                         expect_type="log",
                         port=0,
                         mode="any"):
    """Release button, matches pattern_list in loglines as specified by expect_type.

    Args:
        button (str): button to release
        pattern_list (list): list of regex expressions to look for in the
          lines
        timeout (float): seconds to look for the patterns
        searchwindowsize (int): number of the last bytes to look at
        expect_type (str): 'log', 'response', or 'all'
        port (int): which port to send on, 0 or 1
        mode (str): type of expect to run ("any", "all" or "sequential")

    Raises:
        DeviceError: If buttons are not supported on the device or
                     button, port, or expect values are invalid

    Returns:
        ExpectResponse: Object with values for the following attributes:
           .index (int): the index of the expected pattern (None if
           timeout).
           .timedout (bool): indicating whether it timed out.
           .time_elapsed (int): number of seconds between start and finish.
           .match (str): re.group of pattern match.
           .before (str): all the characters looked at before the match.
           .after (str):  all the characters after the first matching
           character.
           .remaining (list): remaining patterns not matched
           .match_list (list): re.search pattern MatchObjects

    Note:
        Flushes the expect queue before and after an expect. Starts up
        expect queue right before releasing button to catch fast responses.
    """

  @abc.abstractmethod
  def send(self, command, port=0, slow=False, add_newline=True, newline="\n"):
    """Sends the command to the device on the port (transport) specified.

    Args:
        command (str): to send to the device
        port (int): or transport to send command to
        slow (bool): flag indicating command should be sent byte-by-byte
        add_newline (bool): flag indicating newline should be added to
          command if missing
        newline (str): character to check for and add if missing at the end
          of the command

    Raises:
        DeviceError: if port specified is an invalid value or out of
                     range of the available ports
    """

  @abc.abstractmethod
  def send_and_expect(self,
                      command,
                      pattern_list,
                      timeout=30.0,
                      searchwindowsize=config.SEARCHWINDOWSIZE,
                      expect_type=line_identifier.LINE_TYPE_ALL,
                      mode=MODE_TYPE_ANY,
                      port=0,
                      slow=False,
                      add_newline=True,
                      newline="\n",
                      command_tries=1,
                      raise_for_timeout=False):
    r"""Sends the command and expects on the patterns provided.

    Note: this method does not prepend the command with a wakeup character
    which some devices require. The reason this may be needed is because
    some devices go into a sleep state to save energy and will wakeup on
    receiving the first character sent to it which means the character won't
    get registered into the command buffer. This can be dealt with by
    prepending the command with a nop character that won't affect the
    command being executed in the case that the device has already woken up.
    If there is an issue with this method, try adding "\n" in front of the
    command. E.g. "\nsome_command"

    Args:
        command (str): command to send to the device
        pattern_list (list): list of regex expressions to look for in the
          lines
        timeout (float): Seconds to look for the patterns
        searchwindowsize (int): Number of the last bytes to look at
        expect_type (str): 'log', 'response', or 'all'
        mode (str): type of expect to run ("any", "all" or "sequential")
        port (int): Which port to send on, 0 or 1
        slow (bool): flag indicating command should be sent byte-by-byte
        add_newline (bool): flag indicating newline should be added to
          command if missing
        newline (str): character to check for and add if missing at the end
          of the command
        command_tries (int): The number of tries to send the command if it
          times out.
        raise_for_timeout (bool): Raise an exception if the expect times out

    Raises:
        DeviceError: if port specified or other expect arguments are
                     invalid, or timed out and raise_for_timeout was True.

    Returns:
        ExpectResponse: Object with values for the following attributes:
           .index (int): the index of the expected pattern (None if
           timeout).
           .timedout (bool): indicating whether it timed out.
           .time_elapsed (int): number of seconds between start and finish.
           .match (str): re.group of pattern match.
           .before (str): all the characters looked at before the match.
           .after (str):  all the characters after the first matching
           character.
           .remaining (list): remaining patterns not matched
           .match_list (list): re.search pattern MatchObjects

    Note:
        Flushes the expect queue before and after an send.
    """

  @abc.abstractmethod
  def set_max_log_size(self, max_log_size):
    """Sets the max_log_size value to the value provided.

    Args:
        max_log_size (int): the max log size to use for log rotation.

    Raises:
        ValueError: if max_log_size is not an integer value
        RuntimeError: if log writer process is not running

    Note:
        A max_log_size of 0 means no log rotation should ever occur.
    """

  @abc.abstractmethod
  def start_new_log(self, log_path):
    """Changes log filter and writer to use a new log path provided.

    Args:
        log_path (str): to log file to switch to

    Raises:
        RuntimeError: if LogWriterProcess is not available or running.
    """

  @abc.abstractmethod
  def transport_jlink_flash(self, image_path, port=0):
    """Sends the flash command to the 'J-Link' transport.

    Args:
        image_path (str): path to the image file to be flashed onto the
          device.
        port (int): the transport port to send the command to.
    """

  @abc.abstractmethod
  def transport_jlink_reset(self, port=0):
    """Sends the reset command to the J - Link transport.

    Args:
        port(int): the transport port to send the command to.
    """

  @abc.abstractmethod
  def transport_serial_set_baudrate(self, new_baudrate, port=0):
    """Sets the serial interface baudrate to a different baudrate.

    Args:
        new_baudrate(int): new baudrate to be set, generally 115200 or
          921600
        port(int or str): the transport port to open

    Raises:
        DeviceError
    """

  @abc.abstractmethod
  def transport_serial_send_xon(self, port=0):
    """Sends the XON control character to the serial interface.

    Args:
        port(int or str): the transport port to open
    """

  @abc.abstractmethod
  def transport_serial_send_xoff(self, port=0):
    """Sends the XOFF control character to the serial interface.

    Args:
        port(int or str): the transport port to open
    """

  @abc.abstractmethod
  def transport_serial_send_break_byte(self, port=0):
    """Sends the break control character to the serial interface (Ctrl + C).

    Args:
        port(int or str): the transport port to open
    """

  @abc.abstractmethod
  def verify_file_on_transport(self,
                               source_file,
                               destination_path,
                               port=0,
                               method=VERIFY_METHOD_MD5SUM):
    """Verifies source file contents matches destination_path on transport using method.

    Args:
        source_file(path): to compare content to on transport
        destination_path(path): to file to verify on transport
        port(int or str): the transport port to open
        method(str): the method to use to verify destination_path

    Raises:
        DeviceError: If source_file doesn't exist, can't be opened, or
                     the port or method values are invalid or out of range.

    Returns:
        bool: A boolean status indicating verification was successful.

    Note:
        The caller is responsible for preparing the device to receive one
        of the following verification commands::

            md5sum < destination_path >
    """

  @abc.abstractmethod
  def xmodem_file_to_transport(self, source_file, port=0):
    """Transfers file to transport specified using the XModem protocol.

    Args:
        source_file(path): to the file to transfer
        port(int or str): the transport port to open

    Raises:
        DeviceError: If source_file doesn't exist, can't be opened, or
                     the port value provided is invalid or out of range.

    Returns:
        bool: A boolean status indicating xmodem transfer was successful.

    Note:
        The caller is responsible for putting the transport into XModem
        transfer mode before calling this method.
    """

  @abc.abstractmethod
  def add_transport_process(self, transport, **transport_process_kwargs):
    """Add a new transport process to the list of transport processes.

    Args:
        transport(Transport): transport to the device for this process
        **transport_process_kwargs(dict): keyword arguments to the transport
          process
    transport_process_kwargs can be:
        framer(DataFramer): DataFramer derived classes to use to frame
          incoming raw data into raw lines. Defaults to None.
        partial_line_timeout(float): time in seconds to wait before adding
          partial lines to raw_data_queue and log_queue. Defaults to
          transport_process.PARTIAL_LINE_TIMEOUT.
        read_timeout(float): time to wait in seconds for transport reads.
          Defaults to to transport_process._READ_TIMEOUT
        max_read_bytes(int): to attempt to read on each transport read call.
          Defaults to transport_process._MAX_READ_BYTES
        max_write_bytes(int): to attempt to write on each transport write
          call. Defaults to transport_process._MAX_WRITE_BYTES

    Returns:
        int: position of newly added transport process in list of transport
        processes("port")
    """

  @abc.abstractmethod
  def delete_last_transport_process(self):
    """Stops and deletes the last transport process in self._transport_processes.

    Note:
        Just stopping a transport process does not delete it.
        All stopped processes are typically reopened after a device reboot.
        The process must be deleted to ensure it is not reopened after a
        device reboot.

    Since we're using process numbers to identify the transport, deleting any
    transport other than the last one will cause some other transports in the
    transport list to shift their transport number by 1, breaking their usage.
    To prevent this, allow deleting only the last process for now. The proper
    solution would be to use some other form of identification for processes.

    Raises:
        DeviceError: if there's no transport process to delete.
    """

  @abc.abstractmethod
  def start_transport_process(self, process_num):
    """Start the transport process at position process_num in transport list.

    Args:
        process_num(int): position in self._transport_processes list. This
          position is returned by a prior self.add_transport_process() call.

    Raises:
        DeviceError: if process_num has an invalid value.
    """

  @abc.abstractmethod
  def stop_transport_process(self, process_num):
    """Stop the transport process.

    Args:
        process_num(int): number of transport to stop.
    """
