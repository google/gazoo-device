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
"""Tests the log_process.py module."""
import datetime
import os
import re
import time
from unittest import mock

from gazoo_device import errors
from gazoo_device.capabilities import event_parser_default
from gazoo_device.switchboard import log_process
from gazoo_device.switchboard import switchboard_process
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import multiprocessing_utils

_NEW_LOG_FILE_MESSAGE = "<2017-07-01 12:23:43.123456> GDM-0: {}".format(
    log_process.NEW_LOG_FILE_MESSAGE)
_FULL_LOG_MESSAGE = "<2017-07-01 12:23:43.123456> GDM-0: Full log line\n"
_PARTIAL_LOG_MESSAGE = ("<2017-07-01 12:23:43.123456> GDM-1: my-prompt> "
                        "\ufffd\ufffd")
_ROTATE_LOG_MESSAGE = "<2017-07-01 12:23:43.123456> GDM-0: {}".format(
    log_process.ROTATE_LOG_MESSAGE)
_SHORT_LOG_MESSAGE = "<2017-07-01 12:23:43.123456> GDM-0: Short line\n"
_EVENT_LOG_MESSAGE = ("<2017-07-01 12:23:43.123456> GDM-0: [APPL] Some "
                      "non-existent message with non-ascii \xf7\n")
_EVENT_LINE_RETURN_LOG_MESSAGE = (
    "<2017-07-01 12:23:43.123456> GDM-0: \r[APPL] "
    "Some non-existent message with extra line return chars\r")
_WRITE_TIMEOUT = 1

wait_for_queue_writes = switchboard_process.wait_for_queue_writes


def get_file_size(file_path, size=0, timeout=_WRITE_TIMEOUT):
  end_time = time.time() + timeout
  while not os.path.isfile(file_path) and time.time() < end_time:
    time.sleep(0.001)
  filesize = os.path.getsize(file_path)
  while filesize <= size and time.time() < end_time:
    time.sleep(0.001)
    filesize = os.path.getsize(file_path)
  return os.path.getsize(file_path)


