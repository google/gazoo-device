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

"""Module for log parser."""
import codecs
import os
import time

from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.switchboard import data_framer
from gazoo_device.switchboard import log_process

logger = gdm_logger.get_logger("log_parser")

DISPLAY_REFRESH = 3.0  # secs


class LogParser(object):
  """Provides ability to search for specific events in log file."""

  def __init__(self, parser_obj, log_path, display_refresh=DISPLAY_REFRESH):
    """Initialize LogParser class using provided information.

    Args:
        parser_obj (Parser): Instance of class Parser
        log_path (str): Path to log filename containing raw, log event data
        display_refresh (float): Number of seconds to wait prior to refresh
          of display

    Raises:
        ParserError: If log_path does NOT exist
                     If event_filename already exists
                     If parser_object is None

    Note:
         Since the provided log_path is immediately parsed, initializing
    LogParser using log files exceeding 100 MB can cause test applications
    to appear to be delayed.  The smaller the log file the faster
    initialization will be.
    """

    if parser_obj is None:
      raise errors.ParserError("Log parser parameter check failed. "
                               "Bad parser_obj.")

    if not os.path.isfile(log_path):
      raise errors.ParserError(
          "LogParser parameter check failed. "
          "log file name: {} does not exist.".format(log_path))

    self.event_filename = log_process.get_event_filename(log_path)
    parser_obj.event_file_path = self.event_filename
    if os.path.isfile(self.event_filename):
      raise errors.ParserError("LogParser parameter check failed. "
                               "event_filename: {} already exists.".format(
                                   self.event_filename))
    if display_refresh < 0:
      raise errors.ParserError(
          "LogParser parameter check failed. "
          "Expected display refresh >=0 instead got: {}".format(
              display_refresh))
    self._parser_obj = parser_obj
    self._parse_events(log_path, display_refresh)

  def get_last_event(self, event_labels=None, timeout=1.0):
    r"""Returns the most recent matching event for each item in the list of event labels.

    Args:
        event_labels (list): list of event labels to lookup (example:
          ["power.state", "power.lost"]). None (default) returns the most
          recent event regardless of label.
        timeout (float): Timeout value in seconds. Example: 1.5.

    Raises:
        ParserError: on error parsing event file.

    Returns:
        ParserResult: An object containing the most recent event match for each
        event label in the event_labels list, or the most recent event if
        event_labels is None. The event data is stored in the .results_list
        attribute, and the count of results is in the .count attribute. If no
        matching events are found, the .results_list attribute will be set to
        the empty list.

        If the .timedout attribute is True, the operation timed out before all
        events were searched or the event file was not found before the timeout
        expired.

    Notes:
        The event_label is the desired filter filename without extension a .
        and the filter name (e.g. power.state). The following examples use a
        hypothetical power.json filter file with the following filters:

        .. code-block:: none

            {
                "name": "state",
                "regex_match": "power:(\\w+)"
            },
            {
                "name": "lost",
                "regex_match": "power lost"
            },
            {
                "name": "restored",
                "regex_match": "power restored"
            }

        The original log file being read looks like this:

        .. code-block:: none

            <2018-02-02 10:32:07.167234> [APPL] Spoke: power restored,
            powering on
            <2018-02-02 12:00:57.154328> [APPL] Spoke: power lost, powering
            down
            <2018-02-02 12:00:57.154328> power:OFF
            <2018-02-02 12:01:22.122824> [APPL] Spoke: power restored,
            powering on
            <2018-02-02 12:01:22.122824> power:ON
            <2018-02-02 12:02:18.121948> [APPL] Spoke: power lost, powering
            down
            <2018-02-02 12:02:18.121948> power:OFF

        Example output with event_labels=["power.state"], showing group
        matches:

        .. code-block:: none

            result.timedout = False
            result.results_list =
                [{'system_timestamp': datetime.datetime(2018, 2, 2, 12, 2,
                18, 121948),
                  'raw_log_line': 'power:OFF',
                  'power.state': ['OFF']}]
            result.count = 1

        Example output with event_labels=["power.lost"], showing matches
        with no groups:

        .. code-block:: none

            result.timedout = False
            result.results_list =
                [{'system_timestamp': datetime.datetime(2018, 2, 2, 12, 2,
                18, 121948),
                  'raw_log_line': '[APPL] Spoke: power lost',
                  'power.lost': []}]
            result.count = 1

        Example output with event_labels=["power.state", "power.lost",
        "power.restored"]:

        .. code-block:: none

            result.timedout = False
            result.results_list =
                [{'system_timestamp': datetime(2018, 2, 2, 12, 2, 18,
                121948),
                  'raw_log_line': 'power:OFF',
                  'power.state': ['OFF']},
                 {'system_timestamp': datetime(2018, 2, 2, 12, 2, 18,
                 121948),
                  'raw_log_line': '[APPL] Spoke: power lost',
                  'power.lost': []}
                 {'system_timestamp': datetime(2018, 2, 2, 12, 1, 22,
                 122824),
                  'raw_log_line': '[APPL] Spoke: power restored, powering
                  on',
                  'power.restored': []}]
            results.count = 3
    """
    if event_labels:
      if not isinstance(event_labels, list):
        raise errors.ParserError("Expecting event_labels to be a list "
                                 "or None but received {} instead.".format(
                                     type(event_labels)))
      cur_event_labels = self.get_event_labels()
      for event_label in event_labels:
        if event_label not in cur_event_labels:
          raise errors.ParserError(
              "Event label {} doesn't exist.".format(event_label))

    return self._parser_obj.get_last_event(
        self.event_filename, event_labels, timeout=timeout)

  def get_event_history(self, event_labels=None, count=None, timeout=10.0):
    r"""Returns up to count elements of event data matching given event labels.

    Args:
        event_labels (list): list of event labels to lookup (example:
          ["power.state", "power.lost"]). If None (default), return all
          events.
        count (int): of event data elements to return (Default: None for all
          events).
        timeout (float): Timeout value in seconds. Example: 1.5.

    Raises:
        ParserError: event_labels is not type list or
                     label in event_labels doesn't exist or
                     on error parsing event file

    Returns:
        ParserResult: An object containing events matching any of the event
        labels provided in event_labels, or all available events if event_labels
        in None. The event data is stored in the .results_list attribute and the
        count of results in the .count attribute. If no matching events are
        found, the .results_list attribute will be set to the empty list.

    If the .timedout attribute is True, the operation timed out before all
    events were searched, or the event file was not found before the timeout
    expired.

    Notes:
        Event info is listed in most recent to least recent order.

        The following examples use a hypothetical power.json filter file
        with the
        following filters:

        .. code-block:: none

            {
                "name": "state",
                "regex_match": "power:(\\w+)"
            },
            {
                "name": "lost",
                "regex_match": "power lost"
            },
            {
                "name": "restored",
                "regex_match": "power restored"
            }

        The original log file being read looks like this:

        .. code-block:: none

            <2018-02-02 10:32:07.167234> [APPL] Spoke: power restored,
            powering on
            <2018-02-02 12:00:57.154328> [APPL] Spoke: power lost, powering
            down
            <2018-02-02 12:00:57.154328> power:OFF
            <2018-02-02 12:01:22.122824> [APPL] Spoke: power restored,
            powering on
            <2018-02-02 12:01:22.122824> power:ON
            <2018-02-02 12:02:18.121948> [APPL] Spoke: power lost, powering
            down
            <2018-02-02 12:02:18.121948> power:OFF

        Example output with event_labels ["power.state"], showing group
        matches:

        .. code-block:: none

            result.timedout = False
            result.results_list =
                [{'system_timestamp': datetime.datetime(2018, 2, 2, 12, 2,
                18, 121948),
                  'raw_log_line': 'power:OFF',
                  'power.state': ['OFF']},
                 {'system_timestamp': datetime.datetime(2018, 2, 2, 12, 1,
                 22, 122824),
                  'raw_log_line': 'power:ON',
                  'power.state': ['ON']},
                 {'system_timestamp': datetime.datetime(2018, 2, 2, 12, 0,
                 57, 154328),
                  'raw_log_line': 'power:OFF',
                  'power.state': ['OFF']}]
            result.count = 3

        Example output with event_labels ["power.lost"], showing matches
        with no groups:

        .. code-block:: none

            result.timedout = False
            result.results_list =
                [{'system_timestamp': datetime.datetime(2018, 2, 2, 12, 2,
                18, 121948),
                  'raw_log_line: '[APPL] Spoke: power lost, powering down',
                  'power.lost': []},
                 {'system_timestamp': datetime.datetime(2018, 2, 2, 12, 0,
                 57, 154328),
                  'raw_log_line': '[APPL] Spoke: power lost, powering down',
                  'power.lost': []}]
            result.count = 2

        Example output with event_labels ["power.restored"], showing matches
        with no
        groups and count=1:

        .. code-block:: none

            result.timedout = False
            result.results_list =
                [{'system_timestamp': datetime.datetime(2018, 2, 2, 12, 1,
                22, 122824),
                  'raw_log_line': '[APPL] Spoke: power restored, powering
                  on',
                  'power.restored': []}
            result.count = 1

        Example output with event_labels ["power.lost", "power.restored"]:

        .. code-block:: none

            result.timedout = False
            result.results_list =
                [{'system_timestamp': datetime.datetime(2018, 2, 2, 12, 2,
                18, 121948),
                  'raw_log_line: '[APPL] Spoke: power lost, powering down',
                  'power.lost': []},
                 {'system_timestamp': datetime.datetime(2018, 2, 2, 12, 1,
                 22, 122824),
                  'raw_log_line': '[APPL] Spoke: power restored, powering
                  on',
                  'power.restored': []},
                 {'system_timestamp': datetime.datetime(2018, 2, 2, 12, 0,
                 57, 154328),
                  'raw_log_line': '[APPL] Spoke: power lost, powering down',
                  'power.lost': []}
                 {'system_timestamp': datetime.datetime(2018, 2, 2, 10, 32,
                 7, 167234),
                  'raw_log_line': '[APPL] Spoke: power restored, powering
                  on',
                  'power.restored': []}]
             result.count = 4
    """
    if event_labels:
      if not isinstance(event_labels, list):
        raise errors.ParserError("Expecting event_labels to be a list "
                                 "or None but received {} instead.".format(
                                     type(event_labels)))
      cur_event_labels = self.get_event_labels()
      for event_label in event_labels:
        if event_label not in cur_event_labels:
          raise errors.ParserError(
              "Event label {} doesn't exist.".format(event_label))

    return self._parser_obj.get_event_history(
        event_labels, count=count, timeout=timeout)

  def get_event_history_count(self, event_label, timeout=10.0):
    """Returns count of event history matching event label specified.

    Args:
        event_label (str): event label to lookup (e.g. power.state)
        timeout (float): Timeout value in seconds. Example: 1.5.

    Raises:
        ParserError: on error parsing event file or event_label doesn't exist

    Returns:
        ParserResult: An object containing the count of results in the .count
        attribute. The .results_list field is set to the empty list.

        If the .timedout attribute is True, the operation timed out before all
        events were searched, or the event file was not found before the timeout
        expired.
    """
    if event_label not in self.get_event_labels():
      raise errors.ParserError(
          "Event label {} doesn't exist.".format(event_label))

    return self._parser_obj.get_event_history_count(
        self.event_filename, event_label, timeout=timeout)

  def get_event_label_dict(self, pattern=None):
    """Takes an event label pattern, and returns a dictionary of matching event labels.

    Args:
        pattern (str): An event label pattern regular expression

    Returns:
        dict: containing keys (i.e. event labels), and values (i.e regular
        expressions)

    Raises:
        ParserError: if pattern provided is an invalid regular expression

    Note:
        The pattern regular expression provided will be matched strictly
        against the beginning of each event_label.
        If no pattern is provided, the _filters_dict is returned.
    """
    return self._parser_obj.get_event_label_dict(pattern=pattern)

  def get_event_labels(self, pattern=None):
    """Takes an event label pattern, and returns a list of matching event labels.

    Args:
        pattern (str): An event label pattern regular expression

    Returns:
        list: of matching event label strings

    Raises:
        ParserError: if pattern provided is an invalid regular expression

    Note:
        The pattern regular expression provided will be matched strictly
        against the beginning of each event_label.
        If no pattern is provided, all filter event labels are returned.
    """
    return self._parser_obj.get_event_labels(pattern=pattern)

  def _parse_events(self, log_path, display_refresh):
    """Parses log file searching for events depositing results into an event file.

    Args:
        log_path (str): Path to log filename containing raw, log event data
        display_refresh (float): Number of seconds to wait prior to refresh
          of display

    Raises:
        ParserError: if log parser fails.

    Note:
        With large log files, this process may take a large amount of time.
    """
    logger.info("Parsing log file {} into event file {}, please wait", log_path,
                self.event_filename)
    start_time = time.time()
    with codecs.open(self.event_filename, "a", encoding="utf-8") as event_file:
      log_filename = os.path.basename(log_path)
      with codecs.open(
          log_path, "r", encoding="utf-8", errors="replace") as log_file:
        log_file.seek(0, os.SEEK_END)
        total_bytes = log_file.tell()
        log_file.seek(0, os.SEEK_SET)
        process_time = start_time
        buffered_unicode = u""
        framer = data_framer.NewlineFramer()
        new_header_length = (
            log_process.HOST_TIMESTAMP_LENGTH +
            log_process.LOG_LINE_HEADER_LENGTH)
        old_header_length = 29
        try:
          while True:
            log_data = log_file.read(size=4096)
            if time.time() - process_time > display_refresh:
              process_time = time.time()
              bytes_processed = log_file.tell()
              logger.info("{:.2%} complete - bytes processed: {} of {}",
                          bytes_processed / total_bytes, bytes_processed,
                          total_bytes)
            if not log_data:
              break

            log_lines = buffered_unicode + log_data
            buffered_len = len(buffered_unicode)
            buffered_unicode = u""
            for log_line in framer.get_lines(log_lines, begin=buffered_len):
              if log_line[-1] == "\n":
                if "> GDM-" in log_line:
                  header_length = new_header_length
                else:
                  header_length = old_header_length
                self._parser_obj.process_line(
                    event_file,
                    log_line,
                    header_length=header_length,
                    log_filename=log_filename)
              else:
                buffered_unicode += log_line
        except IOError as err:
          logger.debug("log_parser encountered error: {!r}".format(err))
          raise errors.ParserError("Log file processing failed. "
                                   "IOError: {!r}".format(err))
    logger.info("Parsing log file {} into event file {} finished in {}s",
                log_path, self.event_filename,
                time.time() - start_time)
