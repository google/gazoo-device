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

"""Module for GDM logger.

By default, GDM logger handles only a single (main) process.

GDM logger can handle multiple processes: to change to multiprocessing mode,
call switch_to_multiprocess_logging() and call
initialize_child_process_logging(<main process GDM logger queue>) in each child
process that needs to send GDM logs to the main process. The main process's
logger queue (obtained through get_logging_queue()) must be sent as an argument
to child processes.
"""
import atexit
import logging
import logging.handlers
import os
import sys
from typing import List

from gazoo_device import config
from gazoo_device import multiprocess_logging
from gazoo_device.utility import common_utils
from gazoo_device.utility import multiprocessing_utils

# Making this global enables user control of stdout streaming (indirectly)
_stdout_handler = None
# Logging queue to put messages into. Child processes will send their logs to
# this queue.
_logging_queue = None
# Logging thread consumes messages from the logging queue in the main process.
_logging_thread = None

# Log formats for debug
FMT = ('%(asctime)s.%(msecs)03d %(levelname).1s %(process)5d '
       '%(filename)19.19s:%(lineno)d\t%(message)s')
DATEFMT = '%Y%m%d %X'

dirname = os.path.dirname(config.DEFAULT_LOG_FILE)
if not os.path.isdir(dirname):
  os.makedirs(dirname)


def add_handler(handler):
  """Adds a logging handler to the LoggingThread.

  It receives messages sent to GDM Loggers in the main process and its child
  processes.

  Along with remove_handler, allows library users to configure extra
  destinations and formats for log messages emitted from within GDM.

  Args:
      handler (logging.handler): A logging handler
  """
  if _logging_thread:
    _logging_thread.add_handler(handler)
  else:
    get_logger().addHandler(handler)


def flush_queue_messages():
  """Waits until all messages currently in the logger queue are flushed."""
  if _logging_thread:
    _logging_thread.sync()


def get_handlers() -> List[logging.Handler]:
  """Returns the list of active logging handlers."""
  if is_multiprocess_logging_enabled():
    return _logging_thread.handlers
  else:
    return get_logger().handlers


def get_logging_queue():
  """Returns the logging queue used by the GDM logger."""
  return _logging_queue


def get_logger(component_name=None):
  """Returns a Logger that inherits from (or is) the top-level GDM Logger.

  Differs from usual getLogger in that the name given is appended to the name
  of the top-level GDM Logger (e.g. get_logger('component') is equivalent
  to logging.getLogger('gazoo_device_manager.component')), and also in that
  message strings passed to the returned Logger will be combined with the
  given args using .format() rather than %.

  Args:
      component_name (str): name of an GDM component. Nests using '.' char.

  Returns:
      logging.Logger: main logger or sub logger.
  """
  if component_name is not None:
    name = '.'.join(['gazoo_device_manager', component_name])
  else:
    name = 'gazoo_device_manager'

  return logging.getLogger(name)


def initialize_logger():
  """Configures the top-level GDM Logger.

  Configures it to begin logging to stdout and to the default log destination
  (config.DEFAULT_LOG_FILE).
  """
  logger = get_logger()
  logger.setLevel(logging.DEBUG)

  # Ensure no handlers remain during shutdown. GDM logger can log during __del__
  # calls for some objects. This can happen during shutdown. Logging during
  # shutdown can cause crashes in some environments.
  atexit.register(logger.handlers.clear)

  # Configure a handler that writes to GDM logfile
  filepath = config.DEFAULT_LOG_FILE
  args = dict(mode='a', maxBytes=100 * 1024 * 1023, backupCount=5)
  logfile_handler = logging.handlers.RotatingFileHandler(filepath, **args)
  logfile_handler.setLevel(logging.DEBUG)
  logfile_formatter = logging.Formatter(FMT, datefmt=DATEFMT)
  logfile_handler.setFormatter(logfile_formatter)
  logger.addHandler(logfile_handler)

  # Configure a handler that writes INFO logs to stdout
  stdout_handler = logging.StreamHandler(sys.stdout)
  stdout_handler.setLevel(logging.INFO)
  stdout_formatter = logging.Formatter('%(message)s')
  stdout_handler.setFormatter(stdout_formatter)
  logger.addHandler(stdout_handler)

  # Keep global copy of stdout_handler created and added above to allow for
  # changing the log level later for that handler.
  global _stdout_handler
  _stdout_handler = stdout_handler


def is_multiprocess_logging_enabled() -> bool:
  """Returns whether multiprocess logging is enabled."""
  return bool(_logging_queue or _logging_thread)


def switch_to_multiprocess_logging() -> None:
  """Initializes multiprocessing logging in the main process."""
  if is_multiprocess_logging_enabled():
    return

  global _logging_queue
  global _logging_thread
  _logging_queue = multiprocessing_utils.get_context().Queue()
  _logging_queue.cancel_join_thread()
  _logging_thread = multiprocess_logging.LoggingThread(_logging_queue)
  queue_handler = multiprocess_logging.QueueHandler(_logging_queue)
  queue_handler.setLevel(logging.DEBUG)

  logger = get_logger()
  for handler in logger.handlers:  # Transfer log handlers to queue handler.
    _logging_thread.add_handler(handler)
  logger.handlers = [queue_handler]
  if logger.propagate:  # Transfer message propagation to LoggingThread.
    _logging_thread.configure_propagate(logger.propagate, logger.parent)
    logger.propagate = False

  _logging_thread.start()
  atexit.register(common_utils.MethodWeakRef(_logging_thread.stop))


def initialize_child_process_logging(logging_queue):
  """Initializes multiprocessing logging in a child process.

  Used only by GDM child processes (created by Switchboard or parallel_utils),
  which need to use the logging queue sent over by the parent for logging.
  The child's only log handler sends all log messages to the logging queue to be
  logged by the parent.

  Args:
      logging_queue (Queue): multiprocessing queue to put log messages into.
  """
  global _logging_queue
  global _stdout_handler
  _logging_queue = logging_queue
  queue_handler = multiprocess_logging.QueueHandler(logging_queue)
  queue_handler.setLevel(logging.DEBUG)
  logger = get_logger()
  logger.handlers = [queue_handler]
  _stdout_handler = None


def reenable_progress_messages():
  """Reenables streaming GDM Logger messages to stdout."""
  if _stdout_handler:
    add_handler(_stdout_handler)


def remove_handler(handler):
  """Removes the given handler from the GDM Logger's LoggingThread.

  Messages sent to the GDM Logger will no longer be sent to that handler.

  Along with add_handler, allows library users to configure extra destinations
  and formats for log messages emitted from within GDM.

  Args:
      handler (logging.handler): A logging handler that was added earlier
        using add_handler
  """
  if _logging_thread:
    _logging_thread.remove_handler(handler)
  else:
    get_logger().removeHandler(handler)


def set_component_log_level(component_name, log_level):
  """Sets the log level for the named component.

  Args:
      component_name (str): name of an GDM component
      log_level (int): Integer log level, e.g. logging.DEBUG (value is 10)
  """
  logger = get_logger(component_name)
  logger.setLevel(log_level)


def silence_progress_messages():
  """Stops the default behavior of streaming GDM Logger messages to stdout."""
  if _stdout_handler:
    remove_handler(_stdout_handler)


def stream_debug():
  """Sets the log level for GDM Logger stdout streaming to DEBUG."""
  if _stdout_handler:
    fmt = logging.Formatter(FMT, datefmt=DATEFMT)
    _stdout_handler.setFormatter(fmt)
    _stdout_handler.setLevel(logging.DEBUG)
