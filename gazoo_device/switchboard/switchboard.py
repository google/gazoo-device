# Copyright 2020 Google LLC
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

"""Switchboard is the backbone of all device interaction.

It provides the ability to interact with devices using standardized transport, button, and
expect APIs.

By separating these standardized APIs we can more easily test the logic and
eventually unit test device classes independent of hardware.
"""
from __future__ import absolute_import
import io
import multiprocessing
import os
import re
import signal
import subprocess
import time

from gazoo_device import config
from gazoo_device import errors
from gazoo_device import gdm_logger

from gazoo_device.switchboard import jlink_transport
from gazoo_device.switchboard import line_identifier
from gazoo_device.switchboard import log_process
from gazoo_device.switchboard import serial_transport
from gazoo_device.switchboard import switchboard_process
from gazoo_device.switchboard import transport_process
from gazoo_device.switchboard import transport_properties
from gazoo_device.switchboard.expect_response import ExpectResponse
from gazoo_device.utility import common_utils
from gazoo_device.utility import usb_utils

import six
from six.moves import range
import six.moves.queue
import xmodem

logger = gdm_logger.get_gdm_logger("core")

MODE_TYPE_ALL = "all"
MODE_TYPE_ANY = "any"
MODE_TYPE_SEQUENTIAL = "sequential"
VERIFY_METHOD_MD5SUM = "md5sum"
_VALID_EXPECT_TYPES = [line_identifier.LINE_TYPE_ALL,
                       line_identifier.LINE_TYPE_LOG,
                       line_identifier.LINE_TYPE_RESPONSE]
_VALID_EXPECT_MODES = [MODE_TYPE_ALL, MODE_TYPE_ANY, MODE_TYPE_SEQUENTIAL]
_VERIFY_METHODS = [VERIFY_METHOD_MD5SUM]


def _ensure_has_newline(cmd, add_newline=True, newline="\n"):
    """Ensure command ends with a newline (if add_newline is True)."""
    if add_newline and not cmd.endswith(('\n', '\x00', r'\0', newline)):
        cmd += newline
    return cmd


def _get_pattern_index(compiled_list, match_list, mode):
    """Return index of compiled regex pattern that matches the match provided.

    Args:
        compiled_list (list): of regular expression patterns to match
        match_list (list): of Match objects previously found
        mode (str): type of expect to use ("any", "all", or "sequential")

    Returns:
        int: The index to a matching compile regex pattern in compiled_list
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


def _get_pattern_list(compiled_list, match_list, mode):
    """Returns pattern_list to be used in expect search using information provided.

    Args:
        compiled_list (list): of regular expression patterns
        match_list (list): of Match objects previously found
        mode (str): type of expect to use ("any", "all", or "sequential")

    Returns:
        list: A list of compiled regular expression patterns from compiled_list
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


def _get_missing_patterns(compiled_list, match_list, mode):
    """Returns compiled regex patterns from compiled_list that are not in match_list.

    Args:
        compiled_list (list): of regular expression patterns
        match_list (list): of Match objects previously found
        mode (str): type of expect to use ("any", "all", or "sequential")

    Returns:
        list: A list of compiled regex patterns from compiled_list that are not
              in match_list.
    """

    if mode == MODE_TYPE_SEQUENTIAL:
        return compiled_list[len(match_list):]
    else:
        matched_patterns = [match.re for match in match_list]
        return [pattern for pattern in compiled_list if pattern not in matched_patterns]


def _get_pattern_strings(compiled_list):
    """Returns regex pattern strings from a list of compiled regex pattern objects.

    Args:
        compiled_list (list): of regular expression patterns to extract strings from

    Returns:
        list: A list of regex pattern strings extracted from compiled list of
              regex pattern objects.
    """

    return [pattern.pattern for pattern in compiled_list]


