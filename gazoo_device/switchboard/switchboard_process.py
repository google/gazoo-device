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

"""The minimum base class for switchboard subprocesses."""
import contextlib
import multiprocessing
import os
import queue
import signal
import socket
import time
import traceback
import typing

from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.utility import faulthandler_utils
from gazoo_device.utility import multiprocessing_utils
from gazoo_device.utility import retry
import psutil

_PROCESS_START_TIMEOUT_S = 30
_CHILD_PROCESS_COMMAND_CONSUMPTION_TIMEOUT_S = 3
_CHILD_PROCESS_POLLING_INTERVAL_S = 0.01


def get_message(message_queue, timeout=None):
  """Returns next message from message_queue.

  Args:
      message_queue (Queue): to retrieve next message from
      timeout (float): time to wait in seconds for incoming message to arrive.

  Raises:
      ValueError: if queue provided is not a valid queue object

  Returns:
      object: The message data or None if no messages were available or
              retrieved within timeout specified.
  """
  if message_queue is None or not hasattr(message_queue, "get"):
    raise ValueError("Invalid queue of {} provided".format(type(message_queue)))

  message = None
  try:
    message = message_queue.get(block=True, timeout=timeout)
    # manager shutdown or message_queue empty
  except (IOError, queue.Empty, ValueError, socket.error):
    pass
  return message


def put_message(message_queue, message, timeout=None):
  """Puts message into message_queue using the timeout specified.

  Args:
      message_queue (Queue): to add message to
      message (object): to write into the queue
      timeout (float): time to wait in seconds for outgoing message to be
        accepted into queue.

  Raises:
      ValueError: if message_queue provided is not valid or has no put method
      Queue.Full: if outgoing message_queue is full and timeout was provided and
                  was reached before message was sent.
  """
  if message_queue is None or not hasattr(message_queue, "put"):
    raise ValueError("Invalid queue of {} provided".format(type(message_queue)))

  try:
    message_queue.put(message, block=True, timeout=timeout)
  except (IOError, socket.error):  # manager shutdown
    pass


def wait_for_queue_writes(
    message_queue: multiprocessing.Queue, timeout: float = 1) -> None:
  """Wait until the message_queue background thread writes all pending message_queue messages.

  Args:
    message_queue: Queue to wait on.
    timeout: Max seconds to wait for the message_queue buffer to become empty.

  Raises:
    RuntimeError: If the message_queue buffer did not become empty
      in the given time.
  """
  queue_buffer = message_queue._buffer  # pylint: disable=protected-access  # pytype:disable=attribute-error
  deadline = time.time() + timeout
  while time.time() < deadline and queue_buffer:
    time.sleep(0.01)
  if queue_buffer:
    raise RuntimeError(
        f"Buffer of queue {message_queue} didn't get flushed in {timeout}s.")


@contextlib.contextmanager
def _child_process_wrapper(parent_pid, process_name, device_name,
                           exception_queue):
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
                                 "{}".format(device_name, process_name,
                                             stack_trace))
      # Wait until the queue background thread has sent the message before
      # notifying the parent process.
      wait_for_queue_writes(exception_queue)
      os.kill(parent_pid, signal.SIGUSR1)
    except (IOError, OSError):  # queue or parent process doesn't exist anymore
      pass


def _parent_is_alive(parent_pid):
  status = False
  try:
    status = psutil.Process(parent_pid).status() != psutil.STATUS_ZOMBIE
  except psutil.NoSuchProcess:  # parent process doesn't exist anymore
    pass
  return status


def _process_loop(cls, parent_pid):
  """Child process loop which handles start/stop events and exceptions."""
  with _child_process_wrapper(parent_pid, cls.process_name, cls.device_name,
                              cls._exception_queue):
    faulthandler_utils.set_up_faulthandler(
        typing.cast(str, cls._log_directory),  # pylint: disable=protected-access
        log_file_name_prefix=f"{cls.device_name}_{type(cls).__name__}_parent_"
                             f"{parent_pid}_child")
    gdm_logger.initialize_child_process_logging(cls.logging_queue)
    try:
      cls._start_event.set()
    except Exception as err:
      stack_trace = traceback.format_exc()
      gdm_logger.get_logger().info(
          "Device {} Process {} error {!r} start event error. {}".format(
              cls.device_name, cls.process_name, err, stack_trace))
    running = cls._pre_run_hook()
    while running and _parent_is_alive(parent_pid):
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


