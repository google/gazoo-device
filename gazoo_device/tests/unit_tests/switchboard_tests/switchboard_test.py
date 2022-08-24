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
"""Tests the switchboard.py module."""
import os
import pty
import queue
import re
import signal
import subprocess
import sys
import time
from unittest import mock

from gazoo_device import errors
from gazoo_device.capabilities import event_parser_default
from gazoo_device.switchboard import ftdi_buttons
from gazoo_device.switchboard import line_identifier
from gazoo_device.switchboard import log_process
from gazoo_device.switchboard import switchboard
from gazoo_device.switchboard import transport_process
from gazoo_device.switchboard import transport_properties
from gazoo_device.switchboard.transports import serial_transport
from gazoo_device.switchboard.transports import tcp_transport
from gazoo_device.tests.unit_tests.utils import fake_responder
from gazoo_device.tests.unit_tests.utils import fake_transport
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import retry
from gazoo_device.utility import usb_utils

get_queue_size = unit_test_case.get_queue_size

_DEVICE_COMMAND = "command"
_DEVICE_COMMAND_NEWLINE = "command\n"
_DEVICE_WRITE_TIMEOUT = 1
_EXPECT_TIMEOUT = 1.0
_LOG_MESSAGE = "Special log message to write to file"
_LOG_WRITE_TIMEOUT = 1
_MD5SUM_BAD = "bad7070257998981a0c7b7ec003b9bad"
_MD5SUM_GOOD = "4c57070257998981a0c7b7ec003b9d5c"
_FILE_ON_TRANSPORT_PATH = "/some/path/file.json"

_DEFAULT_FAKE_TRANSPORT_READS = ["a"] * 24 + ["b", "c", "d", "e"]


def get_file_lines(file_path):
  with open(file_path) as file:
    return file.readlines()


def get_file_size(file_path, size=0, timeout=_LOG_WRITE_TIMEOUT):
  """Get file size."""
  end_time = time.time() + timeout
  while not os.path.isfile(file_path) and time.time() < end_time:
    time.sleep(0.001)
  filesize = os.path.getsize(file_path)
  while filesize <= size and time.time() < end_time:
    time.sleep(0.001)
    filesize = os.path.getsize(file_path)
  return os.path.getsize(file_path)


def _write_read_for_echo_file_to_transport(data):
  responses = []
  responses.append(data)
  return responses


def _write_read_for_verify_file_on_transport_bad_checksum(data):
  responses = []
  if "md5sum" in data:
    responses.append("md5sum " + _FILE_ON_TRANSPORT_PATH + "\n")
    responses.append(_MD5SUM_BAD + "  " + _FILE_ON_TRANSPORT_PATH + "\n")
  return responses


def _write_read_for_verify_file_on_transport_good_checksum(data):
  responses = []
  if "md5sum" in data:
    responses.append("md5sum " + _FILE_ON_TRANSPORT_PATH + "\n")
    responses.append(_MD5SUM_GOOD + "  " + _FILE_ON_TRANSPORT_PATH + "\n")
  return responses


def _write_read_for_verify_file_on_transport_missing_file(data):
  responses = []
  if "md5sum" in data:
    responses.append("md5sum " + _FILE_ON_TRANSPORT_PATH + "\n")
    responses.append("md5sum: can't open '" + _FILE_ON_TRANSPORT_PATH + "': "
                     "No such file or directory\n")
  return responses


class NumberCruncher:
  """NumberCruncher class to test do_and_expect."""

  def __init__(self, result=5):
    self.result = result
    self.is_ok = False

  def check_result(self, number_list, multiplier=10, divisor=10):
    """Crunch numbers."""
    work_result = 0
    for num in number_list:
      work_result += num
    work_result *= multiplier
    work_result /= divisor
    self.is_ok = work_result == self.result


