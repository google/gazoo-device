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

"""Module for GDM logger."""
from __future__ import absolute_import
import atexit
import logging
import logging.handlers
import os
import re
import sys
import types
import multiprocessing as mp
from gazoo_device import multiprocess_logging
from gazoo_device.config import DEFAULT_LOG_FILE
import six

# Making this global enables user control of stdout streaming (indirectly)
_stdout_handler = None

# Log formats for debug
FMT = ("%(asctime)s.%(msecs)03d %(levelname).1s %(process)5d "
       "%(filename)19.19s:%(lineno)d\t%(message)s")
DATEFMT = '%Y%m%d %X'

dirname = os.path.dirname(DEFAULT_LOG_FILE)
if not os.path.isdir(dirname):
    os.makedirs(dirname)


def add_handler(handler):
    """Adds a logging handler to the LoggingThread.

    It receives messages sent to GDM Loggers in the main process and its subprocesses.

    Along with remove_handler, allows library users to configure extra
    destinations and formats for log messages emitted from within GDM.

    Args:
        handler (logging.handler): A logging handler
    """
    logger = get_gdm_logger()
    logger.logging_thread.add_handler(handler)


def create_queue_handler(log_level):
    """Adds a QueueHandler to the top-level gazoo_device_manager logger.

    Should be used once per process, and will be the only handler on an GDM
    logger object in a given process. Destination handlers are added instead to
    the LoggingThread object via add_handler().

    Args:
        log_level (int): Integer log level, e.g. logging.DEBUG (value is 10)
    """
    logger = get_gdm_logger()
    handler = multiprocess_logging.QueueHandler(logger.logging_queue)
    handler.setLevel(log_level)
    logger.handlers = [handler]


def flush_queue_messages():
    """Wait until all messages currently in the logger queue are flushed."""
    get_gdm_logger().logging_thread.sync()


def get_gdm_logger(component_name=None):
    """Returns a Logger that inherits from (or is) the top-level GDM Logger.

    Differs from usual getLogger in that the name given is appended to the name
    of the top-level GDM Logger (e.g. get_gdm_logger('component') is equivalent
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

    logger = logging.getLogger(name)

    # Override _log with our own _brace_format_log
    if not hasattr(logger, '_original_log'):
        logger._original_log = logger._log
        logger._log = types.MethodType(_brace_format_log, logger)

    return logger


def initialize_logger():
    """Configures the top-level GDM Logger.

    Configures it to begin logging to stdout and to the
    default log destination (e.g. /gazoo/gdm/log/gdm.txt).
    """
    # Set up multiprocess logging thread
    logging_queue = mp.Queue(-1)
    logging_queue.cancel_join_thread()
    logging_thread = multiprocess_logging.LoggingThread(logging_queue)
    atexit.register(logging_thread.stop)

    # Set up core GDM logger
    logger = get_gdm_logger()
    logger.setLevel(logging.DEBUG)
    logger.logging_queue = logging_queue
    logger.logging_thread = logging_thread

    # Create handler for core GDM logger in main process
    create_queue_handler(logging.DEBUG)

    # Configure a handler that writes to GDM logfile
    filepath = DEFAULT_LOG_FILE
    args = dict(mode='a', maxBytes=100 * 1024 * 1023, backupCount=5)
    logfile_handler = logging.handlers.RotatingFileHandler(filepath, **args)
    logfile_handler.setLevel(logging.DEBUG)
    logfile_formatter = logging.Formatter(FMT, datefmt=DATEFMT)
    logfile_handler.setFormatter(logfile_formatter)
    add_handler(logfile_handler)

    # Configure a handler that writes INFO logs to stdout
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    stdout_formatter = logging.Formatter('%(message)s')
    stdout_handler.setFormatter(stdout_formatter)
    add_handler(stdout_handler)

    # Keep global copy of stdout_handler created and added above to allow for
    # changing the log level later for that handler.
    global _stdout_handler
    _stdout_handler = stdout_handler

    logging_thread.start()


def remove_handler(handler):
    """Removes the given handler from the GDM Logger's LoggingThread.

    Messages sent to the GDM Logger will no longer be sent to that handler.

    Along with add_handler, allows library users to configure extra destinations
    and formats for log messages emitted from within GDM.

    Args:
        handler (logging.handler): A logging handler that was added earlier using add_handler
    """
    logger = get_gdm_logger()
    logger.logging_thread.remove_handler(handler)


def set_component_log_level(component_name, log_level):
    """Sets the log level for the named component.

    Args:
        component_name (str): name of an GDM component
        log_level (int): Integer log level, e.g. logging.DEBUG (value is 10)
    """
    logger = get_gdm_logger(component_name)
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


def _brace_format_log(self, level, msg, args, exc_info=None, extra=None, **kwargs):
    """Enables brace logging for GDM Loggers (by overriding Logger._log)."""
    # Combines msg with args and kwargs using .format(),
    # saving special kwargs exc_info and extra for original _log method
    if args or kwargs:
        formatted_msg = str(msg).format(*args, **kwargs)
    else:
        formatted_msg = str(msg)

    new_kwargs = dict(exc_info=exc_info, extra=extra)

    self._original_log(level, formatted_msg, (), **new_kwargs)


class LogData(object):
    """Stores data to be added to log lines and automatically formatted."""

    key_pattern = re.compile(r'\W')

    def __init__(self, **items):
        self.items = items

    def __str__(self):
        r"""Formats data items into the form '##\tkey1=value1\tkey2=value2'.

        In keys, strips non-alphanumeric characters.
        In values, replaces escape char / and delimiters \t, = with /0, /1, /2.

        Returns:
          str: data as string.
        """
        strings = ['##']

        for k, v in six.iteritems(self.items):
            key = self.key_pattern.sub('', str(k))
            val = str(v).replace('/', '/0').replace('\t', '/1').replace('=', '/2')
            key_val_string = '='.join([key, val])
            strings.append(key_val_string)

        return '\t'.join(strings)
