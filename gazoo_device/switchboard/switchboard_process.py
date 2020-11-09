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

"""The minimum base class for switchboard subprocesses."""
from __future__ import absolute_import
import contextlib
import multiprocessing
import os
import six.moves.queue
import signal
import socket
import traceback

import psutil

from gazoo_device import gdm_logger
from gazoo_device.utility import common_utils

logger = gdm_logger.get_gdm_logger()


def get_message(queue, timeout=None):
    """Returns next message from queue.

    Args:
        queue (Queue): to retrieve next message from
        timeout (float): time to wait in seconds for incoming message to arrive.

    Raises:
        ValueError: if queue provided is not a valid queue object

    Returns:
        object: The message data or None if no messages were available or
                retrieved within timeout specified.
    """

    if queue is None or not hasattr(queue, "get") or not hasattr(queue, "task_done"):
        raise ValueError("Invalid queue of {} provided".
                         format(type(queue)))

    message = None
    try:
        message = queue.get(block=True, timeout=timeout)
        queue.task_done()
        # manager shutdown or queue empty
    except (IOError, six.moves.queue.Empty, ValueError, socket.error):
        pass
    return message


def put_message(queue, message, timeout=None):
    """Puts message into queue using the timeout specified.

    Args:
        queue (Queue): to add message to
        message (object): to write into the queue
        timeout (float): time to wait in seconds for outgoing message to
                         be accepted into queue.

    Raises:
        ValueError: if queue provided is not valid or has no put method
        Queue.Full: if outgoing queue is full and timeout was provided and was
                    reached before message was sent.
    """
    if queue is None or not hasattr(queue, "put"):
        raise ValueError("Invalid queue of {} provided".
                         format(type(queue)))

    try:
        queue.put(message, block=True, timeout=timeout)
    except (IOError, socket.error):  # manager shutdown
        pass


@contextlib.contextmanager
def _child_process_wrapper(parent_proc, process_name, device_name, exception_queue):
    """Wrapper to ignore interrupts in child processes; the main process handles cleanup."""
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    try:
        yield
    except EOFError:  # parent process has terminated
        pass
    except Exception:
        stack_trace = traceback.format_exc()
        try:
            exception_queue.put_nowait("Device {} raised exception in {}. "
                                       "{}".
                                       format(device_name,
                                              process_name,
                                              stack_trace))
            os.kill(parent_proc.pid, signal.SIGUSR1)
        except (IOError, OSError):  # queue or parent process doesn't exist anymore
            pass


def _parent_is_alive(parent_proc):
    status = False
    try:
        status = parent_proc.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:  # parent process doesn't exist anymore
        pass
    return status


def _process_loop(cls, parent_proc):
    """Child process loop which handles start/stop events and exceptions."""
    with _child_process_wrapper(parent_proc,
                                cls.process_name,
                                cls.device_name,
                                cls._exception_queue):
        try:
            cls._start_event.set()
        except Exception as err:
            stack_trace = traceback.format_exc()
            logger.info("Device {} Process {} error {!r} "
                        "start event error. {}".
                        format(cls.device_name,
                               cls.process_name,
                               err,
                               stack_trace))
        running = cls._pre_run_hook()
        while running and _parent_is_alive(parent_proc):
            try:
                if cls._terminate_event.is_set():
                    cls._terminate_event.clear()
                    break
            except IOError:  # manager shutdown
                break
            running = cls._do_work()
    try:
        cls._stop_event.set()
    except IOError:  # manager shutdown
        pass
    cls._post_run_hook()


