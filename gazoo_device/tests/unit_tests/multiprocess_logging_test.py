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

"""Unit tests for multiprocess_logging.py."""
import gc
import logging
import sys
import threading
from unittest import mock
from gazoo_device import multiprocess_logging
from gazoo_device.tests.unit_tests.utils import unit_test_case


class _MockGCState:

  def __init__(self):
    self.enabled = True

  def isenabled(self):
    return self.enabled

  def enable(self):
    self.enabled = True

  def disable(self):
    self.enabled = False


def _mock_put_nowait_gc_disabled(_):
  assert not gc.isenabled()


def _mock_put_nowait_gc_enabled(_):
  assert gc.isenabled()


def _handle_error(record):
  _, err, _ = sys.exc_info()
  raise AssertionError(
      "Error {!r} occurred while processing record {!r}".format(err, record))


class LoggingThreadTests(unit_test_case.UnitTestCase):

  def setUp(self):
    super().setUp()

    self.mock_queue = mock.Mock()
    self.mock_sync_event = mock.Mock()
    self.mock_handler = mock.Mock()
    self.mock_handler.level = logging.INFO
    self.mock_thread = mock.Mock()

    with mock.patch.object(
        threading, "Event", return_value=self.mock_sync_event):
      self.uut = multiprocess_logging.LoggingThread(self.mock_queue)
    self.uut.add_handler(self.mock_handler)
    with mock.patch.object(threading, "Thread", return_value=self.mock_thread):
      self.uut.start()

  def test_run_terminate_sentinel_found(self):
    """Test that the logging thread correctly handles terminate sentinel in logging queue."""
    self.mock_queue.get.side_effect = [multiprocess_logging._Sentinel.TERMINATE]
    self.uut._run(self.mock_queue, self.mock_sync_event)
    self.mock_sync_event.set.assert_not_called()

  def test_run_sync_sentinel_found(self):
    """Test that the logging thread correctly handles sync sentinel in logging queue."""
    self.mock_queue.get.side_effect = [
        multiprocess_logging._Sentinel.SYNC,
        multiprocess_logging._Sentinel.TERMINATE
    ]
    self.uut._run(self.mock_queue, self.mock_sync_event)
    self.mock_sync_event.set.assert_called_once()

  def test_run_processed_record_logged(self):
    """Test that the logging thread logs records if record level >= handler level."""
    self.mock_handler.level = logging.INFO

    for record_level in [
        logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL
    ]:
      self.mock_handler.reset_mock()
      mock_record = mock.Mock()
      mock_record.levelno = record_level

      self.mock_queue.get.side_effect = [
          mock_record, multiprocess_logging._Sentinel.TERMINATE
      ]
      self.uut._run(self.mock_queue, self.mock_sync_event)
      self.mock_sync_event.set.assert_not_called()
      self.mock_handler.handle.assert_called_once_with(mock_record)

  def test_run_processed_record_not_logged(self):
    """Test that the logging thread doesn't log records if record level < handler level."""
    self.mock_handler.level = logging.INFO
    mock_record = mock.Mock()
    mock_record.levelno = logging.DEBUG

    self.mock_queue.get.side_effect = [
        mock_record, multiprocess_logging._Sentinel.TERMINATE
    ]
    self.uut._run(self.mock_queue, self.mock_sync_event)
    self.mock_sync_event.set.assert_not_called()
    self.mock_handler.handle.assert_not_called()

  def test_sync_success(self):
    """Test successful synchronization of the logging thread."""
    self.mock_sync_event.wait.side_effect = [True]
    self.uut.sync()
    self.mock_queue.put_nowait.assert_called_once_with(
        multiprocess_logging._Sentinel.SYNC)
    self.mock_sync_event.wait.assert_called_once()
    self.mock_sync_event.clear.assert_called_once()

  def test_sync_timeout(self):
    """Test timeout of synchronization of the logging thread."""
    self.mock_sync_event.wait.side_effect = [False]
    with mock.patch.object(
        sys, "stderr", new_callable=mock.PropertyMock) as mock_stderr:
      self.uut.sync()

    err_msg = (
        "Warning: Logging thread did not reach the synchronization sentinel in"
        " {}s"
        .format(multiprocess_logging.SYNC_TIMEOUT))
    mock_stderr.write.assert_has_calls([mock.call(err_msg)])
    self.mock_queue.put_nowait.assert_called_once_with(
        multiprocess_logging._Sentinel.SYNC)
    self.mock_sync_event.wait.assert_called_once()
    self.mock_sync_event.clear.assert_called_once()

  def test_sync_thread_is_none(self):
    """Test LoggingThread.sync() when logging thread has not been created."""
    self.uut._thread = None
    self.uut.sync()
    self.mock_queue.put_nowait.assert_not_called()

  def test_sync_thread_is_not_alive(self):
    """Test LoggingThread.sync() when logging thread is not alive."""
    self.uut._thread.is_alive.return_value = False
    self.uut.sync()
    self.mock_queue.put_nowait.assert_not_called()

  def test_sync_thread_is_not_main_thread(self):
    """Test LoggingThread.sync() when called from thread other than the main thread."""
    with mock.patch.object(
        threading, "current_thread",
        return_value=threading.Thread(target=self.uut._run)):
      self.uut.sync()
    self.mock_queue.put_nowait.assert_not_called()

  def test_stop_success(self):
    """Test successful LoggingThread.stop."""
    self.mock_thread.is_alive.side_effect = [False]
    self.uut.stop()

    self.mock_queue.put_nowait.assert_called_once_with(
        multiprocess_logging._Sentinel.TERMINATE)
    self.mock_thread.join.assert_called_once_with(
        timeout=multiprocess_logging.TERMINATE_TIMEOUT)

  def test_stop_twice(self):
    """Test calling LoggingThread.stop twice."""
    self.mock_thread.is_alive.side_effect = [False]
    self.uut.stop()
    self.uut.stop()

    self.mock_queue.put_nowait.assert_called_once_with(
        multiprocess_logging._Sentinel.TERMINATE)
    self.mock_thread.join.assert_called_once_with(
        timeout=multiprocess_logging.TERMINATE_TIMEOUT)

  def test_stop_failure(self):
    """Test LoggingThread.stop failure (thread is still alive)."""
    self.mock_thread.is_alive.side_effect = [True]
    err_msg = "Failed to stop LoggingThread in {}s".format(
        multiprocess_logging.TERMINATE_TIMEOUT)

    with self.assertRaisesRegex(RuntimeError, err_msg):
      self.uut.stop()

    self.mock_queue.put_nowait.assert_called_once_with(
        multiprocess_logging._Sentinel.TERMINATE)
    self.mock_thread.join.assert_called_once_with(
        timeout=multiprocess_logging.TERMINATE_TIMEOUT)


