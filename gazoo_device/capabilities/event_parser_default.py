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

"""Log event parser capability.

Parser provides general purpose regular expression matching on a line by line
basis with the ability to extract both the last and history of matching events.

When the Parser class is created it loads filter files or filter file
directories specified in the `filters` argument.

JSON filter file format (version 1.0):
* A single JSON object with the following keys:

    * "description" whose value is a string (optional)
    * "version" whose value is a JSON object with the following keys:

        * "major" whose value is an integer that specifies the major version of
        the file
        * "minor" whose value is an integer that specifies the major version of
        the file

    * "filters" whose value is an array of Filter JSON objects with the
    following keys:

        * "description" whose value is a string (optional)
        * "regex_match" whose value is a regular expression string
        * "name" whose value is a string

::

    {
        "description": "helpful optional description for all filters contained",
        "version": {"major": 1, "minor": 0},
        "filters": [
            {
                "description": "optional description for this specific filter",
                "regex_match": "required regular expression string",
                "name": "required_name"
            }
        ]
    }

As each JSON filter file is loaded and parsed each regular expression is
assigned a name consisting of the JSON filter file name (without the extension)
plus the name assigned to each Filter object (the "name" key) separated with a
'.' (e.g. errors.assert). This is known in the Parser code base as the
"event_label" and is used as a lookup key to retrieve Parser filter events.

The Parser class expects to store all matching events in an event file. To
reduce the memory footprint of the Parser class all matching events are
immediately written to the event file by the process_line method. The caller
must provide the shared dynamic event dictionary, an event file object, and the
raw log line to this method. Keeping the shared dynamic event dictionary and the
opening and closing of the event file outside the Parser class helps to simplify
the Parser class logic and ensures that the file is closed by the caller as
needed (e.g. exception handling).

For each regular expression that matches the raw log line provided to the
process_line method the shared dynamic event dictionary is updated. When all
regular expressions have been processed an event JSON object containing the
results of all matches by "event_lable" is written (and flushed) to the event
file. The event JSON object format is shown as follows:

JSON event file format (version 1.0):
* A single JSON object with the following keys:

    * "raw_log_line" whose value is the raw log line string parsed
    * "system_timestamp" whose value is a string containing the timestamp
    portion of the
      raw log line
    * "event_label" for each regular expression that matched the log line and
    whose value is an
      array of regular expression group data extracted

::

    {
        "system_timestamp": "2018-01-30 12:05:59.118746",
        "state.shutdown_reboot": ["The system is shutting down"],
        "raw_log_line": "<2018-01-30 12:05:59.118746> announce: The system is
        shutting down."
    }

Since event history can only be obtained from the event file, all event history
commands require the path to the event file to retrieve this information. Event
history is obtained by using the "tac" and "grep" unix tools to filter matching
events in the event file and from Python extract and decode each event JSON
object as described above.
"""
import datetime
import json
import os
import re
import subprocess
import time

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import event_parser_base

logger = gdm_logger.get_logger("parser")

FILTER_JSON_FORMAT_MAJOR_VERSION = 1
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
ParserResult = event_parser_base.ParserResult


def _get_full_filter_name(name, filter_path):
  """Returns full filter name using information from name and filter_path provided.

  Args:
      name (str): as specified in filter dictionary in filter file
      filter_path (str): absolute path to filter file

  Returns:
      str: Full filter name to be used in Parser event file as event_label

  Note:
      The full filter name consists of the following elements:
          * filename without extension (e.g. crashes)
          * name as specified for each filter in filter file (e.g. segfault)

      Example:
          crashes.segfault
  """
  filename = os.path.basename(filter_path)
  file_only = os.path.splitext(filename)[0]
  filter_name = "{}.{}".format(file_only, name)
  return filter_name


def _get_datetime(dt_value):
  """Convert string to datetime object.

  Args:
      dt_value (str): string to convert.

  Raises:
      RuntimeError: if datetime string formatting fails to convert the value

  Returns:
      datetime: object converted from value

  Note:
    Looks for 1 or 3 formats:
       "%Y-%m-%d %H:%M:%S.%f %z"
       "%Y-%m-%d %H:%M:%S.%f"
       "%Y-%m-%d %H:%M:%S"
  """
  result = None
  if result is None:
    result = _get_datetime_from_format(dt_value, "%Y-%m-%d %H:%M:%S.%f %z")
  if result is None:
    result = _get_datetime_from_format(dt_value, "%Y-%m-%d %H:%M:%S.%f")
  if result is None:
    result = _get_datetime_from_format(dt_value, "%Y-%m-%d %H:%M:%S")
  if result is None:
    raise RuntimeError(
        "Failed to convert '{}' into datetime object".format(dt_value))
  return result


def _get_datetime_from_format(dt_value, dt_format):
  """Convert value provided into datetime object or None if not successful.

  The purpose of this method is to attempt to convert the value provided
  using the datetime format string also provided into a datetime object. If
  the value provided doesn't correspond to the datetime format provided
  then the datetime strptime method will throw a ValueError that this method
  will catch and consume by returning None for the result. This reduces the
  error checking the calling function must perform when testing multiple
  datetime formats that may or may not successfully convert the value
  provided into a datetime object.

  Args:
      dt_value (str): the datetime string value to be converted to a datetime
        object
      dt_format (str): the datetime format to use in conversion process

  Returns:
      datetime: if value can be formatted with dt_format provided into
      datetime object or None
      if unsuccessful.
  """
  result = None
  try:
    result = datetime.datetime.strptime(dt_value, dt_format)
  except ValueError:
    pass
  return result