class Switchboard(object):
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

    def __init__(self,
                 device_name,
                 exception_queue,
                 transport_list,
                 log_path,
                 framer_list=None,
                 identifier=None,
                 button_list=None,
                 parser=None,
                 partial_line_timeout_list=None,
                 force_slow=False,
                 max_log_size=0):
        """Initialize the Switchboard with the parameters provided.

        Args:
            device_name (str): name of the device
            exception_queue (Queue): a single exception queue to share for all
                                     subprocesses to report exceptions into
            transport_list (list): of Transport type classes to use for
                                   this device.
            log_path (str): path/to/log/file to store device logs
            framer_list (list): list of DataFramer derived classes to use to
                                frame incoming raw data into raw lines.
            identifier (LineIdentifier): LineIdentifier derived class to use to
                                         identify log and response lines from
                                         device for expect_type filtering.
            button_list (list): of Button type classes to use to click, press,
                                release, is_valid, valid_buttons, and close
                                methods defined for button instigation, button
                                name verification and listing, and closing.
            parser (Parser): log filtering object which must have "process_line".
            partial_line_timeout_list (list): of seconds to wait before writing
                                              partial transport line received.
            force_slow (bool): flag indicating all sends should assume slow=True.
            max_log_size (int): maximum size in bytes before performing log rotation.

        Note:
            A max_log_size of 0 means no log rotation should ever occur.
        """
        # Using [] as a default argument is dangerous
        if framer_list is None:
            framer_list = []
        if partial_line_timeout_list is None:
            partial_line_timeout_list = []

        self.device_name = device_name
        self.log_path = log_path
        self._button_list = button_list
        self._force_slow = force_slow
        self._identifier = identifier or line_identifier.AllUnknownIdentifier()
        time.sleep(.1)
        common_utils.run_before_fork()
        self._mp_manager = multiprocessing.Manager()
        common_utils.run_after_fork_in_parent()
        self._transport_processes = []
        self._log_queue = self._mp_manager.Queue()
        self._raw_data_queue = self._mp_manager.Queue()
        self._raw_data_queue_users = 0
        self._transport_process_id = 0
        self._exception_queue = exception_queue

        self._add_transport_processes(transport_list, framer_list,
                                      partial_line_timeout_list)
        self._add_log_writer_process(log_path, max_log_size)
        self._add_log_filter_process(parser, log_path)
        self._start_processes()

    def __del__(self):
        self.close()

    def add_log_note(self, note):
        """Adds given note to device log file.

        Args:
            note (str): to write to the log file
        """

        if note[-1] == "\n":
            log_message = "Note: {}".format(note)
        else:
            log_message = "Note: {}\n".format(note)
        try:
            log_process.log_message(self._log_queue, log_message, "M")
        except (AttributeError, IOError):  # manager shutdown or close called
            pass

    def add_new_filter(self, filter_path):
        """Adds new log filter at path specified to LogFilterProcess.

        Args:
            filter_path (str): filter file to add

        Raises:
            RuntimeError: if LogFilterProcess is not available or running.
            ValueError: if filter_path doesn't exist
        """

        if not os.path.exists(filter_path):
            raise ValueError("Device {} add new filter failed. "
                             "Filter path {} doesn't exist.".
                             format(self.device_name, filter_path))

        if not hasattr(self, "_log_filter_process") or not self._log_filter_process.is_running():
            raise RuntimeError("Device {} add new filter failed. "
                               "Log filter process is not currently running.".
                               format(self.device_name))

        self._log_filter_process.send_command(log_process.CMD_ADD_NEW_FILTER, filter_path)
        while (self._log_filter_process.is_running()
               and not self._log_filter_process.is_command_done()):
            time.sleep(0.001)

    def click(self, button, duration=0.5, port=0):
        """Press and release the button for the duration and port specified.

        Args:
            button (str): button to press and release
            duration (float): seconds to wait before releasing button
            port (int): which port to click on, 0 or 1.

        Raises:
            GazooDeviceError: If buttons are not supported on the device or
                             button, duration, or port values are invalid
        """

        self._check_button_args("click", button, port, duration=duration)

        log_message = "click button {} on port {} for duration {} - begin".format(
            button, port, duration)
        self.add_log_note(log_message)
        self._button_list[port].click(button, duration)
        log_message = "click button {} on port {} for duration {} - end".format(
            button, port, duration)
        self.add_log_note(log_message)

    def click_and_expect(self,
                         button,
                         pattern_list,
                         duration=0.5,
                         timeout=30.0,
                         searchwindowsize=config.SEARCHWINDOWSIZE,
                         expect_type='log',
                         port=0,
                         mode="any",
                         raise_for_timeout=False):
        """Press and release button, log lines matching patterns are returned.

        Args:
            button (str): button to press and release
            pattern_list (list): list of regex expressions to look for in the lines
            duration (int): seconds to press button before releasing it
            timeout (float): seconds to look for the patterns
            searchwindowsize (int): number of the last bytes to look at
            expect_type (str): 'log', 'response', or 'all'
            port (int): which port to send on, 0 or 1
            mode (str): type of expect to run ("any", "all" or "sequential")
            raise_for_timeout (bool): Raise an exception if the expect times out

        Raises:
            GazooDeviceError: If buttons are not supported on the device or
                             other arguments are invalid.

        Returns:
            ExpectResponse: Object with values for the following attributes:
               .index (int): the index of the expected pattern (None if timeout).
               .timedout (bool): indicating whether it timed out.
               .time_elapsed (int): number of seconds between start and finish.
               .match (str): re.group of pattern match.
               .before (str): all the characters looked at before the match.
               .after (str):  all the characters after the first matching character.
               .remaining (list): remaining patterns not matched
               .match_list (list): re.search pattern MatchObjects

        Note:
            Flushes the expect queue before and after an expect. Starts up
            expect queue right before clicking button to catch fast responses.
        """

        return self.do_and_expect(self.click,
                                  [button],
                                  {"duration": duration, "port": port},
                                  pattern_list,
                                  timeout=timeout,
                                  searchwindowsize=searchwindowsize,
                                  expect_type=expect_type,
                                  mode=mode,
                                  raise_for_timeout=raise_for_timeout)

    def close(self):
        """Shuts down the subprocesses and closes the transports.

        NOTE:
            The current implementation relies on queues being garbage collected.
            Instead of explicitly closing the queues, all queue references MUST be deleted to
            release the queues and prevent a memory leak!
        """
        self._stop_processes()
        if hasattr(self, "_button_list") and self._button_list:
            for button in self._button_list:
                button.close()
            self._button_list = []
        if hasattr(self, "_raw_data_queue") and self._raw_data_queue:
            delattr(self, "_raw_data_queue")
        if hasattr(self, "_log_queue") and self._log_queue:
            delattr(self, "_log_queue")
        if hasattr(self, "_exception_queue") and self._exception_queue:
            delattr(self, "_exception_queue")
        if hasattr(self, "_mp_manager") and self._mp_manager:
            self._mp_manager.shutdown()
            delattr(self, "_mp_manager")

    def close_all_transports(self):
        """Leaves the switchboard architecture intact but closes the communication FDs.

        This is used prior to the connections being closed,
        such as disconnecting an ethernet or powering off the device.
        Only closes the ones open so if device.close has already occurred, nothing will be closed.
        """
        num = self.number_transports
        logger.info("{} closing {} switchboard transports".format(self.device_name, num))
        for port in range(num):
            self.close_transport(port=port)

    def close_transport(self, port=0):
        """Closes the transport specified.

        Args:
            port (int or str): the transport port to close

        Raises:
            GazooDeviceError: If port value is invalid or out of range.
        """
        self._validate_port(port, self.close_transport.__name__)

        log_message = "closing transport for port {}".format(port)
        self.add_log_note(log_message)
        try:
            if self._button_list:
                button = self._button_list[port]
                button.close()
        except IndexError:
            pass  # If _button_list does not have an entry for [port], there is nothing to close

        start_time = time.time()
        transport_proc = self._transport_processes[port]
        transport_proc.send_command(transport_process.CMD_TRANSPORT_CLOSE)
        while transport_proc.is_open():
            time.sleep(0.01)
        log_message = "closed transport for port {} in {}s".format(port, time.time() - start_time)
        self.add_log_note(log_message)

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
            func_args (list): positional arguments specified to be passed to function
            func_kwargs (dict): keyword arguments specified to be passed to function
            pattern_list (list): list of regex expressions to look for in the lines
            timeout (float): seconds to look for the patterns
            searchwindowsize (int): number of the last bytes to look at
            expect_type (str): 'log', 'response', or 'all'
            mode (str): type of expect to run ("any", "all" or "sequential")
            raise_for_timeout (bool): Raise an exception if the expect times out

        Returns:
            ExpectResponse: Object with values for the following attributes:
               .index (int): the index of the expected pattern (None if timeout).
               .timedout (bool): indicating whether it timed out.
               .time_elapsed (int): number of seconds between start and finish.
               .match (str): re.group of pattern match.
               .before (str): all the characters looked at before the match.
               .after (str):  all the characters after the first matching character.
               .remaining (list): remaining patterns not matched
               .match_list (list): re.search pattern MatchObjects

        Raises:
            GazooDeviceError: If func is not callable
                             If other arguments are invalid

        Note:
            Input parameter "func" MUST NOT call "shell" nor another
            "core.xxx_expect" method so as to avoid the nested "flush"
            problem described in 'NEP-2343'.
        """

        if not callable(func):
            raise errors.GazooDeviceError("Device {} do_and_expect failed. "
                                          "Function: {} is not callable.".
                                          format(self.device_name, func))
        self._check_expect_args(pattern_list,
                                timeout,
                                searchwindowsize,
                                expect_type,
                                mode)
        compiled_list = self._get_compiled_pattern_list(pattern_list)

        try:
            self._enable_raw_data_queue()
            func(*func_args, **func_kwargs)
            return self._expect(compiled_list,
                                timeout,
                                searchwindowsize,
                                expect_type,
                                mode,
                                raise_for_timeout=raise_for_timeout)
        finally:
            self._disable_raw_data_queue()

    def echo_file_to_transport(self, source_file, destination_path, port=0,
                               bytes_per_echo=50):
        r"""Transfers file to transport specified using echo commands.

        Args:
            source_file (path): to the file to transfer
            destination_path (path): to transfer file to on device
            port (int or str): the transport port to open
            bytes_per_echo (int): call to use during file transfer

        Raises:
            GazooDeviceError: If source_file doesn't exist, can't be opened, or
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
            raise errors.GazooDeviceError("Device {} echo file to transport failed. "
                                          "Source file {} doesn't exist.".
                                          format(self.device_name, source_file))
        elif not isinstance(bytes_per_echo, int):
            raise errors.GazooDeviceError("Device {} echo file to transport failed. "
                                          "Expecting int for bytes_per_echo found {} instead.".
                                          format(self.device_name, type(bytes_per_echo)))
        elif bytes_per_echo <= 0:
            raise errors.GazooDeviceError("Device {} echo file to transport failed. "
                                          "Invalid bytes_per_echo value {} expected >0".
                                          format(self.device_name, bytes_per_echo))

        start_time = time.time()
        log_message = ("starting echo transfer of {} for port {} to {}".
                       format(source_file, port, destination_path))
        self.add_log_note(log_message)

        # Read the data in from the file
        try:
            with io.open(source_file, "rb") as in_file:
                data = in_file.read()
        except IOError as err:
            raise errors.GazooDeviceError("Device {} echo file to transport failed. "
                                          "Unable to read {}. "
                                          "Error: {!r}".
                                          format(self.device_name, source_file, err))

        # Create and zero out the file
        cmd_string = "echo -ne > {}\n".format(destination_path)
        echo_pattern1 = r"echo -ne > [/\w.]+"
        result = self.send_and_expect(cmd_string,
                                      [echo_pattern1],
                                      port=port,
                                      expect_type="response")
        if result.timedout:
            raise errors.GazooDeviceError("Device {} echo file to transport failed. "
                                          "Unable to create/erase file {} on device. "
                                          "Output: {!r}".format(self.device_name,
                                                                destination_path,
                                                                result.before))

        # Loop through the data at bytes_per_echo chunks at a time
        echo_pattern2 = r'echo -ne ".*"\s.*\s[/\w.]+'
        data_indexes = list(range(0, len(data), bytes_per_echo)) + [len(data)]
        for data_index in range(1, len(data_indexes)):
            start_index = data_indexes[data_index - 1]
            end_index = data_indexes[data_index]
            if six.PY2:
                data_chunk = u"".join([u"\\x%02x" % ord(byte)
                                       for byte in data[start_index:end_index]])
            else:  # PY3
                data_chunk = u"".join([u"\\x%02x" % byte
                                       for byte in data[start_index:end_index]])
            cmd_string = "echo -ne \"{}\" >> {}\n".format(data_chunk, destination_path)
            result = self.send_and_expect(cmd_string,
                                          [echo_pattern2],
                                          port=port,
                                          expect_type="response")
            if result.timedout:
                raise errors.GazooDeviceError("Device {} echo file to transport failed. "
                                              "Unable to echo bytes {!r} to file {} "
                                              "Output: {!r}".format(self.device_name,
                                                                    data_chunk,
                                                                    destination_path,
                                                                    result.before))
        log_message = ("finished echo transfer of {} for port {} in {}s".
                       format(source_file, port, time.time() - start_time))
        self.add_log_note(log_message)

    def ensure_path_unlocked(self, name, path):
        """Ensures path is no longer locked by switchboard process after device is closed.

        Args:
          name (str): device name.
          path (str): serial path on host machine.
        """
        if path not in usb_utils.get_all_serial_connections():
            return  # only active serial connections have locks

        try:
            output = subprocess.check_output(["lsof", path],
                                             stderr=subprocess.STDOUT)
            output = output.decode("utf-8", "replace").splitlines()
        except (subprocess.CalledProcessError, ImportError):  # process does not exist
            return

        process_number = output[-1].split()[1]  # process id
        try:
            number = int(process_number)
            logger.info("{}'s communication process still exists. Killing process {}".
                        format(name, number))
            os.kill(int(process_number), signal.SIGTERM)
        except ValueError:
            logger.error("{}'s communication process still exists "
                         "but could not parse process number from lsof output correctly. "
                         "Output: {}. Expected process number: {}".format(
                             name, output, process_number))

    def expect(self,
               pattern_list,
               timeout=30.0,
               searchwindowsize=config.SEARCHWINDOWSIZE,
               expect_type=line_identifier.LINE_TYPE_ALL,
               mode=MODE_TYPE_ANY,
               raise_for_timeout=False):
        """Block until a regex pattern is matched or until a timeout time has elapsed.

        Args:
            pattern_list (list): list of regex expressions to look for in the lines
            timeout (float): seconds to look for the patterns
            searchwindowsize (int): number of the last bytes to look at
            expect_type (str): 'log', 'response', or 'all'
            mode (str): type of expect to run ("any", "all" or "sequential")
            raise_for_timeout (bool): Raise an exception if the expect times out

        Raises:
            GazooDeviceError: if arguments are not valid.

        Returns:
            ExpectResponse: Object with values for the following attributes:
               .index (int): the index of the expected pattern (None if timeout).
               .timedout (bool): indicating whether it timed out.
               .time_elapsed (int): number of seconds between start and finish.
               .match (str): re.group of pattern match.
               .before (str): all the characters looked at before the match.
               .after (str):  all the characters after the first matching character.
               .remaining (list): remaining patterns not matched
               .match_list (list): re.search pattern MatchObjects

        Note:
            Flushes the expect queue before and after an expect.
        """

        self._check_expect_args(pattern_list,
                                timeout,
                                searchwindowsize,
                                expect_type,
                                mode)
        compiled_list = self._get_compiled_pattern_list(pattern_list)

        try:
            self._enable_raw_data_queue()
            return self._expect(compiled_list,
                                timeout,
                                searchwindowsize,
                                expect_type,
                                mode,
                                raise_for_timeout=raise_for_timeout)
        finally:
            self._disable_raw_data_queue()

    def get_line_identifier(self):
        return self._identifier

    def log_debug_message(self, note):
        self.add_log_note(note)

    @property
    def number_transports(self):
        return len(self._transport_processes)

    def open_all_transports(self):
        """Opens the communication FDs, assuming switchboard architecture is intact.

        This is used after a physical connection has been reopened,
        such as reconnecting an ethernet or powering on the device.
        Only opens the ones closed so if device.close has already occurred, nothing will be opened.
        """
        num = self.number_transports
        logger.info("{} opening {} switchboard transports".format(self.device_name, num))
        for port in range(num):
            self.open_transport(port=port)

    def open_transport(self, port=0, timeout=30.0):
        """Opens the transport specified.

        Args:
            port (int or str): the transport port to open
            timeout (float): how long to wait for port to open.

        Raises:
            GazooDeviceError: If port value is invalid or out of range.
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
        log_message = "opened transport for port {} in {}s".format(port, time.time() - start_time)
        self.add_log_note(log_message)

    def press(self, button, wait=0.0, port=0):
        """Presses the button for the port specified and waits the time specified.

        Args:
            button (str): button to press
            wait (float): seconds to wait before returning
            port (int): which port to click on, 0 or 1

        Raises:
            GazooDeviceError: If buttons are not supported on the device or
                             button, wait, or port values are invalid
        """

        self._check_button_args("press", button, port, wait=wait)

        log_message = "pressing button {} on port {} and waiting {}s - begin".format(
            button, port, wait)
        self.add_log_note(log_message)
        self._button_list[port].press(button, wait)
        log_message = "pressing button {} on port {} and waiting {}s - end".format(
            button, port, wait)
        self.add_log_note(log_message)

    def press_and_expect(self, button, pattern_list, wait=0.0, timeout=30.0,
                         searchwindowsize=config.SEARCHWINDOWSIZE,
                         expect_type='log', port=0, mode="any"):
        """Press button and expect for pattern_list and other arguments provided.

        Args:
            button (str): button to press
            pattern_list (list): list of regex expressions to look for in the lines
            wait (float): seconds to wait
            timeout (float): Seconds to look for the patterns
            searchwindowsize (int): Number of the last bytes to look at
            expect_type (str): 'log', 'response', or 'all'
            port (int): Which port to send on, 0 or 1
            mode (str): type of expect to run ("any", "all" or "sequential")

        Raises:
            GazooDeviceError: If buttons are not supported on the device or
                             button, wait, port, or expect values are invalid

        Returns:
            ExpectResponse: Object with values for the following attributes:
               .index (int): the index of the expected pattern (None if timeout).
               .timedout (bool): indicating whether it timed out.
               .time_elapsed (int): number of seconds between start and finish.
               .match (str): re.group of pattern match.
               .before (str): all the characters looked at before the match.
               .after (str):  all the characters after the first matching character.
               .remaining (list): remaining patterns not matched
               .match_list (list): re.search pattern MatchObjects

        Note:
            Flushes the expect queue before and after an expect. Starts up
            expect queue right before pressing button to catch fast responses.
        """

        return self.do_and_expect(self.press,
                                  [button],
                                  {"wait": wait, "port": port},
                                  pattern_list,
                                  timeout=timeout,
                                  searchwindowsize=searchwindowsize,
                                  expect_type=expect_type,
                                  mode=mode)

    def release(self, button, port=0):
        """Release the button for the port specified.

        Args:
            button (str): button to release
            port (int): Which port to release button on, 0 or 1

        Raises:
            GazooDeviceError: If buttons are not supported on the device or
                             button or port values are invalid
        """

        self._check_button_args("release", button, port)

        self._button_list[port].release(button)
        log_message = "released button {}".format(button)
        self.add_log_note(log_message)

    def release_and_expect(self, button, pattern_list, timeout=30.0,
                           searchwindowsize=config.SEARCHWINDOWSIZE,
                           expect_type='log', port=0, mode="any"):
        """Release button, matches pattern_list in loglines as specified by expect_type.

        Args:
            button (str): button to release
            pattern_list (list): list of regex expressions to look for in the lines
            timeout (float): seconds to look for the patterns
            searchwindowsize (int): number of the last bytes to look at
            expect_type (str): 'log', 'response', or 'all'
            port (int): which port to send on, 0 or 1
            mode (str): type of expect to run ("any", "all" or "sequential")

        Raises:
            GazooDeviceError: If buttons are not supported on the device or
                             button, port, or expect values are invalid

        Returns:
            ExpectResponse: Object with values for the following attributes:
               .index (int): the index of the expected pattern (None if timeout).
               .timedout (bool): indicating whether it timed out.
               .time_elapsed (int): number of seconds between start and finish.
               .match (str): re.group of pattern match.
               .before (str): all the characters looked at before the match.
               .after (str):  all the characters after the first matching character.
               .remaining (list): remaining patterns not matched
               .match_list (list): re.search pattern MatchObjects

        Note:
            Flushes the expect queue before and after an expect. Starts up
            expect queue right before releasing button to catch fast responses.
        """

        return self.do_and_expect(self.release,
                                  [button],
                                  {"port": port},
                                  pattern_list,
                                  timeout=timeout,
                                  searchwindowsize=searchwindowsize,
                                  expect_type=expect_type,
                                  mode=mode)

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
            GazooDeviceError: if port specified is an invalid value or out of
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

    def send_and_expect(self,
                        command,
                        pattern_list,
                        timeout=30.0,
                        searchwindowsize=config.SEARCHWINDOWSIZE,
                        expect_type=line_identifier.LINE_TYPE_RESPONSE,
                        mode=MODE_TYPE_ANY,
                        port=0,
                        slow=False,
                        add_newline=True,
                        newline="\n",
                        command_tries=1,
                        raise_for_timeout=False):
        """Sends the command and expects on the patterns provided.

        Args:
            command (str): command to send to the device
            pattern_list (list): list of regex expressions to look for in the lines
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
            command_tries (int): The number of tries to send the command if it times out.
            raise_for_timeout (bool): Raise an exception if the expect times out

        Raises:
            GazooDeviceError: if port specified or other expect arguments are
                             invalid, or timed out and raise_for_timeout was True.

        Returns:
            ExpectResponse: Object with values for the following attributes:
               .index (int): the index of the expected pattern (None if timeout).
               .timedout (bool): indicating whether it timed out.
               .time_elapsed (int): number of seconds between start and finish.
               .match (str): re.group of pattern match.
               .before (str): all the characters looked at before the match.
               .after (str):  all the characters after the first matching character.
               .remaining (list): remaining patterns not matched
               .match_list (list): re.search pattern MatchObjects

        Note:
            Flushes the expect queue before and after an send.
        """

        result = None
        for _ in range(command_tries):
            result = self.do_and_expect(self.send,
                                        [command],
                                        {"port": port,
                                         "slow": slow,
                                         "add_newline": add_newline,
                                         "newline": newline},
                                        pattern_list,
                                        timeout=timeout,
                                        searchwindowsize=searchwindowsize,
                                        expect_type=expect_type,
                                        mode=mode)
            if result.timedout:
                continue
            return result

        if result and result.timedout and raise_for_timeout:
            raise errors.GazooDeviceError("Device {} send_and_expect timed out for command {}"
                                          .format(self.device_name, command))
        return result

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

        if not hasattr(self, "_log_writer_process") or not self._log_writer_process.is_running():
            raise RuntimeError("Device {} set max_log_size failed. "
                               "Log writer process is not currently running.".
                               format(self.device_name))
        elif not isinstance(max_log_size, int):
            raise ValueError("Device {} set max_log_size failed. "
                             "Expected 'type<int>' found {}".
                             format(self.device_name, type(max_log_size)))

        self._log_writer_process.send_command(log_process.CMD_MAX_LOG_SIZE, max_log_size)
        while (self._log_writer_process.is_running()
               and not self._log_writer_process.is_command_done()):
            time.sleep(0.001)

    def start_new_log(self, log_path):
        """Changes log filter and writer to use a new log path provided.

        Args:
            log_path (str): to log file to switch to

        Raises:
            RuntimeError: if LogWriterProcess is not available or running.
        """

        if not hasattr(self, "_log_writer_process") or not self._log_writer_process.is_running():
            raise RuntimeError("Device {} start new log failed. "
                               "Log writer process is not currently running.".
                               format(self.device_name))

        if hasattr(self, "_log_filter_process"):
            self._log_filter_process.send_command(log_process.CMD_NEW_LOG_FILE, log_path)
            while (self._log_filter_process.is_running()
                   and not self._log_filter_process.is_command_done()):
                time.sleep(0.001)

        self._log_writer_process.send_command(log_process.CMD_NEW_LOG_FILE, log_path)
        while (self._log_writer_process.is_running()
               and not self._log_writer_process.is_command_done()):
            time.sleep(0.001)

        # Wait for new log file to appear
        while self._log_writer_process.is_running() and not os.path.exists(log_path):
            time.sleep(0.1)

    def transport_jlink_flash(self, image_path, port=0):
        """Sends the flash command to the 'J-Link' transport.

        Args:
            image_path (str): path to the image file to be flashed onto the device.
            port (int): the transport port to send the command to.
        """
        self._validate_port(port, self.transport_jlink_flash.__name__,
                            jlink_transport.JLinkTransport)
        self.add_log_note("Device {} performing J-Link flash on port {} with image {}"
                          .format(self.device_name, port, image_path))
        transport = self._transport_processes[port]
        transport.send_command(transport_process.CMD_TRANSPORT_JLINK_FLASH, data=image_path)

    def transport_jlink_reset(self, port=0):
        """Sends the reset command to the J - Link transport.

        Args:
            port(int): the transport port to send the command to.
        """
        self._validate_port(port, self.transport_jlink_reset.__name__,
                            jlink_transport.JLinkTransport)
        self.add_log_note("Device {} performing J-Link reset on port {}"
                          .format(self.device_name, port))
        transport = self._transport_processes[port]
        transport.send_command(transport_process.CMD_TRANSPORT_JLINK_RESET)

    def transport_serial_set_baudrate(self, new_baudrate, port=0):
        """Sets the serial interface baudrate to a different baudrate.

        Args:
            new_baudrate(int): new baudrate to be set, generally 115200 or 921600
            port(int or str): the transport port to open

        Raises:
            GazooDeviceError

        """
        self._validate_port(port, self.transport_serial_set_baudrate.__name__,
                            serial_transport.SerialTransport)
        self.add_log_note("Device {} setting baudrate on port {} to {}".format(
            self.device_name, port, new_baudrate))
        transport = self._transport_processes[port]
        transport.send_command(transport_process.CMD_TRANSPORT_SERIAL_FLUSH)
        transport.send_command(transport_process.CMD_TRANSPORT_SET, (transport_properties.BAUDRATE,
                                                                     new_baudrate))
        transport.send_command(transport_process.CMD_TRANSPORT_SERIAL_FLUSH)

    def transport_serial_send_xon(self, port=0):
        """Sends the XON control character to the serial interface.

        Args:
            port(int or str): the transport port to open

        """
        self._validate_port(port, self.transport_serial_send_xon.__name__,
                            serial_transport.SerialTransport)
        self.add_log_note("Device {} sending XON to port {}".format(self.device_name,
                                                                    port))
        transport = self._transport_processes[port]
        transport.send_command(transport_process.CMD_TRANSPORT_SERIAL_XON)

    def transport_serial_send_xoff(self, port=0):
        """Sends the XOFF control character to the serial interface.

        Args:
            port(int or str): the transport port to open

        """
        self._validate_port(port, self.transport_serial_send_xoff.__name__,
                            serial_transport.SerialTransport)
        self.add_log_note("Device {} sending XOFF to port {}".format(self.device_name,
                                                                     port))
        transport = self._transport_processes[port]
        transport.send_command(transport_process.CMD_TRANSPORT_SERIAL_XOFF)

    def transport_serial_send_break_byte(self, port=0):
        """Sends the break control character to the serial interface (Ctrl + C).

        Args:
            port(int or str): the transport port to open
        """
        self._validate_port(port, self.transport_serial_send_break_byte.__name__,
                            serial_transport.SerialTransport)
        self.add_log_note("Device {} sending break to port {}".format(self.device_name,
                                                                      port))
        transport = self._transport_processes[port]
        transport.send_command(transport_process.CMD_TRANSPORT_SERIAL_BREAK_BYTE)

    def verify_file_on_transport(self, source_file, destination_path, port=0,
                                 method=VERIFY_METHOD_MD5SUM):
        """Verifies source file contents matches destination_path on transport using method.

        Args:
            source_file(path): to compare content to on transport
            destination_path(path): to file to verify on transport
            port(int or str): the transport port to open
            method(str): the method to use to verify destination_path

        Raises:
            GazooDeviceError: If source_file doesn't exist, can't be opened, or
                             the port or method values are invalid or out of range.

        Returns:
            bool: A boolean status indicating verification was successful.

        Note:
            The caller is responsible for preparing the device to receive one
            of the following verification commands::

                md5sum < destination_path >
        """

        self._validate_port(port, self.verify_file_on_transport.__name__)

        if not os.path.exists(source_file):
            raise errors.GazooDeviceError("Device {} verify file on transport failed. "
                                          "Source file {} doesn't exist.".
                                          format(self.device_name, source_file))
        elif not isinstance(method, (str, six.text_type)):
            raise errors.GazooDeviceError("Device {} verify file on transport failed. "
                                          "Expecting string for method found {} instead.".
                                          format(self.device_name, type(method)))
        elif method not in _VERIFY_METHODS:
            raise errors.GazooDeviceError("Device {} verify file on transport failed. "
                                          "Unknown method value {} expected: {}".
                                          format(self.device_name,
                                                 method,
                                                 ",".join(_VERIFY_METHODS)))

        # Verify md5sum is available on the host computer
        host_md5sum_path = subprocess.check_output(["which", "md5sum"],
                                                   stderr=subprocess.PIPE).decode('utf-8',
                                                                                  'replace')
        if "md5sum" not in host_md5sum_path:
            raise errors.GazooDeviceError("Device {} echo file to transport failed. "
                                          "md5sum is not installed on host. "
                                          "Unable to verify successful file transfer".
                                          format(self.device_name))

        try:
            md5sum_results = subprocess.check_output([host_md5sum_path.rstrip(),
                                                      source_file]).decode('utf-8',
                                                                           'replace')
        except subprocess.CalledProcessError as err:
            raise errors.GazooDeviceError("Device {} echo file to transport failed. "
                                          "Unable to retrieve md5sum of {}. "
                                          "Error: {!r}".format(self.device_name, source_file, err))
        else:
            host_checksum = md5sum_results.split()[0]

        # Get md5sum of destination_path
        checksum_pattern = r"(\w{32})\s+" + destination_path
        missing_pattern = "can't open '" + destination_path + "': No such file or directory"
        result = self.send_and_expect("md5sum {}\n".format(destination_path),
                                      [checksum_pattern,
                                       missing_pattern],
                                      expect_type="response",
                                      port=port)
        if result.timedout:
            raise errors.GazooDeviceError("Device {} echo file to transport failed. "
                                          "Unable to verify {} using the md5sum command".
                                          format(self.device_name, destination_path))
        elif result.index == 0:  # checksum returned for file pattern
            device_checksum = result.match.group(1)
        elif result.index == 1:  # missing file pattern
            device_checksum = "No such file or directory"
        success = host_checksum == device_checksum
        if success:
            log_message = ("verification of {} for port {} was successful".
                           format(destination_path, port))
        else:
            log_message = ("verification of {} for port {} failed. "
                           "The host md5sum {!r} != device md5sum {!r}".
                           format(destination_path,
                                  port,
                                  host_checksum,
                                  device_checksum))
        self.add_log_note(log_message)
        return success

    def xmodem_file_to_transport(self, source_file, port=0):
        """Transfers file to transport specified using the XModem protocol.

        Args:
            source_file(path): to the file to transfer
            port(int or str): the transport port to open

        Raises:
            GazooDeviceError: If source_file doesn't exist, can't be opened, or
                             the port value provided is invalid or out of range.

        Returns:
            bool: A boolean status indicating xmodem transfer was successful.

        Note:
            The caller is responsible for putting the transport into XModem
            transfer mode before calling this method.
        """
        self._validate_port(port, self.xmodem_file_to_transport.__name__)

        if not os.path.exists(source_file):
            raise errors.GazooDeviceError("Device {} xmodem file to transport failed. "
                                          "Source file {} doesn't exist.".
                                          format(self.device_name, source_file))

        try:
            stream = io.open(source_file, "rb")
        except IOError as err:
            raise errors.GazooDeviceError("Device {} xmodem file to transport failed. "
                                          "Unable to open source file {}. "
                                          "Error: {!r}".
                                          format(self.device_name, source_file, err))
        success = False
        transport = self._transport_processes[port]._transport
        modem = xmodem.XMODEM(transport.read, transport.write)
        start_time = time.time()
        try:
            self.close_transport(port=port)
            log_message = "starting xmodem transfer of {} for port {}".format(source_file, port)
            self.add_log_note(log_message)
            transport.open()
            success = modem.send(stream)
        finally:
            stream.close()
            log_message = ("finished xmodem transfer of {} for port {} in {}s success={}".
                           format(source_file, port, time.time() - start_time, success))
            self.add_log_note(log_message)
            transport.close()
            self.open_transport(port=port)
        return success

    def add_transport_process(self, transport, **transport_process_kwargs):
        """Add a new transport process to the list of transport processes.

        Args:
            transport(Transport): transport to the device for this process
            **transport_process_kwargs(dict): keyword arguments to the transport process

        transport_process_kwargs can be:
            framer(DataFramer): DataFramer derived classes to use to frame incoming raw data
                                 into raw lines. Defaults to None.
            partial_line_timeout(float): time in seconds to wait before adding
                                          partial lines to raw_data_queue and
                                          log_queue.
                                          Defaults to transport_process.PARTIAL_LINE_TIMEOUT.
            read_timeout(float): time to wait in seconds for transport reads.
                                  Defaults to to transport_process._READ_TIMEOUT
            max_read_bytes(int): to attempt to read on each transport read
                                  call. Defaults to transport_process._MAX_READ_BYTES
            max_write_bytes(int): to attempt to write on each transport write
                                   call. Defaults to transport_process._MAX_WRITE_BYTES

        Returns:
            int: position of newly added transport process in list of transport processes("port")
        """
        self._transport_processes.append(
            transport_process.TransportProcess(
                self.device_name,
                self._mp_manager,
                self._exception_queue,
                self._mp_manager.Queue(),
                self._log_queue,
                transport,
                raw_data_queue=self._raw_data_queue,
                raw_data_id=self._transport_process_id,
                **transport_process_kwargs))
        self._transport_process_id += 1
        return len(self._transport_processes) - 1   # The added process is always last

    def _add_transport_processes(self,
                                 transport_list,
                                 framer_list,
                                 partial_line_timeout_list):
        """Create transport processes which handle the given transports.

        Args:
          transport_list(list): list of transports.
          framer_list(list): list of data framers, one per transport.
          partial_line_timeout_list(list): list of float to delay before adding a partial line.
        """
        for idx, transport in enumerate(transport_list):
            kwargs = {}
            if idx < len(framer_list):
                kwargs["framer"] = framer_list[idx]
            if idx < len(partial_line_timeout_list):
                kwargs["partial_line_timeout"] = partial_line_timeout_list[idx]
            self.add_transport_process(transport, **kwargs)

    def _add_log_writer_process(self, log_path, max_log_size):
        self._log_writer_process = log_process.LogWriterProcess(self.device_name,
                                                                self._mp_manager,
                                                                self._exception_queue,
                                                                self._mp_manager.Queue(),
                                                                self._log_queue,
                                                                log_path,
                                                                max_log_size=max_log_size)

    def _add_log_filter_process(self, parser, log_path):
        if parser is not None:
            self._log_filter_process = log_process.LogFilterProcess(self.device_name,
                                                                    self._mp_manager,
                                                                    self._exception_queue,
                                                                    self._mp_manager.Queue(),
                                                                    parser,
                                                                    log_path)

    def _check_button_args(self, func_name, button, port, duration=0.0, wait=0.0):
        """Checks that button arguments are valid.

        Args:
            func_name (str): name of the calling function (to include in the error message).
            button (str): button name.
            port (int): which port to click on, 0 or 1.
            duration (float): seconds to wait before releasing button.
            wait (float): seconds to wait before returning after pressing the button.

        Raises:
            GazooDeviceError: provided button arguments are invalid.
        """
        self._validate_port(port, func_name)

        if not self._button_list:
            raise errors.GazooDeviceError("Device {} {} failed. "
                                          "Buttons are not supported for this device.".
                                          format(self.device_name, func_name))
        elif not isinstance(button, (six.text_type, str)):
            raise errors.GazooDeviceError("Device {} {} failed. "
                                          "Expecting str for button found {} instead.".
                                          format(self.device_name, func_name, type(button)))
        elif not isinstance(duration, (int, float)):
            raise errors.GazooDeviceError("Device {} {} failed. "
                                          "Expecting int or float for duration found {} instead.".
                                          format(self.device_name, func_name, type(duration)))
        elif not isinstance(wait, (int, float)):
            raise errors.GazooDeviceError("Device {} {} failed. "
                                          "Expecting int or float for wait found {} instead.".
                                          format(self.device_name, func_name, type(wait)))
        elif duration < 0.0:
            raise errors.GazooDeviceError("Device {} {} failed. "
                                          "Invalid duration value {} expected >=0.0".
                                          format(self.device_name, func_name, duration))
        elif wait < 0.0:
            raise errors.GazooDeviceError("Device {} {} failed. "
                                          "Invalid wait value {} expected >=0.0".
                                          format(self.device_name, func_name, wait))
        elif not self._button_list[port].is_valid(button):
            raise errors.GazooDeviceError("Device {} {} failed. "
                                          "Invalid button {} for port {} expected {}.".
                                          format(self.device_name, func_name, button, port,
                                                 self._button_list[port].valid_buttons()))

    def _check_expect_args(self, pattern_list, timeout, searchwindowsize, expect_type, mode):
        """Check that expect arguments are valid.

        Args:
            pattern_list (list): list of regex expressions to look for in the lines
            timeout (float): seconds to look for the patterns
            searchwindowsize (int): number of the last bytes to look at
            expect_type (str): 'log', 'response', or 'all'
            mode (str): type of expect to run ("any", "all" or "sequential")

        Raises:
            GazooDeviceError: provided expect arguments are invalid.
        """
        if not isinstance(pattern_list, list):
            raise errors.GazooDeviceError("Device {} expect failed. "
                                          "Expecting list for pattern_list ({}) found {} instead.".
                                          format(self.device_name,
                                                 repr(pattern_list),
                                                 type(pattern_list)))
        elif not isinstance(timeout, (int, float)):
            raise errors.GazooDeviceError("Device {} expect failed. "
                                          "Expecting int or float for timeout found {} instead.".
                                          format(self.device_name, type(timeout)))
        elif not isinstance(searchwindowsize, int):
            raise errors.GazooDeviceError("Device {} expect failed. "
                                          "Expecting int for searchwindowsize found {} instead.".
                                          format(self.device_name, type(searchwindowsize)))
        elif not isinstance(expect_type, (six.text_type, str)):
            raise errors.GazooDeviceError("Device {} expect failed. "
                                          "Expecting str for expect_type found {} instead.".
                                          format(self.device_name, type(expect_type)))
        elif not isinstance(mode, (six.text_type, str)):
            raise errors.GazooDeviceError("Device {} expect failed. "
                                          "Expecting str for mode found {} instead.".
                                          format(self.device_name, type(mode)))
        elif expect_type not in _VALID_EXPECT_TYPES:
            raise errors.GazooDeviceError(
                "Device {} expect failed. "
                "Invalid input for expect_type found {} expecting one of {}.".
                format(self.device_name, expect_type, _VALID_EXPECT_TYPES))
        elif mode not in _VALID_EXPECT_MODES:
            raise errors.GazooDeviceError("Device {} expect failed. "
                                          "Invalid input for mode found {} expecting one of {}.".
                                          format(self.device_name, mode, _VALID_EXPECT_MODES))
        elif not pattern_list:
            raise errors.GazooDeviceError("Device {} expect failed. "
                                          "Expecting at least one pattern in list, found none.".
                                          format(self.device_name))

        log_message = ("expecting {} patterns from {!r} using "
                       "{} lines and {} search window in {}s".
                       format(mode, pattern_list, expect_type, searchwindowsize, timeout))
        self.add_log_note(log_message)

    def _disable_raw_data_queue(self):
        """Decrement the raw_data_queue user count and disable and flush the raw_data_queue.
        """
        if self._raw_data_queue_users:
            self._raw_data_queue_users -= 1
        if self._raw_data_queue_users == 0:
            self._toggle_raw_data()
            self._flush_raw_data_queue()

    def _enable_raw_data_queue(self):
        """Increment the raw_data_queue user count and flush and enable the raw_data_queue.
        """
        self._raw_data_queue_users += 1
        if self._raw_data_queue_users == 1:
            self._flush_raw_data_queue()
            self._toggle_raw_data()

    def _expect(self,
                compiled_list,
                timeout,
                searchwindowsize,
                expect_type,
                mode,
                raise_for_timeout=False):
        """Wait until a message matching the regexps in the list arrives on the data queue.

        Args:
            compiled_list (list): The list of patterns
            timeout (float): seconds to look for the patterns
            searchwindowsize (int): number of the last bytes to look at
            expect_type (str): 'log', 'response', or 'all'
            mode (str): type of expect to run ("any", "all" or "sequential")
            raise_for_timeout (bool): Raise an exception if the expect times out

        Returns:
             ExpectResponse: an expect response

        Raises:
            GazooDeviceError: for a timeout if raise_for_timeout is True.
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
            except (AttributeError, IOError, six.moves.queue.Empty, ValueError):
                # manager shutdown or close called
                break

            if message is None:
                continue

            port, line = message
            if not self._identifier.accept(port, line, expect_type):
                continue

            # Stage 2/4: add raw line to search window in searchwindowsize chunks
            captured_lines.append(line)
            line_split_indexes = list(range(0, len(line), searchwindowsize)) + [len(line)]
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
                    log_message = "found pattern {!r} at index {}".format(pattern.pattern, index)
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

                    missing_patterns = _get_missing_patterns(compiled_list, match_list, mode)
                    remaining_list = _get_pattern_strings(missing_patterns)
                    log_message = ("mode {} expect completed with {!r} remaining patterns in {}s".
                                   format(mode, u", ".join(remaining_list), time_elapsed))
                    self.add_log_note(log_message)
                    return ExpectResponse(index,
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
        after = None

        missing_patterns = _get_missing_patterns(compiled_list, match_list, mode)
        remaining_list = _get_pattern_strings(missing_patterns)
        log_message = ("expect timed out after waiting {}s for {!r} remaining patterns".
                       format(time_elapsed, u", ".join(remaining_list)))
        self.add_log_note(log_message)

        if raise_for_timeout:
            raise errors.GazooDeviceError(
                "{} expect timed out after waiting {}s for {!r} remaining patterns"
                .format(self.device_name, time_elapsed, ", ".join(remaining_list)))

        return ExpectResponse(index,
                              before,
                              after,
                              match,
                              time_elapsed,
                              timedout=True,
                              remaining=remaining_list,
                              match_list=match_list)

    def _flush_raw_data_queue(self):
        try:
            while not self._raw_data_queue.empty():
                self._raw_data_queue.get_nowait()
                self._raw_data_queue.task_done()
        except (AttributeError, IOError, six.moves.queue.Empty):
            # manager shutdown or close called or queue empty
            pass

    def _get_compiled_pattern_list(self, pattern_list):
        """Return compiled regexps objects for the given regex pattern list.

        Args:
            pattern_list (list): list of regular expressions to compile.

        Returns:
            list: compiled regular expressions.

        Raises:
            GazooDeviceError: invalid regular expression provided.
        """
        compiled_list = []
        for pattern in pattern_list:
            try:
                compiled_pattern = re.compile(pattern, re.DOTALL | re.MULTILINE)
                compiled_list.append(compiled_pattern)
            except re.error as err:
                raise errors.GazooDeviceError("Device {} expect failed. "
                                              "Invalid regex pattern {}. Error {!r}".
                                              format(self.device_name, pattern, err))
        return compiled_list

    def _send_command_to_device(self, command, port=0):
        """Send command to port (transport) specified.

        Args:
            command(str): to be sent to port(transport)
            port(int): selecting which transport to send command to
        """

        transport = self._transport_processes[port]
        transport.send_command(transport_process.CMD_TRANSPORT_WRITE, command)

    def delete_last_transport_process(self):
        """Stops and deletes the last transport process in self._transport_processes.

        Note:
            Just stopping a transport process does not delete it.
            All stopped processes are typically reopened after a device reboot.
            The process must be deleted to ensure it is not reopened after a device reboot.

        Since we're using process numbers to identify the transport,
        deleting any transport other than the last one will cause some other transports in
        the transport list to shift their transport number by 1, breaking their usage.
        To prevent this, allow deleting only the last process for now.
        The proper solution would be to use some other form of identification for processes.

        Raises:
            GazooDeviceError: if there's no transport process to delete.
        """
        if self._transport_processes:
            last_proc_num = len(self._transport_processes) - 1
            self.stop_transport_process(last_proc_num)
            del self._transport_processes[last_proc_num]
        else:
            raise errors.GazooDeviceError("There are no transport processes.")

    def start_transport_process(self, process_num):
        """Start the transport process at position process_num in transport list.

        Args:
            process_num(int): position in self._transport_processes list. This position is
                               returned by a prior self.add_transport_process() call.

        Raises:
            GazooDeviceError: if process_num has an invalid value.
        """
        self._validate_port(process_num, self.start_transport_process.__name__)
        if not self._transport_processes[process_num].is_started():
            self._transport_processes[process_num].start()

    def stop_transport_process(self, process_num):
        """Stop the transport process.

        Args:
            process_num(int): number of transport to stop.
        """
        self._validate_port(process_num, self.stop_transport_process.__name__)
        process = self._transport_processes[process_num]
        if process.is_started():
            process.stop()

    def _start_processes(self):
        for process_num in range(len(self._transport_processes)):
            self.start_transport_process(process_num)
        if hasattr(self, "_log_writer_process"):
            if not self._log_writer_process.is_started():
                self._log_writer_process.start()
        if hasattr(self, "_log_filter_process"):
            if not self._log_filter_process.is_started():
                self._log_filter_process.start()

    def _stop_processes(self):
        """Stop all Switchboard processes."""
        if hasattr(self, "_transport_processes") and self._transport_processes:
            logger.info("{} closing switchboard processes".format(self.device_name))
            while self._transport_processes:
                self.delete_last_transport_process()
        if hasattr(self, "_log_writer_process") and self._log_writer_process:
            if self._log_writer_process.is_started():
                self._log_writer_process.stop()
            delattr(self, "_log_writer_process")
        if hasattr(self, "_log_filter_process") and self._log_filter_process:
            if self._log_filter_process.is_started():
                self._log_filter_process.stop()
            delattr(self, "_log_filter_process")

    def _validate_port(self, port, function_name, transport_type=None):
        """Validates the user input (port number). Also validates transport type (if given).

        Args:
            port(int): port number(position of transport in transport list)
            function_name(str): name of function calling _validate_port
            transport_type(object): class object inheriting from TransportBase(or None).

        Raises:
            GazooDeviceError: if port number is not valid OR
                             if transport_type is not None and the transport type doesn't match.
        """
        basic_error = "Device {} {} failed. ".format(self.device_name, function_name)
        if not isinstance(port, int):
            raise errors.GazooDeviceError(basic_error +
                                          "Invalid port type. Expected: int, found: {}."
                                          .format(type(port).__name__))
        elif port < 0 or port >= len(self._transport_processes):
            raise errors.GazooDeviceError(basic_error +
                                          "Invalid port number. Expected: [0..{}), found: {}."
                                          .format(len(self._transport_processes), port))
        elif (transport_type is not None
              and not isinstance(self._transport_processes[port]._transport, transport_type)):
            raise errors.GazooDeviceError(
                basic_error +
                "Invalid type of transport on port {}. Expected type {}, found type {}.".
                format(port, transport_type, type(self._transport_processes[port]._transport)))

    def _toggle_raw_data(self):
        for transport in self._transport_processes:
            transport.toggle_raw_data()