class LogFilterProcessTests(unit_test_case.MultiprocessingTestCase):

  def setUp(self):
    super().setUp()

    self.mock_parser = mock.MagicMock(
        spec=event_parser_default.EventParserDefault)
    self.command_queue = multiprocessing_utils.get_context().Queue()

  def tearDown(self):
    if hasattr(self, "uut"):
      self.uut._post_run_hook()  # close any open files
      del self.uut
    del self.command_queue  # Release shared memory file descriptors.
    super().tearDown()

  def test_000_log_filter_construct_destruct(self):
    """Test LogFilterProcess constructing and destructing raises no errors."""
    filters = []
    parser_obj = event_parser_default.EventParserDefault(
        filters, event_file_path="/foo.txt", device_name="device-1234")
    log_file_name = self._testMethodName + ".txt"
    log_path = os.path.join(self.artifacts_directory, log_file_name)
    self.uut = log_process.LogFilterProcess("fake_device", self.exception_queue,
                                            self.command_queue, parser_obj,
                                            log_path)
    self.assertFalse(self.uut.is_started(),
                     "Expected process not started, found started")
    self.assertFalse(self.uut.is_running(),
                     "Expected process to not running, found running")

  def test_001_log_filter_cant_open_log_file(self):
    """Test log filter unable to open log file."""
    filters = []
    parser_obj = event_parser_default.EventParserDefault(
        filters, event_file_path="/foo.txt", device_name="device-1234")
    log_file_name = self._testMethodName + ".txt"
    log_path = os.path.join(self.artifacts_directory, log_file_name)
    event_path = log_process.get_event_filename(log_path)
    self.uut = log_process.LogFilterProcess("fake_device", self.exception_queue,
                                            self.command_queue, parser_obj,
                                            log_path)
    self.uut._pre_run_hook()
    self.uut._do_work()
    self.uut._post_run_hook()
    self.assertFalse(
        os.path.exists(event_path),
        "Expected event file {} to not exist, but it exists".format(event_path))

  def test_002_log_filter_creates_event_file(self):
    """Test log filter creates event file after opening log file."""
    filter_file = os.path.join(self.TEST_FILTER_DIR,
                               "optional_description.json")
    parser_obj = event_parser_default.EventParserDefault(
        [filter_file], event_file_path="/foo.txt", device_name="device-1234")
    log_file_name = self._testMethodName + ".txt"
    log_path = os.path.join(self.artifacts_directory, log_file_name)
    event_path = log_process.get_event_filename(log_path)
    self.uut = log_process.LogFilterProcess("fake_device", self.exception_queue,
                                            self.command_queue, parser_obj,
                                            log_path)
    self._append_to_log_file(log_path)
    self.uut._pre_run_hook()
    self.uut._do_work()  # opens log file
    self.uut._do_work()  # writes first event
    filesize = get_file_size(event_path)
    self.uut._post_run_hook()
    self.assertTrue(
        os.path.exists(event_path),
        "Expected event file {} to exist, but it doesn't exist".format(
            event_path))
    self.assertGreater(
        filesize, 0,
        "Expected event file {} size > 0 found {}".format(event_path, filesize))

  def test_003_log_filter_tails_log_file(self):
    """Test log filter tails log file for new lines added."""
    filter_file = os.path.join(self.TEST_FILTER_DIR,
                               "optional_description.json")

    log_file_name = self._testMethodName + ".txt"
    log_path = os.path.join(self.artifacts_directory, log_file_name)

    event_path = log_process.get_event_filename(log_path)
    parser_obj = event_parser_default.EventParserDefault(
        [filter_file], event_file_path=event_path, device_name="device-1234")
    self.uut = log_process.LogFilterProcess("fake_device", self.exception_queue,
                                            self.command_queue, parser_obj,
                                            log_path)

    self._append_to_log_file(log_path)
    self.uut._pre_run_hook()
    self.uut._do_work()  # opens log file
    self.uut._do_work()  # writes first event
    filesize1 = get_file_size(event_path)
    self.uut._do_work()  # reads no log line
    self._append_to_log_file(log_path)
    self.uut._do_work()  # writes second event
    filesize2 = get_file_size(event_path, size=filesize1)
    self.uut._post_run_hook()
    self.assertTrue(
        os.path.exists(event_path),
        "Expected event file {} to exist, but it doesn't exist".format(
            event_path))
    self.assertGreater(
        filesize2, filesize1,
        "Expected event file {} to grow from size {}, but found {}".format(
            event_path, filesize1, filesize2))

  def test_004_log_filter_handles_line_return_chars(self):
    """Test log filter tails log file for new lines added."""
    filter_file = os.path.join(self.TEST_FILTER_DIR,
                               "optional_description.json")

    log_file_name = self._testMethodName + ".txt"
    log_path = os.path.join(self.artifacts_directory, log_file_name)
    event_path = log_process.get_event_filename(log_path)
    parser_obj = event_parser_default.EventParserDefault(
        [filter_file], event_file_path=event_path, device_name="device-1234")
    self.uut = log_process.LogFilterProcess("fake_device", self.exception_queue,
                                            self.command_queue, parser_obj,
                                            log_path)
    self._append_to_log_file(log_path, log_line=_EVENT_LINE_RETURN_LOG_MESSAGE)
    self.uut._pre_run_hook()
    self.uut._do_work()  # opens log file
    self.uut._do_work()  # skips writing event due to missing \n
    filesize1 = get_file_size(event_path)
    self.uut._do_work()  # reads no log line
    self._append_to_log_file(log_path, log_line="\r\n")
    self.uut._do_work()  # writes first event
    filesize2 = get_file_size(event_path, size=filesize1)
    self.uut._post_run_hook()
    self.assertTrue(
        os.path.exists(event_path),
        "Expected event file {} to exist, but it doesn't exist".format(
            event_path))
    self.assertEqual(
        0, filesize1, "Expected event file {} to be size 0 but found {}".format(
            event_path, filesize1))
    self.assertLess(
        filesize1, filesize2,
        "Expected event file {} to grow from size {}, but found {}".format(
            event_path, filesize1, filesize2))

  def test_100_log_filter_rejects_invalid_command(self):
    """Test LogFilterProcess rejects invalid command."""
    filters = []
    parser_obj = event_parser_default.EventParserDefault(
        filters, event_file_path="/foo.txt", device_name="device-1234")
    log_file_name = self._testMethodName + ".txt"
    log_path = os.path.join(self.artifacts_directory, log_file_name)
    self.uut = log_process.LogFilterProcess("fake_device", self.exception_queue,
                                            self.command_queue, parser_obj,
                                            log_path)

    self.command_queue.put(("invalid cmd", None))
    wait_for_queue_writes(self.command_queue)
    self.uut._pre_run_hook()
    with self.assertRaisesRegex(RuntimeError, "received an unknown command"):
      self.uut._do_work()
    self.uut._post_run_hook()

  def test_101_log_filter_accepts_valid_common_commands(self):
    """Test LogFilterProcess send_command accepts valid common commands."""
    filters = []
    parser_obj = event_parser_default.EventParserDefault(
        filters, event_file_path="/foo.txt", device_name="device-1234")
    log_file_name = self._testMethodName + ".txt"
    log_path = os.path.join(self.artifacts_directory, log_file_name)
    self.uut = log_process.LogFilterProcess("fake_device", self.exception_queue,
                                            self.command_queue, parser_obj,
                                            log_path)

    for command in log_process._VALID_COMMON_COMMANDS:
      self.uut.send_command(command)
      wait_for_queue_writes(self.command_queue)
      self.assertFalse(
          self.command_queue.empty(),
          "Expected command queue {} to not be empty".format(
              self.command_queue))
      command_message = self.command_queue.get()
      self.assertEqual(
          command, command_message[0],
          "Expected command {} found {}".format(command, command_message[0]))

  def test_120_load_filter_file_returns_error(self):
    """Verifies ParserError seen by method _do_work."""
    filter_file = os.path.join(self.TEST_FILTER_DIR,
                               "optional_description.json")
    log_file_name = self._testMethodName + ".txt"
    log_path = os.path.join(self.artifacts_directory, log_file_name)
    self.uut = log_process.LogFilterProcess("fake_device", self.exception_queue,
                                            self.command_queue,
                                            self.mock_parser, log_path)
    self._append_to_log_file(log_path)
    self.mock_parser.load_filter_file.side_effect = errors.ParserError(
        "Adding new filter failed")
    with self.assertRaisesRegex(errors.ParserError, "Adding new filter failed"):
      self.uut._pre_run_hook()
      self.uut.send_command(log_process.CMD_ADD_NEW_FILTER, filter_file)
      wait_for_queue_writes(self.command_queue)
      self.uut._do_work()  # loads filter file

  def test_121_load_filter_file_adds_new_filter(self):
    """Verifies can add new filter file."""
    filter_file = os.path.join(self.TEST_FILTER_DIR,
                               "optional_description.json")
    log_file_name = self._testMethodName + ".txt"
    log_path = os.path.join(self.artifacts_directory, log_file_name)
    self.uut = log_process.LogFilterProcess("fake_device", self.exception_queue,
                                            self.command_queue,
                                            self.mock_parser, log_path)
    self._append_to_log_file(log_path)
    self.uut._pre_run_hook()
    self.uut.send_command(log_process.CMD_ADD_NEW_FILTER, filter_file)
    wait_for_queue_writes(self.command_queue)
    self.uut._do_work()  # loads filter file
    self.uut._post_run_hook()
    self.mock_parser.load_filter_file.assert_called_once_with(filter_file)

  def test_200_log_filter_uses_new_log_file(self):
    """Test switching LogFilterProcess to use new log file specified."""
    filters = []
    parser_obj = event_parser_default.EventParserDefault(
        filters, event_file_path="/foo.txt", device_name="device-1234")
    old_log_path = os.path.join(self.artifacts_directory, self._testMethodName,
                                "fake-device-old.txt")
    new_log_path = os.path.join(self.artifacts_directory, self._testMethodName,
                                "fake-device-new.txt")
    old_event_path = log_process.get_event_filename(old_log_path)
    new_event_path = log_process.get_event_filename(new_log_path)
    self.uut = log_process.LogFilterProcess("fake_device", self.exception_queue,
                                            self.command_queue, parser_obj,
                                            old_log_path)

    self._append_to_log_file(old_log_path)
    self._append_to_log_file(new_log_path)
    self.uut._pre_run_hook()
    self.uut._do_work(
    )  # Opens old log and event files and processes first line
    switchboard_process.put_message(
        self.command_queue, (log_process.CMD_NEW_LOG_FILE, new_log_path))
    wait_for_queue_writes(self.command_queue)
    self._append_to_log_file(old_log_path, log_line=_NEW_LOG_FILE_MESSAGE)
    self.uut._do_work()  # Process next line in old log file and closes it
    self.assertTrue(
        os.path.exists(old_event_path),
        "Expected {} to exist".format(old_event_path))
    self.assertFalse(
        os.path.exists(new_event_path),
        "Expected {} to not exist".format(new_event_path))
    self.uut._do_work()  # Opens new log and event files
    self.assertTrue(
        os.path.exists(old_event_path),
        "Expected {} to exist".format(old_event_path))
    self.assertTrue(
        os.path.exists(new_event_path),
        "Expected {} to exist".format(new_event_path))
    self.uut._post_run_hook()

  def test_201_log_filter_ignores_extra_new_log_file_message(self):
    """Test LogFilterProcess ignores spurious new log file message."""
    filters = []
    parser_obj = event_parser_default.EventParserDefault(
        filters, event_file_path="/foo.txt", device_name="device-1234")
    old_log_path = os.path.join(self.artifacts_directory, self._testMethodName,
                                "fake-device-old.txt")
    new_log_path = os.path.join(self.artifacts_directory, self._testMethodName,
                                "fake-device-new.txt")
    old_event_path = log_process.get_event_filename(old_log_path)
    new_event_path = log_process.get_event_filename(new_log_path)
    self.uut = log_process.LogFilterProcess("fake_device", self.exception_queue,
                                            self.command_queue, parser_obj,
                                            old_log_path)

    self._append_to_log_file(old_log_path)
    self._append_to_log_file(new_log_path)
    self.uut._pre_run_hook()
    self.uut._do_work(
    )  # Opens old log and event files and processes first line
    self._append_to_log_file(old_log_path, log_line=_NEW_LOG_FILE_MESSAGE)
    self.uut._do_work()  # Process next line in and tries to switch to next log
    self.assertTrue(
        os.path.exists(old_event_path),
        "Expected {} to exist".format(old_event_path))
    self.assertFalse(
        os.path.exists(new_event_path),
        "Expected {} to not exist".format(new_event_path))
    switchboard_process.put_message(
        self.command_queue, (log_process.CMD_NEW_LOG_FILE, new_log_path))
    wait_for_queue_writes(self.command_queue)
    self._append_to_log_file(old_log_path, log_line=_NEW_LOG_FILE_MESSAGE)
    self.uut._do_work()  # Process next line in old log file and closes it
    self.uut._do_work(
    )  # Opens new log and event files and processes first line
    self.assertTrue(
        os.path.exists(old_event_path),
        "Expected {} to exist".format(old_event_path))
    self.assertTrue(
        os.path.exists(new_event_path),
        "Expected {} to exist".format(new_event_path))
    self.uut._post_run_hook()

  def test_210_log_filter_rotates_log_file_only(self):
    """Test LogFilterProcess rotates to next log file only."""
    filters = []
    parser_obj = event_parser_default.EventParserDefault(
        filters, event_file_path="/foo.txt", device_name="device-1234")
    old_log_path = os.path.join(self.artifacts_directory, self._testMethodName,
                                "fake-device.txt")
    next_log_path = os.path.join(self.artifacts_directory, self._testMethodName,
                                 "fake-device.00001.txt")
    old_event_path = log_process.get_event_filename(old_log_path)
    next_event_path = log_process.get_event_filename(next_log_path)
    self.uut = log_process.LogFilterProcess("fake_device", self.exception_queue,
                                            self.command_queue, parser_obj,
                                            old_log_path)

    self._append_to_log_file(old_log_path)
    self._append_to_log_file(next_log_path)
    self.uut._pre_run_hook()
    self.uut._do_work(
    )  # Opens old log and event files and processes first line
    self._append_to_log_file(old_log_path, log_line=_ROTATE_LOG_MESSAGE)
    self.uut._do_work()  # Process next line in old log file and closes it
    self.assertTrue(
        os.path.exists(old_event_path),
        "Expected {} to exist".format(old_event_path))
    self.assertFalse(
        os.path.exists(next_event_path),
        "Expected {} to not exist".format(next_event_path))
    self.uut._do_work(
    )  # Opens next log and event files and processes first line
    self.assertTrue(
        os.path.exists(old_event_path),
        "Expected {} to exist".format(old_event_path))
    self.assertFalse(
        os.path.exists(next_event_path),
        "Expected {} to not exist".format(next_event_path))
    self.uut._post_run_hook()

  def test_211_log_filter_new_log_message_doesnt_trigger_rotate(self):
    """Test rotate log message appears after new log file command."""
    filters = []
    parser_obj = event_parser_default.EventParserDefault(
        filters, event_file_path="/foo.txt", device_name="device-1234")
    old_log_path = os.path.join(self.artifacts_directory, self._testMethodName,
                                "fake-device-old.txt")
    old_event_path = log_process.get_event_filename(old_log_path)
    new_log_path = os.path.join(self.artifacts_directory, self._testMethodName,
                                "fake-device-new.txt")
    new_event_path = log_process.get_event_filename(new_log_path)
    next_log_path1 = os.path.join(self.artifacts_directory,
                                  self._testMethodName,
                                  "fake-device-old.00001.txt")
    next_event_path1 = log_process.get_event_filename(next_log_path1)
    next_log_path2 = os.path.join(self.artifacts_directory,
                                  self._testMethodName,
                                  "fake-device-new.00001.txt")
    next_event_path2 = log_process.get_event_filename(next_log_path2)
    self.uut = log_process.LogFilterProcess("fake_device", self.exception_queue,
                                            self.command_queue, parser_obj,
                                            old_log_path)

    self._append_to_log_file(old_log_path)
    self._append_to_log_file(next_log_path1)
    self._append_to_log_file(new_log_path)
    self.uut._pre_run_hook()
    self.uut._do_work(
    )  # Opens old log and event files and processes first line
    switchboard_process.put_message(
        self.command_queue, (log_process.CMD_NEW_LOG_FILE, new_log_path))
    wait_for_queue_writes(self.command_queue)
    self._append_to_log_file(old_log_path, log_line=_ROTATE_LOG_MESSAGE)
    self.uut._do_work(
    )  # Process next line in old log file and rotates log file
    self.assertTrue(
        os.path.exists(old_event_path),
        "Expected {} to exist".format(old_event_path))
    self.assertFalse(
        os.path.exists(new_event_path),
        "Expected {} to not exist".format(new_event_path))
    self.assertFalse(
        os.path.exists(next_event_path1),
        "Expected {} to not exist".format(next_event_path1))
    self.assertFalse(
        os.path.exists(next_event_path2),
        "Expected {} to not exist".format(next_event_path2))
    self._append_to_log_file(next_log_path1, log_line=_NEW_LOG_FILE_MESSAGE)
    self.uut._do_work(
    )  # Process next line in next log file 1 and opens new log file
    self.assertTrue(
        os.path.exists(old_event_path),
        "Expected {} to exist".format(old_event_path))
    self.assertFalse(
        os.path.exists(new_event_path),
        "Expected {} to not exist".format(new_event_path))
    self.assertFalse(
        os.path.exists(next_event_path1),
        "Expected {} to not exist".format(next_event_path1))
    self.assertFalse(
        os.path.exists(next_event_path2),
        "Expected {} to not exist".format(next_event_path2))
    self.uut._do_work()  # Keeps reading from new log file
    self.assertTrue(
        os.path.exists(old_event_path),
        "Expected {} to exist".format(old_event_path))
    self.assertTrue(
        os.path.exists(new_event_path),
        "Expected {} to exist".format(new_event_path))
    self.assertFalse(
        os.path.exists(next_event_path1),
        "Expected {} to not exist".format(next_event_path1))
    self.assertFalse(
        os.path.exists(next_event_path2),
        "Expected {} to not exist".format(next_event_path2))
    self.uut._post_run_hook()

  def _append_to_log_file(self, log_path, log_line=_EVENT_LOG_MESSAGE):
    if not os.path.exists(os.path.dirname(log_path)):
      os.makedirs(os.path.dirname(log_path))
    with open(log_path, "a", encoding="utf-8") as log_file:
      log_file.write(log_line)
      log_file.flush()