def _get_last_event(device_event_file_path, event_label, timeout=1.0):
  """Returns event data matching the event label specified or None.

  Args:
      device_event_file_path (str): path to file with filtered event
        information.
      event_label (str): event label to lookup (e.g. 'x.state'). If None,
        return the last event regardless of event label.
      timeout (float): Timeout value in seconds. Example: 1.5.

  Raises:
      ValueError: if unable to read json data found in event_file_path.

  Returns:
      tuple: (dict, bool) where the first item is a dict which contains result
      data, and the second item is True if the command timed out, False
      otherwise. The result dict contains data in the following format::

          {"system_timestamp": datetime,
           "raw_log_line": str,
           event_label: list,
           ...}

      If event_label is provided, only the matching event label will be
      included;
      otherwise, all labels recorded in the event file will be included.
  """
  result = None
  timedout = False

  file_exists, remaining_timeout = _wait_for_event_file(device_event_file_path,
                                                        timeout)
  if not file_exists:
    timedout = True
    return result, timedout

  timeout_str = "{:f}".format(remaining_timeout)

  if event_label is None:
    tail_cmd = [
        "timeout", timeout_str, "tail", "-n", "1", device_event_file_path
    ]
    out = ""
    try:
      out = subprocess.check_output(tail_cmd).decode("utf-8", "replace")
    except subprocess.CalledProcessError as err:
      if err.returncode == 124:
        timedout = True
    events = _get_events_from_json_output([out], event_label)
  elif event_label:
    tac_cmd = ["tac", device_event_file_path]
    grep_cmd = ["timeout", timeout_str, "grep", "-m", "1", "-w", event_label]
    tac_proc = subprocess.Popen(tac_cmd, stdout=subprocess.PIPE)
    grep_proc = subprocess.Popen(
        grep_cmd, stdin=tac_proc.stdout, stdout=subprocess.PIPE)
    tac_proc.stdout.close()
    out, _ = grep_proc.communicate()
    if grep_proc.returncode == 124:
      timedout = True
    tac_proc.terminate()
    events = _get_events_from_json_output([out], [event_label])
  else:
    events = None

  if events:
    result = events[0]

  return result, timedout


def _get_events_from_json_output(json_events, event_labels=None):
  """Returns list of event data history matching event_labels provided.

  Args:
      json_events (list): of JSON object strings to return history for.
      event_labels (list): list of event labels to lookup (e.g. ['x.state',
        'x.restored'])

  Raises:
      ValueError: when parsing JSON objects from json_events fails

  Returns:
      list: a list of dictionary objects for each event with the following
      format:
          {"system_timestamp": timestamp as a datetime object,
           "raw_log_line": raw log line as a string
           event_label: a list of regex group data matches, empty list if no
           groups
           ...}

      If multiple event labels match the same line, there will be one
      event_label
      in the dictionary for each match.
  """
  result = []
  for json_object in json_events:
    if json_object:
      try:
        event_dict = json.loads(json_object)
      except ValueError as err:
        logger.info(
            "Failed to parse event log line; skipping. Err: {!r}".format(err))
        continue
      if event_labels is not None:
        filtered_dict = {
            "system_timestamp": _get_datetime(event_dict["system_timestamp"]),
            "raw_log_line": event_dict["raw_log_line"]
        }
        for event_label in event_labels:
          if event_label in event_dict:
            filtered_dict[event_label] = event_dict[event_label]
        result.append(filtered_dict)
      else:
        event_dict["system_timestamp"] = _get_datetime(
            event_dict["system_timestamp"])
        result.append(event_dict)
  return result


def _get_all_event_history(device_event_file_path, event_labels, timeout=10.0):
  """Returns list of event history matching event labels specified.

  Args:
      device_event_file_path (str): path to file with filtered event
        information
      event_labels (list): list of event labels to lookup (e.g. ['x.state',
        'x.restored']). If None, return all events.
      timeout (float): Timeout value in seconds. Example: 10.0.

  Raises:
      ValueError: on (unlikely) invalid JSON data found in
      self.event_file_path file.

  Returns:
     tuple: (list of event objects (dict), bool whether or not command
     timedout )

  Note:
      The Parser standard is to return the list from newest to oldest,
      therefore we reverse the output returned by grep.
  """
  result = []
  timedout = False

  file_exists, remaining_timeout = _wait_for_event_file(device_event_file_path,
                                                        timeout)
  if not file_exists:
    timedout = True
    return result, timedout

  timeout_str = "{:f}".format(remaining_timeout)

  if event_labels is None:
    tac_cmd = ["timeout", timeout_str, "tac", device_event_file_path]
    out = ""
    try:
      out = subprocess.check_output(tac_cmd).decode("utf-8", "replace")
    except subprocess.CalledProcessError as err:
      if err.returncode == 124:
        timedout = True
    json_events = out.splitlines()
  else:
    grep_cmd = ["timeout", timeout_str, "grep", "-w"]
    for event_label in event_labels:
      if event_label:
        grep_cmd.append("-e")
        grep_cmd.append(event_label)
    grep_cmd.append(device_event_file_path)
    grep_proc = subprocess.Popen(grep_cmd, stdout=subprocess.PIPE)
    out, _ = grep_proc.communicate()
    if grep_proc.returncode == 124:
      timedout = True
    json_events = out.splitlines()
    json_events.reverse()

  return _get_events_from_json_output(json_events, event_labels), timedout


