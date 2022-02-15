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

"""Basic unit tests for multiprocessing in GDM with "spawn" start method."""
import os
from unittest import mock

from gazoo_device import gdm_logger
from gazoo_device.auxiliary_devices import raspberry_pi
from gazoo_device.switchboard import switchboard
from gazoo_device.switchboard import switchboard_process
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import multiprocessing_utils
import psutil


def target(logging_queue):
  gdm_logger.initialize_child_process_logging(logging_queue)
  logger = gdm_logger.get_logger()
  logger.info("I'm a child process with PID {}".format(os.getpid()))


class MultiprocessingSpawnTests(fake_device_test_case.FakeDeviceTestCase,
                                unit_test_case.MultiprocessingTestCase):
  """Multiprocessing with "spawn" test suite."""

  def test_simple_process(self):
    """Test spawning a multiprocessing.Process() child process."""
    logging_queue = gdm_logger.get_logging_queue()
    proc = multiprocessing_utils.get_context().Process(
        target=target, args=(logging_queue,))
    proc.start()
    proc.join()

  def test_create_switchboard(self):
    """Test creating a Switchboard."""
    log_path = os.path.join(self.artifacts_directory,
                            self._testMethodName + ".txt")
    switchboard.SwitchboardDefault("test_device",
                                   self.exception_queue,
                                   [],
                                   log_path)

  def test_create_device(self):
    """Test creating a device instance."""
    self.setup_fake_device_requirements("raspberrypi-1234")
    raspberry_pi.RaspberryPi(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory)
    # Close the log file opened by self._log_to_artifacts_directory.
    self.doCleanups()

  def test_switchboard_process(self):
    """Test starting a Switchboard child process."""
    command_queue = multiprocessing_utils.get_context().Queue()
    exception_queue = multiprocessing_utils.get_context().Queue()
    proc = switchboard_process.SwitchboardProcess("some_device",
                                                  "some_process",
                                                  exception_queue,
                                                  command_queue)
    proc.start()
    proc.stop()

  def test_get_message_from_queue(self):
    """Test a Switchboard process getting a message from a queue."""
    echo_message = "Message to be echoed"
    in_queue = multiprocessing_utils.get_context().Queue()
    in_queue.put(echo_message)
    switchboard_process.wait_for_queue_writes(in_queue)
    message = switchboard_process.get_message(in_queue, timeout=0)
    self.assertEqual(echo_message, message,
                     "Expected {} from nonempty queue found {}".
                     format(echo_message, message))

  @mock.patch.object(psutil, "Process",
                     return_value=mock.MagicMock(spec=psutil.Process))
  def test_switchboard_process_loop(self, mock_psutil_proc):
    """Process loop calls _do_work at least once."""
    logging_queue = multiprocessing_utils.get_context().Queue()
    exception_queue = multiprocessing_utils.get_context().Queue()
    mock_start_event = mock.MagicMock(
        spec=multiprocessing_utils.get_context().Event())
    mock_stop_event = mock.MagicMock(
        spec=multiprocessing_utils.get_context().Event())
    mock_terminate_event = mock.MagicMock(
        spec=multiprocessing_utils.get_context().Event())

    mock_switchboard_process = mock.MagicMock(
        spec=switchboard_process.SwitchboardProcess)
    mock_switchboard_process.device_name = "mock_device"
    mock_switchboard_process.process_name = "mock_process"
    mock_switchboard_process.logging_queue = logging_queue
    mock_switchboard_process._exception_queue = exception_queue
    mock_switchboard_process._start_event = mock_start_event
    mock_switchboard_process._stop_event = mock_stop_event
    mock_switchboard_process._terminate_event = mock_terminate_event

    mock_parent_proc = mock_psutil_proc.return_value
    mock_switchboard_process._pre_run_hook.return_value = True
    mock_terminate_event.is_set.return_value = False
    mock_switchboard_process._do_work.return_value = False

    with mock.patch.object(
        gdm_logger, "initialize_child_process_logging") as mock_init_logging:
      switchboard_process._process_loop(mock_switchboard_process, 1234)

    mock_init_logging.assert_called_once()
    mock_start_event.set.assert_called_once()
    mock_switchboard_process._pre_run_hook.assert_called_once()
    mock_parent_proc.status.assert_called_once()
    mock_terminate_event.is_set.assert_called_once()
    mock_terminate_event.clear.assert_not_called()
    mock_switchboard_process._do_work.assert_called_once()
    mock_stop_event.set.assert_called_once()


if __name__ == "__main__":
  unit_test_case.main()
