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

"""This test script verifies GDM is working with parser."""

import datetime
import json
import os
import shutil
from unittest import mock

from gazoo_device import errors
from gazoo_device.capabilities import event_parser_default
from gazoo_device.tests.unit_tests.utils import fake_events
from gazoo_device.tests.unit_tests.utils import unit_test_case


MockOutSubprocess = unit_test_case.MockOutSubprocess
TIMESTAMP_INFO = "<2018-02-02 12:00:01.123456>"
_TIMESTAMP_0 = "<2018-02-02 12:00:00.123456>"
_TIMESTAMP_5 = "<2018-02-02 12:00:05.123456>"
_DATETIME_0 = datetime.datetime.strptime(_TIMESTAMP_0, "<%Y-%m-%d %H:%M:%S.%f>")
_DATETIME_5 = datetime.datetime.strptime(_TIMESTAMP_5, "<%Y-%m-%d %H:%M:%S.%f>")
_DATETIME_1 = datetime.datetime.strptime(TIMESTAMP_INFO,
                                         "<%Y-%m-%d %H:%M:%S.%f>")


class EventParserTests(unit_test_case.SwitchboardParserTestCase):
  """Unit tests for the event parser capability."""

  def test_001_parser_loads_example_filters(self):
    """Loads a valid device type and verifies its filters were loaded."""
    event_label_list = self.uut.get_event_labels()
    self.assertIn("sample.message", event_label_list)
    self.assertIn("sample.message2", event_label_list)
    self.assertIn("sample.state", event_label_list)

  def test_002_parser_loads_no_filters(self):
    """Creates a parser with no filters and verifies no filters were loaded."""
    self.uut = event_parser_default.EventParserDefault(
        (), self.event_file_path, device_name="device-1234")
    event_label_list = self.uut.get_event_labels()
    self.assertNotIn("sample.message", event_label_list)
    self.assertNotIn("sample.message2", event_label_list)
    self.assertNotIn("sample.state", event_label_list)

  def test_004_parser_load_rejects_invalid_path_in_filters_list(self):
    """Parser init rejects invalid paths in filter variable list by raising an error."""
    regex = "doesn't exist"
    with self.assertRaisesRegex(errors.ParserError, regex):
      self.uut.load_filters(["invalid_path/"])

  def test_005_parser_load_rejects_filter_file_with_invalid_json_object(self):
    """Parser init rejects filter file with invalid JSON content by raising an error."""
    regex = "Unable to parse filter file"
    with self.assertRaisesRegex(errors.ParserError, regex):
      filter_file = os.path.join(self.TEST_FILTER_DIR,
                                 "invalid_json_object.json")
      self.uut.load_filters([filter_file])

  def test_006_parser_load_rejects_filter_file_with_missing_version_key(self):
    """Parser init rejects filter file with missing version key by raising an error."""
    regex = r"Missing 'version' key\."
    with self.assertRaisesRegex(errors.ParserError, regex):
      filter_file = os.path.join(self.TEST_FILTER_DIR, "missing_version.json")
      self.uut.load_filters([filter_file])

  def test_007_parser_load_rejects_filter_file_with_missing_filters_key(self):
    """Parser init rejects filter file with missing filters key by raising an error."""
    regex = r"Missing 'filters' key\."
    with self.assertRaisesRegex(errors.ParserError, regex):
      filter_file = os.path.join(self.TEST_FILTER_DIR, "missing_filters.json")
      self.uut.load_filters([filter_file])

  def test_008_parser_load_rejects_filter_file_with_invalid_version_value(self):
    """Parser init rejects filter file with invalid version value by raising an error."""
    regex = "Expecting value of 'version' entry to be a dictionary"
    with self.assertRaisesRegex(errors.ParserError, regex):
      filter_file = os.path.join(self.TEST_FILTER_DIR,
                                 "invalid_version_value.json")
      self.uut.load_filters([filter_file])

  def test_009_parser_load_rejects_filter_file_with_missing_major_in_version_value(
      self):
    """Parser init rejects filter file with missing major key in version value with an error."""
    regex = "Missing 'major' key in 'version' value"
    with self.assertRaisesRegex(errors.ParserError, regex):
      filter_file = os.path.join(self.TEST_FILTER_DIR,
                                 "missing_version_major.json")
      self.uut.load_filters([filter_file])

  def test_010_parser_load_rejects_filter_file_with_missing_minor_in_version_value(
      self):
    """Parser init rejects filter file with missing minor key in version value with an error."""
    regex = "Missing 'minor' key in 'version' value"
    with self.assertRaisesRegex(errors.ParserError, regex):
      filter_file = os.path.join(self.TEST_FILTER_DIR,
                                 "missing_version_minor.json")
      self.uut.load_filters([filter_file])

  def test_011_parser_load_rejects_filter_file_with_invalid_filters_value(self):
    """Parser init rejects filter file with invalid filter value by raising an error."""
    regex = "Expecting value of 'filter_list' entry to be a list"
    with self.assertRaisesRegex(errors.ParserError, regex):
      filter_file = os.path.join(self.TEST_FILTER_DIR,
                                 "invalid_filters_value.json")
      self.uut.load_filters([filter_file])

  def test_012_parser_load_rejects_filter_file_with_missing_name_in_filter_object(
      self):
    """Parser init rejects filter file with missing name key in filter objects."""
    regex = "Missing 'name' key in filter object"
    with self.assertRaisesRegex(errors.ParserError, regex):
      filter_file = os.path.join(self.TEST_FILTER_DIR,
                                 "missing_filter_name.json")
      self.uut.load_filters([filter_file])

  def test_013_parser_load_rejects_filter_file_with_missing_regex_match_in_filter_object(
      self):
    """Parser init rejects filter file with missing regex_match key in filter objects."""
    regex = "Missing 'regex_match' key in filter object"
    with self.assertRaisesRegex(errors.ParserError, regex):
      filter_file = os.path.join(self.TEST_FILTER_DIR,
                                 "missing_filter_regex_match.json")
      self.uut.load_filters([filter_file])

  def test_014_parser_load_rejects_filter_file_with_duplicate_name(self):
    """Parser init rejects filter file with duplicate name value in filter objects."""
    regex = r"Filter named duplicate_name.same_name already exists\."
    with self.assertRaisesRegex(errors.ParserError, regex):
      filter_file = os.path.join(self.TEST_FILTER_DIR, "duplicate_name.json")
      self.uut.load_filters([filter_file])

  def test_015_parser_load_rejects_filter_file_with_invalid_regex_match_value(
      self):
    """Parser init rejects filter file with invalid regex_match value with an error."""
    regex = "Unable to compile regular expression value"
    with self.assertRaisesRegex(errors.ParserError, regex):
      filter_file = os.path.join(self.TEST_FILTER_DIR,
                                 "invalid_regex_match_value.json")
      self.uut.load_filters([filter_file])

  def test_016_parser_load_filter_file_with_missing_description_key(self):
    """Parser init accepts a filter file with a missing description key."""
    filter_file = os.path.join(self.TEST_FILTER_DIR,
                               "optional_description.json")
    self.uut.load_filters([filter_file])
    event_label_list = self.uut.get_event_labels()
    self.assertIn(
        "optional_description.my_message", event_label_list,
        "Expecting optional_description.my_message "
        "in event list but only found {!r}".format(event_label_list))

  def test_017_parser_load_filter_file_with_missing_filter_object_description_key(
      self):
    """Parser init accepts a filter file with a missing filter object description key."""
    filter_file = os.path.join(self.TEST_FILTER_DIR,
                               "optional_filter_description.json")
    self.uut.load_filters([filter_file])
    event_label_list = self.uut.get_event_labels()
    self.assertIn(
        "optional_filter_description.my_message", event_label_list,
        "Expecting optional_filter_description.my_message "
        "in event list but only found {!r}".format(event_label_list))

  def test_018_parser_load_rejects_filter_file_with_unexpected_major_version(
      self):
    """Parser init rejects filter file with a major version other than supported."""
    regex = r"Found unexpected major version in JSON filter file\."
    with self.assertRaisesRegex(errors.ParserError, regex):
      filter_file = os.path.join(self.TEST_FILTER_DIR,
                                 "invalid_major_version.json")
      self.uut.load_filters([filter_file])

  def test_019_parser_load_rejects_filter_file_with_unexpected_major_version_string(
      self):
    """Parser init rejects filter file with a string for the major version."""
    regex = "Expecting int for major version found"
    with self.assertRaisesRegex(errors.ParserError, regex):
      filter_file = os.path.join(self.TEST_FILTER_DIR,
                                 "invalid_major_version_string.json")
      self.uut.load_filters([filter_file])

  def test_020_parser_load_rejects_filter_file_with_unexpected_major_version_float(
      self):
    """Parser init rejects filter file with a float for the major version."""
    regex = "Expecting int for major version found"
    with self.assertRaisesRegex(errors.ParserError, regex):
      filter_file = os.path.join(self.TEST_FILTER_DIR,
                                 "invalid_major_version_float.json")
      self.uut.load_filters([filter_file])

  def test_021_parser_load_rejects_filter_file_with_unexpected_minor_version_string(
      self):
    """Parser init rejects filter file with a string for the minor version."""
    regex = "Expecting int for minor version found"
    with self.assertRaisesRegex(errors.ParserError, regex):
      filter_file = os.path.join(self.TEST_FILTER_DIR,
                                 "invalid_minor_version_string.json")
      self.uut.load_filters([filter_file])

  def test_022_parser_load_rejects_filter_file_with_unexpected_minor_version_float(
      self):
    """Parser init rejects filter file with a float for the minor version."""
    regex = "Expecting int for minor version found"
    with self.assertRaisesRegex(errors.ParserError, regex):
      filter_file = os.path.join(self.TEST_FILTER_DIR,
                                 "invalid_minor_version_float.json")
      self.uut.load_filters([filter_file])

  def test_023_parser_load_filter_file_dir_non_json_files(self):
    """Parser init accepts a list holding 1 directory containing non json files."""
    self.uut.load_filters([self.TEST_EVENTFILES_DIR])
    self.assertIsInstance(
        self.uut, event_parser_default.EventParserDefault,
        "Expecting Parser object to be returned. "
        "Instead found {}".format(type(self.uut)))

  def test_024_parser_load_filter_file_detects_bogus_path(self):
    """Verifies when a bogus path is provided an error is raised."""
    bogus_file = os.path.join(self.TEST_FILTER_DIR, "bogus.json")
    with self.assertRaisesRegex(errors.ParserError, "doesn't exist"):
      self.uut.load_filters([bogus_file])

  def test_025_parser_load_directory(self):
    """Parser able to load a directory."""
    new_directory = os.path.join(self.artifacts_directory, "good_filters")
    os.mkdir(new_directory)
    shutil.copy(
        os.path.join(self.TEST_FILTER_DIR, "sample.json"), new_directory)
    try:
      self.uut = event_parser_default.EventParserDefault(
          filters=[new_directory],
          event_file_path=self.event_file_path,
          device_name="device-1234")
    finally:
      if os.path.exists(new_directory):
        shutil.rmtree(new_directory)

  @mock.patch.object(os.path, "exists", return_value=True, autospec=True)
  @mock.patch.object(os.path, "isdir", return_value=True, autospec=True)
  @mock.patch.object(os, "listdir", side_effect=OSError, autospec=True)
  def test_026_parser_load_rejects_no_directory_access(
      self, mock_listdir, mock_isdir, mock_exists):
    """Ensures an error is raised if unable to access filter directory."""
    with self.assertRaisesRegex(errors.ParserError, "Unable to access"):
      self.uut.load_filters([""])

  def test_100_parser_writes_no_event(self):
    """Verifies process_line writes no events for non-matching log lines."""
    self.uut.process_line(self.fake_file_writer,
                          self._NO_MATCH_LINE.format(TIMESTAMP_INFO))
    self.assertIsNone(
        self.fake_file_writer.out,
        "Fail. Expected no event filtered but instead got event: {!r}".format(
            self.fake_file_writer.out))

  def test_101_parser_writes_state_event(self):
    """Verifies process_line writes state event for matching state log lines.

    Note:
        Its important to make sure both the state and event file are both
        updated as part of
        the test.
    """
    self.uut.process_line(self.fake_file_writer,
                          self._STATE_LINE.format(TIMESTAMP_INFO, 1))
    event_dictionary = self._get_event_dictionary()
    self._verify_required_event_keys(event_dictionary)
    self.assertIn(
        "sample.state", event_dictionary,
        "Missing 'sample.state' as key in dict. Dictionary: {!r}".format(
            event_dictionary))
    self.assertEqual(
        len(list(event_dictionary.keys())), 4,
        "Unexpected keys in JSON data '{!r}'".format(event_dictionary))

  def test_102_parser_writes_unique_message_events(self):
    """Verifies process_line writes multiple unique message events for matching log lines.

    Note:
        Its important to make sure both the state and event file are both
        updated as part of
        the test.
    """
    self.uut.process_line(self.fake_file_writer,
                          self._UNIQUE_MESSAGE_LINE.format(TIMESTAMP_INFO))
    event_dictionary = self._get_event_dictionary()
    self._verify_required_event_keys(event_dictionary)
    self.assertIn(
        "sample.message", event_dictionary,
        "Missing 'sample.message' as key in dict. Dictionary: {!r}".format(
            event_dictionary))
    self.assertIn(
        "sample.message2", event_dictionary,
        "Missing 'sample.message2' as key in dict. Dictionary: {!r}".format(
            event_dictionary))
    self.assertEqual(
        len(list(event_dictionary.keys())), 5,
        "Unexpected keys in dict. Dictionary: {!r}".format(event_dictionary))

  def test_103_parser_writes_stripped_raw_log_line(self):
    """Verifies process_line strips invalid characters from raw_log_line for matching events."""
    invalid_character_line = chr(247) + self._UNIQUE_MESSAGE_LINE.format(
        TIMESTAMP_INFO)
    self.uut.process_line(self.fake_file_writer, invalid_character_line)
    event_dictionary = self._get_event_dictionary()
    self._verify_required_event_keys(event_dictionary)
    self.assertIn(
        "sample.message", event_dictionary,
        "Missing 'sample.message' as key in dict. Dictionary: {!r}".format(
            event_dictionary))
    self.assertIn(
        "sample.message2", event_dictionary,
        "Missing 'sample.message2' as key in dict. Dictionary: {!r}".format(
            event_dictionary))

  def test_104_parser_writes_log_filename_in_event(self):
    """Verifies process_line writes log_filename in event."""
    log_filename = "fake_device.txt"
    self.uut.process_line(
        self.fake_file_writer,
        self._STATE_LINE.format(TIMESTAMP_INFO, 1),
        log_filename=log_filename)
    event_dictionary = self._get_event_dictionary()
    self._verify_required_event_keys(event_dictionary, with_log=True)
    self.assertIn(
        "sample.state", event_dictionary,
        "Missing 'sample.state' as key in dict. Dictionary: {!r}".format(
            event_dictionary))
    self.assertEqual(
        len(list(event_dictionary.keys())), 5,
        "Unexpected keys in JSON data '{!r}'".format(event_dictionary))
    self.assertEqual(
        log_filename, event_dictionary["log_filename"],
        "Expected {} for log_filename value found {}".format(
            log_filename, event_dictionary["log_filename"]))

  def test_200_parser_get_history_of_all_no_match_events(self):
    """Retrieving event history for non-existent event label returns empty list."""
    expected_event_count = 0
    self.uut.load_filter_file(os.path.join(self.TEST_FILTER_DIR, "basic.json"))
    with MockOutSubprocess() as subprocess_mocks:
      event_history = self.uut.get_event_history(["basic.bootup"])
    self.assertEqual(len(event_history.results_list), expected_event_count)
    subprocess_mocks.mock_popen.assert_called()

  def test_201_parser_get_history_of_all_message_events(self):
    """Retrieving event history for message events and count=0 returns full list."""
    expected_event_count = 10
    with MockOutSubprocess([fake_events.ALL_SAMPLE_MESSAGE_EVENTS
                            ]) as subprocess_mocks:
      event_history = self.uut.get_event_history(["sample.message"])
    self.assertEqual(len(event_history.results_list), expected_event_count)
    subprocess_mocks.mock_popen.assert_called()

  def test_202_parser_get_history_of_some_state_events(self):
    """Retrieving event history for state events and count=5 returns partial list."""
    requested_event_count = 5
    expected_event_count = requested_event_count
    with MockOutSubprocess([fake_events.SAMPLE_STATE_EVENTS
                            ]) as subprocess_mocks:
      event_history = self.uut.get_event_history(["sample.state"],
                                                 requested_event_count)
    self.assertEqual(len(event_history.results_list), expected_event_count)
    subprocess_mocks.mock_popen.assert_called()

  def test_203_parser_get_history_none_returns_all_events(self):
    """Retrieving event history with event_labels set to None returns all events."""
    expected_event_count = 30
    with MockOutSubprocess([fake_events.ALL_SAMPLE_EVENTS_TAC
                            ]) as subprocess_mocks:
      event_history = self.uut.get_event_history(None)
    self.assertEqual(len(event_history.results_list), expected_event_count)
    subprocess_mocks.mock_check_output.assert_called()

  def test_204_parser_get_history_none_with_count_returns_events_subset(self):
    """Test retrieving event history with event_labels=None.

    Requested event count should return the correct subset of events.
    """
    requested_event_count = 10
    expected_event_count = 10
    with MockOutSubprocess([fake_events.SAMPLE_MESSAGE_EVENTS_SUBSET
                            ]) as subprocess_mocks:
      event_history = self.uut.get_event_history(None, requested_event_count)
    self.assertEqual(len(event_history.results_list), expected_event_count)
    subprocess_mocks.mock_popen.assert_called()

  def test_205_parser_get_history_timeout(self):
    """Retrieving event history correctly times out."""
    actual_event_count = 4000
    timeout = 0.005
    self._populate_event_file(actual_event_count)
    event_history = self.uut.get_event_history(["sample.state"],
                                               timeout=timeout)
    self.assertTrue(event_history.timedout, "Expected .timedout to be True")

  def test_206_parser_get_history_timeout_with_count(self):
    """Retrieving event history with a count correctly times out."""
    actual_event_count = 4000
    requested_event_count = 3500
    timeout = 0.005
    self._populate_event_file(actual_event_count)
    event_history = self.uut.get_event_history(["sample.state"],
                                               count=requested_event_count,
                                               timeout=timeout)
    self.assertTrue(event_history.timedout, "Expected .timedout to be True")

  def test_207_parser_get_history_none_timeout(self):
    """Retrieving event history for all event labels correctly times out."""
    actual_event_count = 6000
    timeout = 0.001
    self._populate_event_file(actual_event_count)
    event_history = self.uut.get_event_history(timeout=timeout)
    self.assertTrue(event_history.timedout, "Expected .timedout to be True")

  def test_208_parser_get_history_none_timeout_with_count(self):
    """Retrieving event history for all event labels with a count correctly times out."""
    actual_event_count = 6000
    requested_event_count = 5500
    timeout = 0.001
    self._populate_event_file(actual_event_count)
    event_history = self.uut.get_event_history(
        count=requested_event_count, timeout=timeout)
    self.assertTrue(event_history.timedout, "Expecting .timedout to be True")

  def test_209_parser_get_history_event_file_not_exists(self):
    """Attempts to retrieve event history when event file does not exist."""
    actual_event_count = 10
    requested_event_count = 1
    event_labels = ["sample.message"]
    with mock.patch.object(event_parser_default,
                           "_wait_for_event_file") as mock_wait_evt_file:
      mock_wait_evt_file.return_value = (False, 0
                                        )  # (file_exists, remaining_timeout)

      self._populate_event_file(actual_event_count)
      event_history = self.uut.get_event_history(event_labels,
                                                 requested_event_count)
      self.assertTrue(event_history.timedout, "Expecting .timedout to be True")
      self.assertFalse(
          event_history.results_list,
          "Expecting length results_list to be 0 instead got: {}".format(
              len(event_history.results_list)))

  def test_210_parser_get_event_history_value_error(self):
    """Attempts to retrieve event history causes ValueError."""
    actual_event_count = 10
    requested_event_count = 1
    event_labels = ["sample.message"]
    with mock.patch.object(
        event_parser_default,
        "_get_limited_event_history") as mock_get_limited_evt_hist:
      mock_get_limited_evt_hist.side_effect = ValueError(
          "Simulated value error")
      self._populate_event_file(actual_event_count)
      with self.assertRaises(errors.ParserError):
        self.uut.get_event_history(event_labels, requested_event_count)

  def test_300_parser_get_history_count_of_all_message_events(self):
    """Retrieving event history count for message events returns count of full list."""
    expected_event_count = 10
    with MockOutSubprocess([b"10\n"]) as subprocess_mocks:
      event_history = self.uut.get_event_history_count("sample.message")
    self.assertEqual(event_history.count, expected_event_count)
    subprocess_mocks.mock_popen.assert_called()

  def test_301_parser_get_history_count_timeout(self):
    """Retrieving event history count for message events times out correctly."""
    actual_count = 6000
    timeout = 0.001
    self._populate_event_file(actual_count)
    parser_result = self.uut.get_event_history_count(
        "sample.state", timeout=timeout)
    self.assertTrue(parser_result.timedout, "Expected .timedout to be True")

  def test_302_parser_get_history_count_value_error(self):
    """Attempts to retrieve event history count causes ValueError."""
    actual_event_count = 10
    requested_event_count = 1
    event_label = "sample.message"
    with mock.patch.object(
        event_parser_default,
        "_get_event_history_count") as mock_get_event_hist_count:
      mock_get_event_hist_count.side_effect = ValueError(
          "Simulated value error")
      self._populate_event_file(actual_event_count)
      with self.assertRaises(errors.ParserError):
        self.uut.get_event_history_count(event_label, requested_event_count)

  def test_400_parser_get_last_event_fails_with_no_file(self):
    """Retrieving last event with invalid file times out."""
    self.uut.event_file_path = "some_bogus_file"
    parser_result = self.uut.get_last_event(["sample.message"])
    self.assertTrue(parser_result.timedout,
                    "Timeout on invalid event file did not occur")
    self.assertFalse(parser_result.results_list)

  def test_401_parser_get_last_event_retrieve_failed(self):
    """Retrieving last event correctly times out with no event label and a short timeout."""
    actual_event_count = 10
    timeout = 1.0
    with mock.patch.object(event_parser_default,
                           "_get_last_event") as mock_get_last_event:
      mock_get_last_event.side_effect = ValueError("Simulated value error")

      self._populate_event_file(actual_event_count)
      with self.assertRaises(errors.ParserError):
        self.uut.get_last_event(timeout=timeout)

  def test_402_parser_get_event_of_no_group_event(self):
    """Retrieving event for regular expression without a group returns correct data."""
    event_label = "sample.message"
    self._populate_event_file(1)
    with MockOutSubprocess([fake_events.SAMPLE_MESSAGE_EVENT
                            ]) as subprocess_mocks:
      event_data = self.uut.get_last_event([event_label])
    self.assertIsInstance(event_data.results_list[0]["system_timestamp"],
                          datetime.datetime)
    self.assertIn("Some unique message",
                  event_data.results_list[0]["raw_log_line"])
    self.assertEqual(event_data.results_list[0][event_label], [])
    subprocess_mocks.mock_popen.assert_called()

  def test_403_parser_get_event_label_string_instead_of_list(self):
    """Retrieving event correctly returns error when given str for event_labels."""
    event_label = "sample.state"
    self._populate_event_file(1)
    with self.assertRaisesRegex(errors.ParserError,
                                "Expecting event_labels to be a list"):
      self.uut.get_last_event(event_label)

  def test_404_parser_get_event_empty_list_no_matches(self):
    """Passing an empty event_labels list does not produce any matches."""
    self._populate_event_file(1)
    event_data = self.uut.get_last_event([])
    self.assertFalse(event_data.results_list)
    self.assertEqual(event_data.count, 0)

  def test_405_parser_get_event_none_returns_last_event(self):
    """Passing None to event_labels returns the latest event."""
    self._populate_event_file(1)
    with MockOutSubprocess([fake_events.SAMPLE_MESSAGE_EVENT
                            ]) as subprocess_mocks:
      event_data = self.uut.get_last_event(None)
    self.assertIsInstance(event_data.results_list[0]["system_timestamp"],
                          datetime.datetime)
    self.assertEqual("[APPL] Some unique message",
                     event_data.results_list[0]["raw_log_line"])
    subprocess_mocks.mock_check_output.assert_called()

  def test_406_parser_get_event_timeout(self):
    """Retrieving last event correctly times out when given a very short timeout value."""
    actual_count = 500
    timeout = 0.00001
    event_label = "sample.state"
    self._populate_event_file(actual_count)
    event_data = self.uut.get_last_event([event_label], timeout=timeout)
    self.assertTrue(event_data.timedout, "Expected .timedout to be True")

  def test_407_parser_get_event_timeout_none(self):
    """Retrieving last event correctly times out with no event label and a short timeout."""
    actual_count = 500
    timeout = 0.00001
    self._populate_event_file(actual_count)
    event_data = self.uut.get_last_event(timeout=timeout)
    self.assertTrue(event_data.timedout, "Expected .timedout to be True")

  def test_600_parser_get_event_labels_no_pattern(self):
    """Verifies get_event_labels returns all filter event labels."""

    label_list = [
        "sample.message", "sample.message2", "sample.message3", "sample.state"
    ]
    event_label_list = self.uut.get_event_labels()
    all_labels_present = ((label_list[0] in event_label_list) and
                          (label_list[1] in event_label_list) and
                          (label_list[2] in event_label_list) and
                          (label_list[3] in event_label_list))
    self.assertTrue(
        all_labels_present and (len(event_label_list) == 4),
        "Get event label list using no pattern failed. "
        "Expected labels: {} instead found: {}".format(label_list,
                                                       event_label_list))

  def test_601_parser_get_event_labels_bad_pattern(self):
    """Verifies get_event_labels returns ParserError when given a bad pattern."""

    pattern = "("
    regex = "Compiling regular expression pattern"
    with self.assertRaisesRegex(errors.ParserError, regex):
      self.uut.get_event_labels(pattern)

  def test_602_parser_get_event_labels_match_pattern(self):
    """Verifies get_event_labels matches correct patterns."""

    pattern = "sample.mess*"
    label_list = ["sample.message", "sample.message2", "sample.message3"]
    event_label_list = self.uut.get_event_labels(pattern)
    all_labels_present = ((label_list[0] in event_label_list) and
                          (label_list[1] in event_label_list) and
                          (label_list[2] in event_label_list))
    self.assertTrue(
        all_labels_present and (len(event_label_list) == 3),
        "Get event label list match pattern: {} failed. "
        "Expected labels: {} instead found: {}".format(pattern, label_list,
                                                       event_label_list))

  def test_603_parser_get_event_labels_match_one(self):
    """Verifies get_event_labels matches only one pattern."""

    pattern = "sample.message2"
    event_label_list = self.uut.get_event_labels(pattern)
    all_labels_present = ((pattern in event_label_list) and
                          ("sample.message" not in event_label_list) and
                          ("sample.message3" not in event_label_list))
    self.assertTrue(
        all_labels_present and (len(event_label_list) == 1),
        "Get event label list match one pattern failed. "
        "Expected label: {} instead found: {}".format(pattern,
                                                      event_label_list))

  def test_630_wait_for_event_labels_timestamp_filter(self):
    """Verifies wait_for_event_labels filters out events before start time."""
    # Should filter out 1 of the two events basd on the start_datetime.
    event_results = [{
        "system_timestamp": _DATETIME_0,
        "raw_log_line": "alskdjflakdsflasdkjfalsdkjf",
        "same.message3": ["a", "b", "c"]
    }, {
        "system_timestamp": _DATETIME_5,
        "raw_log_line": "whoa",
        "sample.message2": ["q", "r"]
    }]

    last_event = event_parser_default.ParserResult(False, event_results, 0)
    with mock.patch.object(self.uut, "get_last_event", return_value=last_event):
      with self.assertRaisesRegex(
          errors.DeviceError,
          "not all events corresponding to labels were found"):
        self.uut.wait_for_event_labels(["sample.message"],
                                       raise_error=True,
                                       timeout=1.0,
                                       start_datetime=_DATETIME_1)

  def test_631_wait_for_event_labels_not_found_no_raise(self):
    """Verifies wait_for_event_labels not found error is not raised if raise_error=False."""
    event_result = {
        "system_timestamp": _DATETIME_0,
        "raw_log_line": "alskdjflakdsflasdkjfalsdkjf",
        "same.message3": ["a", "b", "c"]
    }

    last_event = event_parser_default.ParserResult(False, [event_result], 0)
    with mock.patch.object(event_parser_default, "logger") as mock_logger:
      with mock.patch.object(
          self.uut, "get_last_event", return_value=last_event):
        self.uut.wait_for_event_labels(["sample.message"],
                                       raise_error=False,
                                       timeout=1.0,
                                       start_datetime=_DATETIME_1)
        mock_logger.warning.assert_called_once()

  def test_632_wait_for_event_labels_all_found(self):
    """Verifies wait_for_event_labels all found is handled."""
    event_result = {
        "system_timestamp": _DATETIME_0,
        "raw_log_line": "alskdjflakdsflasdkjfalsdkjf",
        "sample.message": ["a", "b", "c"]
    }
    last_event = event_parser_default.ParserResult(False, [event_result], 0)
    with mock.patch.object(self.uut, "get_last_event", return_value=last_event):
      self.uut.wait_for_event_labels(["sample.message"],
                                     timeout=1.0,
                                     start_datetime=_DATETIME_0)

  def test_633_wait_for_event_labels_empty_label_list(self):
    """Verifies method does nothing and returns True when the event label list is empty."""
    with mock.patch.object(self.uut, "get_last_event") as mock_get_last_event:
      result = self.uut.wait_for_event_labels([], timeout=1.0)
      self.assertTrue(result)
      mock_get_last_event.assert_not_called()

  def test_650_get_last_event_state(self):
    """Verifies get_last_event_state() when event was seen."""
    self.uut.event_file_path = os.path.join(self.TEST_EVENTFILES_DIR,
                                            "matching-events-events.txt")
    self.uut.load_filter_file(os.path.join(self.TEST_FILTER_DIR, "basic.json"))
    with MockOutSubprocess([fake_events.BASIC_FIRMWARE_EVENT
                            ]) as subprocess_mocks:
      state = self.uut.get_last_event_state("basic.firmware_info")
    self.assertEqual(state, "1.0.0")
    subprocess_mocks.mock_popen.assert_called()

  def test_651_get_last_event_state(self):
    """Verifies get_last_event_state() raises if there's no such group."""
    self.uut.event_file_path = os.path.join(self.TEST_EVENTFILES_DIR,
                                            "matching-events-events.txt")
    self.uut.load_filter_file(os.path.join(self.TEST_FILTER_DIR, "basic.json"))
    with MockOutSubprocess([fake_events.BASIC_FIRMWARE_EVENT
                            ]) as subprocess_mocks:
      with self.assertRaisesRegex(errors.DeviceError, "Group index"):
        self.uut.get_last_event_state(
            "basic.firmware_info", group_index=5, raise_error=True)
    subprocess_mocks.mock_popen.assert_called()

  def test_652_get_last_event_state_not_yet_seen(self):
    self.uut.load_filter_file(os.path.join(self.TEST_FILTER_DIR, "basic.json"))
    with MockOutSubprocess() as subprocess_mocks:
      state = self.uut.get_last_event_state("basic.firmware_info")
    self.assertEqual(state, "")  # should be empty as event not yet seen
    subprocess_mocks.mock_popen.assert_called()

  def test_653_get_last_event_state_raise_error(self):
    self.uut.load_filter_file(os.path.join(self.TEST_FILTER_DIR, "basic.json"))
    with MockOutSubprocess() as subprocess_mocks:
      with self.assertRaisesRegex(errors.DeviceError, "not yet seen"):
        self.uut.get_last_event_state("basic.firmware_info", raise_error=True)
    subprocess_mocks.mock_popen.assert_called()

  def test_700_parser_get_event_label_dict_no_pattern(self):
    """Verifies get_event_label_dict returns entire _filters_dict."""

    all_labels_present = True
    regex_list = [
        "another message", "Some other message with group data",
        "unique message", "Some unique message"
    ]
    key_list = [
        "sample.message3", "sample.state", "sample.message2", "sample.message"
    ]
    event_label_dict = self.uut.get_event_label_dict()
    for i in range(0, len(event_label_dict)):
      if regex_list[i] not in event_label_dict[key_list[i]]:
        all_labels_present = False
        break
    self.assertTrue(
        all_labels_present and (len(list(event_label_dict.values())) == 4),
        "Get event label dict using no pattern failed. "
        "Expected regex_list: {} instead found: {}".format(
            regex_list, list(event_label_dict.values())))

  def test_701_parser_get_event_label_dict_bad_pattern(self):
    """Verifies get_event_label_dict returns ParserError when given a bad pattern."""

    pattern = "("
    regex = "Compiling regular expression pattern"
    with self.assertRaisesRegex(errors.ParserError, regex):
      self.uut.get_event_label_dict(pattern=pattern)

  def test_702_parser_get_event_label_dict_match_pattern(self):
    """Verifies get_event_label_dict matches correct patterns."""

    pattern = "sample.mess*"
    all_labels_present = True
    regex_list = ["another message", "unique message", "Some unique message"]
    key_list = ["sample.message3", "sample.message2", "sample.message"]
    event_label_dict = self.uut.get_event_label_dict(pattern=pattern)
    for i in range(0, len(event_label_dict)):
      if regex_list[i] not in event_label_dict[key_list[i]]:
        all_labels_present = False
        break
    self.assertTrue(
        all_labels_present and (len(event_label_dict) == 3),
        "Get event label dict match pattern: {} failed. "
        "Expected regex_list: {} instead found: {}".format(
            pattern, regex_list, list(event_label_dict.values())))

  def test_703_parser_get_event_label_dict_match_one(self):
    """Verifies get_event_label_dict matches only one pattern."""

    pattern = "sample.message2"
    all_labels_present = True
    regex_list = ["unique message"]
    key_list = ["sample.message2"]
    event_label_dict = self.uut.get_event_label_dict(pattern=pattern)
    for i in range(0, len(event_label_dict)):
      if regex_list[i] not in event_label_dict[key_list[i]]:
        all_labels_present = False
        break
    self.assertTrue(
        all_labels_present and (len(event_label_dict) == 1),
        "Get event label dict match one pattern failed. "
        "Expected label: {} instead found: {}".format(
            pattern, list(event_label_dict.values())))

  def test_800_parser_get_unmatched_events_all_match(self):
    """Verifies get_unmatched_events matches all events."""
    self.uut.event_file_path = os.path.join(self.TEST_EVENTFILES_DIR,
                                            "matching-events-events.txt")
    self.uut.load_filter_file(os.path.join(self.TEST_FILTER_DIR, "basic.json"))
    with MockOutSubprocess([
        fake_events.BASIC_REBOOT_TRIGGER_EVENT,
        fake_events.BASIC_BOOTUP_EVENT]) as subprocess_mocks:
      cause_list, effect_list = self.uut.get_unmatched_events()
    self.assertTrue(
        not cause_list and not effect_list,
        "len(remaining_reboots) should be 0 got: {} "
        "len(remaining_bootups) should be 0 got: {} ".format(
            len(cause_list), len(effect_list)))
    subprocess_mocks.mock_popen.assert_called()

  def test_801_parser_get_unmatched_events_3_bootups(self):
    """Verifies get_unmatched_events finds three bootups remaining event."""
    self.uut.event_file_path = os.path.join(
        self.TEST_EVENTFILES_DIR, "three-bootups-remaining-events.txt")
    self.uut.load_filter_file(os.path.join(self.TEST_FILTER_DIR, "basic.json"))
    with MockOutSubprocess([fake_events.BASIC_EVENTS,
                            fake_events.BASIC_BOOTUP_EVENTS
                            ]) as subprocess_mocks:
      cause_list, effect_list = self.uut.get_unmatched_events()
    self.assertTrue(
        not cause_list and len(effect_list) == 3,
        "len(remaining_reboots) should be 0 got: {} "
        "len(remaining_bootups) should be 3 got: {} ".format(
            len(cause_list), len(effect_list)))
    subprocess_mocks.mock_popen.assert_called()

  def test_802_parser_get_unexpected_reboots(self):
    """Verifies unexpected_reboots detects 3 bootups when no reboots are present."""
    self.uut.event_file_path = os.path.join(
        self.TEST_EVENTFILES_DIR,
        "no-reboots-three-bootups-remaining-events.txt")
    self.uut.load_filter_file(os.path.join(self.TEST_FILTER_DIR, "basic.json"))
    with MockOutSubprocess([b"",
                            fake_events.BASIC_BOOTUP_EVENTS_SUBSET
                            ]) as subprocess_mocks:
      unexpected_reboots = self.uut.get_unexpected_reboots()
    self.assertEqual(len(unexpected_reboots), 3)
    subprocess_mocks.mock_popen.assert_called()

  def _get_event_dictionary(self):
    """Retrieves the event dictionary from the JSON object in the FakeEvent output value."""
    return json.loads(self.fake_file_writer.out)

  def _verify_required_event_keys(self, event_dictionary, with_log=False):
    """Verifies the event dictionary has the required/common keys."""
    self.assertIn(
        "system_timestamp", event_dictionary,
        "Missing 'system_timestamp' as key in dict. Dictionary {!r}".format(
            event_dictionary))
    self.assertIn(
        "raw_log_line", event_dictionary,
        "Missing 'raw_log_line' as key in dict. Dictionary {!r}".format(
            event_dictionary))
    self.assertIn(
        "matched_timestamp", event_dictionary,
        "Missing 'matched_timestamp' as key in dict. Dictionary {!r}".format(
            event_dictionary))
    if with_log:
      self.assertIn(
          "log_filename", event_dictionary,
          "Missing 'log_filename' as key in dict. Dictionary {!r}".format(
              event_dictionary))


if __name__ == "__main__":
  unit_test_case.main()
