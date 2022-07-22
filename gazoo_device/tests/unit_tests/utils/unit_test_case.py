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

"""Base class for unit tests.

Sets up common unit tests components:
* directory to save artifacts;
* test logger;
* test runner that outputs test results in .xml format.

Setup creates:
- self.logger (logger): test logger.
- self.artifacts_directory (str): directory to which all logs should go.
  This directory is created brand new before each test run.
"""
import datetime
import gc
import itertools
import logging
import multiprocessing
import os
import queue
import re
import shutil
import signal
import subprocess
import tempfile
import time
from unittest import mock

from absl import logging as absl_logging
from absl.testing import absltest
from absl.testing import parameterized
from gazoo_device import gdm_logger
from gazoo_device.capabilities import event_parser_default
from gazoo_device.switchboard import data_framer
from gazoo_device.switchboard import ftdi_buttons
from gazoo_device.switchboard import switchboard
from gazoo_device.switchboard.transports import adb_transport
from gazoo_device.switchboard.transports import jlink_transport
from gazoo_device.switchboard.transports import pigweed_rpc_transport
from gazoo_device.switchboard.transports import pty_transport
from gazoo_device.switchboard.transports import serial_transport
from gazoo_device.switchboard.transports import ssh_transport
from gazoo_device.switchboard.transports import tcp_transport
from gazoo_device.tests.unit_tests import utils
from gazoo_device.utility import adb_utils
from gazoo_device.utility import host_utils
from gazoo_device.utility import multiprocessing_utils
from gazoo_device.utility import usb_utils
import pyudev
import usb

main = absltest.main

TEST_DIR = os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR", os.getcwd())
# Ignore file descriptors that contain these substrings
EXCLUDE_FD_FILTERS = (
    "libnss_files",
    "/dev/ptmx",
    "docker/runtime",
)


def mock_get_product_linux(serial_port_path):

  match = re.search(r"(FTDI_|SEGGER_)(\S+)_\S+-if\w+", serial_port_path)
  if match:
    return match.group(2).replace("_", " ")
  elif "silicon_labs" in serial_port_path:
    return "silicon labs cp2104 usb to uart bridge controller"
  return "serial_port_path"


def mock_get_interface_linux(serial_port_path):
  match = re.search(r"(FTDI_|SEGGER_)\S+_\S+-if0(\d)", serial_port_path)
  if match:
    return int(match.group(2))
  return 0


def mock_get_line_linux(serial_port_path, ftdi_interface):
  replacement = "if0" + str(ftdi_interface)
  match = re.search(r"(FTDI_|SEGGER_)\S+_\S+-(if0\d)", serial_port_path)
  if match:
    return serial_port_path.replace(match.group(2), replacement)
  return serial_port_path


class MockFile(mock.Mock):
  """Mock file implementation."""

  def __init__(self, text="", is_binary=False):
    """Mock file object (such as sys.stdout or as returned by open() builtin).

    Args:
        text (str): file content (byte type or unicode type)
        is_binary (bool): whether the file is open in binary mode.
    """
    super().__init__()

    if is_binary and isinstance(text, str):
      text = text.encode()
    elif not is_binary and isinstance(text, bytes):
      text = text.decode()

    self.close = mock.Mock()
    self.readline = mock.Mock(
        side_effect=itertools.chain(
            iter(text.splitlines(True)), itertools.repeat(b"")))
    self.readlines = mock.Mock(return_value=text.splitlines(True))
    self.read = mock.Mock(return_value=text)
    self._text = text

  def __iter__(self):
    return iter(self._text.splitlines())

  def __enter__(self):
    return self

  def __exit__(self, err_type, err_val, err_tb):
    pass


class MockSubprocess(mock.Mock):
  """Mock subprocess implementation."""

  def __init__(self, stdout=b"", stderr=b"", responses=None, return_code=0):
    super().__init__()
    self.returncode = return_code
    self.wait = mock.Mock(return_value=return_code)
    self.terminate = mock.Mock()
    self.responses = responses if responses else [b""]
    self.stdout = MockFile(stdout, is_binary=True)
    self.stderr = MockFile(stderr, is_binary=True)
    self._calls = 0

    # mock output of subprocess.Popen().communicate() calls
    return_codes = [self.returncode] * len(self.responses)
    self.communicate = mock.Mock(side_effect=zip(self.responses, return_codes))


