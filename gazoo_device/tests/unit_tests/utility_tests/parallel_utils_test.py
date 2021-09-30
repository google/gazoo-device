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

"""This script performs unit tests on GDM's Parallel Utility library."""
import multiprocessing
import queue
from unittest import mock

from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.tests.unit_tests.utils import fake_devices
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import parallel_utils

QUEUE_MESSAGE = "Queue message for device {device_name}"
GDM_LOGGER = gdm_logger.get_logger()

# pylint: disable=unused-argument


class MockProcess(object):
  """Mock multiprocessing process object to track parallel methods in single process.

  https://docs.python.org/2/library/multiprocessing.html#multiprocessing.Process
  """

  def __init__(self, target, args, kwargs):
    self.target = target
    self.args = args
    self.kwargs = kwargs

  def start(self):
    """Start the process's activity."""
    self.target(*self.args, **self.kwargs)

  def is_alive(self):
    """Return whether the process is alive."""
    return True  # return True so terminate method will be called

  def join(self, timeout=0):
    """Wait for all processes to complete.

    Args:
        timeout (float): block at most timeout seconds.
    """
    pass  # running in single process, no action needed

  def terminate(self):
    """Terminate the process."""
    pass  # running in single process, no action needed


class MockQueue(object):
  """Mock multiprocessing queue object to track a messaging queue in a single process.

  https://docs.python.org/2/library/multiprocessing.html#multiprocessing.Queue
  """

  def __init__(self):
    self.queue = []  # array representation of a queue

  def cancel_join_thread(self):
    """Prevent join_thread() from blocking."""
    pass  # not using multiple threads, no action needed

  def empty(self):
    """Return whether or not the queue is empty."""
    return not self.queue

  def get(self, block=None, timeout=None):
    """Remove an item from the queue.

    Args:
        block (bool): block if necessary until a free spot is available.
        timeout (float): block at most timeout seconds.

    Returns:
        object: item removed from the queue.

    Raises:
        Queue.Empty: if queue is empty.
    """
    if timeout or not block:
      if self.empty():
        raise queue.Empty
    return self.queue.pop()

  def get_nowait(self):
    """Remove an item from the queue."""
    return self.get(False)

  def put_nowait(self, msg):
    """Put an item into the queue.

    Args:
        msg (object): item to insert into the queue.
    """
    self.queue.insert(0, msg)


class ParallelUtilsTests(unit_test_case.UnitTestCase):
  """Unit tests for utility/parallel_utils.py."""

  def setUp(self):
    super(ParallelUtilsTests, self).setUp()

    # device mocks
    self.devices = [
        fake_devices.FakeSSHDevice(name="sshdevice-first"),
        fake_devices.FakeSSHDevice(name="sshdevice-second"),
        fake_devices.FakeSSHDevice(name="sshdevice-third")
    ]

    # multiprocessing mocks
    self.process_mock = mock.patch.object(
        multiprocessing, "Process", side_effect=MockProcess)
    self.queue_mock = mock.patch.object(
        multiprocessing, "Queue", side_effect=MockQueue)
    self.process_mock.start()
    self.queue_mock.start()

  def tearDown(self):
    super(ParallelUtilsTests, self).tearDown()
    self.process_mock.stop()
    self.queue_mock.stop()
    if hasattr(self, "uut"):
      self.uut.close()

  def test_000_get_messages_from_queue(self):
    """Test retrieving messages from the multiprocessing queue."""
    test_msgs = ["gobbly", "gook"]
    mp_queue = multiprocessing.Queue()
    for msg in test_msgs:
      mp_queue.put_nowait(msg)
    msgs = parallel_utils.get_messages_from_queue(mp_queue)
    self.assertEqual(msgs, test_msgs)

  def test_001_get_messages_from_queue_empty_queue(self):
    """Test retrieving an empty list from an empty multiprocessing queue."""
    mp_queue = multiprocessing.Queue()
    msgs = parallel_utils.get_messages_from_queue(mp_queue)
    self.assertEqual(msgs, [])

  def test_010_parallel_process_devices_not_list(self):
    """Test parallel_process raising an exception if devices isn't a list."""
    with self.assertRaisesRegex(RuntimeError, "Devices should be a list."):
      non_list_devices = "non-list-devices"
      parallel_utils.parallel_process("fake_action", self._mock_method,
                                      non_list_devices)

  def test_011_parallel_process_devices_missing_required_property(self):
    """Test parallel_process raising an exception if devices are missing required props."""
    with self.assertRaisesRegex(AttributeError,
                                "Devices must have name property."):
      string_list = ["", ""]
      parallel_utils.parallel_process("fake_action", self._mock_method,
                                      string_list)

  def test_020_parallel_process_calls_method_returns_results(self):
    """Test parallel_process calling a method for each device and interpreting the results."""
    result = parallel_utils.parallel_process(
        "mock_action", self._mock_method, self.devices, logger=GDM_LOGGER)
    for device in self.devices:
      self.assertIn(QUEUE_MESSAGE.format(device_name=device.name), result)

  def test_021_parallel_process_calls_method_raises_exception(self):
    """Test parallel_process calling a method for each device and raising an exception."""
    # create parameter dict with the "raise_exception" argument
    # this will be passed to _mock_method and an interpretable exception
    # will be raised
    args = {}
    for device in self.devices:
      args[device.DEVICE_TYPE] = {"raise_exception": True}

    error_recv = None
    try:
      parallel_utils.parallel_process(
          "mock_action", self._mock_method, self.devices, parameter_dicts=args)
    except RuntimeError as err:
      error_recv = str(err)

    for device in self.devices:
      self.assertIn(QUEUE_MESSAGE.format(device_name=device.name), error_recv)

  def test_022_parallel_process_calls_method_in_parallel(self):
    """Test parallel_process calling a method for each device in parallel."""
    self.process_mock.stop()
    self.queue_mock.stop()

    # note: no multiprocessing mocks are active here
    # this will call _mock_method in a separate process for each device
    result = parallel_utils.parallel_process("mock_action", self._mock_method,
                                             self.devices)
    for device in self.devices:
      self.assertIn(QUEUE_MESSAGE.format(device_name=device.name), result)

    # restart multiprocessing mocks to avoid "stop called on unstarted patcher"
    # error
    self.process_mock.start()
    self.queue_mock.start()

  def test_030_issue_devices_parallel_calls_method_in_parallel(self):
    """Test issue_devices_parallel calling device methods for each device."""
    params = {"sshdevice": {"device_config": fake_devices._DEFAULT_CONFIG}}
    result = parallel_utils.issue_devices_parallel("is_connected",
                                                   self.devices,
                                                   parameter_dicts=params)
    self.assertEqual(result, [True] * len(self.devices))  # all connected

  def _mock_method(self, device, logger=None, parameter_dict=None):
    """Mock method that adds messages to a multiprocessing queue.

    Args:
        device (MockDevice): Mock Gazoo Device object.
        logger (object): logger object.
        parameter_dict (list): dictionary containing other arguments.

    Returns:
        str: message containing the device's name

    Raises:
        DeviceError: if exception exists in parameter_dict.

    Note:
        Designed to be passed to parallel_utils.parallel_process.
    """
    if parameter_dict and parameter_dict["raise_exception"]:
      raise errors.DeviceError(QUEUE_MESSAGE.format(device_name=device.name))
    return QUEUE_MESSAGE.format(device_name=device.name)


if __name__ == "__main__":
  unit_test_case.main()