class MultiprocessLoggingTests(unit_test_case.UnitTestCase):

  def setUp(self):
    super().setUp()
    self.mock_queue = mock.Mock()
    self.mock_queue.put_nowait.side_effect = _mock_put_nowait_gc_disabled

    self.uut = multiprocess_logging.QueueHandler(self.mock_queue)
    self.uut.format = mock.Mock()
    self.uut.handleError = _handle_error

    # Prevent actual garbage collection from interacting with the mocks
    gc.disable()
    self.addCleanup(gc.enable)

    self._actual_gc_callbacks = None
    if hasattr(gc, "callbacks"):
      self._actual_gc_callbacks = gc.callbacks
      gc.callbacks = []
    self.addCleanup(self._restore_gc_callbacks)

    self.mock_gc = _MockGCState()
    gc_isenabled_patcher = mock.patch.object(
        gc, "isenabled", wraps=self.mock_gc.isenabled)
    gc_enable_patcher = mock.patch.object(
        gc, "enable", wraps=self.mock_gc.enable)
    gc_disable_patcher = mock.patch.object(
        gc, "disable", wraps=self.mock_gc.disable)
    self._gc_patchers = [
        gc_isenabled_patcher, gc_enable_patcher, gc_disable_patcher
    ]
    self.mock_isenabled = gc_isenabled_patcher.start()
    self.mock_enable = gc_enable_patcher.start()
    self.mock_disable = gc_disable_patcher.start()
    self.addCleanup(self._stop_gc_patchers)

  def _stop_gc_patchers(self):
    for patcher in self._gc_patchers:
      patcher.stop()

  def _restore_gc_callbacks(self):
    if self._actual_gc_callbacks is not None:
      gc.callbacks = self._actual_gc_callbacks

  def test_disable_reenable_if_enabled_not_during_gc(self):
    self.mock_gc.enable()
    multiprocess_logging.DisablePeriodicGC._track_gc_state("stop", "")

    self.assertTrue(self.mock_gc.isenabled())
    self.uut.emit(mock.Mock())
    self.assertTrue(self.mock_gc.isenabled())

    self.mock_disable.assert_called_once()
    self.mock_enable.assert_called_once()

  def test_no_disable_and_reenable_if_disabled_not_during_gc(self):
    self.mock_gc.disable()
    multiprocess_logging.DisablePeriodicGC._track_gc_state("stop", "")

    self.assertFalse(self.mock_gc.isenabled())
    self.uut.emit(mock.Mock())
    self.assertFalse(self.mock_gc.isenabled())

    self.mock_disable.assert_not_called()
    self.mock_enable.assert_not_called()

  def test_no_disable_reenable_if_enabled_during_gc(self):
    self.mock_gc.enable()
    multiprocess_logging.DisablePeriodicGC._track_gc_state("start", "")
    self.mock_queue.put_nowait.side_effect = _mock_put_nowait_gc_enabled

    self.assertTrue(self.mock_gc.isenabled())
    self.uut.emit(mock.Mock())
    self.assertTrue(self.mock_gc.isenabled())

    self.mock_disable.assert_not_called()
    self.mock_enable.assert_not_called()

if __name__ == "__main__":
  unit_test_case.main()

