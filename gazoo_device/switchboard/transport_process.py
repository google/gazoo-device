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

"""Implementation of the TransportProcess class which builds on the SwitchboardProcess base class.

The TransportProcess is responsible for reading and writing bytes to and from
the transport class provided and according to the following assumptions:

    * Transport commands from the main process are received using the
      send_command() method.

    * Raw transport data is (optionally) detokenized.

    * Raw/detokenized data is queued in the expect queue provided.

    * Expect queue can be enabled/disabled by the toggle_expect() method.

    * A host system timestamp is added to every line of data and queued in the
      log queue provided.

    * The host system timestamp will be in the following format:
      "<YYYY-MM-DD hh:mm:ss.ssssss> "

    * Custom log messages received as commands will only be added to the log
      queue between full device log messages.
"""
from __future__ import absolute_import
import multiprocessing
import six
import six.moves.queue as queue
import time
from gazoo_device.switchboard import switchboard_process
from gazoo_device.switchboard import data_framer
from gazoo_device.switchboard import log_process
from gazoo_device.switchboard import transport_properties as props
from six.moves import range


CMD_TRANSPORT_CLOSE = "TRANSPORT_CLOSE"
CMD_TRANSPORT_OPEN = "TRANSPORT_OPEN"
CMD_TRANSPORT_WRITE = "TRANSPORT_WRITE"
CMD_TRANSPORT_SET = "TRANSPORT_SET"
CMD_TRANSPORT_SERIAL_FLUSH = "TRANSPORT_SERIAL_FLUSH"
CMD_TRANSPORT_SERIAL_XON = "TRANSPORT_SERIAL_XON"
CMD_TRANSPORT_SERIAL_XOFF = "TRANSPORT_SERIAL_XOFF"
CMD_TRANSPORT_SERIAL_BREAK_BYTE = "TRANSPORT_SERIAL_BREAK_BYTE"
CMD_TRANSPORT_JLINK_RESET = "TRANSPORT_JLINK_RESET"
CMD_TRANSPORT_JLINK_FLASH = "TRANSPORT_JLINK_FLASH"
PARTIAL_LINE_TIMEOUT = 0.1  # time in seconds before publishing partial lines

_MAX_WRITE_BYTES = 32
_MAX_READ_BYTES = 11520  # 115200 / 10
_READ_TIMEOUT = 0.01  # ((115200 / 10) / 100ms) = ~115 bytes per 10ms read
_VALID_COMMANDS = [
    CMD_TRANSPORT_CLOSE,
    CMD_TRANSPORT_OPEN,
    CMD_TRANSPORT_WRITE,
    CMD_TRANSPORT_SET
]
_VALID_SERIAL_COMMANDS = [
    CMD_TRANSPORT_SERIAL_FLUSH,
    CMD_TRANSPORT_SERIAL_XON,
    CMD_TRANSPORT_SERIAL_XOFF,
    CMD_TRANSPORT_SERIAL_BREAK_BYTE,
]
_VALID_JLINK_COMMANDS = [
    CMD_TRANSPORT_JLINK_FLASH,
    CMD_TRANSPORT_JLINK_RESET
]
_ALL_VALID_COMMANDS = _VALID_COMMANDS + _VALID_SERIAL_COMMANDS + _VALID_JLINK_COMMANDS


def _enqueue_command_writes(write_queue, command, max_write_bytes=_MAX_WRITE_BYTES):
    """Splits command into max_write_bytes chunks and puts them into queue provided.

    Args:
        write_queue (Queue): to put split command into
        command (str): bytes to be written to device
        max_write_bytes (int): chunks to split command into.

    Note:
        Splitting commands into smaller write chunks avoids overloading the
        input buffer of the device.
    """

    command_split_indexes = list(range(0, len(command), max_write_bytes)) + [len(command)]
    for index in range(1, len(command_split_indexes)):
        start_index = command_split_indexes[index - 1]
        end_index = command_split_indexes[index]
        write_queue.put(command[start_index:end_index])