class MockOutSubprocess():
  """Context manager for mocking subprocess calls."""

  def __init__(self, proc_output=None):
    proc_output = proc_output if proc_output else [b""]
    self.popen_patcher = mock.patch.object(
        subprocess, "Popen", return_value=MockSubprocess(responses=proc_output))
    self.check_output_patcher = mock.patch.object(
        subprocess, "check_output", return_value=proc_output[0])

  def __enter__(self):
    self.mock_popen = self.popen_patcher.start()
    self.mock_check_output = self.check_output_patcher.start()
    return self

  def __exit__(self, exc_type, exc_value, exc_traceback):
    self.popen_patcher.stop()
    self.check_output_patcher.stop()


class UnitTestCase(parameterized.TestCase):
  """Base class for unit tests."""
  TEST_EVENTFILES_DIR = os.path.join(
      os.path.dirname(utils.__file__), "eventfiles")
  TEST_FILTER_DIR = os.path.join(os.path.dirname(utils.__file__), "filters")

  @classmethod
  def setUpClass(cls):
    """Creates logger and artifacts directory."""
    super().setUpClass()

    cls.artifacts_directory = os.path.join(TEST_DIR, "artifacts", cls.__name__)
    if os.path.exists(cls.artifacts_directory):
      shutil.rmtree(cls.artifacts_directory)
    os.makedirs(cls.artifacts_directory)

    cls.logger = logging.getLogger(cls.__name__)
    stderr_handler = logging.StreamHandler()
    cls.logger.addHandler(stderr_handler)
    cls.logger.setLevel(logging.INFO)
    cls.logger.info("\nArtifacts will be saved to %s", cls.artifacts_directory)
    # Prevent ABSL logger from duplicating logs to stdout.
    absl_logging.get_absl_handler().setLevel(logging.ERROR)

    # Allow accessing pyudev.Context, but prohibit instantiating it:
    # pyudev.Context() only works on Linux hosts.
    cls.pyudev_context_new_patcher = mock.patch.object(
        pyudev.Context,
        "__new__",
        side_effect=RuntimeError(
            "Unit tests must not have a pyudev dependency."))
    cls.pyudev_context_new_patcher.start()

  def add_adb_mocks(self):
    """Mock accessing adb and fastboot binaries."""
    adb_patchers = [
        mock.patch.object(
            adb_utils, "get_adb_path", return_value="/usr/bin/adb"),
        mock.patch.object(
            adb_utils, "get_fastboot_path", return_value="/usr/bin/fastboot"),
        mock.patch.object(adb_utils, "is_fastboot_mode", return_value=False),
        mock.patch.object(adb_utils, "verify_user_has_fastboot"),
        mock.patch.object(adb_utils, "add_port_forwarding"),
        mock.patch.object(adb_utils, "remove_port_forwarding"),
        mock.patch.object(adb_utils, "_adb_command")
    ]
    for patcher in adb_patchers:
      patcher.start()
      self.addCleanup(patcher.stop)

  def add_time_mocks(self):
    """Mock out time.time() and time.sleep()."""
    self.real_sleep = time.sleep
    self.real_time = time.time

    mock_time = _MockTime()
    sleep_patcher = mock.patch.object(
        time, "sleep", side_effect=mock_time.sleep)
    time_patcher = mock.patch.object(time, "time", side_effect=mock_time.time)

    self.mock_sleep = sleep_patcher.start()
    self.addCleanup(sleep_patcher.stop)
    self.mock_time = time_patcher.start()
    self.addCleanup(time_patcher.stop)

  def mock_out_transports(self):
    """Mocks out all transport classes."""
    for module, a_class in [(adb_transport, "AdbTransport"),
                            (jlink_transport, "JLinkTransport"),
                            (pigweed_rpc_transport,
                             "PigweedRpcSocketTransport"),
                            (pty_transport, "PtyTransport"),
                            (serial_transport, "SerialTransport"),
                            (ssh_transport, "SSHTransport"),
                            (tcp_transport, "TcpTransport"),
                            (ftdi_buttons, "FtdiButtons"),
                            (data_framer, "InterwovenLogFramer"),
                            (switchboard, "SwitchboardDefault"),
                            (host_utils, "verify_key")]:
      a_mock = mock.patch.object(module, a_class, autospec=True)
      a_mock.start()
      self.addCleanup(a_mock.stop)

  def mock_out_usb_utils_methods(self):
    """Mocks out usb_utils methods."""
    mock_product_name = mock.patch.object(
        usb_utils,
        "get_product_name_from_path",
        side_effect=mock_get_product_linux)
    mock_ftdi_interface = mock.patch.object(
        usb_utils,
        "get_ftdi_interface_from_path",
        side_effect=mock_get_interface_linux)
    mock_get_line = mock.patch.object(
        usb_utils, "get_other_ftdi_line", side_effect=mock_get_line_linux)
    mock_serial = mock.patch.object(
        usb_utils, "get_serial_number_from_path", return_value="FT2BSR6O")
    mock_devices_with_serial = mock.patch.object(
        usb_utils, "get_usb_devices_having_a_serial_number",
        return_value=[mock.Mock(spec=usb.core.Device, serial_number="123789")])
    mock_product_name.start()
    self.addCleanup(mock_product_name.stop)
    mock_ftdi_interface.start()
    self.addCleanup(mock_ftdi_interface.stop)
    mock_serial.start()
    self.addCleanup(mock_serial.stop)
    mock_get_line.start()
    self.addCleanup(mock_get_line.stop)
    mock_devices_with_serial.start()
    self.addCleanup(mock_devices_with_serial.stop)

  def get_resource(self, path):
    """Get absolute path of resource file included in test dependencies.

    Args:
      path (str): resource path relative to unit_tests/utils directory,
        e.g. 'filters/basic.json'.

    Returns:
      str: absolute path to resource file.
    """
    return os.path.join(os.path.dirname(utils.__file__), path)

  def tearDown(self):
    gdm_logger.flush_queue_messages()
    super().tearDown()

  @classmethod
  def tearDownClass(cls):
    cls.pyudev_context_new_patcher.stop()
    super().tearDownClass()