def _get_event_history_count(device_event_file_path, event_label, timeout=10.0):
  """Returns count of event history matching event label specified.

  Args:
      device_event_file_path (str): to extract event history from
      event_label (str): event label to lookup (e.g. 'x.state')
      timeout (float): Timeout value in seconds. Example: 10.0.

  Raises:
      ValueError: on (unlikely) invalid JSON data found in
      self.event_file_path file.

  Returns:
      tuple: (int count of all events found, bool of whether command timed
      out).
  """
  result = 0
  timedout = False

  file_exists, remaining_timeout = _wait_for_event_file(device_event_file_path,
                                                        timeout)
  if not file_exists:
    timedout = True
    return result, timedout

  timeout_str = "{:f}".format(remaining_timeout)

  grep_cmd = [
      "timeout", timeout_str, "grep", "-c", "-w", event_label,
      device_event_file_path
  ]
  grep_proc = subprocess.Popen(grep_cmd, stdout=subprocess.PIPE)
  out, _ = grep_proc.communicate()
  if grep_proc.returncode == 124:
    timedout = True

  if out:
    result = int(out.strip())

  return result, timedout


def _get_limited_event_history(device_event_file_path,
                               event_labels,
                               limit,
                               timeout=10.0):
  """Returns list of event history matching event labels specified.

  Args:
      device_event_file_path(str): path to file with filtered event
        information
      event_labels(list): list of event labels to lookup(e.g. ['x.state',
        'x.restored']). If None, return all events up to limit.
      limit(int): the number of event data elements returned
      timeout(float): Timeout value in seconds. Example: 10.0.

  Raises:
      ValueError: on(unlikely) invalid JSON data found in self.event_file_path
      file

  Returns:
      tuple: (list of event dicts up to 'limit' length, bool whether or not
      timed out)

  Note:
      Event info listed in most recent to least recent order. If regex_match
      for event_label
      has groups, it will return the group match, else it will return the raw
      log line.
      Implemented via grep and tac for time efficiency.
  """
  result = []
  timedout = False

  file_exists, remaining_timeout = _wait_for_event_file(device_event_file_path,
                                                        timeout)
  if not file_exists:
    timedout = True
    return result, timedout

  timeout_str = "{:f}".format(remaining_timeout)

  if event_labels is None:
    tac_cmd = ["tac", device_event_file_path]
    head_cmd = ["timeout", timeout_str, "head", "-n", str(limit)]
    tac_proc = subprocess.Popen(tac_cmd, stdout=subprocess.PIPE)
    head_proc = subprocess.Popen(
        head_cmd, stdin=tac_proc.stdout, stdout=subprocess.PIPE)
    tac_proc.stdout.close()
    out, _ = head_proc.communicate()
    if head_proc.returncode == 124:
      timedout = True
    tac_proc.terminate()
    json_events = out.splitlines()
  else:
    tac_cmd = ["tac", device_event_file_path]
    grep_cmd = ["timeout", timeout_str, "grep", "-m", str(limit), "-w"]
    for event_label in event_labels:
      if event_label:
        grep_cmd.append("-e")
        grep_cmd.append(event_label)
    tac_proc = subprocess.Popen(tac_cmd, stdout=subprocess.PIPE)
    grep_proc = subprocess.Popen(
        grep_cmd, stdin=tac_proc.stdout, stdout=subprocess.PIPE)
    tac_proc.stdout.close()
    out, _ = grep_proc.communicate()
    if grep_proc.returncode == 124:
      timedout = True
    tac_proc.terminate()
    json_events = out.splitlines()

  return _get_events_from_json_output(json_events, event_labels), timedout


def _wait_for_event_file(event_file_path, timeout):
  """Wait up to the timeout period for the event file to be created.

  Args:
      event_file_path(str): Full path to the event file.
      timeout(float): Timeout value in seconds. Example: 1.5.

  Returns:
      tuple: (bool, float) A tuple where the first value is True if the file
      was found before the timeout expired, and False otherwise, and the second
      value is the amount of timeout time remaining.  For example, (True, 0.958)
      would indicate the file was found with 0.958 seconds of timeout left, and
      (False, 0) indicates that the event file was not found.  If the file is
      not found, the remaining time will always be 0.
  """

  start_time = time.time()
  end_time = start_time + timeout

  while True:
    timeout_remaining = end_time - time.time()
    if timeout_remaining <= 0:
      return (False, 0)
    elif os.path.exists(event_file_path):
      return (True, timeout_remaining)
    else:
      time.sleep(0.1)


