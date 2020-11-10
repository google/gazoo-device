# Copyright 2020 Google LLC
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

"""Enables logging from multiple processes.

Step 1: Initialize a queue in the main process.
Step 2: Pass that queue to a LoggingThread object.
Step 3: Add handlers (StreamHandler, FileHandler, etc) to the LoggingThread.
Step 4: In each process, initialize a QueueHandler and add it to a Logger.
Step 5: Send messages to the Logger.

Messages travel from the Logger, to the QueueHandler, into the LoggingThread's
child thread via the queue, then into the destination handlers.

Adapted from the implementation in Python 3.5.
"""

from __future__ import absolute_import
from __future__ import print_function
import gc
import logging
import sys
import threading

SYNC_TIMEOUT = 0.25
TERMINATE_TIMEOUT = 2


class _Sentinel(object):
    """Sentinels to put in the queue to signal certain events."""
    TERMINATE = 0
    SYNC = 1


class DisablePeriodicGC(object):
    """Context manager for disabling & re-enabling periodic garbage collection.

    Note: will not disable periodic GC if called during periodic garbage collection.
    See b/143321081 for why logging during __del__ can deadlock if periodic GC is not disabled.
    """
    is_periodic_gc_active = False

    @classmethod
    def _track_gc_state(cls, phase, _):
        if phase == "start":
            cls.is_periodic_gc_active = True
        elif phase == "stop":
            cls.is_periodic_gc_active = False

    def __enter__(self):
        """Enter the context manager & disable periodic GC."""
        self._was_periodic_gc_enabled = gc.isenabled()
        if self._was_periodic_gc_enabled and not self.is_periodic_gc_active:
            gc.disable()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """Exit the context manager & re-enable periodic GC (if it had been enabled before)."""
        if self._was_periodic_gc_enabled and not self.is_periodic_gc_active:
            gc.enable()


if hasattr(gc, "callbacks"):  # Available in Python 3 only
    gc.callbacks.append(DisablePeriodicGC._track_gc_state)


class QueueHandler(logging.Handler):
    """Receives all messages destined for the handlers in LoggingThread."""

    def __init__(self, queue):
        logging.Handler.__init__(self)
        self._queue = queue

    def emit(self, record):
        try:
            self.format(record)
            record.msg = record.message
            record.args = None
            record.exc_info = None

            with DisablePeriodicGC():
                self._queue.put_nowait(record)

        except Exception:
            self.handleError(record)


class LoggingThread(object):
    """Runs in main process and pulls log messages from the shared queue."""

    def __init__(self, queue):
        self._handlers = []
        self._queue = queue
        self._thread = None
        self._synchonize_event = threading.Event()

    def add_handler(self, handler):
        """Adds a logging handler to the LoggingThread.

        Args:
            handler (logging.Handler): logging handler to add to the logging queue handlers.

        The handler will receive messages that are placed on the shared queue by QueueHandlers.
        """

        self._handlers.append(handler)

    def remove_handler(self, handler):
        """Removes the given logging handler from the LoggingThread."""

        try:
            self._handlers.remove(handler)
        except ValueError:
            pass

    def start(self):
        """Starts the child thread, which pulls messages from the queue."""

        self._thread = threading.Thread(target=self._run,
                                        args=[self._queue, self._synchonize_event])
        self._thread.daemon = True
        self._thread.start()

    def stop(self):
        """Signals to the child thread to stop by putting None on the queue.

        Raises:
          RuntimeError: Thread alive after attempt to stop it.
        """

        if self._thread:
            with DisablePeriodicGC():
                self._queue.put_nowait(_Sentinel.TERMINATE)
            self._thread.join(timeout=TERMINATE_TIMEOUT)

            if self._thread.is_alive():
                raise RuntimeError('Failed to stop LoggingThread in {}s'.format(TERMINATE_TIMEOUT))

        self._thread = None

    def sync(self, timeout=SYNC_TIMEOUT):
        """Put a sentinel in the message queue and block until the logging thread reaches it.

        Args:
            timeout (float): maximum time to wait for logging thread to reach the synchronization
                             sentinel.

        Note:
            Does nothing in child (forked) processes because logging thread is not copied over
            by os.fork().
            Also does nothing if called in any thread other than the main thread.
        """
        if (self._thread is not None and self._thread.is_alive()
                and isinstance(threading.current_thread(), threading._MainThread)):
            with DisablePeriodicGC():
                self._queue.put_nowait(_Sentinel.SYNC)
            if not self._synchonize_event.wait(timeout):
                print("Warning: Logging thread did not reach the synchronization sentinel in {}s"
                      .format(timeout), file=sys.stderr)
            self._synchonize_event.clear()

    def _run(self, queue, synchronize_event):
        """Runs as a child thread.

        Args:
            queue (multiprocessing.Queue): multiprocess queue to receive log messages from.
            synchronize_event (threading.Event): event used for synchronization with the main
                                                 execution thread.

        Continuously receiving messages placed on the
        queue by QueueHandlers. Passes messages to each of the LoggingThread's
        handlers. Stops when None is found on the queue.
        """

        while True:
            record = queue.get()

            if record == _Sentinel.TERMINATE:
                break
            elif record == _Sentinel.SYNC:
                synchronize_event.set()
            else:
                for handler in self._handlers:
                    if record.levelno >= handler.level:
                        handler.handle(record)
