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

"""Tests the switchboard_process.py module."""
import multiprocessing
import queue
import time
from unittest import mock

from gazoo_device import gdm_logger
from gazoo_device.switchboard import switchboard_process
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import multiprocessing_utils
import psutil

MagicMock = mock.MagicMock

_ECHO_MESSAGE = "My message to be echoed"
_EXIT_TIMEOUT = 1
_EXCEPTION_MESSAGE = "Test exception handler"
_EXCEPTION_TIMEOUT = 3
_MULTIPROCESSING_EVENT = multiprocessing_utils.get_context().Event()

wait_for_queue_writes = switchboard_process.wait_for_queue_writes


def do_work_return_true():
  return True


class BadQueue:
  pass


class ErrorProcess(switchboard_process.SwitchboardProcess):

  def _do_work(self):
    raise RuntimeError(_EXCEPTION_MESSAGE)


class RunningProcess(switchboard_process.SwitchboardProcess):

  def _do_work(self):
    time.sleep(0.001)
    return True


class SwitchboardProcessTests(unit_test_case.MultiprocessingTestCase):
  """Tests Switchboard Process."""

  def setUp(self):
    super().setUp()
    self.command_queue = multiprocessing_utils.get_context().Queue()

  def tearDown(self):
    if hasattr(self, "uut"):
      del self.uut
    del self.command_queue  # Release shared memory file descriptors.
    super().tearDown()

  def test_000_switchboard_process_construct_destruct(self):
    """Test constructing and destructing raises no errors."""
    self.uut = switchboard_process.SwitchboardProcess("fake_device",
                                                      "fake_process",
                                                      self.exception_queue,
                                                      self.command_queue)
    self.assertFalse(self.uut.is_started(),
                     "Expected process not started, found started")
    self.assertFalse(self.uut.is_running(),
                     "Expected process to not running, found running")

  def test_001_switchboard_process_get_message_no_queue(self):
    """Test getting message from no queue."""
    with self.assertRaisesRegex(ValueError, "Invalid queue of"):
      switchboard_process.get_message(None)

  def test_002_switchboard_process_get_message_bad_queue(self):
    """Test getting message from a bad queue."""
    with self.assertRaisesRegex(ValueError, "Invalid queue of"):
      switchboard_process.get_message(BadQueue())

  def test_003_switchboard_process_get_message_empty_queue(self):
    """Test getting message from an empty queue."""
    in_queue = multiprocessing_utils.get_context().Queue()
    message = switchboard_process.get_message(in_queue, timeout=0)
    self.assertIsNone(message,
                      "Expected None from empty queue found {}".format(message))

  def test_004_switchboard_process_get_message_nonempty_queue(self):
    """Test getting message from an empty queue."""
    in_queue = multiprocessing_utils.get_context().Queue()
    in_queue.put(_ECHO_MESSAGE)
    wait_for_queue_writes(in_queue)
    message = switchboard_process.get_message(in_queue, timeout=0)
    self.assertEqual(
        _ECHO_MESSAGE, message,
        "Expected {} from nonempty queue found {}".format(
            _ECHO_MESSAGE, message))

  def test_010_switchboard_process_put_message_no_queue(self):
    """Test putting message into no queue."""
    with self.assertRaisesRegex(ValueError, "Invalid queue of"):
      switchboard_process.put_message(None, _ECHO_MESSAGE)

  def test_011_switchboard_process_put_message_bad_queue(self):
    """Test putting message into a bad queue."""
    with self.assertRaisesRegex(ValueError, "Invalid queue of"):
      switchboard_process.put_message(BadQueue(), _ECHO_MESSAGE)

  def test_012_switchboard_process_put_message_full_queue(self):
    """Test putting message into an full queue."""
    out_queue = multiprocessing_utils.get_context().Queue(maxsize=1)
    switchboard_process.put_message(out_queue, _ECHO_MESSAGE)
    with self.assertRaises(queue.Full):
      switchboard_process.put_message(out_queue, _ECHO_MESSAGE, timeout=0)

  def test_013_switchboard_process_put_message_closed_queue(self):
    out_queue = multiprocessing_utils.get_context().Queue()
    out_queue.close()
    with self.assertRaisesRegex(
        (AssertionError, ValueError), "Queue.*closed"):
      switchboard_process.put_message(out_queue, _ECHO_MESSAGE, timeout=0)

  @mock.patch.object(psutil, "Process", autospec=True)
  def test_020_switchboard_process_loop_pre_run_hook_returns_false(
      self, mock_psutil_proc):
    mock_start_event = MagicMock(spec=_MULTIPROCESSING_EVENT)
    mock_stop_event = MagicMock(spec=_MULTIPROCESSING_EVENT)
    mock_terminate_event = MagicMock(spec=_MULTIPROCESSING_EVENT)

    mock_switchboard_process = MagicMock(
        spec=switchboard_process.SwitchboardProcess)
    mock_switchboard_process.device_name = "mock_device"
    mock_switchboard_process.process_name = "mock_process"
    mock_switchboard_process._exception_queue = self.exception_queue
    mock_switchboard_process.logging_queue = MagicMock()
    mock_switchboard_process._start_event = mock_start_event
    mock_switchboard_process._stop_event = mock_stop_event
    mock_switchboard_process._terminate_event = mock_terminate_event

    mock_parent_proc = mock_psutil_proc.return_value
    mock_switchboard_process._pre_run_hook.return_value = False

    with mock.patch.object(
        gdm_logger,
        "initialize_child_process_logging") as mock_initialize_logging:
      switchboard_process._process_loop(mock_switchboard_process, 1234)

    mock_initialize_logging.assert_called_once()
    mock_start_event.set.assert_called_once()
    mock_switchboard_process._pre_run_hook.assert_called_once()
    mock_parent_proc.status.assert_not_called()
    mock_switchboard_process._do_work.assert_not_called()
    mock_stop_event.set.assert_called_once()

  @mock.patch.object(psutil, "Process", autospec=True)
  def test_021_switchboard_process_loop_parent_is_zombie(self,
                                                         mock_psutil_proc):
    """Process loop exits on parent process in zombie status."""
    mock_start_event = MagicMock(spec=_MULTIPROCESSING_EVENT)
    mock_stop_event = MagicMock(spec=_MULTIPROCESSING_EVENT)
    mock_terminate_event = MagicMock(spec=_MULTIPROCESSING_EVENT)

    mock_switchboard_process = MagicMock(
        spec=switchboard_process.SwitchboardProcess)
    mock_switchboard_process.device_name = "mock_device"
    mock_switchboard_process.process_name = "mock_process"
    mock_switchboard_process._exception_queue = self.exception_queue
    mock_switchboard_process.logging_queue = MagicMock()
    mock_switchboard_process._start_event = mock_start_event
    mock_switchboard_process._stop_event = mock_stop_event
    mock_switchboard_process._terminate_event = mock_terminate_event

    mock_parent_proc = mock_psutil_proc.return_value
    mock_switchboard_process._pre_run_hook.return_value = True
    mock_parent_proc.status.return_value = psutil.STATUS_ZOMBIE

    with mock.patch.object(
        gdm_logger,
        "initialize_child_process_logging") as mock_initialize_logging:
      switchboard_process._process_loop(mock_switchboard_process, 1234)

    mock_initialize_logging.assert_called_once()
    mock_start_event.set.assert_called_once()
    mock_switchboard_process._pre_run_hook.assert_called_once()
    mock_parent_proc.status.assert_called_once()
    mock_terminate_event.is_set.assert_not_called()
    mock_terminate_event.clear.assert_not_called()
    mock_switchboard_process._do_work.assert_not_called()
    mock_stop_event.set.assert_called_once()

  @mock.patch.object(psutil, "Process", autospec=True)
  def test_022_switchboard_process_loop_parent_is_killed(self,
                                                         mock_psutil_proc):
    """Process loop exits on parent process is killed."""
    mock_start_event = MagicMock(spec=_MULTIPROCESSING_EVENT)
    mock_stop_event = MagicMock(spec=_MULTIPROCESSING_EVENT)
    mock_terminate_event = MagicMock(spec=_MULTIPROCESSING_EVENT)

    mock_switchboard_process = MagicMock(
        spec=switchboard_process.SwitchboardProcess)
    mock_switchboard_process.device_name = "mock_device"
    mock_switchboard_process.process_name = "mock_process"
    mock_switchboard_process._exception_queue = self.exception_queue
    mock_switchboard_process.logging_queue = MagicMock()
    mock_switchboard_process._start_event = mock_start_event
    mock_switchboard_process._stop_event = mock_stop_event
    mock_switchboard_process._terminate_event = mock_terminate_event

    mock_parent_proc = mock_psutil_proc.return_value
    mock_switchboard_process._pre_run_hook.return_value = True
    mock_parent_proc.status.side_effect = psutil.NoSuchProcess(0, "foo")

    with mock.patch.object(
        gdm_logger,
        "initialize_child_process_logging") as mock_initialize_logging:
      switchboard_process._process_loop(mock_switchboard_process, 1234)

    mock_initialize_logging.assert_called_once()
    mock_start_event.set.assert_called_once()
    mock_switchboard_process._pre_run_hook.assert_called_once()
    mock_parent_proc.status.assert_called_once()
    mock_terminate_event.is_set.assert_not_called()
    mock_terminate_event.clear.assert_not_called()
    mock_switchboard_process._do_work.assert_not_called()
    mock_stop_event.set.assert_called_once()

  @mock.patch.object(psutil, "Process", autospec=True)
  def test_023_switchboard_process_loop_terminates_on_signal(self,
                                                             mock_psutil_proc):
    """Process loop exits on terminate_event signal."""
    mock_start_event = MagicMock(spec=_MULTIPROCESSING_EVENT)
    mock_stop_event = MagicMock(spec=_MULTIPROCESSING_EVENT)
    mock_terminate_event = MagicMock(spec=_MULTIPROCESSING_EVENT)

    mock_switchboard_process = MagicMock(
        spec=switchboard_process.SwitchboardProcess)
    mock_switchboard_process.device_name = "mock_device"
    mock_switchboard_process.process_name = "mock_process"
    mock_switchboard_process._exception_queue = self.exception_queue
    mock_switchboard_process.logging_queue = MagicMock()
    mock_switchboard_process._start_event = mock_start_event
    mock_switchboard_process._stop_event = mock_stop_event
    mock_switchboard_process._terminate_event = mock_terminate_event

    mock_parent_proc = mock_psutil_proc.return_value
    mock_switchboard_process._pre_run_hook.return_value = True
    mock_terminate_event.is_set.return_value = True

    with mock.patch.object(
        gdm_logger,
        "initialize_child_process_logging") as mock_initialize_logging:
      switchboard_process._process_loop(mock_switchboard_process, 1234)

    mock_initialize_logging.assert_called_once()
    mock_start_event.set.assert_called_once()
    mock_switchboard_process._pre_run_hook.assert_called_once()
    mock_parent_proc.status.assert_called_once()
    mock_terminate_event.is_set.assert_called_once()
    mock_terminate_event.clear.assert_called_once()
    mock_switchboard_process._do_work.assert_not_called()
    mock_stop_event.set.assert_called_once()

  @mock.patch.object(psutil, "Process", autospec=True)
  def test_024_switchboard_process_loop_calls_do_work_once(self,
                                                           mock_psutil_proc):
    """Process loop calls _do_work at least once."""
    mock_start_event = MagicMock(spec=_MULTIPROCESSING_EVENT)
    mock_stop_event = MagicMock(spec=_MULTIPROCESSING_EVENT)
    mock_terminate_event = MagicMock(spec=_MULTIPROCESSING_EVENT)

    mock_switchboard_process = MagicMock(
        spec=switchboard_process.SwitchboardProcess)
    mock_switchboard_process.device_name = "mock_device"
    mock_switchboard_process.process_name = "mock_process"
    mock_switchboard_process._exception_queue = self.exception_queue
    mock_switchboard_process.logging_queue = MagicMock()
    mock_switchboard_process._start_event = mock_start_event
    mock_switchboard_process._stop_event = mock_stop_event
    mock_switchboard_process._terminate_event = mock_terminate_event

    mock_parent_proc = mock_psutil_proc.return_value
    mock_switchboard_process._pre_run_hook.return_value = True
    mock_terminate_event.is_set.return_value = False
    mock_switchboard_process._do_work.return_value = False

    with mock.patch.object(
        gdm_logger,
        "initialize_child_process_logging") as mock_initialize_logging:
      switchboard_process._process_loop(mock_switchboard_process, 1234)

    mock_initialize_logging.assert_called_once()
    mock_start_event.set.assert_called_once()
    mock_switchboard_process._pre_run_hook.assert_called_once()
    mock_parent_proc.status.assert_called_once()
    mock_terminate_event.is_set.assert_called_once()
    mock_terminate_event.clear.assert_not_called()
    mock_switchboard_process._do_work.assert_called_once()
    mock_stop_event.set.assert_called_once()

  @mock.patch.object(psutil, "Process", autospec=True)
  def test_025_switchboard_process_loop_manager_shutdown(self,
                                                         mock_psutil_proc):
    """Process loop manager in parent process shutdown."""
    mock_start_event = MagicMock(spec=_MULTIPROCESSING_EVENT)
    mock_stop_event = MagicMock(spec=_MULTIPROCESSING_EVENT)
    mock_terminate_event = MagicMock(spec=_MULTIPROCESSING_EVENT)

    mock_switchboard_process = MagicMock(
        spec=switchboard_process.SwitchboardProcess)
    mock_switchboard_process.device_name = "mock_device"
    mock_switchboard_process.process_name = "mock_process"
    mock_switchboard_process._exception_queue = self.exception_queue
    mock_switchboard_process.logging_queue = MagicMock()
    mock_switchboard_process._start_event = mock_start_event
    mock_switchboard_process._stop_event = mock_stop_event
    mock_switchboard_process._terminate_event = mock_terminate_event

    mock_parent_proc = mock_psutil_proc.return_value
    mock_switchboard_process._pre_run_hook.return_value = True
    mock_terminate_event.is_set.side_effect = IOError("[Errno 32] Broken pipe")
    mock_stop_event.set.side_effect = IOError("[Errno 32] Broken pipe")

    with mock.patch.object(
        gdm_logger,
        "initialize_child_process_logging") as mock_initialize_logging:
      switchboard_process._process_loop(mock_switchboard_process, 1234)

    mock_initialize_logging.assert_called_once()
    mock_start_event.set.assert_called_once()
    mock_switchboard_process._pre_run_hook.assert_called_once()
    mock_parent_proc.status.assert_called_once()
    mock_terminate_event.is_set.assert_called_once()
    mock_terminate_event.clear.assert_not_called()
    mock_switchboard_process._do_work.assert_not_called()
    mock_stop_event.set.assert_called_once()

  @mock.patch.object(psutil, "Process", autospec=True)
  def test_026_switchboard_process_loop_start_event_set_exception(
      self, mock_psutil_proc):
    """Process loop manager in parent process shutdown."""
    mock_start_event = MagicMock(spec=_MULTIPROCESSING_EVENT)
    mock_stop_event = MagicMock(spec=_MULTIPROCESSING_EVENT)
    mock_terminate_event = MagicMock(spec=_MULTIPROCESSING_EVENT)

    mock_switchboard_process = MagicMock(
        spec=switchboard_process.SwitchboardProcess)
    mock_switchboard_process.device_name = "mock_device"
    mock_switchboard_process.process_name = "mock_process"
    mock_switchboard_process._exception_queue = self.exception_queue
    mock_switchboard_process.logging_queue = MagicMock()
    mock_switchboard_process._start_event = mock_start_event
    mock_switchboard_process._stop_event = mock_stop_event
    mock_switchboard_process._terminate_event = mock_terminate_event

    mock_switchboard_process._pre_run_hook.return_value = True
    mock_switchboard_process._do_work.return_value = False
    mock_terminate_event.is_set.return_value = False
    mock_start_event.set.side_effect = IOError("[Errno 32] Broken pipe")

    with mock.patch.object(
        gdm_logger,
        "initialize_child_process_logging") as mock_initialize_logging:
      switchboard_process._process_loop(mock_switchboard_process, 1234)

    mock_initialize_logging.assert_called_once()
    mock_start_event.set.assert_called_once()
    mock_terminate_event.is_set.assert_called_once()
    mock_terminate_event.clear.assert_not_called()
    mock_switchboard_process._do_work.assert_called_once()
    mock_stop_event.set.assert_called_once()

  @mock.patch.object(psutil, "Process", autospec=True)
  def test_030_switchboard_process_wrapper_puts_exception(self,
                                                          mock_psutil_proc):
    """Test child_process_wrapper puts message in exception_queue."""
    error_queue = multiprocessing_utils.get_context().Queue()

    with switchboard_process._child_process_wrapper(1234,
                                                    "fake_process",
                                                    "fake_device", error_queue):
      raise Exception("my_exception")
    wait_for_queue_writes(error_queue)
    message = error_queue.get_nowait()
    self.assertIn(
        "Device fake_device raised exception in fake_process", message,
        "Expected 'Device ... raised exception in ...' found {!r}".format(
            message))

  @mock.patch.object(psutil, "Process", autospec=True)
  def test_031_switchboard_process_wrapper_skips_exception(self,
                                                           mock_psutil_proc):
    """Test child_process_wrapper skips exception_queue message on EOFError."""
    error_queue = multiprocessing_utils.get_context().Queue()

    with switchboard_process._child_process_wrapper(1234,
                                                    "fake_process",
                                                    "fake_device", error_queue):
      raise EOFError("end of file")
    wait_for_queue_writes(error_queue, timeout=0.5)
    self.assertTrue(error_queue.empty(),
                    "Expected exception queue to be empty, but found contents")

  def test_100_switchboard_process_start_stop(self):
    """Test starting and stopping child process that exits immediately."""
    self.uut = switchboard_process.SwitchboardProcess("fake_device",
                                                      "fake_process",
                                                      self.exception_queue,
                                                      self.command_queue)
    self.uut.start()
    end_time = time.time() + _EXIT_TIMEOUT
    while self.uut.is_running() and time.time() < end_time:
      time.sleep(0.001)
    self.assertFalse(self.uut.is_running(),
                     "Expected process to end, still running")
    self.assertTrue(self.uut.is_started(),
                    "Expected process started, found not started")
    self.uut.stop()
    self.assertFalse(self.uut.is_started(),
                     "Expected process not started, found started")

  def test_101_switchboard_process_start_twice(self):
    """Test calling start twice for child process that doesn't exit."""
    self.uut = RunningProcess("fake_device", "fake_process",
                              self.exception_queue, self.command_queue)
    self.uut.start()
    self.assertTrue(self.uut.is_started(),
                    "Expected process started, found not started")
    self.assertTrue(self.uut.is_running(),
                    "Expected process to be running, found !running")

    with self.assertRaisesRegex(RuntimeError,
                                "Child process is already running"):
      self.uut.start()
    self.uut.stop()
    self.assertFalse(self.uut.is_started(),
                     "Expected process not started, found started")
    self.assertFalse(self.uut.is_running(),
                     "Expected process to end, still running")

  def test_102_switchboard_process_stop_twice(self):
    """Test calling stop twice for child process that doesn't exit."""
    self.uut = RunningProcess("fake_device", "fake_process",
                              self.exception_queue, self.command_queue)
    self.uut.start()
    self.assertTrue(self.uut.is_started(),
                    "Expected process started, found not started")
    self.assertTrue(self.uut.is_running(),
                    "Expected process to be running, found !running")
    self.uut.stop()
    self.assertFalse(self.uut.is_started(),
                     "Expected process not started, found started")
    self.assertFalse(self.uut.is_running(),
                     "Expected process to end, still running")
    with self.assertRaisesRegex(RuntimeError,
                                "Child process is not currently running"):
      self.uut.stop()

  def test_103_switchboard_process_two_running_processes(self):
    """Test two started running processes."""
    uut1 = RunningProcess("fake_device", "echo_process1",
                          self.exception_queue, self.command_queue)
    command_queue2 = multiprocessing_utils.get_context().Queue()
    uut2 = RunningProcess("fake_device", "echo_process2",
                          self.exception_queue, command_queue2)
    uut1.start()
    self.assertTrue(uut1.is_running(),
                    "Expected process1 to be running, found !running")
    uut2.start()
    self.assertTrue(uut2.is_running(),
                    "Expected process2 to be running, found !running")
    uut1.stop()
    self.assertFalse(uut1.is_running(),
                     "Expected process1 to be not running, found running")
    uut2.stop()
    self.assertFalse(uut2.is_running(),
                     "Expected process2 to be not running, found running")
    del uut1
    del uut2

  def test_104_switchboard_process_stop_after_manager_shutdown(self):
    """Test stopping child process after manager shutdown."""
    self.uut = switchboard_process.SwitchboardProcess("fake_device",
                                                      "fake_process",
                                                      self.exception_queue,
                                                      self.command_queue)
    self.uut._do_work = do_work_return_true
    self.uut.start()
    self.assertTrue(self.uut.is_running(),
                    "Expected process to end, still running")
    self.assertTrue(self.uut.is_started(),
                    "Expected process started, found not started")
    self.uut.stop()
    self.assertFalse(self.uut.is_started(),
                     "Expected process not started, found started")

  def test_110_switchboard_process_exception_handler_works(self):
    """Test exceptions raised end up in exception queue."""
    self.uut = ErrorProcess("fake_device", "error_process",
                            self.exception_queue, self.command_queue)
    self.uut.start()
    end_time = time.time() + _EXCEPTION_TIMEOUT
    while self.uut.is_running() and time.time() < end_time:
      time.sleep(1)
    self.assertFalse(self.uut.is_running(),
                     "Expected process to end, still running")
    self.uut.stop()
    self.assertIsNotNone(self.exception,
                         "Expected exception to be raised found None")
    self.assertIn(
        _EXCEPTION_MESSAGE, repr(self.exception),
        "Expected exception message {!r} found {!r}".format(
            _EXCEPTION_MESSAGE, self.exception))

    # Clear raised exception that was handled
    self.exception = None

  def test_120_switchboard_process_send_command_rejects_invalid_command(self):
    """Test send_command rejects invalid command."""
    self.uut = switchboard_process.SwitchboardProcess("fake_device",
                                                      "fake_command",
                                                      self.exception_queue,
                                                      self.command_queue)
    # Invalid command
    with self.assertRaisesRegex(ValueError, "is not a valid command in"):
      self.uut.send_command("invalid command")

  def test_121_switchboard_process_send_message_accepts_valid_command(self):
    """Test send_command accepts a valid command."""
    self.uut = switchboard_process.SwitchboardProcess(
        "fake_device",
        "fake_command",
        self.exception_queue,
        self.command_queue,
        valid_commands=("valid_command",))
    self.uut.send_command("valid_command", "Data")
    wait_for_queue_writes(self.command_queue)
    self.assertFalse(
        self.command_queue.empty(),
        "Expected command queue to not be empty")

  def test_122_switchboard_process_send_command_and_is_command_consumed(self):
    """Test send_command and is_command_consumed works."""
    self.uut = switchboard_process.SwitchboardProcess(
        "fake_device",
        "fake_command",
        self.exception_queue,
        self.command_queue,
        valid_commands=("valid_command",))
    self.assertTrue(self.uut.is_command_consumed())
    self.uut.send_command("valid_command", "Data")
    wait_for_queue_writes(self.command_queue)
    self.assertFalse(self.uut.is_command_consumed())
    self.command_queue.get()
    self.assertTrue(self.uut.is_command_consumed())

  def test_130_switchboard_process_protected_methods_exist(self):
    """Test that switchboard_process private methods exist and work."""
    self.uut = switchboard_process.SwitchboardProcess(
        "fake_device",
        "fake_command",
        self.exception_queue,
        self.command_queue,
        valid_commands=("valid_command",))
    self.assertFalse(self.uut._do_work(), "Expected _do_work to return False")
    self.assertTrue(self.uut._pre_run_hook(),
                    "Expected _pre_run_hook to return True")
    self.assertIsNone(self.uut._post_run_hook(),
                      "Expected _post_run_hook to return None")

  def test_terminate(self):
    """Tests terminating a Switchboard process."""
    self.uut = switchboard_process.SwitchboardProcess(
        "fake_device", "some_process", self.exception_queue, self.command_queue)
    mock_process = mock.MagicMock(spec=multiprocessing.Process)
    self.uut._process = mock_process
    self.uut.terminate()
    mock_process.terminate.assert_called_once()
    mock_process.join.assert_called_once()
    self.assertIsNone(self.uut._process)


if __name__ == "__main__":
  unit_test_case.main()
