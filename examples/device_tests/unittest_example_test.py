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

"""Example reboot device test with GDM + unittest.

Usage:
  python3 unittest_example_test.py -d somedevice-1234

See README.md for more details.
"""
import argparse
import logging
import sys
from typing import List, Tuple
import unittest

import gazoo_device

# If using a device controller from an extension package:
# import my_extension_package
# gazoo_device.register(my_extension_package)

_LOG_LINE_FORMAT = "%(asctime)s.%(msecs).03d %(levelname)s %(message)s"
_LOG_LINE_TIME_FORMAT = "%m-%d %H:%M:%S"

_device_name = None  # Global variable set in __main__.


def _parse_cli_args() -> Tuple[str, List[str]]:
  """Parses CLI args to return device name and args for unittest runner."""
  parser = argparse.ArgumentParser(
      description="Runs a GDM + unittest reboot test on a device. All "
                  "arguments other than the device name are passed through to "
                  "the unittest runner.")
  parser.add_argument(
      "-d", "--device", required=True,
      help="GDM device name to run the test on. For example, 'device-1234'. "
           "The device must be shown as 'available' or 'connected' in the "
           "output of 'gdm devices'.")
  args, remaining_argv = parser.parse_known_args()
  return args.device, [sys.argv[0]] + remaining_argv


def _set_up_stderr_logging() -> logging.StreamHandler:
  """Directs the output of the root logger to stderr.

  Returns:
    stderr log handler that was created.
  """
  logging.getLogger().setLevel(logging.DEBUG)
  stderr_handler = logging.StreamHandler()
  stderr_handler.setLevel(logging.INFO)
  formatter = logging.Formatter(_LOG_LINE_FORMAT, _LOG_LINE_TIME_FORMAT)
  stderr_handler.setFormatter(formatter)
  logging.getLogger().addHandler(stderr_handler)
  return stderr_handler


class UnittestExampleRebootTest(unittest.TestCase):
  """Example reboot device test with GDM + unittest."""
  manager = None
  _logger_handler = None

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.device = None

  @classmethod
  def setUpClass(cls):
    """Creates a Manager instance and sets up stderr logging."""
    super().setUpClass()
    cls._logger_handler = _set_up_stderr_logging()
    cls.manager = gazoo_device.Manager(
        # Avoid log duplication with the test stderr log handler.
        stdout_logging=False)

  @classmethod
  def tearDownClass(cls):
    """Closes the Manager instance and removes the stderr log handler."""
    cls.manager.close()
    cls.manager = None
    logging.getLogger().removeHandler(cls._logger_handler)
    cls._logger_handler = None
    super().tearDownClass()

  def setUp(self):
    """Creates a device controller for the device."""
    super().setUp()
    self.device = self.manager.create_device(_device_name)
    logging.info("Created device for test: %s", self.device.name)

  def tearDown(self):
    """Closes the device controller."""
    self.device.close()
    self.device = None
    super().tearDown()

  def test_reboot(self):
    """Reboots the device."""
    self.device.reboot()
    self.assertTrue(
        self.device.connected,
        f"Device {self.device.name} did not come back online after reboot")


if __name__ == "__main__":
  # Parse out the device name from CLI arguments and pass the rest to unittest.
  _device_name, unittest_argv = _parse_cli_args()
  unittest.main(argv=unittest_argv, verbosity=2)
