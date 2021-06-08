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

"""Defines Switchboard processes responsible for writing and filtering logs.

The LogFilterProcess is responsible for tailing the log file specified and
producing filter events into the event file specified according to the
following assumptions:

    * The log file will be flushed frequently.

    * If an event file path is not provided then "-events.txt" will be added to
      the log file path provided.

The LogWriterProcess is responsible for receiving log lines added externally
to the provided log_queue and write them to a log file as quickly as possible
according to the following assumptions:

    * Log lines all have a host system timestamp added before being added
      to log queue.

    * Partial log lines contain no newline character at the end

    * Log lines missing a newline character will have one added when written

    * Log lines are queued in the correct order to be written to the log file

"""
import codecs
import datetime
import os
import re
import time

from gazoo_device.switchboard import data_framer
from gazoo_device.switchboard import switchboard_process

CMD_NEW_LOG_FILE = "NEW_LOG_FILE"
CMD_MAX_LOG_SIZE = "MAX_LOG_SIZE"
CMD_ADD_NEW_FILTER = "ADD_NEW_FILTER"
CHANGE_MAX_LOG_SIZE = "Changing max_log_size"
NEW_LOG_FILE_MESSAGE = "Starting new log file at"
ROTATE_LOG_MESSAGE = "Rotating from log file"
LOG_LINE_HEADER_LENGTH = 8  # len(" GDM-#: ")
LOG_LINE_HEADER_FORMAT = r"\sGDM-(.):\s(.*)$"
HOST_TIMESTAMP_LENGTH = 28  # len("<YYYY-MM-DD hh:mm:ss.ssssss>")
HOST_TIMESTAMP_FORMAT = "<%Y-%m-%d %H:%M:%S.%f>"
_MAX_READ_BYTES = 4096
_VALID_COMMON_COMMANDS = [CMD_NEW_LOG_FILE]
_VALID_FILTER_COMMANDS = [CMD_ADD_NEW_FILTER] + _VALID_COMMON_COMMANDS
_VALID_WRITER_COMMANDS = [CMD_MAX_LOG_SIZE] + _VALID_COMMON_COMMANDS


def get_event_filename(log_path):
  """Returns event filename for a given log_path.

  Args:
      log_path (str): path to log filename to get event filename for.

  Returns:
      str: Path to event filename for the given log_path provided.
  """
  return os.path.splitext(log_path)[0] + "-events.txt"


def get_next_log_filename(current_log_path):
  """Returns the next log filename using the current log path as a reference.

  Args:
      current_log_path (str): path to current log filename to get next name
        from.

  Returns:
      str: Path to expected next log filename given current_log_path.

  Note:
      If the current log file name is as follows (the first log file):
          <name_prefix>-<device_name>-<timestamp>.txt

      This method will return the following as the next log filename:
          <name_prefix>-<device_name>-<timestamp>.00001.txt

      Otherwise the rotation count will be extracted and incremented:
          <name_prefix>-<device_name>-<timestamp>.00002.txt
  """
  log_path_no_ext, log_path_ext = os.path.splitext(current_log_path)
  if re.search(r"\.\d{5}$", log_path_no_ext):
    base_log_path, counter_str = log_path_no_ext.rsplit(".", 1)
    counter = int(counter_str)
  else:
    base_log_path = log_path_no_ext
    counter = 0
  next_counter_str = ".{:05}".format(counter + 1)
  return base_log_path + next_counter_str + log_path_ext


def log_message(log_queue, raw_log_line, port):
  """Add host system timestamp to log_line and add result to log_queue.

  Args:
      log_queue (Queue): to send final log message to
      raw_log_line (str): to add system timestamp and GDM log header to
      port (int or str): to identify as source for log line
  """

  switchboard_process.put_message(log_queue,
                                  _add_log_header(raw_log_line, port))


def _add_log_header(raw_log_line, port="M"):
  """Add host system timestamp and GDM log header to raw_log_line.

  Args:
      raw_log_line (str): to add system timestamp and GDM log header to
      port (int or str): to identify as source for GDM log header

  Returns:
      str: The adjusted log line with system timestamp and GDM log header
      added.
  """

  host_timestamp = datetime.datetime.now().strftime(HOST_TIMESTAMP_FORMAT)
  return u"{} GDM-{}: {}".format(host_timestamp, port, raw_log_line)


