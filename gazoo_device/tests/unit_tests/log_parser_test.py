# Copyright 2023 Google LLC
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

"""This test script verifies GDM is working with log_parser.LogParser."""
import datetime
import os
from unittest import mock
from gazoo_device import errors
from gazoo_device import log_parser
from gazoo_device.capabilities import event_parser_default
from gazoo_device.switchboard import log_process
from gazoo_device.tests.unit_tests.utils import unit_test_case

_ANOTHER_MESSAGE_LINE = "{} [APPL] This is another message\n"
_HISTORY_COUNT = 2018
_MAX_LOG_LINES = 10
_NO_MATCH_LINE = "{} [BOOT] Non-matching line\n"
_NON_ASCII_LINE = "{} [APPL] Some non-existent message with non-ascii \xf7\n"
_LINE_RETURN_LINE = ("{} \r[APPL] Some non-existent message with extra LR "
                     "chars\r\n")
_NEW_HEADER_LINE = ("{} GDM-0: [APPL] Some non-existent message with new log "
                    "header\r\n")

_RESULTS_LIST = ["a", "b", "c"]
_STATE_LINE = "{} [APPL] Some other message with group data {}\n"
_TEST_LABEL_DICT = {
    "sample.message": "\\[APPL\\] Some unique message",
    "sample.message2": "unique message",
    "sample.message3": "another message",
    "sample.state": "\\[APPL\\] Some other message with group data (\\d+)"
}
_TIMED_OUT_NO = False
_UNIQUE_MESSAGE_LINE = "{} [APPL] Some unique message\n"


def _remove_file(filename):
  if filename is not None and os.path.isfile(filename):
    os.remove(filename)