class SwitchboardTests(unit_test_case.MultiprocessingTestCase):
  """Switchboard unit test suite."""

  def setUp(self):
    super().setUp()

    # Mock out the usb_utils call used by Switchboard.close().
    get_all_serial_connections_patcher = mock.patch.object(
        usb_utils, "get_all_serial_connections", return_value=[])
    get_all_serial_connections_patcher.start()
    self.addCleanup(get_all_serial_connections_patcher.stop)

    self.log_path = os.path.join(self.artifacts_directory,
                                 self._testMethodName + ".txt")

  def tearDown(self):
    if hasattr(self, "uut"):
      self.uut.close()
      del self.uut
    if hasattr(self, "fake_transport"):
      self.fake_transport.close()
      del self.fake_transport

    super().tearDown()

  def test_switchboard_health_check_error_propagation(self):
    """Tests that an error in health_check method gets surfaced."""
    self.fake_transport = fake_transport.FakeTransport()
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              [self.fake_transport],
                                              self.log_path)
    # self.uut._healthy = False
    with mock.patch.object(
        self.uut, "_add_transport_processes") as mock_add_transports:
      mock_add_transports.side_effect = RuntimeError("A very bad error")
      with self.assertRaisesRegex(
          errors.CapabilityNotReadyError, "A very bad error") as cm:
        self.uut.health_check()
      error_cause = cm.exception.__cause__

    self.assertIsNotNone(error_cause, "Error cause is not being set.")
    self.assertIn(
        "A very bad error", str(error_cause), "Error is not propagated")

  def test_switchboard_close_with_no_transports(self):
    """Test switchboard close with no transports."""
    transport_list = []
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              transport_list, self.log_path)

  def test_switchboard_close_with_one_transport(self):
    """Test switchboard close with one transport."""
    self.fake_transport = fake_transport.FakeTransport()
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              [self.fake_transport],
                                              self.log_path)

  def test_switchboard_close_with_two_transports(self):
    """Test switchboard close with two transports."""
    transport_list = [
        fake_transport.FakeTransport(),
        fake_transport.FakeTransport()
    ]
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              transport_list, self.log_path)
    for tst_transport in transport_list:
      tst_transport.close()

  def test_switchboard_close_with_parser(self):
    """Test switchboard close with parser and no transports."""
    transport_list = []
    filter_list = []
    parser_obj = event_parser_default.EventParserDefault(
        filters=filter_list,
        event_file_path="/foo.txt",
        device_name="device-1234")
    self.uut = switchboard.SwitchboardDefault(
        "test_device",
        self.exception_queue,
        transport_list,
        self.log_path,
        parser=parser_obj)

  def test_switchboard_get_pattern_index_returns_none(self):
    """Test switchboard _get_pattern_index returns none for no match found."""
    compiled_list = [re.compile("fake pattern")]
    match_list = []
    result1 = switchboard._get_pattern_index(compiled_list, match_list,
                                             switchboard.MODE_TYPE_ANY)
    self.assertIsNone(
        result1,
        "Expected None for _get_pattern_list(any) found {}".format(result1))

    result2 = switchboard._get_pattern_index(compiled_list, match_list,
                                             switchboard.MODE_TYPE_SEQUENTIAL)
    self.assertIsNone(
        result2,
        "Expected None for _get_pattern_list(sequential) found {}".format(
            result2))

  def test_switchboard_multiple_close_with_no_transport(self):
    """Test core multiple close with no transport."""
    transport_list = []
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              transport_list, self.log_path)
    self.uut.close()
    self.uut.close()

  def test_switchboard_multiple_close_with_one_transport(self):
    """Test switchboard multiple close with one transport."""
    self.fake_transport = fake_transport.FakeTransport()
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              [self.fake_transport],
                                              self.log_path)
    self.uut.close()
    self.uut.close()

  def test_switchboard_add_log_note_with_newline(self):
    """Test add_log_note method without newline writes to log file."""
    transport_list = []
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              transport_list, self.log_path)
    self.uut.add_log_note(_LOG_MESSAGE + "\n")
    self._wait_for_log_write()
    lines = self._verify_log_file_and_lines(1)
    self.assertIn("GDM-M: Note: ", lines[0])

  def test_switchboard_add_log_note_without_newline(self):
    """Test switchboard add_log_note method with newline writes to log file."""
    transport_list = []
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              transport_list, self.log_path)
    self.uut.add_log_note(_LOG_MESSAGE)
    self._wait_for_log_write()
    lines = self._verify_log_file_and_lines(1)
    self.assertIn("GDM-M: Note: ", lines[0])

  def test_switchboard_start_new_log_raises_error(self):
    """Test switchboard start_new_log method raises error if closed."""
    transport_list = []
    old_log_path = os.path.join(self.artifacts_directory,
                                self._testMethodName + "-old",
                                "fake-device.txt")
    new_log_path = os.path.join(self.artifacts_directory,
                                self._testMethodName + "-new",
                                "fake-device.txt")
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              transport_list, old_log_path)
    self.uut.close()

    # Mock event where processes are closed despite healthy state.
    self.uut._healthy = True
    err_regex = "RuntimeError: Log writer process is not currently running"
    with self.assertRaisesRegex(errors.DeviceError, err_regex):
      self.uut.start_new_log(new_log_path)

  def test_switchboard_start_new_log_no_deadlock(self):
    """Test switchboard start_new_log method can't deadlock on log processes."""
    transport_list = []
    old_log_path = os.path.join(self.artifacts_directory,
                                self._testMethodName + "-old",
                                "fake-device.txt")
    new_log_path = os.path.join(self.artifacts_directory,
                                self._testMethodName + "-new",
                                "fake-device.txt")
    filter_list = []
    parser_obj = event_parser_default.EventParserDefault(
        filters=filter_list,
        event_file_path="/foo.txt",
        device_name="device-1234")
    self.uut = switchboard.SwitchboardDefault(
        "test_device",
        self.exception_queue,
        transport_list,
        old_log_path,
        parser=parser_obj)

    self.uut._log_filter_process.stop()
    self.uut.start_new_log(new_log_path)
    expected_message = "Expected in new log file"
    self.uut.add_log_note(expected_message)
    self._wait_for_log_write(log_path=new_log_path)
    old_log_lines = self._verify_log_file_and_lines(1, log_path=old_log_path)
    new_log_lines = self._verify_log_file_and_lines(1, log_path=new_log_path)
    self.assertIn(log_process.NEW_LOG_FILE_MESSAGE, old_log_lines[0])
    self.assertIn(expected_message, new_log_lines[0])

  def test_switchboard_start_new_log(self):
    """Test switchboard start_new_log method switches to new log file."""
    transport_list = []
    old_log_path = os.path.join(self.artifacts_directory,
                                self._testMethodName + "-old",
                                "fake-device.txt")
    new_log_path = os.path.join(self.artifacts_directory,
                                self._testMethodName + "-new",
                                "fake-device.txt")
    filter_list = []
    parser_obj = event_parser_default.EventParserDefault(
        filters=filter_list,
        event_file_path="/foo.txt",
        device_name="device-1234")
    self.uut = switchboard.SwitchboardDefault(
        "test_device",
        self.exception_queue,
        transport_list,
        old_log_path,
        parser=parser_obj)
    self.uut.add_log_note(_LOG_MESSAGE)
    self._wait_for_log_write(log_path=old_log_path)
    self._verify_log_file_and_lines(1, log_path=old_log_path)

    self.uut.start_new_log(new_log_path)
    expected_message = "Expected in new log file"
    self.uut.add_log_note(expected_message)
    self._wait_for_log_write(log_path=new_log_path)
    old_log_lines = self._verify_log_file_and_lines(2, log_path=old_log_path)
    new_log_lines = self._verify_log_file_and_lines(1, log_path=new_log_path)
    self.assertIn(log_process.NEW_LOG_FILE_MESSAGE, old_log_lines[1])
    self.assertIn(expected_message, new_log_lines[0])

  def test_switchboard_rotate_log_file(self):
    """Test switchboard rotates to new log file."""
    transport_list = []
    header = (
        log_process.LOG_LINE_HEADER_LENGTH + log_process.HOST_TIMESTAMP_LENGTH)
    max_log_size = header + len("Note: ") + len(_LOG_MESSAGE)
    old_log_path = os.path.join(self.artifacts_directory, self._testMethodName,
                                "fake-device.txt")
    new_log_path = os.path.join(self.artifacts_directory, self._testMethodName,
                                "fake-device.00001.txt")
    filter_list = []
    parser_obj = event_parser_default.EventParserDefault(
        filters=filter_list,
        event_file_path="/foo.txt",
        device_name="device-1234")
    self.uut = switchboard.SwitchboardDefault(
        "test_device",
        self.exception_queue,
        transport_list,
        old_log_path,
        parser=parser_obj,
        max_log_size=max_log_size)
    self.uut.add_log_note(_LOG_MESSAGE)
    self._wait_for_log_write(log_path=old_log_path)
    expected_message = "Expected in new log file"
    self.uut.add_log_note(expected_message)

    self._wait_for_log_write(log_path=new_log_path)
    old_log_lines = self._verify_log_file_and_lines(2, log_path=old_log_path)
    new_log_lines = self._verify_log_file_and_lines(1, log_path=new_log_path)
    self.assertIn(log_process.ROTATE_LOG_MESSAGE, old_log_lines[1])
    self.assertIn(expected_message, new_log_lines[0])

  def test_switchboard_no_log_rotate(self):
    """Test switchboard doesn't rotate to new log file if max_log_size=0."""
    transport_list = []
    new_log_path = log_process.get_next_log_filename(self.log_path)
    filter_list = []
    parser_obj = event_parser_default.EventParserDefault(
        filters=filter_list,
        event_file_path="/foo.txt",
        device_name="device-1234")
    # Start with max_log_size that would trigger a rotation
    self.uut = switchboard.SwitchboardDefault(
        "test_device",
        self.exception_queue,
        transport_list,
        self.log_path,
        parser=parser_obj,
        max_log_size=len(_LOG_MESSAGE))
    # Change max_log_size to 0 to disable log rotation
    max_log_size = 0
    self.uut.set_max_log_size(max_log_size)
    initial_filesize = self._wait_for_log_write()
    self.uut.add_log_note(_LOG_MESSAGE)
    if len(get_file_lines(self.log_path)) < 2:
      self._wait_for_log_write(initial_filesize=initial_filesize)
    old_log_lines = self._verify_log_file_and_lines(2)
    self.assertFalse(
        os.path.exists(new_log_path),
        "Expected {} log file to not exist".format(new_log_path))
    self.assertIn(log_process.CHANGE_MAX_LOG_SIZE, old_log_lines[0])
    self.assertIn(_LOG_MESSAGE, old_log_lines[1])

  def test_switchboard_set_max_log_size_raises_error(self):
    """Test switchboard set_max_log_size method raises error if closed."""
    transport_list = []
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              transport_list, self.log_path)

    # Invalid type of value passed to set_max_log_size
    err_regex = "ValueError: Expected 'type<int>' found"
    with self.assertRaisesRegex(errors.DeviceError, err_regex):
      self.uut.set_max_log_size("1")
    self.uut.close()

    # Mock event where processes are closed despite healthy state.
    self.uut._healthy = True
    # Log writer process is not running
    err_regex = "RuntimeError: Log writer process is not currently running"
    with self.assertRaisesRegex(errors.DeviceError, err_regex):
      self.uut.set_max_log_size(1)

  def test_switchboard_send_raises_error(self):
    """Test switchboard send method raises error for invalid port."""
    self.fake_transport = fake_transport.FakeTransport()
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              [self.fake_transport],
                                              self.log_path)

    # port is None
    with self.assertRaisesRegex(
        errors.DeviceError,
        "Invalid port type. Expected: int, found: NoneType"):
      self.uut.send(_DEVICE_COMMAND, port=None)

    # port is 1
    with self.assertRaisesRegex(errors.DeviceError, "Invalid port number"):
      self.uut.send(_DEVICE_COMMAND, port=1)

  def test_switchboard_send_to_default_port(self):
    """Test send method sends command and writes port number to log file."""
    self.fake_transport = fake_transport.FakeTransport()
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              [self.fake_transport],
                                              self.log_path)
    self.uut.send(_DEVICE_COMMAND, add_newline=False)
    self._wait_for_log_write()
    lines = self._verify_log_file_and_lines(1)
    self.assertIn("wrote command 'command' to port 0", lines[0])
    command = self._get_command(self.fake_transport)
    self.assertEqual(
        _DEVICE_COMMAND, command,
        "Expected command {!r} written to device found {!r}".format(
            _DEVICE_COMMAND, command))

  def test_switchboard_send_to_specified_port(self):
    """Test switchboard send method writes specified port to log file."""
    transport_list = [
        fake_transport.FakeTransport(),
        fake_transport.FakeTransport()
    ]
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              transport_list, self.log_path)
    self.uut.send(_DEVICE_COMMAND, port=1, add_newline=False)
    self._wait_for_log_write()
    lines = self._verify_log_file_and_lines(1)
    self.assertIn("wrote command 'command' to port 1", lines[0])
    command = self._get_command(transport_list[1])
    self.assertEqual(
        _DEVICE_COMMAND, command,
        "Expected command {!r} written to device found {!r}".format(
            _DEVICE_COMMAND, command))
    for tst_transport in transport_list:
      tst_transport.close()

  def test_switchboard_send_adds_newline_if_not_found(self):
    """Test send method adds a newline to command if it doesn't end with one."""
    self.fake_transport = fake_transport.FakeTransport()
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              [self.fake_transport],
                                              self.log_path)
    newline = "!"
    self.uut.send(_DEVICE_COMMAND, newline=newline)
    self._wait_for_log_write()
    lines = self._verify_log_file_and_lines(1)
    self.assertIn("wrote command 'command' to port 0", lines[0])
    command = self._get_command(self.fake_transport)
    self.assertEqual(
        _DEVICE_COMMAND + newline, command,
        "Expected command {!r} written to device found {!r}".format(
            _DEVICE_COMMAND + newline, command))

  def test_switchboard_send_doesnt_add_newline_if_found(self):
    """Test send doesn't add a newline to command if it is ends with one."""
    self.fake_transport = fake_transport.FakeTransport()
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              [self.fake_transport],
                                              self.log_path)
    newline = "!"
    self.uut.send(_DEVICE_COMMAND + newline, newline=newline)
    command = self._get_command(self.fake_transport)
    self.assertEqual(_DEVICE_COMMAND + newline, command)

    self.uut.send(_DEVICE_COMMAND + "\x00", newline=newline)
    command = self._get_command(self.fake_transport)
    self.assertEqual(_DEVICE_COMMAND + "\x00", command)

  def test_switchboard_send_slow(self):
    """Test switchboard send sends one byte at a time when slow=True."""
    self.fake_transport = fake_transport.FakeTransport()
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              [self.fake_transport],
                                              self.log_path)
    self.uut.send(_DEVICE_COMMAND_NEWLINE, slow=True)
    self._wait_for_log_write()
    command = ""
    for _ in range(0, len(_DEVICE_COMMAND_NEWLINE)):
      command += self._get_command(self.fake_transport)
    lines = self._verify_log_file_and_lines(1)

    expected_line = "wrote command {!r} to port 0".format(
        _DEVICE_COMMAND_NEWLINE)
    self.assertIn(expected_line, lines[0])
    self.assertEqual(
        _DEVICE_COMMAND_NEWLINE, command,
        "Expected command {!r} written to device found {!r}".format(
            _DEVICE_COMMAND_NEWLINE, command))

  def test_switchboard_send_force_slow(self):
    """Test switchboard send sends one byte at a time when force_slow=True."""
    self.fake_transport = fake_transport.FakeTransport()
    self.uut = switchboard.SwitchboardDefault(
        "test_device",
        self.exception_queue, [self.fake_transport],
        self.log_path,
        force_slow=True)
    self.uut.send(_DEVICE_COMMAND_NEWLINE)
    self._wait_for_log_write()
    command = ""
    for _ in range(0, len(_DEVICE_COMMAND_NEWLINE)):
      command += self._get_command(self.fake_transport)
    lines = self._verify_log_file_and_lines(1)

    expected_line = "wrote command {!r} to port 0".format(
        _DEVICE_COMMAND_NEWLINE)
    self.assertIn(expected_line, lines[0])
    self.assertEqual(
        _DEVICE_COMMAND_NEWLINE, command,
        "Expected command {!r} written to device found {!r}".format(
            _DEVICE_COMMAND_NEWLINE, command))

  def test_switchboard_do_and_expect_non_callable_raises_error(self):
    """Test do_and_expect with non callable function raises an error."""

    self.fake_transport = fake_transport.FakeTransport()
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              [self.fake_transport],
                                              self.log_path)

    # pattern_list is a string
    with self.assertRaisesRegex(errors.DeviceError, "is not callable"):
      non_callable = 1
      self.uut.do_and_expect(non_callable, [], {}, ["valid_pattern"])

  def test_switchboard_do_and_expect_args_none_kwargs_none(self):
    """Test switchboard do_and_expect with args=None and kwargs=None works."""
    number_cruncher = NumberCruncher(0)
    self._setup_expect_test()
    target_patterns = ["a"]

    self.uut.do_and_expect(
        number_cruncher.check_result, [[]], {},
        target_patterns,
        timeout=_EXPECT_TIMEOUT)

    self.assertTrue(
        number_cruncher.is_ok,
        "Using args [] and kwargs {} in call to 'do_and_expect' failed")

  def test_switchboard_do_and_expect_kwargs_none(self):
    """Test switchboard do_and_expect with kwargs=None works."""
    number_cruncher = NumberCruncher()
    self._setup_expect_test()
    target_patterns = ["a"]

    self.uut.do_and_expect(
        number_cruncher.check_result, [[2, 3]], {},
        target_patterns,
        timeout=_EXPECT_TIMEOUT)

    self.assertTrue(
        number_cruncher.is_ok,
        "Using args [] and kwargs {} in call to 'do_and_expect' failed")

  def test_switchboard_do_and_expect_args_none(self):
    """Test switchboard do_and_expect with kwargs=None works."""
    number_cruncher = NumberCruncher(0)
    self._setup_expect_test()
    target_patterns = ["a"]

    self.uut.do_and_expect(
        number_cruncher.check_result, [[]], {
            "multiplier": 1,
            "divisor": 1
        },
        target_patterns,
        timeout=_EXPECT_TIMEOUT)

    self.assertTrue(
        number_cruncher.is_ok,
        "Using args [] and kwargs {} in call to 'do_and_expect' failed")

  def test_switchboard_do_and_expect_args_and_kwargs(self):
    """Test switchboard do_and_expect with args and kwargs works."""
    number_cruncher = NumberCruncher(5)
    self._setup_expect_test()
    target_patterns = ["a"]

    self.uut.do_and_expect(
        number_cruncher.check_result, [[2, 3]], {},
        target_patterns,
        timeout=_EXPECT_TIMEOUT)

    self.assertTrue(
        number_cruncher.is_ok,
        "Using args [] and kwargs {} in call to 'do_and_expect' failed")

  def test_switchboard_do_and_expect_close(self):
    """Test switchboard do_and_expect calls switchboard close."""
    self._setup_expect_test()
    target_patterns = ["a"]

    with self.assertRaisesRegex(
        errors.CapabilityNotReadyError, "Switchboard has been closed"):
      self.uut.do_and_expect(
          self.uut.close, [], {}, target_patterns, timeout=_EXPECT_TIMEOUT)

  def test_switchboard_do_and_expect_nested_expect(self):
    """Test switchboard do_and_expect calls switchboard expect."""
    self._setup_expect_test(_DEFAULT_FAKE_TRANSPORT_READS +
                            ["z", "y", "x", "w"])

    def nested_func():
      target_patterns = ["a", "b", "c", "d", "e"]
      result = self.uut.expect(
          target_patterns, timeout=_EXPECT_TIMEOUT, mode="sequential")
      self.assertFalse(result.timedout,
                       "Expected nested expect to NOT time out")
      time.sleep(0.5)

    target_patterns = ["z", "y", "x", "w"]
    result = self.uut.do_and_expect(
        nested_func, [], {},
        target_patterns,
        timeout=_EXPECT_TIMEOUT,
        mode="sequential")
    self.assertFalse(result.timedout, "Expected do_and_expect to NOT time out")

  def test_expect_raise_for_timeout(self):
    """Verify exception is raised for timeout if raise_for_timeout is True."""
    self._setup_expect_test()
    target_patterns = ["c", "f", "b"]

    with self.assertRaisesRegex(errors.DeviceError, "timed out after waiting"):
      self.uut.expect(
          target_patterns,
          mode="all",
          timeout=_EXPECT_TIMEOUT,
          raise_for_timeout=True)

  def test_switchboard_do_and_expect_raise_for_timeout(self):
    """Verify exception is raised for timeout if raise_for_timeout is True."""
    self._setup_expect_test()
    target_patterns = ["unmatched_pattern"]

    with self.assertRaisesRegex(errors.DeviceError, "timed out after waiting"):
      self.uut.do_and_expect(
          mock.Mock(), [], {},
          target_patterns,
          timeout=_EXPECT_TIMEOUT,
          raise_for_timeout=True)

  def test_switchboard_expect_raises_errors(self):
    """Test switchboard expect raises errors for bad arguments."""

    self.fake_transport = fake_transport.FakeTransport()
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              [self.fake_transport],
                                              self.log_path)
    # pattern_list is a string
    with self.assertRaisesRegex(errors.DeviceError,
                                "Expecting list for pattern_list"):
      self.uut.expect("string_pattern_list")

    # pattern_list is empty
    with self.assertRaisesRegex(errors.DeviceError,
                                "Expecting at least one pattern in list"):
      self.uut.expect([])

    # pattern in pattern_list is an invalid regex
    with self.assertRaisesRegex(errors.DeviceError, "Invalid regex pattern"):
      self.uut.expect(["(invalid group"])

    # timeout is not an int or float
    with self.assertRaisesRegex(errors.DeviceError,
                                "Expecting int or float for timeout"):
      self.uut.expect(["valid pattern"], timeout=None)

    # searchwindowsize is not an int
    with self.assertRaisesRegex(errors.DeviceError,
                                "Expecting int for searchwindowsize"):
      self.uut.expect(["valid pattern"], searchwindowsize="")

    # expect_type is not a string
    with self.assertRaisesRegex(errors.DeviceError,
                                "Expecting str for expect_type"):
      self.uut.expect(["valid pattern"], expect_type=1)

    # expect_type value is not valid
    with self.assertRaisesRegex(errors.DeviceError,
                                "Invalid input for expect_type"):
      self.uut.expect(["valid pattern"], expect_type="bogus")

    # mode is not a string
    with self.assertRaisesRegex(errors.DeviceError, "Expecting str for mode"):
      self.uut.expect(["valid pattern"], mode=1)

    # mode value is not valid
    with self.assertRaisesRegex(errors.DeviceError, "Invalid input for mode"):
      self.uut.expect(["valid pattern"], mode="bogus")

  def test_switchboard_expect_any_fails(self):
    """Test switchboard expect any mode fails."""
    self._setup_expect_test()
    target_patterns = ["f", "g", "h"]

    expect_response = self.uut.expect(target_patterns, timeout=_EXPECT_TIMEOUT)
    self.assertTrue(expect_response.timedout,
                    "Expected any pattern to timedout")
    self.assertIsNone(
        expect_response.index,
        "Expected index to be None found {}".format(expect_response.index))
    err_msg = []
    self.assertTrue(
        self._is_ok_any_all(_DEFAULT_FAKE_TRANSPORT_READS, target_patterns,
                            expect_response, err_msg),
        "Failed expected outcome: {}".format(err_msg))

  def test_switchboard_expect_any_succeeds(self):
    """Test switchboard expect any mode succeeds."""
    self._setup_expect_test()
    target_patterns = ["e", "f", "g"]

    expect_response = self.uut.expect(target_patterns, timeout=_EXPECT_TIMEOUT)
    self.assertFalse(expect_response.timedout,
                     "Expected any pattern to not time out")
    self.assertEqual(
        0, expect_response.index,
        "Expected index to be {} found {}".format(0, expect_response.index))
    err_msg = []
    self.assertTrue(
        self._is_ok_any_all(_DEFAULT_FAKE_TRANSPORT_READS, target_patterns,
                            expect_response, err_msg),
        "Failed expected outcome: {}".format(err_msg))

  def test_switchboard_expect_all_fails(self):
    """Test switchboard expect all mode fails."""
    self._setup_expect_test()
    target_patterns = ["c", "f", "b"]

    expect_response = self.uut.expect(
        target_patterns, mode="all", timeout=_EXPECT_TIMEOUT)

    self.assertTrue(expect_response.timedout,
                    "Expected all pattern to timedout")
    self.assertEqual(
        0, expect_response.index,
        "Expected index to be {} found {}".format(0, expect_response.index))
    err_msg = []
    self.assertTrue(
        self._is_ok_any_all(_DEFAULT_FAKE_TRANSPORT_READS, target_patterns,
                            expect_response, err_msg),
        "Failed expected outcome: {}".format(err_msg))

  def test_switchboard_expect_all_succeeds(self):
    """Test switchboard expect all mode succeeds."""
    self._setup_expect_test()
    target_patterns = ["b", "c", "e", "a"]

    expect_response = self.uut.expect(
        target_patterns, mode="all", timeout=_EXPECT_TIMEOUT)

    self.assertFalse(expect_response.timedout,
                     "Expected all pattern to not time out")
    self.assertEqual(
        2, expect_response.index,
        "Expected index to be {} found {}".format(2, expect_response.index))
    err_msg = []
    self.assertTrue(
        self._is_ok_any_all(_DEFAULT_FAKE_TRANSPORT_READS, target_patterns,
                            expect_response, err_msg),
        "Failed expected outcome: {}".format(err_msg))

  def test_switchboard_expect_sequential_fails(self):
    """Test switchboard expect sequential mode fails."""
    all_patterns = ["a"] * 24 + ["e", "d", "c", "b"]
    self._setup_expect_test(all_patterns)
    target_patterns = ["a", "b", "c", "d", "e"]

    expect_response = self.uut.expect(
        target_patterns, mode="sequential", timeout=_EXPECT_TIMEOUT)

    self.assertTrue(expect_response.timedout,
                    "Expected sequential pattern to timedout")
    self.assertEqual(
        1, expect_response.index,
        "Expected index to be {} found {}".format(1, expect_response.index))
    err_msg = []
    self.assertTrue(
        self._is_ok_sequential(all_patterns, target_patterns, expect_response,
                               err_msg),
        "Failed expected outcome: {}".format(err_msg))

  def test_switchboard_expect_sequential_succeeds(self):
    """Test switchboard expect sequential mode succeeds."""
    all_patterns = ["a"] * 24 + ["e", "d", "c", "b", "c", "d", "e"]
    self._setup_expect_test(all_patterns)
    target_patterns = ["a", "b", "c", "d", "e"]

    expect_response = self.uut.expect(
        target_patterns, mode="sequential", timeout=_EXPECT_TIMEOUT)
    self.assertFalse(expect_response.timedout,
                     "Expected sequential pattern to not time out")
    self.assertEqual(
        4, expect_response.index,
        "Expected index to be {} found {}".format(4, expect_response.index))
    err_msg = []
    self.assertTrue(
        self._is_ok_sequential(all_patterns, target_patterns, expect_response,
                               err_msg),
        "Failed expected outcome: {}".format(err_msg))

  def test_switchboard_expect_long_receive_succeeds(self):
    """Test switchboard expect long receive (>searchwindowsize) succeeds."""
    long_receive = "c" * 60
    self._setup_expect_test(["a"] * 24 + ["b" + long_receive])
    searchwindowsize = 10
    search_pattern = "a\nb"

    target_patterns = [search_pattern]
    expect_response = self.uut.expect(
        target_patterns,
        timeout=_EXPECT_TIMEOUT,
        searchwindowsize=searchwindowsize)
    self.assertFalse(expect_response.timedout,
                     "Expected any pattern with long receive to not time out")
    self.assertEqual(
        0, expect_response.index,
        "Expected index to be {} found {}".format(0, expect_response.index))
    expected_after = search_pattern + long_receive + "\n"
    self.assertEqual(
        expected_after, expect_response.after,
        "Expected after to be {!r} found {!r}".format(expected_after,
                                                      expect_response.after))

  def test_switchboard_expect_sequential_same_pattern(self):
    """Test switchboard expect sequential mode with same patterns."""
    all_patterns = ["a"] * 24 + ["e", "d", "c", "b", "c", "d", "c", "e", "c"]
    self._setup_expect_test(all_patterns)
    target_patterns = ["a", "b", "c", "d", "c", "e", "c"]

    expect_response = self.uut.expect(
        target_patterns, mode="sequential", timeout=_EXPECT_TIMEOUT)

    self.assertFalse(expect_response.timedout,
                     "Expected sequential pattern to not time out")
    self.assertEqual(
        6, expect_response.index,
        "Expected index to be {} found {}".format(6, expect_response.index))
    err_msg = []
    self.assertTrue(
        self._is_ok_sequential(all_patterns, target_patterns, expect_response,
                               err_msg),
        "Failed expected outcome: {}".format(err_msg))

  def test_switchboard_expect_sequential_similar_patterns(self):
    """Test switchboard expect sequential mode with similar patterns."""
    all_patterns = ["a"] * 24 + ["e", "d", "c", "b", "c", "d", "c", "c"]
    self._setup_expect_test(all_patterns)
    target_patterns = ["a", "b", "c", "d", "c", "e", "c"]

    expect_response = self.uut.expect(
        target_patterns, mode="sequential", timeout=_EXPECT_TIMEOUT)

    self.assertTrue(expect_response.timedout,
                    "Expected sequential pattern to time out")
    self.assertEqual(
        4, expect_response.index,
        "Expected index to be {} found {}".format(4, expect_response.index))
    err_msg = []
    self.assertTrue(
        self._is_ok_sequential(all_patterns, target_patterns, expect_response,
                               err_msg),
        "Failed expected outcome: {}".format(err_msg))

  def test_switchboard_send_and_expect_sends_command(self):
    """Test switchboard send_and_expect method sends command."""
    identifier = line_identifier.AllLogIdentifier()
    self._setup_expect_test(
        ["a"] * 24 + ["e", "d", "c", "b", "c", "d", "e"], identifier=identifier)
    target_patterns = ["e"]
    expect_response = self.uut.send_and_expect(
        _DEVICE_COMMAND,
        target_patterns,
        timeout=_EXPECT_TIMEOUT,
        add_newline=False,
        expect_type="response")
    command = self._get_command(self.fake_transport)
    self.assertEqual(
        _DEVICE_COMMAND, command,
        "Expected command {!r} written to device found {!r}".format(
            _DEVICE_COMMAND, command))
    self.assertTrue(expect_response.timedout,
                    "Expected send_and_expect response to be timedout")
    self.assertEqual(
        0, len(expect_response.before),
        "Expected length of lines shown is {} found {}".format(
            0, len(expect_response.before)))

  def test_switchboard_sent_and_expect_with_raise_for_timeout_set(self):
    """Test send_and_expect with raise_for_timeout=True."""
    identifier = line_identifier.AllLogIdentifier()
    self._setup_expect_test(
        ["a"] * 24 + ["e", "d", "c", "b", "c", "d", "e"], identifier=identifier)
    target_patterns = ["e"]
    with self.assertRaises(errors.DeviceError):
      self.uut.send_and_expect(
          _DEVICE_COMMAND,
          target_patterns,
          timeout=_EXPECT_TIMEOUT,
          add_newline=False,
          raise_for_timeout=True,
          expect_type="response")

  def test_switchboard_click_raises_errors_no_button_list(self):
    """Test switchboard click method raises errors with no button list."""
    self.fake_transport = fake_transport.FakeTransport()
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              [self.fake_transport],
                                              self.log_path)

    with self.assertRaisesRegex(errors.DeviceError,
                                "Buttons are not supported for this device."):
      self.uut.click("button_btn")

  def test_switchboard_click_raises_errors_bad_args(self):
    """Test switchboard click method raises errors with bad arguments."""
    self.fake_transport = fake_transport.FakeTransport()
    buttons = mock.MagicMock(spec=ftdi_buttons.FtdiButtons)
    buttons.valid_buttons.return_value = ["reset_btn", "boot_btn", "button_btn"]
    self.uut = switchboard.SwitchboardDefault(
        "test_device",
        self.exception_queue, [self.fake_transport],
        self.log_path,
        button_list=[buttons])

    # invalid button value (int)
    with self.assertRaisesRegex(errors.DeviceError, "Expecting str for button"):
      self.uut.click(1)

    # invalid button
    buttons.is_valid.return_value = False
    with self.assertRaisesRegex(errors.DeviceError,
                                "Invalid button bogus_btn for port"):
      self.uut.click("bogus_btn")

    # invalid port of None
    with self.assertRaisesRegex(errors.DeviceError, "Invalid port type"):
      self.uut.click("valid_btn", port=None)

    # invalid port of 1
    with self.assertRaisesRegex(errors.DeviceError, "Invalid port number"):
      self.uut.click("valid_btn", port=1)

    # invalid duration of None
    with self.assertRaises(errors.DeviceError):
      self.uut.click("valid_btn", duration=None)

    # invalid duration < 0.0
    with self.assertRaisesRegex(errors.DeviceError, "Invalid duration value"):
      self.uut.click("valid_btn", duration=-0.1)

  def test_switchboard_click_works(self):
    """Test switchboard click method works."""
    self.fake_transport = fake_transport.FakeTransport()
    buttons = mock.MagicMock(spec=ftdi_buttons.FtdiButtons)
    self.uut = switchboard.SwitchboardDefault(
        "test_device",
        self.exception_queue, [self.fake_transport],
        self.log_path,
        button_list=[buttons])

    buttons.is_valid.return_value = True
    self.uut.click("valid_btn")
    initial_filesize = self._wait_for_log_write()
    if len(get_file_lines(self.log_path)) < 2:
      self._wait_for_log_write(initial_filesize=initial_filesize)
    self.uut.close()
    self._verify_log_file_and_lines(2)
    self.assertEqual(
        1, buttons.click.call_count,
        "Expected click count of {} found {}".format(1,
                                                     buttons.click.call_count))
    self.assertEqual(
        1, buttons.close.call_count,
        "Expected close count of {} found {}".format(1,
                                                     buttons.close.call_count))

  def test_switchboard_click_and_expect(self):
    """Test switchboard click_and_expect method finds pattern."""
    buttons = mock.MagicMock(spec=ftdi_buttons.FtdiButtons)
    buttons.is_valid.return_value = True
    self._setup_expect_test(
        ["a", "a", "a", "a", "a", "a", "e", "d", "c", "b", "c", "d", "e"],
        button_list=[buttons])

    target_patterns = ["e"]
    expect_response = self.uut.click_and_expect(
        "valid_btn", target_patterns, timeout=_EXPECT_TIMEOUT)
    self.uut.close()
    self.assertEqual(
        1, buttons.click.call_count,
        "Expected click count of {} found {}".format(1,
                                                     buttons.click.call_count))
    self.assertEqual(
        1, buttons.close.call_count,
        "Expected close count of {} found {}".format(1,
                                                     buttons.close.call_count))
    self.assertFalse(expect_response.timedout,
                     "Expected click_and_expect response to not be timedout")
    self.assertTrue(
        len(expect_response.before),
        "Expected length of lines > 0 found {}".format(
            len(expect_response.before)))

  def test_click_and_expect_raise_for_timeout(self):
    """Verify exception is raised for timeout if raise_for_timeout is True."""
    buttons = mock.MagicMock(spec=ftdi_buttons.FtdiButtons)
    buttons.is_valid.return_value = True
    self._setup_expect_test(["a"], button_list=[buttons])
    target_patterns = ["z"]

    with self.assertRaisesRegex(errors.DeviceError, "timed out after waiting"):
      self.uut.click_and_expect(
          "valid_btn",
          target_patterns,
          timeout=_EXPECT_TIMEOUT,
          raise_for_timeout=True)

  def test_switchboard_press_raises_errors_no_button_list(self):
    """Test switchboard press method raises errors with no button list."""
    self.fake_transport = fake_transport.FakeTransport()
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              [self.fake_transport],
                                              self.log_path)

    with self.assertRaisesRegex(errors.DeviceError,
                                "Buttons are not supported for this device."):
      self.uut.press("button_btn")

  def test_switchboard_press_raises_errors_bad_args(self):
    """Test switchboard press method raises errors with bad arguments."""
    self.fake_transport = fake_transport.FakeTransport()
    buttons = mock.MagicMock(spec=ftdi_buttons.FtdiButtons)
    buttons.valid_buttons.return_value = ["reset_btn", "boot_btn", "button_btn"]
    self.uut = switchboard.SwitchboardDefault(
        "test_device",
        self.exception_queue, [self.fake_transport],
        self.log_path,
        button_list=[buttons])

    # invalid button value (int)
    with self.assertRaisesRegex(errors.DeviceError, "Expecting str for button"):
      self.uut.press(1)

    # invalid button
    buttons.is_valid.return_value = False
    with self.assertRaisesRegex(errors.DeviceError,
                                "Invalid button bogus_btn for port"):
      self.uut.press("bogus_btn")

    # invalid port of None
    with self.assertRaisesRegex(errors.DeviceError, "Invalid port type"):
      self.uut.click("valid_btn", port=None)

    # invalid port of 1
    with self.assertRaisesRegex(errors.DeviceError, "Invalid port number"):
      self.uut.press("valid_btn", port=1)

    # invalid wait of None
    with self.assertRaisesRegex(errors.DeviceError,
                                "Expecting int or float for wait"):
      self.uut.press("valid_btn", wait=None)

    # invalid wait < 0.0
    with self.assertRaisesRegex(errors.DeviceError, "Invalid wait value"):
      self.uut.press("valid_btn", wait=-0.1)

  def test_switchboard_press_works(self):
    """Test switchboard press method works."""
    self.fake_transport = fake_transport.FakeTransport()
    buttons = mock.MagicMock(spec=ftdi_buttons.FtdiButtons)
    self.uut = switchboard.SwitchboardDefault(
        "test_device",
        self.exception_queue, [self.fake_transport],
        self.log_path,
        button_list=[buttons])

    buttons.is_valid.return_value = True
    self.uut.press("valid_btn")
    initial_filesize = self._wait_for_log_write()
    if len(get_file_lines(self.log_path)) < 2:
      self._wait_for_log_write(initial_filesize=initial_filesize)
    self.uut.close()
    self._verify_log_file_and_lines(2)
    self.assertEqual(
        1, buttons.press.call_count,
        "Expected press count of {} found {}".format(1,
                                                     buttons.press.call_count))
    self.assertEqual(
        1, buttons.close.call_count,
        "Expected close count of {} found {}".format(1,
                                                     buttons.close.call_count))

  def test_switchboard_press_and_expect(self):
    """Test switchboard press_and_expect method finds pattern."""
    buttons = mock.MagicMock(spec=ftdi_buttons.FtdiButtons)
    buttons.is_valid.return_value = True

    self._setup_expect_test(
        ["a", "a", "a", "a", "a", "a", "e", "d", "c", "b", "c", "d", "e"],
        button_list=[buttons])
    target_patterns = ["e"]

    expect_response = self.uut.press_and_expect(
        "valid_btn", target_patterns, timeout=_EXPECT_TIMEOUT)
    self.uut.close()
    self.assertEqual(
        1, buttons.press.call_count,
        "Expected press count of {} found {}".format(1,
                                                     buttons.press.call_count))
    self.assertEqual(
        1, buttons.close.call_count,
        "Expected close count of {} found {}".format(1,
                                                     buttons.close.call_count))
    self.assertFalse(expect_response.timedout,
                     "Expected press_and_expect response to not be timedout")
    self.assertTrue(
        len(expect_response.before),
        "Expected length of lines > 0 found {}".format(
            len(expect_response.before)))

  def test_switchboard_release_raises_errors_no_button_list(self):
    """Test switchboard release method raises errors with no button list."""
    self.fake_transport = fake_transport.FakeTransport()
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              [self.fake_transport],
                                              self.log_path)

    with self.assertRaisesRegex(errors.DeviceError,
                                "Buttons are not supported for this device."):
      self.uut.release("button_btn")

  def test_switchboard_release_raises_errors_bad_args(self):
    """Test switchboard release method raises errors with bad arguments."""
    self.fake_transport = fake_transport.FakeTransport()
    buttons = mock.MagicMock(spec=ftdi_buttons.FtdiButtons)
    buttons.valid_buttons.return_value = ["reset_btn", "boot_btn", "button_btn"]
    self.uut = switchboard.SwitchboardDefault(
        "test_device",
        self.exception_queue, [self.fake_transport],
        self.log_path,
        button_list=[buttons])

    # invalid button value (int)
    with self.assertRaisesRegex(errors.DeviceError, "Expecting str for button"):
      self.uut.release(1)

    # invalid button
    buttons.is_valid.return_value = False
    with self.assertRaisesRegex(errors.DeviceError,
                                "Invalid button bogus_btn for port"):
      self.uut.release("bogus_btn")

    # invalid port of None
    with self.assertRaisesRegex(errors.DeviceError, "Invalid port type"):
      self.uut.release("valid_btn", port=None)

    # invalid port of 1
    with self.assertRaisesRegex(errors.DeviceError, "Invalid port number"):
      self.uut.release("valid_btn", port=1)

  def test_switchboard_release_works(self):
    """Test switchboard release method works."""
    self.fake_transport = fake_transport.FakeTransport()
    buttons = mock.MagicMock(spec=ftdi_buttons.FtdiButtons)
    self.uut = switchboard.SwitchboardDefault(
        "test_device",
        self.exception_queue, [self.fake_transport],
        self.log_path,
        button_list=[buttons])

    buttons.is_valid.return_value = True
    self.uut.release("valid_btn")
    self._wait_for_log_write()
    self.uut.close()
    self._verify_log_file_and_lines(1)
    self.assertEqual(
        1, buttons.release.call_count,
        "Expected release count of {} found {}".format(
            1, buttons.release.call_count))
    self.assertEqual(
        1, buttons.close.call_count,
        "Expected close count of {} found {}".format(1,
                                                     buttons.close.call_count))

  def test_switchboard_release_and_expect(self):
    """Test switchboard release_and_expect method finds pattern."""
    buttons = mock.MagicMock(spec=ftdi_buttons.FtdiButtons)
    buttons.is_valid.return_value = True

    self._setup_expect_test(
        ["a", "a", "a", "a", "a", "a", "e", "d", "c", "b", "c", "d", "e"],
        button_list=[buttons])
    target_patterns = ["e"]

    expect_response = self.uut.release_and_expect(
        "valid_btn", target_patterns, timeout=_EXPECT_TIMEOUT)
    self.uut.close()
    self.assertEqual(
        1, buttons.release.call_count,
        "Expected release count of {} found {}".format(
            1, buttons.release.call_count))
    self.assertEqual(
        1, buttons.close.call_count,
        "Expected close count of {} found {}".format(1,
                                                     buttons.close.call_count))
    self.assertFalse(expect_response.timedout,
                     "Expected release_and_expect response to not be timedout")
    self.assertTrue(
        len(expect_response.before),
        "Expected length of lines > 0 found {}".format(
            len(expect_response.before)))

  def test_switchboard_close_transport_raises_error(self):
    """Test switchboard close_transport method raises error for invalid port."""
    self.fake_transport = fake_transport.FakeTransport()
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              [self.fake_transport],
                                              self.log_path)

    # port is None
    with self.assertRaisesRegex(errors.DeviceError, "Invalid port type"):
      self.uut.close_transport(port=None)

    # port is 1
    with self.assertRaisesRegex(errors.DeviceError, "Invalid port number"):
      self.uut.close_transport(port=1)

  def test_switchboard_close_transport_to_default_port(self):
    """Test close_transport method closes transport and logs message."""
    self.fake_transport = fake_transport.FakeTransport()
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              [self.fake_transport],
                                              self.log_path)
    self.uut.close_transport()
    self._wait_for_log_write()
    self._wait_for_transport_write(self.fake_transport)
    lines = self._verify_log_file_and_lines(2)
    self.assertIn("closing transport for port 0", lines[0])
    self.assertIn("closed transport for port 0 in", lines[1])

  def test_switchboard_close_transport_to_specified_port(self):
    """Test close_transport method closes transport and logs message."""
    transport_list = [
        fake_transport.FakeTransport(),
        fake_transport.FakeTransport()
    ]
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              transport_list, self.log_path)
    self.uut.close_transport(port=1)
    self._wait_for_log_write()
    self._wait_for_transport_write(transport_list[1])
    lines = self._verify_log_file_and_lines(2)
    self.assertIn("closing transport for port 1", lines[0])
    self.assertIn("closed transport for port 1 in", lines[1])
    for tst_transport in transport_list:
      tst_transport.close()

  def test_switchboard_close_transport_with_buttons(self):
    """Test close_transport method closes transport and logs message."""
    transport_list = [
        fake_transport.FakeTransport(),
        fake_transport.FakeTransport()
    ]
    buttons = mock.MagicMock(spec=ftdi_buttons.FtdiButtons)
    self.uut = switchboard.SwitchboardDefault(
        "test_device",
        self.exception_queue,
        transport_list,
        self.log_path,
        button_list=[buttons])
    self.uut.close_transport(port=0)
    self._wait_for_log_write()
    self._wait_for_transport_write(transport_list[1])
    lines = self._verify_log_file_and_lines(2)
    self.assertIn("closing transport for port 0", lines[0])
    self.assertIn("closed transport for port 0 in", lines[1])
    for tst_transport in transport_list:
      tst_transport.close()

  def test_switchboard_close_transport_with_buttons_invalid_port(self):
    """Test close_transport method closes transport and logs message."""
    transport_list = [
        fake_transport.FakeTransport(),
        fake_transport.FakeTransport()
    ]
    buttons = mock.MagicMock(spec=ftdi_buttons.FtdiButtons)
    self.uut = switchboard.SwitchboardDefault(
        "test_device",
        self.exception_queue,
        transport_list,
        self.log_path,
        button_list=[buttons])
    self.uut.close_transport(port=1)
    self._wait_for_log_write()
    self._wait_for_transport_write(transport_list[1])
    lines = self._verify_log_file_and_lines(2)
    self.assertIn("closing transport for port 1", lines[0])
    self.assertIn("closed transport for port 1 in", lines[1])
    for tst_transport in transport_list:
      tst_transport.close()

  def test_switchboard_open_transport_raises_error(self):
    """Test switchboard open_transport method raises error for invalid port."""
    self.fake_transport = fake_transport.FakeTransport()
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              [self.fake_transport],
                                              self.log_path)

    # port is None
    with self.assertRaisesRegex(errors.DeviceError, "Invalid port type"):
      self.uut.open_transport(port=None)

    # port is 1
    with self.assertRaisesRegex(errors.DeviceError,
                                r"Invalid port number. Expected: \[0\.\.1\)"):
      self.uut.open_transport(port=1)

  def test_switchboard_open_transport_to_default_port(self):
    """Test open_transport method closes transport and logs message."""
    self.fake_transport = fake_transport.FakeTransport()
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              [self.fake_transport],
                                              self.log_path)
    self.uut.open_transport()
    self._wait_for_log_write()
    self._wait_for_transport_write(self.fake_transport)
    lines = self._verify_log_file_and_lines(2)
    self.assertIn("opening transport for port 0", lines[0])
    self.assertIn("opened transport for port 0 in", lines[1])

  def test_switchboard_open_transport_to_specified_port(self):
    """Test open_transport method opens transport and logs message."""
    transport_list = [
        fake_transport.FakeTransport(),
        fake_transport.FakeTransport()
    ]
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              transport_list, self.log_path)
    self.uut.open_transport(port=1)
    self._wait_for_log_write()
    self._wait_for_transport_write(transport_list[1])
    lines = self._verify_log_file_and_lines(2)
    self.assertTrue("opening transport for port 1", lines[0])
    self.assertTrue("opened transport for port 1 in", lines[1])
    for tst_transport in transport_list:
      tst_transport.close()

  def test_close_all_transports_works_with_health_check(self):
    """Ensure device closes all transport lists."""
    transport_list = [
        fake_transport.FakeTransport(),
        fake_transport.FakeTransport()
    ]
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              transport_list, self.log_path)
    self.uut.health_check()

    with mock.patch.object(self.uut, "close_transport") as mock_close:
      self.uut.close_all_transports()

      self.assertEqual(mock_close.call_count, 2,
                       "close transports should have been called twice.")

  def test_close_all_transports_works_without_health_check(self):
    """Ensure device closes all transport lists."""
    transport_list = [
        fake_transport.FakeTransport(),
        fake_transport.FakeTransport()
    ]
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              transport_list, self.log_path)

    with mock.patch.object(self.uut, "close_transport") as mock_close:
      self.uut.close_all_transports()
      mock_close.assert_not_called()

  def test_open_all_transports_works(self):
    """Ensure device opens all transports."""
    transport_list = [
        fake_transport.FakeTransport(),
        fake_transport.FakeTransport()
    ]
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              transport_list, self.log_path)
    with mock.patch.object(self.uut, "open_transport") as mock_open:
      self.uut.open_all_transports()
      self.assertEqual(mock_open.call_count, 2,
                       "open transports should have been called twice.")

  def test_switchboard_xmodem_file_to_transport_raises_errors(self):
    """Test switchboard xmodem_file_to_transport method raises errors."""
    if "linux" not in sys.platform:
      self.skipTest("Doesn't work on mac")
    self.fake_transport = fake_transport.FakeTransport()
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              [self.fake_transport],
                                              self.log_path)

    source_file = os.path.join(self.artifacts_directory,
                               self._testMethodName + ".json")

    # source_file doesn't exist
    with self.assertRaisesRegex(errors.DeviceError, "doesn't exist"):
      self.uut.xmodem_file_to_transport(source_file)

    # Create source_file for remaining tests
    open(source_file, "w").close()

    # port is None
    with self.assertRaisesRegex(errors.DeviceError, "Invalid port type"):
      self.uut.xmodem_file_to_transport(source_file, port=None)

    # port is 1
    with self.assertRaisesRegex(errors.DeviceError,
                                r"Invalid port number. Expected: \[0\.\.1\)"):
      self.uut.xmodem_file_to_transport(source_file, port=1)

    # source_file exists but only root can access it
    bad_source_file = "/dev/console"
    with self.assertRaisesRegex(errors.DeviceError,
                                "Unable to open source file"):
      self.uut.xmodem_file_to_transport(bad_source_file)

  def test_switchboard_xmodem_file_to_transport_works(self):
    """Test switchboard xmodem_file_to_transport method can send file."""
    process = subprocess.Popen(["which", "rb"], stdout=subprocess.PIPE)
    output, _ = process.communicate()
    rb_path = output.strip(b"\n")
    if not rb_path or not os.path.exists(rb_path):
      self.skipTest(
          "The lrzsz package is missing or the rb executable is unavailable. "
          "Unable to test xmodem file send")

    source_file = os.path.join(self.artifacts_directory,
                               self._testMethodName + ".out")
    destination_file = os.path.join(self.artifacts_directory,
                                    self._testMethodName + ".in")

    # Create output source_file with binary contents to send
    with open(source_file, "wb") as out_file:
      for i in range(0x00, 0xFF + 1):
        out_file.write(bytes([i]))

    primary, secondary = pty.openpty()

    # Work around FD check since openpty causes
    # a new shared library to be loaded
    self.starting_fds = self.get_open_fds()

    self.fake_transport = serial_transport.SerialTransport(
        os.ttyname(secondary))
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              [self.fake_transport],
                                              self.log_path)
    proc = subprocess.Popen((rb_path, "--xmodem", "--verbose",
                             "--delay-startup", "1", destination_file),
                            stdin=primary,
                            stdout=primary,
                            stderr=subprocess.PIPE,
                            bufsize=0)
    try:
      self.uut.xmodem_file_to_transport(source_file)
    finally:
      proc.wait()
      os.close(primary)
      os.close(secondary)
      self.assertEqual(
          0, proc.returncode,
          "Expected rb (xmodem receive) return code 0 found {}".format(
              proc.returncode))
    self._verify_files(source_file, destination_file)

  def test_switchboard_echo_file_to_transport_raises_errors(self):
    """Test switchboard echo_file_to_transport method raises errors."""
    if "linux" not in sys.platform:
      self.skipTest("Doesn't work on mac")
    self.fake_transport = fake_transport.FakeTransport()
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              [self.fake_transport],
                                              self.log_path)

    source_file = os.path.join(self.artifacts_directory,
                               self._testMethodName + ".json")
    destination_path = os.path.join("/some/path",
                                    self._testMethodName + ".json")

    # source_file doesn't exist
    with self.assertRaisesRegex(errors.DeviceError, "doesn't exist"):
      self.uut.echo_file_to_transport(source_file, destination_path)

    # Create source_file for remaining tests
    open(source_file, "w").close()

    # port is None
    with self.assertRaisesRegex(errors.DeviceError, "Invalid port type"):
      self.uut.echo_file_to_transport(source_file, destination_path, port=None)

    # port is 1
    with self.assertRaisesRegex(errors.DeviceError,
                                r"Invalid port number. Expected: \[0\.\.1\)"):
      self.uut.echo_file_to_transport(source_file, destination_path, port=1)

    # bytes_per_echo is None
    with self.assertRaisesRegex(errors.DeviceError, "int for bytes_per_echo"):
      self.uut.echo_file_to_transport(
          source_file, destination_path, bytes_per_echo=None)

    # bytes_per_echo is -1
    with self.assertRaisesRegex(errors.DeviceError, "expected >0"):
      self.uut.echo_file_to_transport(
          source_file, destination_path, bytes_per_echo=-1)

    # bytes_per_echo is 0
    with self.assertRaisesRegex(errors.DeviceError, "expected >0"):
      self.uut.echo_file_to_transport(
          source_file, destination_path, bytes_per_echo=0)

    # source_file exists but only root can access it
    bad_source_file = "/dev/console"
    with self.assertRaisesRegex(errors.DeviceError, "Permission denied"):
      self.uut.echo_file_to_transport(bad_source_file, destination_path)

  def test_switchboard_echo_file_to_transport_one_byte(self):
    """Test echo_file_to_transport method can send file one byte at a time."""
    source_file = os.path.join(self.artifacts_directory,
                               self._testMethodName + ".json")
    source_data = b"The quick brown fox jumps over lazy dogs."

    # Create source_file
    with open(source_file, "wb") as out_file:
      out_file.write(source_data)

    self.fake_transport = fake_transport.FakeTransport(
        write_read_func=_write_read_for_echo_file_to_transport)
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              [self.fake_transport],
                                              self.log_path)

    bytes_per_echo = 1
    self.uut.echo_file_to_transport(
        source_file, _FILE_ON_TRANSPORT_PATH, bytes_per_echo=bytes_per_echo)
    command1 = self._get_command(self.fake_transport)
    self.assertEqual(
        "echo -ne > " + _FILE_ON_TRANSPORT_PATH + "\n", command1,
        "Expected 'echo -ne > /some/path/...' found {}".format(command1))

    count = 0
    command_n = self._get_command(self.fake_transport)
    expected_count = len(source_data) // bytes_per_echo
    while count < expected_count:
      self.assertIn("echo -ne \"\\x", command_n)
      count += 1
      command_n = self._get_command(self.fake_transport)
    self.assertEqual(
        expected_count, count,
        "Expected {} echo commands found {} commands".format(
            expected_count, count))
    remaining_commands = get_queue_size(self.fake_transport.writes)
    self.assertFalse(
        remaining_commands,
        f"Expected no more commands but found {remaining_commands} more "
        "commands")

  def test_switchboard_verify_file_on_transport_raises_errors(self):
    """Test switchboard verify_file_on_transport method raises errors."""
    if "linux" not in sys.platform:
      self.skipTest("Doesn't work on mac")
    self.fake_transport = fake_transport.FakeTransport()
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              [self.fake_transport],
                                              self.log_path)

    source_file = os.path.join(self.artifacts_directory,
                               self._testMethodName + ".json")
    destination_path = os.path.join("/some/path",
                                    self._testMethodName + ".json")

    # source_file doesn't exist
    with self.assertRaisesRegex(errors.DeviceError, "doesn't exist"):
      self.uut.verify_file_on_transport(source_file, destination_path)

    # Create source_file for remaining tests
    open(source_file, "w").close()

    # port is None
    with self.assertRaisesRegex(errors.DeviceError, "Invalid port type"):
      self.uut.verify_file_on_transport(
          source_file, destination_path, port=None)

    # port is 1
    with self.assertRaisesRegex(errors.DeviceError,
                                r"Invalid port number. Expected: \[0\.\.1\)"):
      self.uut.verify_file_on_transport(source_file, destination_path, port=1)

    # method is None
    with self.assertRaisesRegex(errors.DeviceError, "string for method"):
      self.uut.verify_file_on_transport(
          source_file, destination_path, method=None)

    # method is "bogus"
    with self.assertRaisesRegex(errors.DeviceError, "Unknown method value"):
      self.uut.verify_file_on_transport(
          source_file, destination_path, method="bogus")

    # source_file exists but only root can access it
    bad_source_file = "/dev/console"
    with self.assertRaisesRegex(errors.DeviceError,
                                "Unable to retrieve md5sum of"):
      self.uut.verify_file_on_transport(bad_source_file, destination_path)

  def test_switchboard_verify_file_on_transport_fails(self):
    """Test switchboard verify_file_on_transport method fails checksum."""
    if "linux" not in sys.platform:
      self.skipTest("Doesn't work on mac")
    source_file = os.path.join(self.artifacts_directory,
                               self._testMethodName + ".json")
    source_data = b"The quick brown fox jumps over lazy dogs."

    # Create source_file
    with open(source_file, "wb") as out_file:
      out_file.write(source_data)

    self.fake_transport = fake_transport.FakeTransport(
        write_read_func=_write_read_for_verify_file_on_transport_bad_checksum)
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              [self.fake_transport],
                                              self.log_path)

    result = self.uut.verify_file_on_transport(source_file,
                                               _FILE_ON_TRANSPORT_PATH)
    self.assertFalse(result,
                     "Expected verify file on transport to return False")
    command = self._get_command(self.fake_transport)
    self.assertEqual("md5sum " + _FILE_ON_TRANSPORT_PATH + "\n", command,
                     "Expected 'md5sum ...' found {}".format(command))
    self.assertTrue(
        self.fake_transport.writes.empty(),
        "Expected no more commands but found {} more commands".format(
            get_queue_size(self.fake_transport.writes)))

  def test_switchboard_verify_file_on_transport_missing(self):
    """Test verify_file_on_transport method fails on missing file."""
    source_file = os.path.join(self.artifacts_directory,
                               self._testMethodName + ".json")
    source_data = b"The quick brown fox jumps over lazy dogs."

    # Create source_file
    with open(source_file, "wb") as out_file:
      out_file.write(source_data)

    self.fake_transport = fake_transport.FakeTransport(
        write_read_func=_write_read_for_verify_file_on_transport_missing_file)
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              [self.fake_transport],
                                              self.log_path)

    result = self.uut.verify_file_on_transport(source_file,
                                               _FILE_ON_TRANSPORT_PATH)
    self.assertFalse(result,
                     "Expected verify file on transport to return False")
    command = self._get_command(self.fake_transport)
    self.assertEqual("md5sum " + _FILE_ON_TRANSPORT_PATH + "\n", command,
                     "Expected 'md5sum ...' found {}".format(command))
    self.assertTrue(
        self.fake_transport.writes.empty(),
        "Expected no more commands but found {} more commands".format(
            get_queue_size(self.fake_transport.writes)))

  def test_switchboard_verify_file_on_transport_success(self):
    """Test switchboard verify_file_on_transport method succeeds."""
    if "linux" not in sys.platform:
      self.skipTest("Doesn't work on mac")
    source_file = os.path.join(self.artifacts_directory,
                               self._testMethodName + ".json")
    source_data = b"The quick brown fox jumps over lazy dogs."

    # Create source_file
    with open(source_file, "wb") as out_file:
      out_file.write(source_data)

    self.fake_transport = fake_transport.FakeTransport(
        write_read_func=_write_read_for_verify_file_on_transport_good_checksum)
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              [self.fake_transport],
                                              self.log_path)

    result = self.uut.verify_file_on_transport(source_file,
                                               _FILE_ON_TRANSPORT_PATH)
    self.assertTrue(result, "Expected verify file on transport to return True")
    command = self._get_command(self.fake_transport)
    self.assertEqual("md5sum " + _FILE_ON_TRANSPORT_PATH + "\n", command,
                     "Expected 'md5sum ...' found {}".format(command))
    self.assertTrue(
        self.fake_transport.writes.empty(),
        "Expected no more commands but found {} more commands".format(
            get_queue_size(self.fake_transport.writes)))

  def test_switchboard_add_new_filter_raises_error(self):
    """Test add_new_filter if given bad path or without _log_filter_process."""
    transport_list = []
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              transport_list, self.log_path)

    # Invalid path passed to add_new_filter
    err_regex = "ValueError: Filter path bogus_path doesn't exist."
    with self.assertRaisesRegex(errors.DeviceError, err_regex):
      self.uut.add_new_filter("bogus_path")
    self.uut.close()

    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              transport_list, self.log_path,
                                              parser=None)
    # The _log_filter_process is no longer running.
    err_regex = "Log filter process is not currently running"
    with self.assertRaisesRegex(errors.DeviceError, err_regex):
      filter_file = os.path.join(self.TEST_FILTER_DIR,
                                 "optional_description.json")
      self.uut.add_new_filter(filter_file)

  def test_switchboard_add_new_filter_successful(self):
    """Verifies add_new_filter completes successfully."""
    transport_list = []
    device_type = "test_device"
    event_file_path = "{}-{}".format(
        self.log_path.split(".txt")[0], "events.txt")
    filter_list = []
    parser_obj = event_parser_default.EventParserDefault(
        filters=filter_list,
        event_file_path="/foo.txt",
        device_name="device-1234")
    self.uut = switchboard.SwitchboardDefault(
        device_type,
        self.exception_queue,
        transport_list,
        self.log_path,
        parser=parser_obj)
    new_filter_file = os.path.join(self.TEST_FILTER_DIR, "add_this_filter.json")
    self.uut.add_new_filter(new_filter_file)
    max_log_size = 0  # No log rotation
    self.uut.set_max_log_size(max_log_size)
    initial_filesize = self._wait_for_log_write()
    self.uut.add_log_note(_LOG_MESSAGE)
    if len(get_file_lines(self.log_path)) < 2:
      self._wait_for_log_write(initial_filesize=initial_filesize)

    file_creation_timeout = 5
    try:
      retry.retry(
          os.path.exists, (event_file_path,),
          is_successful=bool,
          timeout=file_creation_timeout,
          interval=0.1)
    except errors.CommunicationTimeoutError:
      self.fail("Event file {} wasn't created within {} seconds.".format(
          event_file_path, file_creation_timeout))

  @mock.patch.object(os, "kill")
  @mock.patch.object(
      subprocess,
      "check_output",
      side_effect=iter([
          subprocess.CalledProcessError(1, "lsof /foo/bar",
                                        b"No such file or directory"),
          (b"COMMAND  PID     USER   FD   TYPE DEVICE SIZE/OFF   NODE NAME\n"
           b"gdm     4093 someuser   10uW  CHR 188,16      0t0 541701 /dev/serial/"
           b"by-id/../../ttyUSB16"),
          (b"lsof: Warning: can't start() tracefs file"
           b"   Output information may be incomplete."
           b"COMMAND  PID     USER   FD   TYPE DEVICE SIZE/OFF   NODE NAME\n"
           b"gdm     4093 someuser   10uW  CHR 188,16      0t0 541701 /dev/serial/"
           b"by-id/../../ttyUSB16")
      ]))
  def test_ensure_communication_unlocked(self, mock_output, mock_kill):
    """Test device can close even when console_port_name exists but unlocked."""
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue, [],
                                              self.log_path)
    self.uut.close()

    # Serial path already closed
    usb_utils.get_all_serial_connections.return_value = ["/foo/bar"]
    self.uut.ensure_serial_paths_unlocked(["/foo/bar"])
    mock_kill.assert_not_called()

    # Not a serial path
    self.uut.ensure_serial_paths_unlocked(["123.45.67.89"])
    mock_kill.assert_not_called()

    # Serial path that hasn't been closed yet
    usb_utils.get_all_serial_connections.return_value = ["/dev/serial/by-id/1"]
    self.uut.ensure_serial_paths_unlocked(["/dev/serial/by-id/1"])
    mock_kill.assert_called_once_with(4093, signal.SIGTERM)

  def test_call_success(self):
    """Test a successful Switchboard.call() transport method call."""
    self.fake_transport = fake_transport.FakeTransport()
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              [self.fake_transport],
                                              self.log_path)
    self.assertEqual(
        self.uut.call(
            fake_transport.FakeTransport.test_method.__name__,
            method_args=(False,)),
        "Some return")

  def test_call_error(self):
    """Test a Switchboard.call() transport method call which raises an error."""
    self.fake_transport = fake_transport.FakeTransport()
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              [self.fake_transport],
                                              self.log_path)
    full_regex = (  # (?s) sets re.DOTALL flag.
        r"(?s)test_device Switchboard\.call of method "
        r"FakeTransport\.test_method in transport 0 failed\. Traceback.*"
        r"RuntimeError: Something failed")
    with self.assertRaisesRegex(errors.DeviceError, full_regex):
      self.uut.call(
          fake_transport.FakeTransport.test_method.__name__,
          method_kwargs={"raise_error": True})

  def test_call_error_transport_doesnt_have_requested_method(self):
    """Test a Switchboard.call() when transport doesn't have the method."""
    self.fake_transport = fake_transport.FakeTransport()
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue,
                                              [self.fake_transport],
                                              self.log_path)
    regex = (
        r"Transport 0 \('FakeTransport'\) does not have method 'flush_buffers'")
    with self.assertRaisesRegex(AttributeError, regex):
      self.uut.call(serial_transport.SerialTransport.flush_buffers.__name__)

  @mock.patch.object(switchboard.SwitchboardDefault, "_start_processes")
  @mock.patch.object(switchboard.SwitchboardDefault, "close")
  def test_transport_serial_set_baudrate(
      self, mock_close, mock_start_processes):
    """Tests transport_serial_set_baudrate()."""
    self.uut = switchboard.SwitchboardDefault(
        "test_device",
        self.exception_queue,
        [serial_transport.SerialTransport("/dev/serial/by-id/some_path")],
        self.log_path)
    with mock.patch.object(
        self.uut, "call", autospec=True) as mock_switchboard_call:
      self.uut.transport_serial_set_baudrate(115200)
    mock_switchboard_call.assert_has_calls([
        mock.call(
            method_name=serial_transport.SerialTransport.flush_buffers.__name__,
            port=0),
        mock.call(
            method_name=serial_transport.SerialTransport.set_property.__name__,
            method_args=(transport_properties.BAUDRATE, 115200),
            port=0),
        mock.call(
            method_name=serial_transport.SerialTransport.flush_buffers.__name__,
            port=0),
    ])

  @mock.patch.object(switchboard.SwitchboardDefault, "_start_processes")
  @mock.patch.object(switchboard.SwitchboardDefault, "close")
  def test_transport_serial_send_xon(self, mock_close, mock_start_processes):
    """Tests transport_serial_send_xon()."""
    self.uut = switchboard.SwitchboardDefault(
        "test_device",
        self.exception_queue,
        [serial_transport.SerialTransport("/dev/serial/by-id/some_path")],
        self.log_path)
    with mock.patch.object(
        self.uut, "call", autospec=True) as mock_switchboard_call:
      self.uut.transport_serial_send_xon()
    mock_switchboard_call.assert_called_once_with(
        method_name=serial_transport.SerialTransport.send_xon.__name__,
        port=0)

  @mock.patch.object(switchboard.SwitchboardDefault, "_start_processes")
  @mock.patch.object(switchboard.SwitchboardDefault, "close")
  def transport_serial_send_break_byte(self, mock_close, mock_start_processes):
    """Tests transport_serial_send_break_byte()."""
    self.uut = switchboard.SwitchboardDefault(
        "test_device",
        self.exception_queue,
        [serial_transport.SerialTransport("/dev/serial/by-id/some_path")],
        self.log_path)
    with mock.patch.object(
        self.uut, "call", autospec=True) as mock_switchboard_call:
      self.uut.transport_serial_send_break_byte()
    mock_switchboard_call.assert_called_once_with(
        method_name=serial_transport.SerialTransport.send_break_byte.__name__,
        port=0)

  def test_delete_last_transport_process_no_transports(self):
    """Test deleting last transport process with no transports."""
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue, [],
                                              self.log_path)
    with self.assertRaisesRegex(errors.DeviceError, "no transport processes"):
      self.uut.delete_last_transport_process()

  def test_delete_last_transport_process_process_not_stopped(self):
    """Test process.stop() is called before deletion if transport is running."""
    mock_transport = mock.Mock()
    mock_transport.is_started.return_value = True
    mock_transport_process_list = [mock_transport]
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue, [],
                                              self.log_path)
    self.uut._transport_processes_cache = mock_transport_process_list
    self.uut.delete_last_transport_process()
    mock_transport.stop.assert_called_once()
    self.assertFalse(
        mock_transport_process_list,
        "Expected transport list to be empty after deleting the last process, "
        "found {}.".format(mock_transport_process_list))

  def test_delete_last_transport_process_process_already_stopped(self):
    """Verify process.stop() is not called when transport is already stopped."""
    mock_transport_should_not_be_touched = mock.Mock()
    mock_transport_should_not_be_touched.is_started.side_effect = RuntimeError(
        "is_started() should not have been called for this process.")
    mock_transport = mock.Mock()
    mock_transport.is_started.return_value = False
    mock_transport_process_list = [
        mock_transport_should_not_be_touched, mock_transport
    ]
    self.uut = switchboard.SwitchboardDefault("test_device",
                                              self.exception_queue, [],
                                              self.log_path)
    self.uut.health_check()
    self.uut._transport_processes_cache = mock_transport_process_list
    self.uut.delete_last_transport_process()
    mock_transport.stop.assert_not_called()
    self.assertEqual(mock_transport_process_list,
                     [mock_transport_should_not_be_touched])
    self.uut._transport_processes_cache = [
    ]  # Remove the error-raising transport from the list

  def test_switchboard_call_and_expect(self):
    """Test switchboard call_and_expect method."""
    self._setup_expect_test(["a"] * 24 + ["e", "d", "c", "b", "c", "d", "e"])
    target_patterns = ["e"]
    expect_response, func_response = self.uut.call_and_expect(
        method_name=fake_transport.FakeTransport.test_method.__name__,
        pattern_list=target_patterns,
        timeout=_EXPECT_TIMEOUT,
        method_args=(False,))
    self.assertFalse(expect_response.timedout)
    self.assertEqual(func_response, "Some return")

  def test_switchboard_call_and_expect_timeout(self):
    """Test switchboard call_and_expect timeout failure."""
    self._setup_expect_test(["a"])
    full_regex = r"call_and_expect timed out for method test_method"
    with self.assertRaisesRegex(errors.DeviceError, full_regex):
      self.uut.call_and_expect(
          method_name=fake_transport.FakeTransport.test_method.__name__,
          pattern_list=["b"],
          timeout=_EXPECT_TIMEOUT,
          method_args=(False,),
          raise_for_timeout=True)

  def test_switchboard_call_and_expect_error(self):
    """Test switchboard call_and_expect unexpected failure."""
    self._setup_expect_test(["a"])
    full_regex = r"RuntimeError: Something failed"
    with self.assertRaisesRegex(errors.DeviceError, full_regex):
      self.uut.call_and_expect(
          method_name=fake_transport.FakeTransport.test_method.__name__,
          pattern_list=["a"],
          timeout=_EXPECT_TIMEOUT,
          method_kwargs={"raise_error": True})

  def test_start_processes_terminates_processes_on_failure(self):
    """Tests _start_processes terminates processes on process start failure."""
    self.uut = switchboard.SwitchboardDefault("device-1234",
                                              self.exception_queue, [],
                                              self.log_path)
    self.uut._transport_processes_cache = [
        mock.MagicMock(spec=transport_process.TransportProcess),
        mock.MagicMock(spec=transport_process.TransportProcess)
    ]
    self.uut._log_writer_process_cache = mock.MagicMock(
        spec=log_process.LogWriterProcess)
    self.uut._log_filter_process_cache = mock.MagicMock(
        spec=log_process.LogFilterProcess)
    process_mocks = self.uut._transport_processes_cache + [
        self.uut._log_writer_process_cache, self.uut._log_filter_process_cache
    ]
    for process_mock in process_mocks:
      process_mock.is_started.return_value = False
    self.uut._transport_processes_cache[
        0].wait_for_start.side_effect = RuntimeError(
            "failed to start child process. Start event was not set")

    with self.assertRaisesRegex(
        RuntimeError, "failed to start child process.*Start event was not set"):
      self.uut._start_processes()

    for process_mock in process_mocks:
      process_mock.start.assert_called_once_with(wait_for_start=False)
      process_mock.terminate.assert_called_once()
    self.uut._transport_processes_cache = []

  def _generate_fake_transport_reads(self, patterns):
    """Generate FakeTransport's read responses.

    Args:
        patterns (list): list of strings.
    """
    for pattern in patterns:
      self.fake_transport.reads.put((pattern + "\n").encode())

  def _get_command(self, transport):
    """Returns last message sent to fake transport."""
    command = ""
    while not command or command[-1] != "\n":
      try:
        command += transport.writes.get(timeout=_DEVICE_WRITE_TIMEOUT)
      except queue.Empty:
        break
    return command

  def _is_ok_any_all(self, all_patterns, target_patterns, expect_response,
                     err_msg):
    """Given expect modes "any" or "all", verifies expect_response is correct.

    Args:
        all_patterns (list): List of all patterns given to switchboard
        target_patterns (list): List of patterns switchboard should find
        expect_response (obj): Results of switchboard _expect_loop processing
        err_msg (list): Error message describing expected vs. actual results

    Returns:
        bool: expect_response holds correct, expected outcome.
    """

    all_set = set(all_patterns)
    target_set = set(target_patterns)
    calc_match_set = target_set.intersection(all_set)
    calc_remaining_set = target_set - all_set
    is_ok_remaining = calc_remaining_set == set(expect_response.remaining)
    msg_remaining = ("Expected remaining: {}  Actual remaining: {}".format(
        list(calc_remaining_set), expect_response.remaining))
    if not is_ok_remaining:
      err_msg.append(msg_remaining)

    pattern_list = []
    for match_obj in expect_response.match_list:
      pattern_list.append(match_obj.group(0))

    is_ok_match = calc_match_set == set(pattern_list)
    msg_match = ("Expected match: {}  Actual match: {}".format(
        list(calc_match_set), pattern_list))
    if not is_ok_match:
      err_msg.append(msg_match)

    return is_ok_remaining and is_ok_match

  def _is_ok_sequential(self, master_sequence, target_sequence, expect_response,
                        err_msg):
    """Given expect mode "sequential", verifies expect_response is correct.

    Args:
        master_sequence (list): List of patterns that may be sequential.
        target_sequence (list): List of patterns defined as sequential.
        expect_response (obj): Results of switchboard _expect_loop_sequential
          processing
        err_msg (list): Error message describing expected vs. actual results

    Returns:
        bool: expect_response holds correct, expected outcome.
    """

    # Determine where target_sequence begins matching master sequence.
    expected_index = None
    target_index = 0
    expected_match_list = []
    for _, pattern in enumerate(master_sequence):
      if pattern == target_sequence[target_index]:
        expected_index = target_index
        expected_match_list.append(target_sequence[target_index])
        target_index += 1
    expected_remaining = target_sequence[target_index:]

    is_ok_index = expected_index == expect_response.index
    if not is_ok_index:
      msg_index = ("Expected index: {} Actual index: {}".format(
          expected_index, expect_response.index))
      err_msg.append(msg_index)

    is_ok_remaining = not set(expected_remaining) ^ set(
        expect_response.remaining)
    if not is_ok_remaining:
      msg_remaining = ("Expected remaining: {} Actual remaining: {}".format(
          expected_remaining, expect_response.remaining))
      err_msg.append(msg_remaining)

    actual_match_list = [m.re.pattern for m in expect_response.match_list]
    is_ok_match_list = not set(expected_match_list) ^ set(actual_match_list)
    if not is_ok_match_list:
      msg_match_list = ("Expected match_list: {} Actual match_list: {}".format(
          expected_match_list, actual_match_list))
      err_msg.append(msg_match_list)

    if expect_response.match:
      is_ok_match = expect_response.match == expect_response.match_list[-1]
      if not is_ok_match:
        msg_match = ("Expected match in {} Found {}".format(
            actual_match_list, expect_response.match.re.pattern))
        err_msg.append(msg_match)
    else:
      is_ok_match = expect_response.match is None
      if not is_ok_match:
        msg_match = ("Expected match to be None Actual {}".format(
            expect_response.match))
        err_msg.append(msg_match)
    return is_ok_index and is_ok_remaining and is_ok_match_list and is_ok_match

  def _setup_expect_test(self, patterns=None, **kwargs):
    """Set up the switchboard for a test involving expect().

    Args:
        patterns (list): list of patterns (strings) which will be returned by
          FakeTransport.
        **kwargs (dict): extra keyword argument to Switchboard __init__.
    Note: This setup will only read from the FakeTransport when the raw data
      queue is enabled. This allows to avoid race conditions.
    """
    if patterns is None:
      patterns = _DEFAULT_FAKE_TRANSPORT_READS

    self.fake_transport = fake_transport.FakeTransport(
        read_only_if_raw_data_queue_enabled=True)

    # Important: it's only possible to bind raw_data_enabled method in
    # FakeTransport before transport process is started.
    with mock.patch.object(switchboard.SwitchboardDefault, "_start_processes"):
      self.uut = switchboard.SwitchboardDefault("test_device",
                                                self.exception_queue,
                                                [self.fake_transport],
                                                self.log_path, **kwargs)
      self.uut.health_check()
    self.fake_transport.bind_raw_data_enabled_method(
        self.uut._transport_processes_cache[0])
    self.uut._start_processes()

    self._generate_fake_transport_reads(patterns)

  def _verify_files(self, source_file, destination_file):
    with open(source_file, "rb") as orig_file:
      orig_data = orig_file.read()
    with open(destination_file, "rb") as new_file:
      new_data = new_file.read()
    self.assertEqual(
        orig_data, new_data,
        "Expected data {!r} to match data {!r}".format(orig_data, new_data))

  def _wait_for_log_write(self,
                          initial_filesize=0,
                          get_size=False,
                          log_path=None):
    if log_path is None:
      my_log_path = self.log_path
    else:
      my_log_path = log_path
    if get_size:
      filesize = os.path.getsize(my_log_path)
    else:
      filesize = initial_filesize
    newsize = get_file_size(my_log_path, size=filesize)
    self.assertGreater(
        newsize, filesize,
        "Expected {} file size {} > {}".format(my_log_path, newsize, filesize))
    return newsize

  def _wait_for_transport_write(self, transport, timeout=_DEVICE_WRITE_TIMEOUT):
    end_time = time.time() + timeout
    while transport.writes.empty() and time.time() < end_time:
      time.sleep(0.001)

  def _verify_log_file_and_lines(self, count, log_path=None):
    if log_path is None:
      my_log_path = self.log_path
    else:
      my_log_path = log_path
    filesize = os.path.getsize(my_log_path)
    self.assertGreater(
        filesize, 0,
        "Expected {} file size > 0 found {}".format(my_log_path, filesize))
    lines = get_file_lines(my_log_path)
    self.assertEqual(
        count, len(lines),
        "Expected {} log line(s) in {} found {}".format(count, my_log_path,
                                                        len(lines)))
    return lines


if __name__ == "__main__":
  unit_test_case.main()
