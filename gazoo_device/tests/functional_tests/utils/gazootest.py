# Copyright 2021 Google LLC
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

"""Base class for Gazoo device tests based on unittest.

It does 4 things:
- defines a testbed config format (.textproto) and parses the provided config;
- sets up a test logger;
- creates a test output directory;
- creates a gazoo_device Manager instance for device management.
"""
import datetime
import logging
import os
import tempfile
from typing import List
from typing import Tuple

from absl import logging as absl_logging
from absl.testing import absltest
import gazoo_device

from gazoo_device.tests.functional_tests.utils import gazoo_input
from gazoo_device.tests.functional_tests.utils import testbed_config_pb2

_DATETIME_FORMAT = "%m-%d-%Y_%H-%M-%S-%f"
_OUTPUT_DIR_PREFIX = "gazoo-{suite_name}-{date_time}_"
_LOG_LINE_FORMAT = "%(asctime)s.%(msecs).03d %(levelname)s %(message)s"
_LOG_LINE_TIME_FORMAT = "%m-%d %H:%M:%S"

# Testbed config. Initialized by TestCase.setUpClass().
_testbed = None


def _create_output_dir(suite_name: str) -> str:
  """Creates a temporary directory for the test output."""
  date_time_str = datetime.datetime.now().strftime(_DATETIME_FORMAT)[:-3]
  output_dir = tempfile.mkdtemp(
      prefix=_OUTPUT_DIR_PREFIX.format(
          suite_name=suite_name.lower(), date_time=date_time_str))
  return output_dir


def _set_up_logger(
    log_path: str) -> Tuple[logging.Logger, List[logging.Handler]]:
  """Sets up a test logger.

  Logs to test_log.DEBUG, test_log.INFO, test_log.WARNING depending
    on the log message level.

  Args:
    log_path (str): directory path for log files.

  Returns:
    tuple: (created logger, list of added logger handlers).
  """
  log_levels = ["DEBUG", "INFO", "WARNING"]
  logger = logging.getLogger()
  logger.setLevel(logging.DEBUG)
  formatter = logging.Formatter(_LOG_LINE_FORMAT, _LOG_LINE_TIME_FORMAT)

  handlers = []
  for level in log_levels:
    filename = os.path.join(log_path, "test_log.{}".format(level))
    int_level = getattr(logging, level)
    handler = logging.FileHandler(filename)
    handler.setLevel(int_level)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    handlers.append(handler)
  stderr_handler = logging.StreamHandler()
  stderr_handler.setLevel(logging.INFO)
  stderr_handler.setFormatter(formatter)
  logger.addHandler(stderr_handler)
  handlers.append(stderr_handler)
  logger.removeHandler(absl_logging.get_absl_handler())

  return logger, handlers


def _teardown_logger(logger: logging.Logger,
                     handler_list: List[logging.Handler]) -> None:
  """Closes and removes log handlers from the logger."""
  for handler in handler_list:
    logger.removeHandler(handler)
    handler.close()


class TestCase(absltest.TestCase):
  """Base class for Gazoo device tests based on absltest."""
  logger = None
  _logger_handlers = []
  _manager = None
  _output_dir = None

  @classmethod
  def setUpClass(cls):
    """Loads the testbed config and creates a Manager instance."""
    super().setUpClass()
    global _testbed
    cls._output_dir = (
        gazoo_input.get_output_dir_setting() or
        _create_output_dir(suite_name=cls.__name__))
    cls.logger, cls._logger_handlers = _set_up_logger(
        log_path=cls.get_output_dir())
    cls.logger.info("Test output folder: %s", cls.get_output_dir())
    if not _testbed:
      _testbed = gazoo_input.get_testbed_config()
    gdm_log_file = os.path.join(cls.get_output_dir(), "gdm.log")
    cls._manager = gazoo_device.Manager(
        log_directory=cls.get_output_dir(),
        gdm_log_file=gdm_log_file,
        stdout_logging=False)  # Avoid stdout log duplication

  @classmethod
  def tearDownClass(cls):
    """Closes the Manager instance.

    Note that this closes all devices which have been created through this
    manager instance and are still open.
    """
    cls.get_manager().close()
    cls._manager = None
    _teardown_logger(logger=cls.logger, handler_list=cls._logger_handlers)
    cls._logger_handlers = []
    super().tearDownClass()

  def tearDown(self):
    """Closes all open device objects."""
    self.get_manager().close_open_devices()
    super().tearDown()

  @classmethod
  def get_manager(cls) -> gazoo_device.Manager:
    """Returns the Manager instance for managing devices in tests."""
    return cls._manager

  @classmethod
  def get_output_dir(cls) -> str:
    """Returns the path to the test artifact directory."""
    return cls._output_dir

  @classmethod
  def get_testbed(cls) -> testbed_config_pb2.TestbedConfig:
    """Returns the testbed configuration."""
    return _testbed


def main(*args, **kwargs):
  return absltest.main(*args, **kwargs)