class SwitchboardProcess(object):
    """Simplifies creating Switchboard processes.

    Provides the following capabilities:
        * starting and verifying process start
        * stopping and verifying process stop
        * checking if process was started
        * checking if process is still running
        * providing pre and post process loop hooks
        * signaling main process when exceptions are raised in subprocess
        * receiving queue commands with optional data to be processed
        * Simplifying process loop definition for subclasses
    """

    def __init__(self, device_name, process_name, mp_manager, exception_queue,
                 command_queue, valid_commands=None):
        """Initialize SwitchboardProcess with the arguments provided.

        Args:
            device_name (str): of the device for exception error messages
            process_name (str): to use for process name and exception error messages
            mp_manager (multiprocessing.Manager): object to use for creating Events
            exception_queue (Queue): to use for reporting exception traceback
                                     message from subprocess
            command_queue (Queue): to receive commands into
            valid_commands (list): optional list of valid command strings
        """

        self.device_name = device_name
        self.process_name = process_name
        self._command_queue = command_queue
        self._exception_queue = exception_queue
        self._start_event = mp_manager.Event()
        self._stop_event = mp_manager.Event()
        self._terminate_event = mp_manager.Event()
        self._valid_commands = valid_commands or []

    def __del__(self):
        if self.is_started():
            self.stop()

    def start(self):
        """Starts process if process is not already running.

        Raises:
            RuntimeError: if called when process is already running

        Note:
            When calling this method you should use is_started() to check if
            process was previously started to prevent raising an error.
        """

        if not self.is_started():
            parent_proc = psutil.Process(os.getpid())
            self._start_event.clear()
            self._stop_event.clear()
            process = multiprocessing.Process(name=self.process_name,
                                              target=_process_loop,
                                              args=(self, parent_proc))
            common_utils.run_before_fork()
            process.start()
            common_utils.run_after_fork_in_parent()
            start_event_value = self._start_event.wait(timeout=5)
            if not start_event_value:
                raise RuntimeError("Device {} failed to start child process {}. "
                                   "Start event was not set."
                                   .format(self.device_name, self.process_name))
            self._process = process
        else:
            raise RuntimeError("Device {} failed to start child process {}. "
                               "Child process is already running.".
                               format(self.device_name, self.process_name))

    def is_started(self):
        """Returns True if process was started, False otherwise.

        Return:
            bool: True if process was started
        """

        return hasattr(self, "_process")

    def is_running(self):
        """Returns True if process is currently running, False otherwise.

        Return:
            bool: True if process was started and is currently running

        Note:
            Use this method to determine if a process is still running, since
            the process might choose to self exit.
        """

        if self.is_started():
            return self._process.is_alive()
        return False

    def send_command(self, command, data=None):
        """Sends command with optional data provided.

        Args:
            command (str): string to send
            data (object): optional data to include with command.

        Raises:
            ValueError: if command provided is not in the list of valid commands
        """

        if command not in self._valid_commands:
            raise ValueError("Device {} send command to child process {} failed. "
                             "{} is not a valid command in {!r}".
                             format(self.device_name,
                                    self.process_name,
                                    command,
                                    self._valid_commands))
        put_message(self._command_queue, (command, data))

    def stop(self):
        """Stops process if process is running.

        Raises:
            RuntimeError: if called when process is not currently running
            OSError: if a system related exception occurs.

        Note:
            When calling this method you should use is_started() to check if
            process was previously started to prevent raising an error.
        """

        if self.is_started():
            if self._process.is_alive():
                try:
                    self._terminate_event.set()
                except IOError:  # manager shutdown
                    pass
            try:
                stop_event_value = self._stop_event.wait(timeout=5)
                if not stop_event_value:
                    msg = ("Device {} failed to stop child process {}. "
                           "Stop event was not set.").format(self.device_name, self.process_name)
                    logger.error(msg)
                    raise IOError(msg)
            except (IOError, ValueError):  # manager shutdown failed
                pass
            self._process.join(timeout=1)
            if self._process.is_alive():
                self._process.terminate()
            delattr(self, "_process")
        else:
            msg = ("Device {} failed to stop child process {}. Child process is not "
                   "currently running.").format(self.device_name, self.process_name)
            logger.error(msg)
            raise RuntimeError(msg)

    def is_command_done(self):
        """Returns True if command queue is empty, false otherwise.

        Returns:
            bool: True if command queue is empty
        """

        return self._command_queue.empty()

    def _do_work(self):
        """Perform subprocess work and indicate if process should continue.

        Returns:
            bool: indicating process should continue running

        Note:
            This implementation just returns False.
        """

        return False

    def _post_run_hook(self):
        """Cleanup hook for derived classes after process terminates.

        Note:
            Try to avoid raising any exceptions from this method as any
            exception raised will not reach the main process.
        """

        pass

    def _pre_run_hook(self):
        """Setup hook for derived classes before child process run loop begins.

        Returns:
            bool: A boolean value indicating the process loop should proceed.

        Note:
            Returning None or False from this method will prevent the process
            loop from proceeding.
        """

        return True