class LogParserTests(unit_test_case.UnitTestCase):

  def setUp(self):
    super().setUp()
    # configure mock test resource
    self.mock_parser = mock.MagicMock(
        spec=event_parser_default.EventParserDefault)
    self.log_filename = os.path.join(self.artifacts_directory,
                                     self._testMethodName + ".txt")
    self.event_filename = log_process.get_event_filename(self.log_filename)
    self.event_label = list(_TEST_LABEL_DICT.keys())[0]
    self._create_log_file(_MAX_LOG_LINES)
    self.add_time_mocks()

  def test_log_parser_init_parser_obj_none(self):
    """Verify log parser method init returns error if parser obj is none."""

    with self.assertRaisesRegex(errors.ParserError, "Bad parser_obj"):
      log_parser.LogParser(None, self.log_filename)

  def test_log_parser_init_bad_log_filename(self):
    """Verify log parser method init returns error if a bad log filename is given."""

    with self.assertRaisesRegex(errors.ParserError, "does not exist"):
      log_parser.LogParser(self.mock_parser, "/home/noway/jose.txt")

  def test_log_parser_init_event_filename_already_exists(self):
    """Verify log parser method init detects event filename already exists."""

    log_parser.LogParser(self.mock_parser, self.log_filename)
    with self.assertRaisesRegex(errors.ParserError, "already exists"):
      log_parser.LogParser(self.mock_parser, self.log_filename)

  def test_log_parser_init_valid_parameters(self):
    """Verify log parser method init is successful if valid parameters are given."""

    uut = log_parser.LogParser(self.mock_parser, self.log_filename)
    self.assertIsInstance(uut, log_parser.LogParser)

  def test_log_parser_init_parse_events(self):
    """Verify log parser method init's call to Parser process_line."""

    log_parser.LogParser(self.mock_parser, self.log_filename)
    self.assertEqual(
        self.expected_parser_calls, self.mock_parser.process_line.call_count,
        "Expected Parser process_line method to be called {} times. "
        "Instead got: {}".format(self.expected_parser_calls,
                                 self.mock_parser.process_line.call_count))

  def test_log_parser_init_display_refresh_negative(self):
    """Verify log parser method init returns error if display refresh is negative."""
    with self.assertRaisesRegex(errors.ParserError,
                                "Expected display refresh >=0"):
      log_parser.LogParser(
          self.mock_parser, self.log_filename, display_refresh=-1)

  def test_log_parser_init_display_refresh_zero(self):
    """Verify log parser method init works if display refresh is zero."""

    _remove_file(self.log_filename)
    self._create_log_file(event_count=1)
    uut = log_parser.LogParser(
        self.mock_parser, self.log_filename, display_refresh=0)
    self.assertIsInstance(uut, log_parser.LogParser)

  def test_log_parser_init_display_refresh_zero_io_error(self):
    """Verify log parser method init works if display refresh is zero and IOError exception."""

    self.mock_parser.process_line.side_effect = IOError("Test IOError")
    with self.assertRaisesRegex(errors.ParserError,
                                "Log file processing failed"):
      log_parser.LogParser(
          self.mock_parser, self.log_filename, display_refresh=0)

  def test_log_parser_get_event_history_works(self):
    """Verify log parser init's call to real Parser doesn't raise errors."""

    filter_file = os.path.join(self.TEST_FILTER_DIR,
                               "optional_description.json")
    event_parser = event_parser_default.EventParserDefault(
        [filter_file], event_file_path="unknown.txt", device_name="device-1234")
    uut = log_parser.LogParser(event_parser, self.log_filename)
    with mock.patch.object(event_parser_default.EventParserDefault,
                           "get_event_history") as mock_event_history:
      uut.get_event_history()
    mock_event_history.assert_called()

  def test_log_parser_get_event_history(self):
    """Verify log parser method get_event_history is called and results are expected."""
    self.mock_parser.get_event_history.return_value = event_parser_default.ParserResult(
        _TIMED_OUT_NO, _RESULTS_LIST, len(_RESULTS_LIST))
    self.mock_parser.get_event_labels.return_value = list(
        _TEST_LABEL_DICT.keys())
    uut = log_parser.LogParser(self.mock_parser, self.log_filename)
    result = uut.get_event_history([self.event_label])
    self.assertIsInstance(result, event_parser_default.ParserResult)
    self.assertEqual(result.timedout, _TIMED_OUT_NO)
    self.assertIsInstance(result.results_list, list)
    self.assertEqual(result.count, len(_RESULTS_LIST))
    self.mock_parser.get_event_history.assert_called_once_with(
        [self.event_label], count=None, timeout=10.0)

  def test_log_parser_get_event_history_bad_list(self):
    """Attempt to retrieve event history using bad event label list."""
    uut = log_parser.LogParser(self.mock_parser, self.log_filename)
    with self.assertRaises(errors.ParserError):
      uut.get_event_history(event_labels="not a list")

  def test_log_parser_get_event_history_bad_event_label(self):
    """Attempt to retrieve event history using bad event label list."""
    self.mock_parser.get_event_labels.return_value = ["some.label"]
    uut = log_parser.LogParser(self.mock_parser, self.log_filename)
    with self.assertRaises(errors.ParserError):
      uut.get_event_history(["bad.label"])

  def test_log_parser_get_event_history_count(self):
    """Verify log parser method get_event_history_count is called and results are expected."""
    self.mock_parser.get_event_history_count.return_value = event_parser_default.ParserResult(
        _TIMED_OUT_NO, [], _HISTORY_COUNT)
    self.mock_parser.get_event_labels.return_value = list(
        _TEST_LABEL_DICT.keys())
    uut = log_parser.LogParser(self.mock_parser, self.log_filename)
    parser_result = uut.get_event_history_count(self.event_label)
    count = parser_result.count
    self.assertEqual(count, _HISTORY_COUNT)
    self.mock_parser.get_event_history_count.assert_called_once_with(
        self.event_filename, self.event_label, timeout=10.0)

  def test_log_parser_get_event_history_count_bad_event_label(self):
    """Attempt to retrieve event history count using bad event label."""
    self.mock_parser.get_event_labels.return_value = ["some.label"]
    uut = log_parser.LogParser(self.mock_parser, self.log_filename)
    with self.assertRaises(errors.ParserError):
      uut.get_event_history_count("bad.label")

  def test_log_parser_get_event_label_dict(self):
    """Verify log parser method get_event_label_dict is called and results are expected."""

    self.mock_parser.get_event_label_dict.return_value = _TEST_LABEL_DICT
    uut = log_parser.LogParser(self.mock_parser, self.log_filename)
    event_label_dict = uut.get_event_label_dict()
    self.mock_parser.get_event_label_dict.assert_called_once_with(pattern=None)
    self.assertIsInstance(event_label_dict, dict)
    self.assertEqual(len(event_label_dict), len(_TEST_LABEL_DICT))
    is_ok = True
    for key in event_label_dict:
      if event_label_dict[key] not in _TEST_LABEL_DICT[key]:
        is_ok = False
        break
    self.assertTrue(
        is_ok, "Expected {} but instead got: {}".format(_TEST_LABEL_DICT,
                                                        event_label_dict))

  def test_log_parser_get_event_labels(self):
    """Verify log parser method get_event_labels is called and results are expected."""

    self.mock_parser.get_event_labels.return_value = list(
        _TEST_LABEL_DICT.keys())
    uut = log_parser.LogParser(self.mock_parser, self.log_filename)
    event_list = uut.get_event_labels()
    self.mock_parser.get_event_labels.assert_called_once_with(pattern=None)
    self.assertIsInstance(event_list, list)
    self.assertEqual(len(event_list), len(list(_TEST_LABEL_DICT.keys())))
    is_ok = True
    key_list = list(_TEST_LABEL_DICT.keys())
    for event in event_list:
      if event not in key_list:
        is_ok = False
        break
    self.assertTrue(
        is_ok, "Expected event list to contain {} but instead got: {}".format(
            list(_TEST_LABEL_DICT.keys()), event_list))

  def test_log_parser_get_last_event(self):
    """Verify log parser method get_last_event is called and results are expected."""
    self.mock_parser.get_last_event.return_value = event_parser_default.ParserResult(
        _TIMED_OUT_NO, _RESULTS_LIST, len(_RESULTS_LIST))
    self.mock_parser.get_event_labels.return_value = list(
        _TEST_LABEL_DICT.keys())
    uut = log_parser.LogParser(self.mock_parser, self.log_filename)
    result = uut.get_last_event([self.event_label])
    self.mock_parser.get_last_event.assert_called_once_with(
        self.event_filename, [self.event_label], timeout=1.0)
    self.assertIsInstance(result, event_parser_default.ParserResult)
    self.assertEqual(result.timedout, _TIMED_OUT_NO)
    self.assertIsInstance(result.results_list, list)
    self.assertEqual(result.count, len(_RESULTS_LIST))

  def test_log_parser_get_last_event_bad_event_label(self):
    """Attempt to retrieve last event using bad event label."""
    self.mock_parser.get_event_labels.return_value = ["some.label"]
    uut = log_parser.LogParser(self.mock_parser, self.log_filename)
    with self.assertRaises(errors.ParserError):
      uut.get_last_event(["bad.label"])

  def test_log_parser_get_last_event_bad_event_labels(self):
    """Attempt to retrieve last event using bad event label list."""
    uut = log_parser.LogParser(self.mock_parser, self.log_filename)
    with self.assertRaises(errors.ParserError):
      uut.get_last_event(event_labels="not a list")

  def _create_log_file(self, event_count):
    """Creates a temporary event history log file for testing Parser event history commands.

    Args:
       event_count: number of events to populate in file.

    Note:
        The temporary event history log file will contain event_count total
        events for each
        of the following raw log lines:
            * _ANOTHER_MESSAGE_LINE
            * _NO_MATCH_LINE
            * _STATE_LINE
            * _UNIQUE_MESSAGE_LINE
    """

    self.expected_parser_calls = 0
    with open(self.log_filename, "w", encoding="utf-8") as log_file:
      for i in range(event_count):
        now = datetime.datetime.now()
        time_info = now.strftime("<%Y-%m-%d %H:%M:%S.%f>")
        self.expected_parser_calls += 1
        log_file.write(_ANOTHER_MESSAGE_LINE.format(time_info))
        self.expected_parser_calls += 1
        log_file.write(_NO_MATCH_LINE.format(time_info))
        self.expected_parser_calls += 1
        log_file.write(_STATE_LINE.format(time_info, i))
        self.expected_parser_calls += 1
        log_file.write(_UNIQUE_MESSAGE_LINE.format(time_info))
        self.expected_parser_calls += 1
        log_file.write(_NON_ASCII_LINE.format(time_info))
        self.expected_parser_calls += 1
        log_file.write(_LINE_RETURN_LINE.format(time_info))
        self.expected_parser_calls += 1
        log_file.write(_NEW_HEADER_LINE.format(time_info))


if __name__ == "__main__":
  unit_test_case.main()