class LogFilterProcess(switchboard_process.SwitchboardProcess):
  """A process which filters log lines to find device events and records them to an event file.

  The device events are specified as regular expressions in JSON event filter
  files.
  """

  def __init__(self,
               device_name,
               mp_manager,
               exception_queue,
               command_queue,
               parser,
               log_path,
               max_read_bytes=_MAX_READ_BYTES,
               framer=None):
    """Initialize LogFilterProcess with the arguments provided.

    Args:
        device_name (str): name of device used for process and error
          messages
        mp_manager (multiprocessing.Manager): object to use for creating
          Events
        exception_queue (Queue): to use for reporting exception traceback
          message from subprocess
        command_queue (Queue): to receive commands into
        parser (Parser): object to use for filtering log lines
        log_path (str): path and filename to write log messages to
        max_read_bytes (int): to attempt to read from log file each time.
        framer (DataFramer): to use to frame log data into partial and
          complete lines.
    """

    super(LogFilterProcess, self).__init__(
        device_name,
        device_name + "-LogFilter",
        mp_manager,
        exception_queue,
        command_queue,
        valid_commands=_VALID_FILTER_COMMANDS)

    self._buffered_unicode = u""
    self._framer = framer or data_framer.NewlineFramer()
    self._header_length = HOST_TIMESTAMP_LENGTH + LOG_LINE_HEADER_LENGTH
    self._max_read_bytes = max_read_bytes
    self._next_log_path = None
    self._parser = parser
    self._log_file = None
    self._log_filename = os.path.basename(log_path)
    self._log_directory = os.path.dirname(log_path)
    self._event_file = None
    self._event_path = get_event_filename(log_path)

  def _close_files(self):
    if hasattr(self, "_event_file") and self._event_file:
      self._event_file.flush()
      self._event_file.close()
      self._event_file = None
    if hasattr(self, "_log_file") and self._log_file:
      self._log_file.close()
      self._log_file = None

  def _is_log_swap_or_rotation(self, log_line):
    """Returns True if log_line indicates a log swap or rotation should occur.

    Args:
        log_line (str): to check for log swap indicator

    Returns:
        bool: True if log swap or rotation should occur.

    Note:
        If the log_line contains the ROTATE_LOG_MESSAGE then this method
        will identify what the next log file should be using the current
        log path and append it to the list of next log files to switch to.

        If the log_line contains the NEW_LOG_FILE_MESSAGE then the next log
        file was already prepended to the list of next log files when the
        command was received.

        It is expected that the LogWriterProcess will only allow one or the
        other message to be written to any given log file and not both.
    """

    result = False
    if ROTATE_LOG_MESSAGE in log_line:
      result = True
      log_path = os.path.join(self._log_directory, self._log_filename)
      next_log_path = get_next_log_filename(log_path)
      self._next_log_path.append(next_log_path)
    elif NEW_LOG_FILE_MESSAGE in log_line and self._next_log_path:
      self._event_path = get_event_filename(self._next_log_path[-1])
      result = True
    return result

  def _do_work(self):
    """Perform log filtering work.

    Returns:
        bool: indicating process should continue running

    Note:
        This implementation always returns True
    """

    command_message = switchboard_process.get_message(
        self._command_queue, timeout=0)
    if command_message:
      self._process_command_message(command_message)
    if self._has_log_file(self._log_filename):
      if not self._is_open():
        self._open_log_file(self._log_filename)
        if hasattr(self, "_log_file") and self._log_file:
          self._open_event_file()
      self._filter_log_lines()
    else:
      time.sleep(0.001)

    return True

  def _has_log_file(self, log_filename):
    log_path = os.path.join(self._log_directory, log_filename)
    return os.path.isfile(log_path)

  def _is_open(self):
    return (hasattr(self, "_log_file") and self._log_file and
            hasattr(self, "_event_file") and self._event_file)

  def _open_event_file(self):
    self._event_file = codecs.open(self._event_path, "a", encoding="utf-8")

  def _open_log_file(self, log_filename):
    log_path = os.path.join(self._log_directory, log_filename)
    self._log_file = codecs.open(
        log_path, "r", encoding="utf-8", errors="replace")
    self._log_filename = log_filename

  def _filter_log_lines(self):
    # Can't use readline here or splitlines later below because some devices
    # emit multiple return characters on each
    # log line read which prevents readline and splitlines from working
    # correctly. Each log line is expected to only have 1 newline but could
    # have multiple line return characters (see NEP-2855).
    change_log_file = False

    # NEP-3848: in Python 2, for file descriptor Foo whose EOF flag is set
    # and another file descriptor Bar which then appends to the same file,
    # the next read() for file descriptor Foo will return "" even though B has added new data.
    self._log_file.seek(self._log_file.tell())  # Unset EOF flag
    log_data = self._log_file.read(size=self._max_read_bytes)

    if log_data:
      log_lines = self._buffered_unicode + log_data
      buffered_len = len(self._buffered_unicode)
      self._buffered_unicode = u""
      for log_line in self._framer.get_lines(log_lines, begin=buffered_len):
        if log_line[-1] == "\n":
          self._parser.process_line(
              self._event_file,
              log_line,
              header_length=self._header_length,
              log_filename=self._log_filename)
        else:
          self._buffered_unicode += log_line
        if self._is_log_swap_or_rotation(log_line):
          change_log_file = True
    else:
      time.sleep(0.001)
    if change_log_file:
      self._open_next_log_file()

  def _open_next_log_file(self):
    try:
      new_log_path = self._next_log_path.pop()
    except IndexError:
      # No new log file
      pass
    else:
      self._close_files()
      self._buffered_unicode = u""
      self._log_directory = os.path.dirname(new_log_path)
      self._log_filename = os.path.basename(new_log_path)

  def _post_run_hook(self):
    self._close_files()

  def _pre_run_hook(self):
    self._next_log_path = []
    return True

  def _process_command_message(self, command_message):
    """Processes command messages which are received as a (command, data) tuple.

    Args:
        command_message (tuple): as received from command queue

    Raises:
        RuntimeError: if command in command_message is unknown.
    """

    command, data = command_message
    if CMD_NEW_LOG_FILE == command:
      self._next_log_path.insert(0, data)
    elif CMD_ADD_NEW_FILTER == command:
      self._parser.load_filter_file(data)
    else:
      raise RuntimeError("Device {} received an unknown command {}.".format(
          self.device_name, command))


