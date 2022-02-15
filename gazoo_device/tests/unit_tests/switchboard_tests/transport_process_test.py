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

"""Tests the transport_process.py module."""
import time
import unittest
from unittest import mock

from gazoo_device.switchboard import data_framer
from gazoo_device.switchboard import switchboard_process
from gazoo_device.switchboard import transport_process
from gazoo_device.switchboard import transport_properties
from gazoo_device.tests.unit_tests.utils import fake_transport
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import multiprocessing_utils

_EXCEPTION_TIMEOUT = 3
_LOG_MESSAGE_TIMEOUT = 1

get_queue_size = unit_test_case.get_queue_size
wait_for_queue_writes = switchboard_process.wait_for_queue_writes


class TransportProcessTests(unit_test_case.MultiprocessingTestCase):

  def setUp(self):
    super().setUp()

    self.command_queue = multiprocessing_utils.get_context().Queue()
    self.log_queue = multiprocessing_utils.get_context().Queue()
    self.raw_data_queue = multiprocessing_utils.get_context().Queue()
    self.call_result_queue = multiprocessing_utils.get_context().Queue()

  def tearDown(self):
    if hasattr(self, "uut"):
      del self.uut
    # Release shared memory file descriptors used by queues.
    del self.command_queue
    del self.log_queue
    del self.raw_data_queue
    del self.call_result_queue
    super().tearDown()

  def test_000_transport_construct_destruct(self):
    """Test TransportProcess constructing and destructing raises no errors."""
    transport = None
    self.uut = transport_process.TransportProcess(
        "fake_transport",
        self.exception_queue,
        self.command_queue,
        self.log_queue,
        transport,
        call_result_queue=self.call_result_queue)
    self.assertFalse(self.uut.is_started(),
                     "Expected process not started, found started")
    self.assertFalse(self.uut.is_running(),
                     "Expected process to not running, found running")

  def test_001_transport_enqueue_command_writes_below_split(self):
    """Test _enqueue_command_writes can split commands below max write limit."""
    write_queue = multiprocessing_utils.get_context().Queue()
    command = "short command"
    transport_process._enqueue_command_writes(write_queue, command)
    wait_for_queue_writes(write_queue)
    self._verify_command_split(command, write_queue)

  def test_002_transport_enqueue_command_writes_above_split(self):
    """Test _enqueue_command_writes splits commands below max write limit."""
    write_queue = multiprocessing_utils.get_context().Queue()
    command = ("this will be a really long command that exceeds the 32 byte "
               "limit")
    transport_process._enqueue_command_writes(write_queue, command)
    wait_for_queue_writes(write_queue)
    self._verify_command_split(command, write_queue)

  def test_100_transport_accepts_valid_transport_commands(self):
    """Test send_command accepts valid transport commands."""
    transport = None
    self.uut = transport_process.TransportProcess(
        "fake_transport",
        self.exception_queue,
        self.command_queue,
        self.log_queue,
        transport,
        call_result_queue=self.call_result_queue)
    for command in transport_process._ALL_VALID_COMMANDS:
      self.uut.send_command(command)
      wait_for_queue_writes(self.command_queue)
      self.assertFalse(self.command_queue.empty(),
                       "Expected command queue to not be empty")
      command_message = self.command_queue.get()
      self.assertEqual(
          command, command_message[0],
          "Expected command {} found {}".format(command, command_message[0]))

  def test_110_transport_toggle_raw_data_raises_error(self):
    """Test toggle_raw_data raises error."""
    transport = None
    self.uut = transport_process.TransportProcess(
        "fake_transport",
        self.exception_queue,
        self.command_queue,
        self.log_queue,
        transport,
        call_result_queue=self.call_result_queue)
    with self.assertRaisesRegex(RuntimeError, r"No queue provided"):
      self.uut.toggle_raw_data()

  def test_111_transport_toggle_raw_data_toggles(self):
    """Test toggle_raw_data toggles raw_data_enable."""
    transport = None
    self.uut = transport_process.TransportProcess(
        "fake_transport",
        self.exception_queue,
        self.command_queue,
        self.log_queue,
        transport,
        call_result_queue=self.call_result_queue,
        raw_data_queue=self.raw_data_queue)
    self.assertFalse(self.uut.raw_data_enabled(),
                     "Expected raw_data streaming to be disabled")
    self.uut.toggle_raw_data()
    self.assertTrue(self.uut.raw_data_enabled(),
                    "Expected raw_data streaming to be enabled")
    self.uut.toggle_raw_data()
    self.assertFalse(self.uut.raw_data_enabled(),
                     "Expected raw_data streaming to be disabled")

  def test_120_transport_get_raw_data_raises_error(self):
    """Test get_raw_data raises error."""
    transport = None
    self.uut = transport_process.TransportProcess(
        "fake_transport",
        self.exception_queue,
        self.command_queue,
        self.log_queue,
        transport,
        call_result_queue=self.call_result_queue)
    with self.assertRaisesRegex(RuntimeError, r"No queue provided"):
      self.uut.get_raw_data()

  def test_200_transport_opens_and_closes_transport(self):
    """Test transport process calls transport open and close."""
    transport = fake_transport.FakeTransport()
    self.uut = transport_process.TransportProcess(
        "fake_transport",
        self.exception_queue,
        self.command_queue,
        self.log_queue,
        transport,
        call_result_queue=self.call_result_queue)
    self.uut.start()
    self.uut.stop()
    self.assertEqual(
        1, transport.open_count.value,
        "Expected transport.open to be called {} called {}".format(
            1, transport.open_count.value))
    self.assertEqual(
        1, transport.close_count.value,
        "Expected transport.close to be called {} called {}".format(
            1, transport.close_count.value))

  def test_201_transport_closes_transport_on_command(self):
    """Test transport closes transport on command."""
    transport = mock.MagicMock(spec=fake_transport.FakeTransport)
    self.uut = transport_process.TransportProcess(
        "fake_transport",
        self.exception_queue,
        self.command_queue,
        self.log_queue,
        transport,
        call_result_queue=self.call_result_queue)

    self.command_queue.put((transport_process.CMD_TRANSPORT_CLOSE, None))
    wait_for_queue_writes(self.command_queue)
    self.uut._pre_run_hook()
    self.assertTrue(self.uut.is_open(),
                    "Expected transport process to be opened, found closed")
    self.uut._do_work()
    transport.close.assert_called_once()
    transport.close.assert_called_once()
    self.uut._post_run_hook()
    transport.open.assert_called_once()
    self.assertEqual(
        2, transport.close.call_count,
        "Expected transport.close to be called {} called {}".format(
            2, transport.close.call_count))

  def test_202_transport_opens_transport_on_command(self):
    """Test transport opens transport on command."""
    transport = mock.MagicMock(spec=fake_transport.FakeTransport)
    self.uut = transport_process.TransportProcess(
        "fake_transport",
        self.exception_queue,
        self.command_queue,
        self.log_queue,
        transport,
        call_result_queue=self.call_result_queue)

    self.command_queue.put((transport_process.CMD_TRANSPORT_OPEN, None))
    wait_for_queue_writes(self.command_queue)
    self.uut._pre_run_hook()
    self.assertTrue(self.uut.is_open(),
                    "Expected transport process to be opened, found closed")
    self.uut._do_work()
    self.assertTrue(self.uut.is_open(),
                    "Expected transport process to be opened, found closed")
    self.uut._post_run_hook()
    self.assertEqual(
        2, transport.open.call_count,
        "Expected transport.open to be called {} called {}".format(
            2, transport.open.call_count))
    transport.close.assert_called_once()

  def test_203_transport_skips_opens_on_start(self):
    """Test transport process calls transport open and close."""
    transport = fake_transport.FakeTransport()
    transport.set_property(transport_properties.OPEN_ON_START, False)
    self.uut = transport_process.TransportProcess(
        "fake_transport",
        self.exception_queue,
        self.command_queue,
        self.log_queue,
        transport,
        call_result_queue=self.call_result_queue)
    self.uut.start()
    self.uut.stop()
    self.assertEqual(
        0, transport.open_count.value,
        "Expected transport.open to be called {} called {}".format(
            0, transport.open_count.value))
    self.assertEqual(
        1, transport.close_count.value,
        "Expected transport.close to be called {} called {}".format(
            1, transport.close_count.value))

  def test_204_transport_auto_reopen_with_close(self):
    """Transport process shouldn't reopen after being closed via close()."""
    transport = mock.MagicMock(spec=fake_transport.FakeTransport)
    transport._properties = {}
    transport._properties[transport_properties.AUTO_REOPEN] = True
    transport._transport_open = mock.MagicMock(
        spec=multiprocessing_utils.get_context().Event())
    transport.is_open.side_effect = iter([False, False])
    self.uut = transport_process.TransportProcess(
        "fake_transport",
        self.exception_queue,
        self.command_queue,
        self.log_queue,
        transport,
        call_result_queue=self.call_result_queue)

    self.uut._pre_run_hook()
    transport.open.assert_called_once()

    self.command_queue.put((transport_process.CMD_TRANSPORT_CLOSE, None))
    wait_for_queue_writes(self.command_queue)
    self.uut._do_work()
    transport.close.assert_called()

    self.uut._do_work()  # Shouldn't reopen here

    self.uut._post_run_hook()
    transport.open.assert_called_once()

  def test_205_transport_auto_reopen_unexpected_close(self):
    """Test transport process reopens if it closes unexpectedly."""
    transport = mock.MagicMock(spec=fake_transport.FakeTransport)
    transport._properties = {}
    transport._properties[transport_properties.AUTO_REOPEN] = True
    transport._transport_open = mock.MagicMock(
        spec=multiprocessing_utils.get_context().Event())
    transport.is_open.side_effect = iter([False])
    self.uut = transport_process.TransportProcess(
        "fake_transport",
        self.exception_queue,
        self.command_queue,
        self.log_queue,
        transport,
        call_result_queue=self.call_result_queue)

    self.uut._pre_run_hook()
    transport.open.assert_called_once()

    self.uut._do_work()  # Should reopen here
    self.assertEqual(
        2, transport.open.call_count,
        "Expected transport.open to be called {} called {}".format(
            2, transport.open.call_count))
    # If transport closes unexpectedly, transport.close() should be called
    # before re-opening the transport to clean up resources (b/183527797).
    transport.close.assert_called_once()

    self.uut._post_run_hook()
    self.assertEqual(transport.close.call_count, 2)

  def test_210_transport_rejects_invalid_command(self):
    """Test transport rejects invalid command."""
    transport = fake_transport.FakeTransport()
    self.uut = transport_process.TransportProcess(
        "fake_transport",
        self.exception_queue,
        self.command_queue,
        self.log_queue,
        transport,
        call_result_queue=self.call_result_queue)

    self.command_queue.put(("invalid cmd", None))
    wait_for_queue_writes(self.command_queue)
    self.uut._pre_run_hook()
    with self.assertRaisesRegex(RuntimeError, r"received an unknown command"):
      self.uut._do_work()
    self.uut._post_run_hook()

  def test_211_transport_writes_split_commands(self):
    """Test transport writes split commands."""
    transport = mock.MagicMock(spec=fake_transport.FakeTransport)
    transport.read.return_value = (b"this will be a really long command that "
                                   b"will be split")

    self.uut = transport_process.TransportProcess(
        "fake_transport",
        self.exception_queue,
        self.command_queue,
        self.log_queue,
        transport,
        call_result_queue=self.call_result_queue)

    self.uut._pre_run_hook()
    long_command = "this will be a really long command that will be split"
    self.uut.send_command(transport_process.CMD_TRANSPORT_WRITE, long_command)
    wait_for_queue_writes(self.command_queue)
    self.uut._do_work()
    self.uut._do_work()
    self.uut._post_run_hook()

    self.assertEqual(
        2, transport.write.call_count,
        "Expecting write to be called twice, found {}".format(
            transport.write.call_count))

  def test_220_transport_can_disable_raw_data_queue(self):
    """Test transport can disable raw_data_queue."""
    device_data1 = b"some device message\n"
    device_data2 = b"other device message\n"
    transport = mock.MagicMock(spec=fake_transport.FakeTransport)
    transport.read.side_effect = iter([device_data1, device_data2])
    raw_data_id = 1
    self.uut = transport_process.TransportProcess(
        "fake_transport",
        self.exception_queue,
        self.command_queue,
        self.log_queue,
        transport,
        call_result_queue=self.call_result_queue,
        raw_data_queue=self.raw_data_queue,
        raw_data_id=raw_data_id)

    self.uut._pre_run_hook()
    self.uut.toggle_raw_data()  # enable raw data for first message
    self.uut._do_work()  # publish first raw data message

    self.uut.toggle_raw_data()  # disable raw data for second message
    self.uut._do_work()  # skips publishing second raw data message
    self.uut._post_run_hook()

    self.assertEqual(
        1, self.raw_data_queue.qsize(),
        "Expected 1 entry in raw_data_queue found {}".format(
            self.raw_data_queue.qsize()))
    self.assertEqual(
        2, self.log_queue.qsize(),
        "Expected 2 entries in log_queue found {}".format(
            self.log_queue.qsize()))

    data_id, raw_data = self.uut.get_raw_data()
    self.assertIsInstance(
        data_id, int,
        "Expecting int for raw data id found {}".format(type(data_id)))
    self.assertIsInstance(raw_data, str)
    self.assertEqual(raw_data_id, data_id,
                     "Expecting {} found {}".format(raw_data_id, data_id))
    self.assertEqual(
        device_data1.decode("utf-8", "replace"), raw_data,
        "Expecting {!r} found {!r}".format(
            device_data1.decode("utf-8", "replace"), raw_data))

  def test_230_transport_invalid_command_raises_error(self):
    """Test transport raises exception on invalid command."""
    transport = fake_transport.FakeTransport()

    self.uut = transport_process.TransportProcess(
        "fake_transport",
        self.exception_queue,
        self.command_queue,
        self.log_queue,
        transport,
        call_result_queue=self.call_result_queue)
    self.command_queue.put(("Invalid command", None))
    wait_for_queue_writes(self.command_queue)
    self.uut.start()
    end_time = time.time() + _EXCEPTION_TIMEOUT
    while self.uut.is_running() and time.time() < end_time:
      time.sleep(0.001)
    self.assertFalse(self.uut.is_running(),
                     "Expected process to end, still running")
    self.uut.stop()

    self.assertEqual(
        1, transport.open_count.value,
        "Expected transport.open to be called {} called {}".format(
            1, transport.open_count.value))
    self.assertEqual(
        1, transport.close_count.value,
        "Expected transport.close to be called {} called {}".format(
            1, transport.close_count.value))
    self.assertIsNotNone(self.exception,
                         "Expected exception to be raised found None")
    self.assertIn(
        "received an unknown command", repr(self.exception),
        "Expected 'received an unknown command' found {!r}".format(
            self.exception))
    # Clear raised exception that was handled
    self.exception = None

  def test_231_transport_read_error_raises_error(self):
    """Test transport raises error on read exception."""
    transport = fake_transport.FakeTransport(fail_read=True)

    self.uut = transport_process.TransportProcess(
        "fake_transport",
        self.exception_queue,
        self.command_queue,
        self.log_queue,
        transport,
        call_result_queue=self.call_result_queue)
    self.uut.start()
    end_time = time.time() + _EXCEPTION_TIMEOUT
    while self.uut.is_running() and time.time() < end_time:
      time.sleep(0.001)
    self.assertFalse(self.uut.is_open(),
                     "Expected transport process to be closed, found open")
    self.assertFalse(self.uut.is_running(),
                     "Expected process to end, still running")
    self.uut.stop()

    self.assertEqual(
        1, transport.open_count.value,
        "Expected transport.open to be called {} called {}".format(
            1, transport.open_count.value))
    self.assertEqual(
        1, transport.close_count.value,
        "Expected transport.close to be called {} called {}".format(
            1, transport.close_count.value))
    self.assertIsNotNone(self.exception,
                         "Expected exception to be raised found None")
    self.assertIn(
        fake_transport.EXCEPTION_MESSAGE, self.exception,
        "Expected exception message {} found {!r}".format(
            fake_transport.EXCEPTION_MESSAGE, self.exception))
    # Clear raised exception that was handled
    self.exception = None

  @unittest.skip("Skipping test_232_transport_read_retains_partial_lines")
  def test_232_transport_read_retains_partial_lines(self):
    """Test transport read can retain partial log lines."""
    transport = fake_transport.FakeTransport()
    self.uut = transport_process.TransportProcess(
        "fake_transport",
        self.exception_queue,
        self.command_queue,
        self.log_queue,
        transport,
        call_result_queue=self.call_result_queue)

    device_data1 = "partial log line\r"
    transport.reads.put(device_data1)
    wait_for_queue_writes(transport.reads)
    self.uut._pre_run_hook()
    self.uut._do_work()
    self.assertTrue(self.log_queue.empty(), "Expected log queue to be empty")
    time.sleep(_LOG_MESSAGE_TIMEOUT)
    self.uut._do_work()
    self.assertFalse(self.log_queue.empty(),
                     "Expected log queue to not be empty")
    self.uut._post_run_hook()

  @unittest.skip(
      "Skipping test_233_transport_read_reorders_log_interrupted_partial_lines")
  def test_233_transport_read_reorders_log_interrupted_partial_lines(self):
    """Test transport read can order partial and full lines correctly.

    See NEP-3223 which is a bug in the interaction of TransportProcess and
    LogFramer.
    """
    transport = fake_transport.FakeTransport()
    response_start = u"response start"
    response_end = u" end"
    response_full = response_start + response_end
    log_line = u"my custom log line\n"
    log_regex = "({})".format(log_line)
    framer = data_framer.InterwovenLogFramer(log_regex)
    uut = transport_process.TransportProcess(
        "fake_transport",
        self.exception_queue,
        self.command_queue,
        self.log_queue,
        transport,
        call_result_queue=self.call_result_queue,
        framer=framer)

    device_data1 = response_start + log_line + response_end
    transport.reads.put(device_data1)
    wait_for_queue_writes(transport.reads)
    uut._pre_run_hook()
    uut._do_work()
    line1 = self.log_queue.get()
    self.assertIn(
        log_line, line1,
        "Expected {!r} in line but found {!r}".format(log_line, line1))
    self.assertTrue(self.log_queue.empty(), "Expected log queue to be empty")
    time.sleep(_LOG_MESSAGE_TIMEOUT)
    uut._do_work()
    line2 = self.log_queue.get()
    self.assertIn(
        response_full, line2,
        "Expected {!r} in line but found {!r}".format(response_full, line2))
    self.assertTrue(self.log_queue.empty(), "Expected log queue to be empty")
    uut._post_run_hook()

  def test_234_transport_read_orders_lines_correctly(self):
    """Test transport read can order partial and full lines correctly.

    See NEP-3223 which is a bug in the interaction of TransportProcess and
    LogFramer.
    """
    response_start = u"response start"
    response_end = u" end\n"
    response_full = response_start + response_end
    log_line = u"my custom log line\n"
    log_regex = "({})".format(log_line)
    device_data1 = response_start + log_line + response_end
    transport = mock.MagicMock(fake_transport.FakeTransport)
    transport.read.return_value = device_data1.encode("utf-8", "replace")
    framer = data_framer.InterwovenLogFramer(log_regex)
    self.uut = transport_process.TransportProcess(
        "fake_transport",
        self.exception_queue,
        self.command_queue,
        self.log_queue,
        transport,
        call_result_queue=self.call_result_queue,
        framer=framer)

    self.uut._pre_run_hook()
    self.uut._do_work()
    line1 = self.log_queue.get()
    self.assertIn(
        log_line, line1,
        "Expected {!r} in line but found {!r}".format(log_line, line1))
    line2 = self.log_queue.get()
    self.assertIn(
        response_full, line2,
        "Expected {!r} in line but found {!r}".format(response_full, line2))
    self.assertTrue(self.log_queue.empty(), "Expected log queue to be empty")
    self.uut._post_run_hook()

  @unittest.skip("Skipping test_240_transport_sleeps_if_not_open")
  def test_240_transport_sleeps_if_not_open(self):
    """Test transport read can retain partial log lines."""
    transport = fake_transport.FakeTransport()
    transport.set_property(transport_properties.OPEN_ON_START, False)
    read_timeout = 0.03
    self.uut = transport_process.TransportProcess(
        "fake_transport",
        self.exception_queue,
        self.command_queue,
        self.log_queue,
        transport,
        call_result_queue=self.call_result_queue,
        read_timeout=read_timeout)

    device_data1 = "partial log line\r"
    transport.reads.put(device_data1)
    wait_for_queue_writes(transport.reads)
    self.uut._pre_run_hook()
    start_time = time.time()
    self.uut._do_work()
    end_time = time.time()
    self.assertFalse(self.uut.is_open(),
                     "Expected transport process to be closed, found open")
    self.uut._post_run_hook()

    self.assertGreater(
        end_time - start_time, read_timeout,
        "Expected transport to sleep for > {}s, found {}s".format(
            read_timeout, end_time - start_time))

  @unittest.skip(
      "Skipping test_300_transport_exceeds_maximum_baudrate_required")
  def test_300_transport_exceeds_maximum_baudrate_required(self):
    """Test baud rate which exceeds the maximum baud rate of 921600."""

    baudrate = 115200 * 10
    minimum_bytes_per_second = 115200 * 8 / 10
    transport = fake_transport.FakeTransport(
        baudrate=baudrate, generate_lines=True)
    self.uut = transport_process.TransportProcess(
        "fake_transport",
        self.exception_queue,
        self.command_queue,
        self.log_queue,
        transport,
        call_result_queue=self.call_result_queue,
        raw_data_queue=self.raw_data_queue)
    self.uut.toggle_raw_data()
    start_time = time.time()
    end_time = start_time + 5.0
    self.uut._pre_run_hook()
    while time.time() < end_time:
      self.uut._do_work()
    finish_time = time.time()
    self.uut._post_run_hook()
    generated_bytes_per_second = transport.bytes_per_second.value
    self.assertLess(
        minimum_bytes_per_second, generated_bytes_per_second,
        "Expected generator to produce bytes > {} but found {}. "
        "Check load on this lab server.".format(minimum_bytes_per_second,
                                                generated_bytes_per_second))
    bytes_received = 0
    expected_count = 0
    while not self.raw_data_queue.empty():
      expected_count += 1
      _, raw_data = self.raw_data_queue.get()
      actual_count = int(raw_data[:8])
      self.assertEqual(
          expected_count, actual_count,
          "Expected line count {} found {} in {!r}".format(
              expected_count, actual_count, raw_data))
      bytes_received += len(raw_data)
    actual_bytes_per_second = bytes_received / (finish_time - start_time)
    self.assertLess(
        minimum_bytes_per_second, actual_bytes_per_second,
        "Expected actual bytes per second > {} but found {}".format(
            minimum_bytes_per_second, actual_bytes_per_second))

  def test_310_transport_process_open_close_commands(self):
    """Verify transport process processes OPEN and CLOSE commands correctly."""
    transport = mock.Mock()
    uut = transport_process.TransportProcess(
        "fake_transport",
        self.exception_queue,
        self.command_queue,
        self.log_queue,
        transport=transport,
        call_result_queue=self.call_result_queue)

    test_data = [
        ((transport_process.CMD_TRANSPORT_CLOSE, None), transport.close),
        ((transport_process.CMD_TRANSPORT_OPEN, None), transport.open)
    ]

    for message, expected_action in test_data:
      with self.subTest(command=message[0]):
        transport.reset_mock()
        uut._process_command_message(message)
        expected_action.assert_called_once()

  def test_311_transport_process_write_command(self):
    """Verify transport process processes WRITE command correctly."""
    transport = mock.Mock()
    uut = transport_process.TransportProcess(
        "fake_transport",
        self.exception_queue,
        self.command_queue,
        self.log_queue,
        transport=transport,
        call_result_queue=self.call_result_queue)

    with mock.patch.object(transport_process,
                           "_enqueue_command_writes") as mock_write:
      uut._process_command_message(
          (transport_process.CMD_TRANSPORT_WRITE, b"stuff"))
      mock_write.assert_called_once_with(
          mock.ANY, b"stuff", max_write_bytes=mock.ANY)

  def test_312_transport_process_call_command(self):
    """Verify transport process processes CALL command correctly."""
    transport = mock.Mock()
    uut = transport_process.TransportProcess(
        "fake_transport",
        self.exception_queue,
        self.command_queue,
        self.log_queue,
        transport=transport,
        call_result_queue=self.call_result_queue)

    transport.some_method.return_value = 123
    uut._process_command_message((
        transport_process.CMD_TRANSPORT_CALL,
        ("some_method",
         ("a", "b"),
         {"foo": "bar"})))
    transport.some_method.assert_called_once_with("a", "b", foo="bar")
    success, return_value = self.call_result_queue.get(block=True, timeout=0.1)
    self.assertTrue(success)
    self.assertEqual(return_value, 123)

  def test_313_transport_process_call_command_error_handling(self):
    """Verify exceptions in transport methods are put into the result queue."""
    transport = mock.Mock()
    uut = transport_process.TransportProcess(
        "fake_transport",
        self.exception_queue,
        self.command_queue,
        self.log_queue,
        transport=transport,
        call_result_queue=self.call_result_queue)

    transport.some_method.side_effect = RuntimeError("Something failed")
    uut._process_command_message((
        transport_process.CMD_TRANSPORT_CALL,
        ("some_method",
         ("a", "b"),
         {"foo": "bar"})))
    transport.some_method.assert_called_once_with("a", "b", foo="bar")
    success, error_traceback = self.call_result_queue.get(
        block=True, timeout=0.1)
    self.assertFalse(success)
    self.assertIn("RuntimeError: Something failed", error_traceback)

  def _verify_command_split(self, original_command, a_queue):
    count = 0
    command = ""
    while not a_queue.empty():
      count += 1
      partial_command = switchboard_process.get_message(a_queue)
      self.assertIsInstance(partial_command, str)
      partial_command_len = len(partial_command)
      self.assertLessEqual(
          partial_command_len, transport_process._MAX_WRITE_BYTES,
          "Expected enqueued command of length {} found {}".format(
              transport_process._MAX_WRITE_BYTES, partial_command_len))
      command += partial_command
    expected_count = 1 + (
        len(original_command) // transport_process._MAX_WRITE_BYTES)
    self.assertEqual(
        expected_count, count,
        "Expected {} enqueued commands found {}".format(expected_count, count))
    self.assertEqual(
        original_command, command,
        "Expected {!r} to match original command {!r}".format(
            command, original_command))


if __name__ == "__main__":
  unit_test_case.main()
