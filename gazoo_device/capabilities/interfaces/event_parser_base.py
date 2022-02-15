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

"""Log event parser capability interface.

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
import abc
from typing import Collection

from gazoo_device.capabilities.interfaces import capability_base

LABEL_REBOOT_TRIGGER = "basic.reboot_trigger",
LABEL_BOOTUP = "basic.bootup"


class ParserResult(object):
  """Store the results of a Parser API call.

    Attributes:
        timedout (bool): True if the Parser request timed out; False otherwise
        results_list (list): A list of Event Results
        count (int): The number of Event Results returned

    Notes:
        An Event Result is a dict with the following format:
            {"system_timestamp": datetime,
             "raw_log_line": str,
             event_label: list, ...}
        The value of the "system_timestamp" key is
        a datetime object with the timestamp when the log line was
        captured by GDM. The value for the "raw_log_line" key is a string
        containing the entire log line captured by GDM, not including the
        timestamp added by GDM. The Event Result also contains one or
        more key - value pairs representing event matches for that log
        line, i.e., there will always be at least one event match, but
        there may be more than one if multiple event regexes match the
        same line.  For each match, the key is the event_label, and the
        value is a list of group matches for the corresponding regex. If
        no groups were specified in the event regex, the group matches
        list will be empty.
  """

  def __init__(self, timedout, results_list, count):
    self.timedout = timedout
    self.results_list = results_list
    self.count = count


class EventParserBase(capability_base.CapabilityBase):
  """Log event parser capability interface."""

  @abc.abstractmethod
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

  @abc.abstractmethod
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

  @abc.abstractmethod
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

  @abc.abstractmethod
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

  @abc.abstractmethod
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

  @abc.abstractmethod
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

  @abc.abstractmethod
  def get_unexpected_reboots(self):
    """Device's event file is used to identify unmatched reboot events.

    Returns:
        list: unexpected reboot event

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

        This method would return::

            [{"basic.reboot_trigger": [],
             "system_timestamp": datetime.datetime.strptime("2018-06-18
             15:13:48.011747",
                                                            "%Y-%m-%d
                                                            %H:%M:%S.%f"),
             "raw_log_line": "Note: GDM triggered reboot"}]
    """

  @abc.abstractmethod
  def get_unmatched_events(self,
                           event_cause_label=LABEL_REBOOT_TRIGGER,
                           event_effect_label=LABEL_BOOTUP):
    """Device's event file is used to identify unmatched events.

    Args:
        event_cause_label (str): Name of event label causing event
        event_effect_label (str): Name of event label signifying effect event

    Returns:
        tuple:  list of unmatched cause event dict entries
                list of unmatched effect event dict entries

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

        This method would return the following tuple::

            ([{"basic.reboot_trigger": [],
             "system_timestamp": datetime.datetime.strptime("2018-06-18
             15:13:48.011747",
                                                            "%Y-%m-%d
                                                            %H:%M:%S.%f"),
             "raw_log_line": "Note: GDM triggered reboot"}],
            [])
    """

  @abc.abstractmethod
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

  @abc.abstractmethod
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

  @abc.abstractmethod
  def verify_event_labels(self, event_labels, error_message=""):
    """Verifies event_labels in correct format and exist.

    Args:
        event_labels (list): list of event_labels.
        error_message (str): error_message to use as header.

    Raises:
        ParserError: if bad format or certain labels don't exist.
    """

  @abc.abstractmethod
  def wait_for_event_labels(self,
                            event_labels,
                            raise_error=False,
                            timeout=20.0,
                            start_datetime=None):
    """Waits up to timeout seconds for event labels to appear in device logs.

    Args:
        event_labels (list): labels(strings) to wait for. Will wait for at
          least one of each.
        raise_error (bool): raise an error if the labels are not found in time.
        timeout (float): seconds to wait for labels to appear in logs.
        start_datetime (datetime): events before this time will be ignored.

    Raises:
        ParserError: if input format is bad
        ParserError: raise_error is True and not all labels were found.

    Returns:
        bool: whether all event labels were found.
    """

  @abc.abstractmethod
  def load_filters(self, filters: Collection[str]) -> None:
    """Load JSON filter files or directories specified.

    Args:
        filters: JSON filter files or paths to filter files.

    Raises:
        ParserError: if files or paths do not exist

    Note:
        Only files ending in .json are loaded, others are skipped(see
        load_filter_file method for an example)
    """