class LogWriterProcessTests(unit_test_case.MultiprocessingTestCase):

  def setUp(self):
    super().setUp()

    self.command_queue = multiprocessing_utils.get_context().Queue()
    self.log_queue = multiprocessing_utils.get_context().Queue()

  def tearDown(self):
    if hasattr(self, "uut"):
      del self.uut
    del self.command_queue  # Release shared memory file descriptors.
    del self.log_queue
    super().tearDown()

  def test_000_log_writer_construct_destruct(self):
    """Test LogWriterProcess constructing and destructing raises no errors."""
    log_file_name = self._testMethodName + ".txt"
    log_path = os.path.join(self.artifacts_directory, log_file_name)
    self.uut = log_process.LogWriterProcess("fake_device", self.exception_queue,
                                            self.command_queue, self.log_queue,
                                            log_path)
    self.assertFalse(self.uut.is_started(),
                     "Expected process not started, found started")
    self.assertFalse(self.uut.is_running(),
                     "Expected process to not running, found running")

  def test_001_log_message_adds_log_timestamp(self):
    """Test log_message method adds host system timestamp."""
    port = 0
    raw_log_line = "my log line"
    log_process.log_message(self.log_queue, raw_log_line, port)
    wait_for_queue_writes(self.log_queue)
    log_line = self.log_queue.get()

    # Log line format check
    self.assertIsInstance(
        log_line, str,
        "Expected log line to be unicode, found {}".format(type(log_line)))

    # System timestamp checks
    timestamp_length = log_process.HOST_TIMESTAMP_LENGTH
    host_timestamp = datetime.datetime.strptime(
        log_line[:timestamp_length], log_process.HOST_TIMESTAMP_FORMAT)
    self.assertIsInstance(
        host_timestamp, datetime.datetime,
        "Expected datetime found {}".format(type(host_timestamp)))
    log_line_without_timestamp = log_line[timestamp_length:]

    # Log line header checks
    match = re.search(log_process.LOG_LINE_HEADER_FORMAT,
                      log_line_without_timestamp)
    self.assertIsNotNone(
        match, "Expected log line header format {} to match {}".format(
            log_process.LOG_LINE_HEADER_FORMAT, log_line_without_timestamp))
    self.assertEqual(
        str(port), match.group(1),
        "Expected log line source port {} to equal {} from line header".format(
            port, match.group(1)))
    self.assertEqual(
        raw_log_line, match.group(2),
        "Expected raw log line {} to equal {} from line header".format(
            raw_log_line, match.group(2)))

  def test_002_get_next_log_filename_no_counter(self):
    """Test get_next_log_filename handles file with no log counter."""
    current_log_filename = (
        "/tmp/TestSuite.prefix-device-1234-20180912-111222.txt")
    expected_log_filename = (
        "/tmp/TestSuite.prefix-device-1234-20180912-111222.00001.txt")

    log_filename = log_process.get_next_log_filename(current_log_filename)
    self.assertEqual(
        expected_log_filename, log_filename,
        "Expected log filename {} found {}".format(expected_log_filename,
                                                   log_filename))

  def test_003_get_next_log_filename_with_counter(self):
    """Test get_next_log_filename handles file with log counter."""
    current_log_filename = (
        "/tmp/TestSuite.prefix-device-0203-20180912-111222.99998.txt")
    expected_log_filename = (
        "/tmp/TestSuite.prefix-device-0203-20180912-111222.99999.txt")

    log_filename = log_process.get_next_log_filename(current_log_filename)
    self.assertEqual(
        expected_log_filename, log_filename,
        "Expected log filename {} found {}".format(expected_log_filename,
                                                   log_filename))

  def test_010_log_writer_writes_full_log_line(self):
    """Test writing full log line to file."""
    log_file_name = self._testMethodName + ".txt"
    log_path = os.path.join(self.artifacts_directory, log_file_name)
    self.uut = log_process.LogWriterProcess("fake_device", self.exception_queue,
                                            self.command_queue, self.log_queue,
                                            log_path)
    switchboard_process.put_message(self.log_queue, _FULL_LOG_MESSAGE)
    wait_for_queue_writes(self.log_queue)
    self.uut._pre_run_hook()
    self.uut._do_work()
    self.uut._post_run_hook()
    self._verify_log_file_and_lines(log_path, 1)

  def test_011_log_writer_writes_partial_log_line(self):
    """Test writing partial log lines with unicode characters to file."""
    log_file_name = self._testMethodName + ".txt"
    log_path = os.path.join(self.artifacts_directory, log_file_name)
    self.uut = log_process.LogWriterProcess("fake_device", self.exception_queue,
                                            self.command_queue, self.log_queue,
                                            log_path)
    switchboard_process.put_message(self.log_queue, _PARTIAL_LOG_MESSAGE)
    wait_for_queue_writes(self.log_queue)
    self.uut._pre_run_hook()
    self.uut._do_work()
    self.uut._post_run_hook()
    lines = self._verify_log_file_and_lines(log_path, 1)
    self.assertIn(
        "[NO EOL]", lines[0],
        "Expected '[NO EOL]' at end of partial line found {!r}".format(
            lines[0]))

  def test_012_log_writer_writes_partial_and_full_log_lines(self):
    """Test writing partial and full log lines with unicode characters."""
    log_file_name = self._testMethodName + ".txt"
    log_path = os.path.join(self.artifacts_directory, log_file_name)
    self.uut = log_process.LogWriterProcess("fake_device", self.exception_queue,
                                            self.command_queue, self.log_queue,
                                            log_path)
    switchboard_process.put_message(self.log_queue, _PARTIAL_LOG_MESSAGE)
    switchboard_process.put_message(self.log_queue, _FULL_LOG_MESSAGE)
    wait_for_queue_writes(self.log_queue)
    self.uut._pre_run_hook()
    self.uut._do_work()
    self.uut._do_work()
    self.uut._post_run_hook()
    self._verify_log_file_and_lines(log_path, 2)

  def test_100_log_writer_rejects_invalid_command(self):
    """Test LogWriterProcess rejects invalid command."""
    log_file_name = self._testMethodName + ".txt"
    log_path = os.path.join(self.artifacts_directory, log_file_name)
    self.uut = log_process.LogWriterProcess("fake_device", self.exception_queue,
                                            self.command_queue, self.log_queue,
                                            log_path)

    self.command_queue.put(("invalid cmd", None))
    wait_for_queue_writes(self.command_queue)
    self.uut._pre_run_hook()
    with self.assertRaisesRegex(RuntimeError, "received an unknown command"):
      self.uut._do_work()
    self.uut._post_run_hook()

  def test_101_log_writer_accepts_valid_common_commands(self):
    """Test LogWriterProcess send_command accepts valid common commands."""
    log_file_name = self._testMethodName + ".txt"
    log_path = os.path.join(self.artifacts_directory, log_file_name)
    self.uut = log_process.LogWriterProcess("fake_device", self.exception_queue,
                                            self.command_queue, self.log_queue,
                                            log_path)

    for command in log_process._VALID_WRITER_COMMANDS:
      self.uut.send_command(command)
      wait_for_queue_writes(self.command_queue)
      self.assertFalse(self.command_queue.empty(),
                       "Expected command queue to not be empty")
      command_message = self.command_queue.get()
      self.assertEqual(
          command, command_message[0],
          "Expected command {} found {}".format(command, command_message[0]))

  def test_200_log_writer_uses_new_log_file(self):
    """Test switching LogWriterProcess to use new log file specified."""
    old_log_path = os.path.join(self.artifacts_directory, self._testMethodName,
                                "fake-device-old.txt")
    new_log_path = os.path.join(self.artifacts_directory, self._testMethodName,
                                "fake-device-new.txt")
    self.uut = log_process.LogWriterProcess("fake_device", self.exception_queue,
                                            self.command_queue, self.log_queue,
                                            old_log_path)
    switchboard_process.put_message(
        self.command_queue, (log_process.CMD_NEW_LOG_FILE, new_log_path))
    wait_for_queue_writes(self.command_queue)
    self.uut._pre_run_hook()  # Open old log file
    self.uut._do_work()  # Process new log file command and opens new log file
    switchboard_process.put_message(self.log_queue, _FULL_LOG_MESSAGE)
    wait_for_queue_writes(self.log_queue)
    self.uut._do_work()  # Writes full log message to new log file
    self.uut._post_run_hook()
    old_lines = self._verify_log_file_and_lines(old_log_path, 1)
    new_lines = self._verify_log_file_and_lines(new_log_path, 1)
    self.assertNotEqual(old_lines, new_lines,
                        "Expected {!r} == {!r}".format(old_lines, new_lines))

  def test_210_log_writer_rotates_log_file(self):
    """Test LogWriterProcess rotating to new log file."""
    max_log_size = len(_FULL_LOG_MESSAGE)
    old_log_path = os.path.join(self.artifacts_directory, self._testMethodName,
                                "fake-device.txt")
    new_log_path = os.path.join(self.artifacts_directory, self._testMethodName,
                                "fake-device.00001.txt")
    next_log_path = os.path.join(self.artifacts_directory, self._testMethodName,
                                 "fake-device.00002.txt")
    self.uut = log_process.LogWriterProcess(
        "fake_device",
        self.exception_queue,
        self.command_queue,
        self.log_queue,
        old_log_path,
        max_log_size=max_log_size)
    switchboard_process.put_message(self.log_queue, _FULL_LOG_MESSAGE)
    wait_for_queue_writes(self.log_queue)
    self.uut._pre_run_hook()
    self.uut._do_work()
    switchboard_process.put_message(self.log_queue, _SHORT_LOG_MESSAGE)
    wait_for_queue_writes(self.log_queue)
    self.uut._do_work()
    self.uut._post_run_hook()
    old_lines = self._verify_log_file_and_lines(old_log_path, 2)
    self._verify_log_file_and_lines(new_log_path, 1)
    self.assertIn(
        log_process.ROTATE_LOG_MESSAGE, old_lines[1],
        "Expected {} log message in old log file found {!r}".format(
            log_process.ROTATE_LOG_MESSAGE, old_lines))
    self.assertTrue(
        os.path.exists(new_log_path),
        "Expected log rotation to {}".format(new_log_path))
    self.assertFalse(
        os.path.exists(next_log_path),
        "Expected no log rotation to {}".format(next_log_path))

  def test_211_log_writer_new_log_command_handled_before_log_rotate(self):
    """Test new log message could but doesn't trigger rotate log."""
    max_log_size = len(_NEW_LOG_FILE_MESSAGE)
    old_log_path = os.path.join(self.artifacts_directory, self._testMethodName,
                                "fake-device-old.txt")
    new_log_path = os.path.join(self.artifacts_directory, self._testMethodName,
                                "fake-device-new.txt")
    next_log_path1 = os.path.join(self.artifacts_directory,
                                  self._testMethodName,
                                  "fake-device-old.00001.txt")
    next_log_path2 = os.path.join(self.artifacts_directory,
                                  self._testMethodName,
                                  "fake-device-new.00001.txt")
    self.uut = log_process.LogWriterProcess(
        "fake_device",
        self.exception_queue,
        self.command_queue,
        self.log_queue,
        old_log_path,
        max_log_size=max_log_size)
    switchboard_process.put_message(
        self.command_queue, (log_process.CMD_NEW_LOG_FILE, new_log_path))
    wait_for_queue_writes(self.command_queue)
    self.uut._pre_run_hook()  # Opens old log file
    self.uut._do_work()  # Process new log file command and opens new log file
    self.uut._do_work()  # Allows for possible log rotation issue
    self.uut._post_run_hook()
    old_lines = self._verify_log_file_and_lines(old_log_path, 1)
    self._verify_log_file_and_lines(new_log_path, 0)
    self.assertIn(
        log_process.NEW_LOG_FILE_MESSAGE, old_lines[0],
        "Expected {} log message in old log file found {!r}".format(
            log_process.NEW_LOG_FILE_MESSAGE, old_lines))
    self.assertTrue(
        os.path.exists(new_log_path),
        "Expected new log file of {}".format(new_log_path))
    self.assertFalse(
        os.path.exists(next_log_path1),
        "Expected no log rotation to {}".format(next_log_path1))
    self.assertFalse(
        os.path.exists(next_log_path2),
        "Expected no log rotation to {}".format(next_log_path2))

  def test_212_log_writer_can_change_max_log_size(self):
    """Test LogWriterProcess can change max_log_size."""
    max_log_size = 0
    old_log_path = os.path.join(self.artifacts_directory, self._testMethodName,
                                "fake-device-old.txt")
    next_log_path = os.path.join(self.artifacts_directory, self._testMethodName,
                                 "fake-device-old.00001.txt")
    self.uut = log_process.LogWriterProcess(
        "fake_device",
        self.exception_queue,
        self.command_queue,
        self.log_queue,
        old_log_path,
        max_log_size=len(_FULL_LOG_MESSAGE))
    switchboard_process.put_message(
        self.command_queue, (log_process.CMD_MAX_LOG_SIZE, max_log_size))
    wait_for_queue_writes(self.command_queue)
    self.uut._pre_run_hook()  # Opens old log file
    self.uut._do_work()  # Process max_log_size command and opens new log file
    switchboard_process.put_message(self.log_queue, _FULL_LOG_MESSAGE)
    wait_for_queue_writes(self.log_queue)
    self.uut._do_work()  # Allows for possible log rotation issue
    self.uut._post_run_hook()
    old_lines = self._verify_log_file_and_lines(old_log_path, 2)
    self.assertIn(
        log_process.CHANGE_MAX_LOG_SIZE, old_lines[0],
        "Expected {} log message in old log file found {!r}".format(
            log_process.CHANGE_MAX_LOG_SIZE, old_lines))
    self.assertIn(
        _FULL_LOG_MESSAGE, old_lines[1],
        "Expected {} log message in old log file found {!r}".format(
            _FULL_LOG_MESSAGE, old_lines))
    self.assertFalse(
        os.path.exists(next_log_path),
        "Expected no log rotation to {}".format(next_log_path))

  def _verify_log_file_and_lines(self, log_path, count):
    filesize = os.path.getsize(log_path)
    if count > 0:
      self.assertGreater(filesize, 0,
                         "Expected file size > 0 found {}".format(filesize))
    else:
      self.assertEqual(0, filesize,
                       "Expected file size 0 found {}".format(filesize))
    with open(log_path, encoding="utf-8") as file:
      lines = file.readlines()
    self.assertEqual(
        count, len(lines),
        "Expected {} log line(s) found {}".format(count, len(lines)))
    for line in lines:
      match = re.search(log_process.LOG_LINE_HEADER_FORMAT, line)
      self.assertIsNotNone(
          match, "Expected log line header {!r} in {!r}".format(
              log_process.LOG_LINE_HEADER_FORMAT, line))
    return lines


if __name__ == "__main__":
  unit_test_case.main()