class LogWriterProcess(switchboard_process.SwitchboardProcess):
  """A process which writes all logs found in the log queue into a log file.

  It expects each log line to be prepended with a host system timestamp.
  Log lines that are missing a newline character will have one added.
  Partial log lines should be handled by log line producers.
  """

  def __init__(self,
               device_name,
               mp_manager,
               exception_queue,
               command_queue,
               log_queue,
               log_path,
               max_log_size=0):
    """Initialize LogWriterProcess with the arguments provided.

    Args:
        device_name (str): name of device used for process and error
          messages
        mp_manager (multiprocessing.Manager): object to use for creating
          Events
        exception_queue (Queue): to use for reporting exception traceback
          message from subprocess
        command_queue (Queue): to receive commands into
        log_queue (Queue): to retrieve log messages from to be written
        log_path (str): path and filename to write log messages to
        max_log_size (int): maximum size in bytes before performing log
          rotation

    Note: A max_log_size of 0 means no log rotation should ever occur.
    """

    super(LogWriterProcess, self).__init__(
        device_name,
        device_name + "-LogWriter",
        mp_manager,
        exception_queue,
        command_queue,
        valid_commands=_VALID_WRITER_COMMANDS)
    self._log_queue = log_queue
    self._log_filename = os.path.basename(log_path)
    self._log_directory = os.path.dirname(log_path)
    self._log_file = None
    self._max_log_size = max_log_size

  def _close_file(self):
    if hasattr(self, "_log_file") and self._log_file:
      self._log_file.flush()
      self._log_file.close()

  def _do_log_rotation(self):
    """Perform log rotation if necessary."""
    if self._max_log_size:
      log_size = self._log_file.tell()
      if log_size >= self._max_log_size:
        new_log_filename = get_next_log_filename(self._log_filename)
        raw_log_message = "{} {} to {}\n".format(ROTATE_LOG_MESSAGE,
                                                 self._log_filename,
                                                 new_log_filename)
        self._write_log_line(_add_log_header(raw_log_message))
        new_log_path = os.path.join(self._log_directory, new_log_filename)
        self._open_new_log_file(new_log_path)

  def _do_work(self):
    """Perform log writing work.

    Returns:
        bool: indicating process should continue running

    Note:
        This implementation always returns True
    """
    command_message = switchboard_process.get_message(
        self._command_queue, timeout=0)
    if command_message:
      self._process_command_message(command_message)
    log_line = switchboard_process.get_message(self._log_queue, timeout=0.01)
    if log_line:
      self._write_log_line(log_line)
      self._do_log_rotation()
    else:
      time.sleep(0.01)

    return True

  def _open_file(self):
    if self._log_directory and not os.path.exists(self._log_directory):
      os.makedirs(self._log_directory)
    log_path = os.path.join(self._log_directory, self._log_filename)
    self._log_file = codecs.open(log_path, "a", encoding="utf-8")

  def _open_new_log_file(self, new_log_path):
    self._close_file()
    self._log_directory = os.path.dirname(new_log_path)
    self._log_filename = os.path.basename(new_log_path)
    self._open_file()

  def _post_run_hook(self):
    self._close_file()

  def _pre_run_hook(self):
    self._open_file()
    return hasattr(self, "_log_file") and self._log_file

  def _process_command_message(self, command_message):
    """Processes command messages which are received as a (command, data) tuple.

    Args:
        command_message (tuple): as received from command queue

    Raises:
        RuntimeError: if command in command_message is unknown.
    """

    command, data = command_message
    if CMD_MAX_LOG_SIZE == command:
      raw_log_message = "{} from {} to {}\n".format(CHANGE_MAX_LOG_SIZE,
                                                    self._max_log_size, data)
      self._write_log_line(_add_log_header(raw_log_message))
      self._max_log_size = data
    elif CMD_NEW_LOG_FILE == command:
      raw_log_message = "{} {}\n".format(NEW_LOG_FILE_MESSAGE, data)
      self._write_log_line(_add_log_header(raw_log_message))
      self._open_new_log_file(data)
    else:
      raise RuntimeError("Device {} received an unknown command {}.".format(
          self.device_name, command))

  def _write_log_line(self, log_line):
    if hasattr(self, "_log_file") and self._log_file:
      if log_line[-1] != "\n":
        # Write log line with newline added
        self._log_file.write(log_line + "[NO EOL]\n")
      else:
        self._log_file.write(log_line)
      self._log_file.flush()