class TransportProcess(switchboard_process.SwitchboardProcess):
    """A process which manages (writes to and reads from) a transport instance."""

    def __init__(self,
                 device_name,
                 mp_manager,
                 exception_queue,
                 command_queue,
                 log_queue,
                 transport,
                 raw_data_queue=None,
                 raw_data_id=0,
                 framer=None,
                 partial_line_timeout=PARTIAL_LINE_TIMEOUT,
                 read_timeout=_READ_TIMEOUT,
                 max_read_bytes=_MAX_READ_BYTES,
                 max_write_bytes=_MAX_WRITE_BYTES):
        """Initialize TransportProcess with the arguments provided.

        Args:
            device_name (str): name of device using this transport
            mp_manager (multiprocessing.Manager): object to use for creating Events
            exception_queue (Queue): to use for reporting exception traceback
                                     message from subprocess
            command_queue (Queue): to receive commands into
            log_queue (Queue): to write each log line with host stamp added
            transport (Transport): to use to receive and send raw data
            raw_data_queue (Queue): to put raw (if applicable, detokenized)
                                    data into when enabled.
            raw_data_id (int): unique identifier for data published by this
                               transport process to the raw_data_queue.
            framer (DataFramer): to use to frame raw data into partial and
                                 complete lines.
            partial_line_timeout (float): time in seconds to wait before adding
                                          partial lines to raw_data_queue and
                                          log_queue.
            read_timeout (float): time to wait in seconds for transport reads.
            max_read_bytes (int): to attempt to read on each transport read
                                  call.
            max_write_bytes (int): to attempt to write on each transport write
                                   call.
        """

        process_name = "{}-Transport{}".format(device_name, raw_data_id)
        super(TransportProcess, self).__init__(device_name,
                                               process_name,
                                               mp_manager,
                                               exception_queue,
                                               command_queue,
                                               valid_commands=_ALL_VALID_COMMANDS)
        self._buffered_unicode = u""
        self._can_reopen = True
        self._framer = framer or data_framer.NewlineFramer()
        self._log_queue = log_queue
        self._max_read_bytes = max_read_bytes
        self._max_write_bytes = max_write_bytes
        self._partial_line_timeout = partial_line_timeout
        self._partial_log_time = time.time()
        self._pending_writes = None
        self._raw_data_enabled = multiprocessing.Event()
        self._raw_data_id = raw_data_id
        self._raw_data_queue = raw_data_queue
        self._read_timeout = read_timeout
        self._transport = transport
        self._transport_open = multiprocessing.Event()

    def get_raw_data(self, timeout=None):
        """Returns raw data message from optional raw data queue.

        Args:
            timeout (float): time to wait in seconds for incoming message to arrive.

        Raises:
            RuntimeError: if optional expect_queue was not provided when class
                          was initialized

        Returns:
            tuple: A tuple containing the raw_data_id and raw data received from
                   the transport device when enabled or None if no data was
                   available within timeout specified.
        """

        if self._raw_data_queue is None:
            raise RuntimeError("Device {} can't retrieve raw data. "
                               "No queue provided".
                               format(self.device_name))

        return switchboard_process.get_message(self._raw_data_queue, timeout=timeout)

    def is_open(self):
        """Returns True if transport is currently open.

        Returns:
            bool: A boolean indicating transport is currently open.
        """

        return self._transport_open.is_set()

    def raw_data_enabled(self):
        """Returns raw data streaming state.

        Returns:
            bool: A boolean indicating raw data streaming is enabled
        """

        return self._raw_data_enabled.is_set()

    def toggle_raw_data(self):
        """Toggles raw data queue to be enabled/disabled.

        Raises:
            RuntimeError: if optional raw_data_queue was not provided when class
                          was initialized
        """

        if self._raw_data_queue is None:
            raise RuntimeError("Device {} can't enable raw data output. "
                               "No queue provided".
                               format(self.device_name))

        if self._raw_data_enabled.is_set():
            self._raw_data_enabled.clear()
        else:
            self._raw_data_enabled.set()

    def _close_transport(self):
        if self._transport:
            self._transport.close()
            self._can_reopen = False
            if not self._transport.is_open():
                self._transport_open.clear()

    def _do_work(self):
        """Performs transport work and feeding log messages to log_queue.

        Returns:
            bool: always returns True
        """

        command_message = switchboard_process.get_message(self._command_queue, timeout=0)
        if command_message:
            self._process_command_message(command_message)
        if self._transport.is_open():
            self._transport_open.set()
            self._transport_write()
            self._transport_read()
        else:
            self._transport_open.clear()
            if self._transport.get_property(props.AUTO_REOPEN, False) and self._can_reopen:
                self._open_transport()
            else:
                time.sleep(self._read_timeout)
        return True

    def _is_line_published(self, line):
        elapsed_time = time.time() - self._partial_log_time
        if line and (line[-1] == "\n" or elapsed_time > self._partial_line_timeout):
            # NEP-3223 deal with partial line being finished by subsequent line
            if line[-1] == "\n" and self._buffered_unicode:
                self._publish_line(self._buffered_unicode + line)
                self._buffered_unicode = u""
            else:
                self._publish_line(line)
            return True
        return False

    def _open_transport(self):
        self._transport.open()
        self._can_reopen = True
        if self._transport.is_open():
            self._transport_open.set()

    def _post_run_hook(self):
        """Close transport at end of process."""
        self._close_transport()

    def _pre_run_hook(self):
        """Setup variables and open transport at start of process.

        Returns:
            bool: always returns True
        """

        self._pending_writes = queue.Queue()
        if self._transport.get_property(props.OPEN_ON_START, True):
            self._open_transport()
        self._partial_log_time = time.time()
        return True

    def _process_command_message(self, command_message):
        """Processes command messages which are received as a (command, data) tuple.

        Args:
            command_message (tuple): as received from command queue

        Raises:
            RuntimeError: if command in command_message is unknown.
            ValueError: if data doesn't contain a 2-tuple for CMD_TRANSPORT_SET.
            AttributeError: if the transport doesn't support the called command (eg. calling
                CMD_TRANSPORT_SERIAL_FLUSH on a non-serial transport.
        """

        command, data = command_message
        if CMD_TRANSPORT_CLOSE == command:
            self._close_transport()
        elif CMD_TRANSPORT_OPEN == command:
            self._open_transport()
        elif CMD_TRANSPORT_WRITE == command:
            _enqueue_command_writes(self._pending_writes,
                                    data,
                                    max_write_bytes=self._max_write_bytes)
        elif CMD_TRANSPORT_SET == command:
            property_key, property_value = data
            self._transport.set_property(property_key, property_value)
        elif CMD_TRANSPORT_SERIAL_FLUSH == command:
            self._transport.flush_buffers()
        elif CMD_TRANSPORT_SERIAL_XON == command:
            self._transport.send_xon()
        elif CMD_TRANSPORT_SERIAL_XOFF == command:
            self._transport.send_xoff()
        elif CMD_TRANSPORT_SERIAL_BREAK_BYTE == command:
            self._transport.send_break_byte()
        elif CMD_TRANSPORT_JLINK_FLASH == command:
            self._transport.flash(data)
        elif CMD_TRANSPORT_JLINK_RESET == command:
            self._transport.reset()
        else:
            raise RuntimeError("Device {} received an unknown command {}.".
                               format(self.device_name, command))

    def _publish_line(self, line):
        if self._raw_data_enabled.is_set():
            switchboard_process.put_message(self._raw_data_queue,
                                            (self._raw_data_id, line),
                                            timeout=0)
        log_process.log_message(self._log_queue, line, self._raw_data_id)

    def _transport_read(self):
        """Reads and processing incoming bytes from transport.
        """

        bytes_in = self._transport.read(size=self._max_read_bytes,
                                        timeout=self._read_timeout)
        if bytes_in:
            if isinstance(bytes_in, six.binary_type):
                unicode_in = bytes_in.decode("utf-8", "replace")
            else:
                unicode_in = bytes_in
            unicode_in = self._buffered_unicode + unicode_in
            buffered_len = len(self._buffered_unicode)
            self._buffered_unicode = u""
            # Can't use splitlines here because some devices
            # emit multiple line return characters without corresponding line
            # feed characters which prevents desired line splitting behavior.
            for line in self._framer.get_lines(unicode_in, begin=buffered_len):
                self._partial_log_time = time.time()
                if not self._is_line_published(line):
                    self._buffered_unicode += line
        elif self._buffered_unicode:
            if self._is_line_published(self._buffered_unicode):
                self._buffered_unicode = u""

    def _transport_write(self):
        """Writes previously split commands into transport."""
        if not self._pending_writes.empty():
            self._transport.write(self._pending_writes.get())