def get_queue_size(
    a_queue: multiprocessing.Queue, timeout: float = 0.25) -> int:
  """Return the size of the queue by reading everything from it.

  The built-in Queue.qsize() method is not implemented on Macs and is not
  reliable:
  docs.python.org/3.7/library/multiprocessing.html#multiprocessing.Queue.qsize

  Args:
    a_queue: Queue to return the size of.
    timeout: Seconds before timing out.

  Returns:
    Size of queue.
  """
  size = 0
  deadline = time.time() + timeout
  while time.time() < deadline:
    try:
      a_queue.get_nowait()
      size += 1
    except queue.Empty:
      time.sleep(0.01)
  return size


class MultiprocessingTestCase(UnitTestCase):
  """Base class for multiprocessing tests.

  Checks that there are no file descriptor leaks at the end of each test.
  """

  @classmethod
  def setUpClass(cls):
    """Performs one-time setup before FD leak check starts."""
    # Create the ABSL error log file before any test starts.
    gdm_logger.get_logger().error("Starting a log file")
    # Creating the first multiprocessing.Value instance initializes some shared
    # memory structure (and thus opens a new file descriptor).
    multiprocessing_utils.get_context().Value("l", 0)
    # Switching to multiprocess logging creates several multiprocessing objects
    # and opens some shared file descriptors. (Only the first call; subsequent
    # calls are no-ops.) Switch to multiprocess logging before setUp and
    # tearDown start keeping track of opened file descriptors.
    gdm_logger.switch_to_multiprocess_logging()
    super().setUpClass()

  def setUp(self):
    super().setUp()

    self.exception_queue = multiprocessing_utils.get_context().Queue()
    self.exception = None

    self._orig_usr1_handler = signal.getsignal(signal.SIGUSR1)
    # Register USR1 signal to get exception messages from exception_queue
    signal.signal(signal.SIGUSR1, self._process_exceptions)

    self.starting_fds = self.get_open_fds()

  def tearDown(self):
    del self.exception_queue  # Release shared memory file descriptors.
    gc.collect()

    signal.signal(signal.SIGUSR1, self._orig_usr1_handler)

    if self.exception:
      self.fail("Unhandled exception {}".format(self.exception))
    self.verify_no_fds_left_open()

    super().tearDown()

  def verify_no_fds_left_open(self):
    """Verifies that any file descriptors opened by the test are not left open.

    It does this by tracking all the fds open before the test starts and
    comparing it to fds open after the test. pty library does have a known fd
    leak that is ignored in this check.
    """

    ending_fds = self.get_open_fds()
    new_fds = list(set(ending_fds) - set(self.starting_fds))
    # Some modules are known to add/leak a file descriptor
    # Filter out FDs from known leakers (e.g. PTY process transport, docker)
    new_fds = [
        fd for fd in new_fds
        if not any(fd_filter in fd for fd_filter in EXCLUDE_FD_FILTERS)
    ]

    self.assertFalse(
        new_fds, "Expected no FDs left open but these still exist: {}. "
        "Count before: {} Count after: {}.".format(new_fds,
                                                   len(self.starting_fds),
                                                   len(ending_fds)))

  def get_open_fds(self):
    """Get a list of all open fd addresses (for test tracking)."""
    pid = os.getpid()
    cmd = "lsof -a -p {}".format(pid)
    out = subprocess.check_output(
        cmd, shell=True, stderr=subprocess.STDOUT).decode("utf-8", "replace")
    if out:
      return [x.split()[-1] for x in out.splitlines()[1:]]
    return []

  def _process_exceptions(self, *args):
    """Process exception queue and store them for tests to check."""
    del args
    self.exception = self.exception_queue.get()