class SwitchboardProcess:
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

  def __init__(self,
               device_name,
               process_name,
               exception_queue,
               command_queue,
               log_path,
               valid_commands=None):
    """Initialize SwitchboardProcess with the arguments provided.

    Args:
        device_name (str): of the device for exception error messages.
        process_name (str): to use for process name and exception error
          messages.
        exception_queue (Queue): to use for reporting exception traceback
          message from subprocess.
        command_queue (Queue): to receive commands into.
        log_path (str): path and filename to write log messages to.
        valid_commands (Optional[Tuple[str, ...]]): Valid command strings.
    """
    log_directory = os.path.dirname(log_path)
    self.device_name = device_name
    self.process_name = process_name
    self._command_queue = command_queue
    self._exception_queue = exception_queue
    self._log_directory = log_directory
    gdm_logger.switch_to_multiprocess_logging()
    self.logging_queue = gdm_logger.get_logging_queue()
    self._start_event = multiprocessing_utils.get_context().Event()
    self._stop_event = multiprocessing_utils.get_context().Event()
    self._terminate_event = multiprocessing_utils.get_context().Event()
    self._valid_commands = valid_commands or ()
    self._process = None

  def __del__(self):
    if self.is_started():
      self.stop()

  def start(self, wait_for_start: bool = True) -> None:
    """Starts the process.

    Args:
        wait_for_start: Whether to wait for the process to start. If False, the
            caller is responsible for calling wait_for_start() separately.

    Raises:
        RuntimeError: if the process has already been started or fails to start.
    """
    if not self.is_started():
      self._start_event.clear()
      self._stop_event.clear()
      parent_pid = os.getpid()
      process = multiprocessing_utils.get_context().Process(  # pytype: disable=attribute-error  # re-none
          name=self.process_name,
          target=_process_loop,
          args=(self, parent_pid))
      process.start()
      if wait_for_start:
        self.wait_for_start()
      self._process = process
    else:
      raise RuntimeError("Device {} failed to start child process {}. "
                         "Child process is already running.".format(
                             self.device_name, self.process_name))

  def wait_for_start(self) -> None:
    """Waits for the process to start.

    Raises:
      RuntimeError: process failed to start before a timeout was reached.
    """
    start_event_value = self._start_event.wait(timeout=_PROCESS_START_TIMEOUT_S)
    if not start_event_value:
      per_core_cpu_utilization = psutil.cpu_percent(interval=0.1, percpu=True)
      per_core_cpu_utilization_formatted = [
          f"{value:.1f}%" for value in per_core_cpu_utilization]
      num_cores = len(per_core_cpu_utilization)
      avg_cpu_utilization = sum(per_core_cpu_utilization) / num_cores
      # Average load for the last 1 minute, 5 minutes, 15 minutes.
      # The "load" is defined as the average number of processes in a runnable
      # state per CPU core. Load over 100% indicates throttling.
      avg_historic_load = [f"{load / num_cores * 100:.1f}%"
                           for load in psutil.getloadavg()]
      raise RuntimeError(
          f"{self.device_name} failed to start child process "
          f"{self.process_name}. "
          f"Start event was not set in {_PROCESS_START_TIMEOUT_S}s. "
          "This typically means that the test binary has not been allocated a "
          "sufficient share of the host's CPU. Common causes: too many "
          "simultaneous task executions or process leaks from previous tests.\n"
          "Check the host CPU utilization and active processes by running "
          "'top' on the host. Also check the CPU model and frequency via "
          "'lscpu'.\n"
          "Diagnostic information: "
          f"host CPU cores: {num_cores}, "
          f"current combined CPU load: {avg_cpu_utilization:.1f}, "
          f"current per-core CPU load: {per_core_cpu_utilization_formatted}, "
          "average combined CPU load in the last 1 minute, 5 minutes, 15 "
          f"minutes: {avg_historic_load}. Load over 100% indicates throttling.")

  def is_started(self):
    """Returns True if process was started, False otherwise.

    Return:
        bool: True if process was started
    """
    return self._process is not None

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

  def send_command(self, command, data=None,
                   wait_for_command_consumption: bool = False):
    """Sends command with optional data provided.

    Args:
        command (str): string to send
        data (object): optional data to include with command.
        wait_for_command_consumption: wait until command is consummed.

    Raises:
        ValueError: if command provided is not in the list of valid commands
    """
    if command not in self._valid_commands:
      raise ValueError("Device {} send command to child process {} failed. "
                       "{} is not a valid command in {!r}".format(
                           self.device_name, self.process_name, command,
                           self._valid_commands))
    put_message(self._command_queue, (command, data))
    if wait_for_command_consumption:
      try:
        retry.retry(
            func=self.is_command_consumed,
            is_successful=retry.is_true,
            timeout=_CHILD_PROCESS_COMMAND_CONSUMPTION_TIMEOUT_S,
            interval=_CHILD_PROCESS_POLLING_INTERVAL_S)
      except errors.CommunicationTimeoutError as err:
        self.stop()
        raise errors.ProcessCommunicationError(
            self.device_name,
            "Device {} Process {} command {} consumption timed out. "
            "Stopped the process.".format(
                self.device_name, self.process_name, command)) from err

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
                 "Stop event was not set.").format(self.device_name,
                                                   self.process_name)
          gdm_logger.get_logger().error(msg)
          raise IOError(msg)
      except (IOError, ValueError):  # manager shutdown failed
        pass
      self._process.join(timeout=1)
      if self._process.is_alive():
        self.terminate()
      else:
        self._process = None
    else:
      msg = ("Device {} failed to stop child process {}. Child process is not "
             "currently running.").format(self.device_name, self.process_name)
      gdm_logger.get_logger().error(msg)
      raise RuntimeError(msg)

  def terminate(self):
    """Terminates the process."""
    self._process.terminate()
    self._process.join(timeout=1)
    self._process = None

  def is_command_consumed(self):
    """Returns True if command queue is empty, false otherwise.

    This does not guarantee that the command processing is complete, only that
    it has started.

    Returns:
      bool: True if command queue is empty.
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
        Try to avoid raising any exceptions from this method as any exception
        raised will not reach the main process.
    """
    pass

  def _pre_run_hook(self):
    """Setup hook for derived classes before child process run loop begins.

    Returns:
        bool: A boolean value indicating the process loop should proceed.

    Note:
        Returning None or False from this method will prevent the process loop
        from proceeding.
    """
    return True