class _EventMatch(object):
  """Encapsulates matching events with event time delta."""

  def __init__(self, event_delta, event_list):
    """Initializes _EventMatch.

    Args:
        event_delta (timedelta): Difference between event datetime instances
        event_list (list): Containing filter events

    Note:
        Filter events in event_list typically appear as::  [
            {"basic.reboot_trigger": [],
            "system_timestamp": datetime.datetime.strptime("2018-06-18
              15:13:48.011747",
                                                           "%Y-%m-%d
                                                             %H:%M:%S.%f"),
            "raw_log_line": "Note: GDM triggered reboot"},
            {"basic.bootup": [],
            "system_timestamp": datetime.datetime.strptime("2018-06-18
              15:13:49.092755",
                                                           "%Y-%m-%d
                                                             %H:%M:%S.%f"),
            "raw_log_line": "[0:00:00.035] [APPL] Welcome to Lock App"} ]
    """

    self.event_delta = event_delta
    self.event_list = event_list


class EventParserDefault(event_parser_base.EventParserBase):
  """Parser class for filtering log lines."""

  def __init__(self, filters, event_file_path, device_name):
    """Initializes the log event parser.

    Args:
        filters (list[str]): list of paths to JSON filter files or filter
          directories.
        event_file_path (str): path to the log event file.
        device_name (str): the name of the device using this capability.
    """
    super().__init__(device_name=device_name)
    self._filters_dict = {}
    self.event_file_path = event_file_path
    self.load_filters(filters)

  def get_event_history(self, event_labels=None, count=None, timeout=10.0):
    r"""Returns up to count elements of event data matching given list of event labels.

    Args:
        event_labels (list): list of event labels to lookup(example:
          ["power.state", "power.lost"]). If None(default), return all
          events.
        count (int): of event data elements to return (Default: None for all
          events).
        timeout (float): Timeout value in seconds. Example: 10.0.

    Raises:
        ParserError: on error parsing event file.

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
        with the following filters:

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
            <2018-02-02 12:02:18.121948> power:OF

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

        Example output with event_labels["power.restored"], showing matches
        with no groups and count=1:

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
      self.verify_event_labels(
          event_labels,
          error_message="{} get_event_history failed.".format(
              self._device_name))
    timedout = False
    try:
      if count:
        history_results, timedout = _get_limited_event_history(
            self.event_file_path, event_labels, count, timeout=timeout)
      else:
        history_results, timedout = _get_all_event_history(
            self.event_file_path, event_labels, timeout=timeout)
      return ParserResult(
          timedout=timedout,
          results_list=history_results,
          count=len(history_results))
    except Exception as err:
      raise errors.ParserError(
          "Retrieving events {} history from {} failed. Error {!r}".format(
              event_labels, self.event_file_path, err))

  def get_event_history_count(self, event_label, timeout=10.0):
    """Returns count of event history matching event label specified.

    Args:
        event_label(str): event label to lookup(e.g. power.state)
        timeout(float): Timeout value in seconds. Example: 10.0.

    Raises:
        ParserError: on error parsing event file

    Returns:
        ParserResult: An object containing the count of results in the
        .count attribute. The .results_list field is set to the empty list.

        If the .timedout attribute is True, the operation timed out before
        all events were searched, or the event file was not found before the
        timeout expired.
    """

    self.verify_event_labels(
        [event_label],
        error_message="%s get_event_history_count failed." % self._device_name)

    try:
      count, timedout = _get_event_history_count(
          self.event_file_path, event_label, timeout=timeout)
      return ParserResult(timedout=timedout, results_list=[], count=count)
    except Exception as err:
      raise errors.ParserError(
          "Retrieving event {} history from {} failed. Error {!r}".format(
              event_label, self.event_file_path, err))

  def get_event_label_dict(self, pattern=None):
    """Takes an event label pattern, and returns a dictionary of matching event labels.

    Args:
        pattern(str): Regex for event labels. Default: None

    Returns:
        dict: containing keys(i.e. event labels), and values(i.e regular
        expressions)

    Raises:
        ParserError: if pattern provided is an invalid regular expression

    Note:
        The pattern regular expression provided will be matched strictly
        against the beginning of each event_label.
        If no pattern is provided, the _filters_dict is returned.
    """

    if pattern is None:
      return {key: value.pattern for key, value in self._filters_dict.items()}
    else:
      try:
        result_dict = {}
        regex = re.compile(pattern)
        for event_label in list(filter(regex.match, list(self._filters_dict))):
          result_dict[event_label] = self._filters_dict[event_label].pattern
        return result_dict
      except Exception as err:
        raise errors.ParserError(
            "Compiling regular expression pattern {} failed. "
            "Error: {!r}".format(pattern, err))

  def get_event_labels(self, pattern=None):
    """Takes an event label pattern, and returns a list of matching event labels.

    Args:
        pattern(str):  Regex for event labels. Default: None

    Returns:
        list: of matching event label strings

    Raises:
        ParserError: if pattern provided is an invalid regular expression

    Note:
        The pattern regular expression provided will be matched strictly
        against the beginning of each event_label.
        If no pattern is provided, all filter event labels are returned.
    """

    if pattern is None:
      return list(self._filters_dict.keys())
    else:
      try:
        regex = re.compile(pattern)
        return list(filter(regex.match, list(self._filters_dict.keys())))
      except Exception as err:
        raise errors.ParserError(
            "Compiling regular expression pattern {} failed. "
            "Error {!r}".format(pattern, err))

  def get_last_event(self, event_labels=None, timeout=1.0):
    r"""Returns the most recent matching event for each item in the list of event labels.

    Args:
        event_labels (list): list of event labels to lookup (example:
          ["power.state", "power.lost"]). None (default) returns the most
          recent event regardless of label.
        timeout (float): Timeout value in seconds. Example: 1.5.

    Raises:
        ParserError: on error parsing event file.
        DeviceError: Label doesn't exist or
                     event_labels is not type list

    Returns:
        ParserResult: An object containing the most recent event match for
        each event label in the event_labels list, or the most recent event if
        event_labels is None. The event data is stored in the .results_list
        attribute, and the count of results is in the .count attribute. If
        no matching events are found, the .results_list attribute will be set to
        the empty list.

        If the .timedout attribute is True, the operation timed out before
        all events were searched, or the event file was not found before the
        timeout expired.

    Notes:
        The event_label is the desired filter filename without extension a .
        and the filter name (e.g. power.state).

        The following examples use a hypothetical power.json filter file
        with the following filters:

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
    if event_labels is None:
      event_labels = [None]
    else:
      self.verify_event_labels(
          event_labels,
          error_message="%s get_last_event failed." % self._device_name)

    results = []
    any_timed_out = False

    try:
      for event_label in event_labels:
        event_data, timedout = _get_last_event(self.event_file_path,
                                               event_label, timeout)
        if event_data:
          results.append(event_data)
        any_timed_out |= timedout

      return ParserResult(
          timedout=any_timed_out, results_list=results, count=len(results))

    except Exception as err:
      raise errors.ParserError(
          "{} get_last_event failed for {}. Error: {!r}.".format(
              self._device_name, event_labels, err))

  def get_last_event_state(self,
                           event_label,
                           event_name=None,
                           raise_error=False,
                           timeout=1.0,
                           group_index=0):
    r"""Return the matching group of the event label regex if one is found.

    Args:
        event_label(str): The event label based on the filter name and
          filter file name.
        event_name (str): name of event. Defaults to event_label.
        raise_error(bool): Raise an exception if the event has not been seen
          or otherwise return an empty string.
        timeout (float): time to parse events.
        group_index (int): index of the match group to return (default 0 for
          first).

    Returns:
        str: The result from the call to get_last_event and getting the
        first group.

    Raises:
        ParserError: if there is an error getting the last event.

        .. code-block:: none
            {
                "name": "state",
                "regex_match": "power:(\\w+)"
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

        With event_labels=["power.state"], it would return 'OFF'
    """
    if not event_name:
      event_name = event_label
    result = self.get_last_event([event_label], timeout=timeout)

    if not result.results_list:
      msg = "{} get event state failed. {} not yet seen in logs".format(
          self._device_name, event_name)
    else:
      match_groups = result.results_list[0][event_label]
      if group_index < len(match_groups):
        return match_groups[group_index]
      else:
        msg = (
            "{} get event state failed. Group index ({}) is greater than "
            "number of match groups ({})").format(self._device_name, group_index,
                                        match_groups)

    if raise_error:
      raise errors.ParserError(msg)
    else:
      logger.warning(msg)
      return ""

  def get_unexpected_reboots(self):
    """Device's event file is used to identify unmatched reboot events.

    Returns:
        list: unexpected reboot event

    Note:
        For example in the following case there are two reboot triggers but
        only one
        bootup event::

            {"basic.reboot_trigger": [],
             "system_timestamp": datetime.datetime.strptime("2018-06-18
             15:13:48.011747",
                                                            "%Y-%m-%d
                                                            %H:%M:%S.%f"),
             "raw_log_line": "Note: GDM triggered reboot"},
            {"basic.reboot_trigger": [],
             "system_timestamp": datetime.datetime.strptime("2018-06-18
             15:13:52.825231",
                                                            "%Y-%m-%d
                                                            %H:%M:%S.%f"),
             "raw_log_line": "Note: GDM triggered reboot"}
            {"basic.bootup": [],
             "system_timestamp": datetime.datetime.strptime("2018-06-18
             15:13:58.540417",
                                                            "%Y-%m-%d
                                                            %H:%M:%S.%f"),
             "raw_log_line": "[0:00:00.035] [APPL] Welcome to Lock App"}

        This method would return::

            [{"basic.reboot_trigger": [],
             "system_timestamp": datetime.datetime.strptime("2018-06-18
             15:13:48.011747",
                                                            "%Y-%m-%d
                                                            %H:%M:%S.%f"),
             "raw_log_line": "Note: GDM triggered reboot"}]
    """

    _, remaining_bootups = self.get_unmatched_events(
        event_cause_label="basic.reboot_trigger",
        event_effect_label="basic.bootup")

    return remaining_bootups

  def get_unmatched_events(self,
                           event_cause_label="basic.reboot_trigger",
                           event_effect_label="basic.bootup"):
    """Device's event file is used to identify unmatched events.

    Args:
        event_cause_label (str): Name of event label causing event
        event_effect_label (str): Name of event label signifying effect
          event

    Returns:
        tuple:  list of unmatched cause event dict entries
                list of unmatched effect event dict entries

    Note:
        For example in the following case there are two reboot triggers but
        only one bootup event::

            {"basic.reboot_trigger": [],
             "system_timestamp": datetime.datetime.strptime("2018-06-18
             15:13:48.011747",
                                                            "%Y-%m-%d
                                                            %H:%M:%S.%f"),
             "raw_log_line": "Note: GDM triggered reboot"},
            {"basic.reboot_trigger": [],
             "system_timestamp": datetime.datetime.strptime("2018-06-18
             15:13:52.825231",
                                                            "%Y-%m-%d
                                                            %H:%M:%S.%f"),
             "raw_log_line": "Note: GDM triggered reboot"}
            {"basic.bootup": [],
             "system_timestamp": datetime.datetime.strptime("2018-06-18
             15:13:58.540417",
                                                            "%Y-%m-%d
                                                            %H:%M:%S.%f"),
             "raw_log_line": "[0:00:00.035] [APPL] Welcome to Lock App"}

        This method would return the following tuple::

            ([{"basic.reboot_trigger": [],
             "system_timestamp": datetime.datetime.strptime("2018-06-18
             15:13:48.011747",
                                                            "%Y-%m-%d
                                                            %H:%M:%S.%f"),
             "raw_log_line": "Note: GDM triggered reboot"}],
            [])
    """
    event_cause_list = []  # Cause events matching event_cause_label
    event_match_list = [
    ]  # EventMatch objects holding events matched together based on time
    remaining_cause_list = []  # Cause events with no matching effect events
    remaining_effect_list = []  # Effect events with no matching cause events

    event_cause_hist = self.get_event_history([event_cause_label])
    if not event_cause_hist.timedout:
      remaining_cause_list = event_cause_hist.results_list[:]
      event_cause_list = event_cause_hist.results_list
    event_effect_hist = self.get_event_history([event_effect_label])
    if not event_effect_hist.timedout:
      remaining_effect_list = event_effect_hist.results_list[:]

    # List of each cause event's datetime.datetime value
    cause_datetime_list = [
        event["system_timestamp"] for event in event_cause_list
    ]

    # A copy of cause_datetime_list adjusted during event match processing
    wrk_datetime_list = cause_datetime_list[:]

    # Create list of matching events
    for effect_event in event_effect_hist.results_list:
      effect_datetime = effect_event["system_timestamp"]
      try:
        nearest_cause_datetime = self._nearest_datetime(wrk_datetime_list,
                                                        effect_datetime)
      except errors.ParserError:  # Means wrk_datetime_list is empty
        break
      delta_time = effect_datetime - nearest_cause_datetime
      cause_event = event_cause_list[cause_datetime_list.index(
          nearest_cause_datetime)]
      event_match = _EventMatch(
          event_delta=delta_time, event_list=[cause_event, effect_event])
      event_match_list.append(event_match)
      # The datetime has been used, adjust list to avoid reuse
      del wrk_datetime_list[wrk_datetime_list.index(nearest_cause_datetime)]
    if len(event_match_list) > 1:
      event_match_list.sort(key=lambda match_obj: match_obj.event_delta)

    # Use list of matching events to determine unmatched events
    for event_match in event_match_list:
      if remaining_cause_list and remaining_effect_list:
        cause_event = event_match.event_list[0]
        effect_event = event_match.event_list[1]
        try:
          idx = remaining_cause_list.index(cause_event)
          del remaining_cause_list[idx]
        except ValueError:
          pass
        try:
          idx = remaining_effect_list.index(effect_event)
          del remaining_effect_list[idx]
        except ValueError:
          pass
    return remaining_cause_list, remaining_effect_list

  @decorators.CapabilityLogDecorator(logger, level=decorators.DEBUG)
  def load_filter_file(self, filter_path):
    """Load JSON filter file specified.

    Args:
        filter_path (str): path to JSON filter file

    Raises:
        ParserError: when loading JSON filter file fails or on unexpected
        JSON key values

    Note:
        Only files ending in .json are loaded, others are skipped

        Example:
            {
                "description": "Assertion event filter",
                "version": {"major": 1, "minor": 0},
                "filters": [
                    {
                        "description": "match and extract assert message"
                        "regex_match": "ASSERT: (.+)",
                        "name": "state"
                    }
                ]
            }
        """
    logger.debug("Adding filter file {}", filter_path)
    try:
      with open(filter_path, "r") as filter_file:
        try:
          json_filter_data = json.load(filter_file)
        except Exception as err:
          msg = "Unable to parse filter file {} as a json file. {!r}".format(
              filter_path, err)
          logger.debug(msg)
          raise errors.ParserError(msg)
    except IOError:
      raise errors.ParserError(
          "Unable to access filter path '{}'".format(filter_path))

    if "version" not in json_filter_data:
      raise errors.ParserError(
          "Loading filter-file {} failed. Missing 'version' key.".format(
              filter_path))

    if "filters" not in json_filter_data:
      raise errors.ParserError(
          "Loading filter-file {} failed. Missing 'filters' key.".format(
              filter_path))

    if not isinstance(json_filter_data["version"], dict):
      raise errors.ParserError(
          "Loading filter-file {} failed. "
          "Expecting value of 'version' entry to be a dictionary "
          "but instead its a {}.".format(filter_path,
                                         type(json_filter_data["version"])))

    version_info = json_filter_data["version"]

    if "major" not in version_info:
      raise errors.ParserError(
          "Loading filter-file {} failed. "
          "Missing 'major' key in 'version' value.".format(filter_path))

    if "minor" not in version_info:
      raise errors.ParserError(
          "Loading filter-file {} failed. "
          "Missing 'minor' key in 'version' value.".format(filter_path))

    if not isinstance(version_info["major"], int):
      raise errors.ParserError(
          "Loading filter-file {} failed. "
          "Expecting int for major version found {} instead.".format(
              filter_path, type(version_info["major"])))

    if not isinstance(version_info["minor"], int):
      raise errors.ParserError(
          "Loading filter-file {} failed. "
          "Expecting int for minor version found {} instead.".format(
              filter_path, type(version_info["minor"])))

    if version_info["major"] != FILTER_JSON_FORMAT_MAJOR_VERSION:
      raise errors.ParserError(
          "Loading filter-file {} failed. "
          "Found unexpected major version in JSON filter file.".format(
              filter_path))

    self._add_filters(json_filter_data["filters"], filter_path)

  @decorators.CapabilityLogDecorator(logger, level=None)
  def process_line(self,
                   event_file,
                   raw_log_line,
                   header_length=29,
                   log_filename=""):
    """Parser line against filters and write JSON result to event_file provided.

    Args:
        event_file (file): to write matching filter results to
        raw_log_line (str): to match filters against
        header_length (int): added by GDM to strip off from raw_log_line
        log_filename (str): name of log file raw_log_line came from

    Note: The expected format for the raw_log_line is one that contains the
      system timestamp between characters 1 and 27 as shown in the following
      example:
        <2018-02-01 14:39:00.492376> ...
        A line containing a event_entry should be written as follows:
            * Key: log_filename, Value: filename where raw_log_line was found
            * Key: matched_timestamp, Value: a host timestamp when match was
              found.
            * Key: raw_log_line, Value: the line provided without any trailing
              whitespace
            * Key: system_timestamp, Value: the timestamp portion of the raw log
              line
            * Key: <event_label>, Value: regular expression group tuple as
              an array which might be empty  In addition to writing results
              to the event file the <event_label> is used as a key to update
              the shared dynamic events dictionary with the same information
              to allow for easier access to the data for the last matching
              <event_label> in the main process
    """

    event_data = {}
    for filter_name, regex in self._filters_dict.items():
      match = regex.search(raw_log_line)
      if match:
        match_data = match.groups()
        event_data[filter_name] = match_data

    if event_data:
      if log_filename:
        event_data["log_filename"] = log_filename
      event_data["raw_log_line"] = raw_log_line.rstrip()[header_length:]
      event_data["system_timestamp"] = raw_log_line[1:27]
      event_data["matched_timestamp"] = \
          datetime.datetime.now().strftime(TIMESTAMP_FORMAT)
      event_file.write(json.dumps(event_data) + "\n")
      event_file.flush()

  @decorators.CapabilityLogDecorator(logger, level=decorators.DEBUG)
  def verify_event_labels(self, event_labels, error_message=""):
    """Verifies event_labels in correct format and exist.

    Args:
       event_labels (list): list of event_labels.
       error_message (str): error_message to use as header.

    Raises:
       ParserError: if bad format or certain labels don't exist.
    """
    if event_labels is not None and not isinstance(event_labels, list):
      raise errors.ParserError("{} Expecting event_labels to be a list "
                               "or None but received {} instead.".format(
                                   error_message, type(event_labels)))
    if any(not isinstance(label, str) for label in event_labels):
      raise errors.ParserError(
          "{} Expected event_labels to be a list of strings. "
          "Found {}.".format(error_message, event_labels))

    cur_event_labels = self.get_event_labels()
    for event_label in event_labels:
      if event_label not in cur_event_labels:
        raise errors.ParserError(
            "{} label {} not available. Choose from: {}".format(
                self._device_name, event_label, self.get_event_labels()))

  def wait_for_event_labels(self,
                            event_labels,
                            raise_error=False,
                            timeout=20.0,
                            start_datetime=None):
    """Waits up to timeout seconds for event labels to appear in device logs.

    Args:
        event_labels (list): labels(strings) to wait for. Will wait for at
          least one of each.
        raise_error (bool): raise an error if the labels are not found in
          time.
        timeout (float): seconds to wait for labels to appear in logs.
        start_datetime (datetime): events before this time will be ignored.

    Raises:
        ParserError: if input format is bad
        ParserError: raise_error is True and not all labels were found.

    Returns:
        bool: whether all event labels were found.
    """
    self.verify_event_labels(
        event_labels,
        error_message="{} wait_for_event_labels failed.".format(
            self._device_name))
    logger.info("{} waiting up to {}s for the following labels: {}.".format(
        self._device_name, timeout, event_labels))

    if start_datetime is None:
      start_datetime = datetime.datetime.now()
    start_time = time.time()
    end_time = start_time + timeout

    all_found = False

    while not all_found and time.time() < end_time:
      remaining_time = timeout - (time.time() - start_time)
      # len(event_labels) can be 0; avoid zero division
      time_per_label = remaining_time / max(len(event_labels), 1)

      any_timed_out = False
      found_labels = []
      missed_labels = []

      for event_label in event_labels:
        result = self.get_last_event([event_label], timeout=time_per_label)
        any_timed_out |= result.timedout
        if (result.results_list and
            result.results_list[0]["system_timestamp"] >= start_datetime):
          found_labels.append(event_label)
        else:
          missed_labels.append(event_label)

      all_found = not any_timed_out and len(found_labels) == len(event_labels)

    if not all_found:
      msg = (
          "{}: not all events corresponding to labels were found in {}s. "
          "Looked for labels: {}. Found labels: {}. Missed labels: {}.".format(
              self._device_name, timeout, event_labels, found_labels,
              missed_labels))
      if raise_error:
        raise errors.ParserError(msg)
      else:
        logger.warning(msg)

    return all_found

  def _add_filter(self, filter_list, filter_path):
    """Adds filter dictionary expression from filter_path specified.

    Args:
        filter_list(list): of filter dictionaries definitions to add
        filter_path(str): that provided the list of filters being added

    Raises:
        ParserError: when one of the following occurs
            * filter dictionary is missing the name key
            * filter dictionary is missing the regex_match key
            * full filter name already exists(e.g. already loaded)
            * the regex_match is invalid(won't compile)
    """
    if "name" not in filter_list:
      raise errors.ParserError(
          "Loading filter-file {} failed. "
          "Missing 'name' key in filter object '{!r}'.".format(
              filter_path, filter_list))
    if "regex_match" not in filter_list:
      raise errors.ParserError(
          "Loading filter-file {} failed. "
          "Missing 'regex_match' key in filter object '{!r}'.".format(
              filter_path, filter_list))

    full_filter_name = _get_full_filter_name(filter_list["name"], filter_path)
    if full_filter_name in self._filters_dict:
      raise errors.ParserError("Loading filter-file {} failed. "
                               "Filter named {} already exists.".format(
                                   filter_path, full_filter_name))

    try:
      self._filters_dict[full_filter_name] = re.compile(
          filter_list["regex_match"])
      logger.debug("Added filter {} from filter file {}", full_filter_name,
                   filter_path)
    except re.error as err:
      raise errors.ParserError(
          "Loading filter-file {} failed. Unable to"
          " compile regular expression value '{}'. Error {!r}".format(
              filter_path, filter_list["regex_match"], err))

  def _add_filters(self, filter_list, filter_path):
    """Adds filters loaded from file_name to list of filters to use.

    Args:
        filter_list(list): of filter dictionaries definitions to add
        filter_path(str): that provided the list of filters being added

    Raises:
        ParserError: when filters is not of type list
    """
    if not isinstance(filter_list, list):
      raise errors.ParserError(
          "Loading filter-file {} failed. "
          "Expecting value of 'filter_list' entry to be a list "
          "but instead its a {}.".format(filter_path, type(filter_list)))

    for cur_filter in filter_list:
      self._add_filter(cur_filter, filter_path)

  def _load_filter_directory(self, filter_path):
    """Loads every .json file found in filter_path specified.

    Args:
        filter_path(str): path to filter directory

    Raises:
        ParserError: if unable to access the filter_path provided

    Note:
        Only files ending in .json are loaded, others are skipped(see
        load_filter_file method for an example)
    """
    try:
      logger.debug("Adding filters from directory {}", filter_path)
      for filter_file in os.listdir(filter_path):
        if filter_file.endswith(".json"):
          filter_file_path = os.path.join(filter_path, filter_file)
          self.load_filter_file(filter_file_path)
        else:
          logger.debug("Skipping file {} missing .json extension", filter_path)
    except OSError:
      raise errors.ParserError(
          "Unable to access filter path '{}'".format(filter_path))

  @decorators.CapabilityLogDecorator(logger, level=decorators.DEBUG)
  def load_filters(self, filters):
    """Load JSON filter files or directories specified.

    Args:
        filters(list): of JSON filter files or paths to filter files

    Raises:
        ParserError: if files or paths do not exist

    Note:
        Only files ending in .json are loaded, others are skipped(see
        load_filter_file method for an example)
    """
    if not filters:
      return
    if not isinstance(filters, list):
      raise errors.ParserError("Expecting 'filters' value to be a list "
                               "but instead its a {}.".format(type(filters)))
    for filter_path in filters:
      if not os.path.exists(filter_path):
        raise errors.ParserError(
            "Filter path '{}' doesn't exist".format(filter_path))
      elif os.path.isdir(filter_path):
        self._load_filter_directory(filter_path)
      else:
        self.load_filter_file(filter_path)

  def _nearest_datetime(self, datetime_list, target_datetime):
    """Locates a datetime.datetime closest to target datetime.

    Args:
        datetime_list(list): Containing datetime.datetime entries
        target_datetime(datetime.datetime): Desired target

    Returns:
        datetime.datetime: Closest entry to target datetime without
        exceeding target datetime

    Raises:
        ParserError: If datetime_list is empty
    """
    if not datetime_list:
      raise errors.ParserError(
          "Input parameter datetime_list length is zero. Required"
          " parameters: [datetime.datetime], datetime.datetime")
    work_list = [entry for entry in datetime_list if entry < target_datetime]
    if not work_list:
      raise errors.ParserError(
          "work_list length is zero. Entries in datetime_list"
          " {} are not < target_datetime {}".format(datetime_list,
                                                    target_datetime))
    return min(
        work_list,
        key=lambda datetime_entry: abs(datetime_entry - target_datetime))