class SwitchboardParserTestCase(UnitTestCase):
  """Base class for Switchboard parser tests."""
  # Event log lines.
  _ANOTHER_MESSAGE_LINE = "{} [APPL] This is another message\n"
  _NO_MATCH_LINE = "{} [BOOT] Non-matching line"
  _STATE_LINE = "{} [APPL] Some other message with group data {}"
  _UNIQUE_MESSAGE_LINE = "{} [APPL] Some unique message\n"

  def setUp(self):
    super().setUp()
    fd, self.event_file_path = tempfile.mkstemp(dir="/tmp")
    self.fake_file_writer = _FakeFileWriter()
    os.close(fd)
    filters_list = [self.get_resource("filters/sample.json")]
    self.uut = event_parser_default.EventParserDefault(
        filters=filters_list,
        event_file_path=self.event_file_path,
        device_name="device-1234")
    self.add_time_mocks()

  def tearDown(self):
    os.remove(self.event_file_path)
    super().tearDown()

  def _populate_event_file(self, event_count):
    """Creates a temporary event history log file for testing Parser event history commands.

    The temporary event history log file will contain event_count total events
    for each of the following raw log lines:
      * ANOTHER_MESSAGE_LINE
      * NO_MATCH_LINE
      * STATE_LINE
      * UNIQUE_MESSAGE_LINE

    Args:
      event_count (int): number of events to log.
    """
    with open(self.event_file_path, "w") as real_event_file:
      for i in range(event_count):
        now = datetime.datetime.now()
        time_info = now.strftime("<%Y-%m-%d %H:%M:%S.%f>")
        self.uut.process_line(real_event_file,
                              self._ANOTHER_MESSAGE_LINE.format(time_info))
        self.uut.process_line(real_event_file,
                              self._NO_MATCH_LINE.format(time_info))
        self.uut.process_line(real_event_file,
                              self._STATE_LINE.format(time_info, i))
        self.uut.process_line(real_event_file,
                              self._UNIQUE_MESSAGE_LINE.format(time_info))


class _FakeFileWriter:

  def __init__(self):
    self.out = None

  def write(self, output):
    self.out = output

  def flush(self):
    pass


class _MockTime():
  """Mock time.sleep() and time.time() implementation."""
  _default_start_sec = 0
  _default_time_step = 0.01

  def __init__(self, start=_default_start_sec, step=_default_time_step):
    self._current_time = start
    self._step = step

  def time(self):
    # Minor time increment to avoid endlessly spinning in busy wait loops.
    self._current_time += self._step
    return self._current_time

  def sleep(self, sleep_duration_sec):
    self._current_time += sleep_duration_sec
