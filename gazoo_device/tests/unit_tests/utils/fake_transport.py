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

"""Fake transport for testing Switchboard."""
import copy
import time

from gazoo_device.switchboard import switchboard_process
from gazoo_device.switchboard import transport_properties
from gazoo_device.utility import multiprocessing_utils

EXCEPTION_MESSAGE = "Something bad happened during read"


def _produce_data(byte_rate, bytes_per_second, exit_flag,
                  generate_raw_log_lines, read_queue):
  """Generates dummy data to imitate reading from a device."""
  byte_count = 0
  delay = 0.0
  line_count = 0
  padding = 0
  start_time = time.time()
  while not exit_flag.is_set():
    line_count += 1
    if callable(generate_raw_log_lines):
      raw_log_line = u"{}{}\n".format(generate_raw_log_lines(), "*" * padding)
    else:
      raw_log_line = u"{:08d}{}\n".format(line_count, "*" * padding)
    byte_count += len(raw_log_line)
    bytes_per_second.value = byte_count / (time.time() - start_time)
    if bytes_per_second.value > byte_rate:
      delay += 0.001
    elif bytes_per_second.value < byte_rate:
      if delay > 0.0:
        delay -= 0.001
      else:
        padding += 1
    time.sleep(delay)
    read_queue.put(raw_log_line)


class FakeTransport:
  """Mock Switchboard transport class for testing."""

  def __init__(self,
               baudrate=115200,
               generate_lines=False,
               generate_raw_log_lines=None,
               fail_open=False,
               fail_read=False,
               failure_message=EXCEPTION_MESSAGE,
               write_read_func=None,
               open_on_start=True,
               read_only_if_raw_data_queue_enabled=False):
    self.comms_address = "/some/serial/path"
    self.bytes_per_second = multiprocessing_utils.get_context().Value("f", 0.0)
    self.is_open_count = multiprocessing_utils.get_context().Value("i", 0)
    self.open_count = multiprocessing_utils.get_context().Value("i", 0)
    self.close_count = multiprocessing_utils.get_context().Value("i", 0)
    self.read_size = multiprocessing_utils.get_context().Value("i", 0)
    self.reads = multiprocessing_utils.get_context().Queue()
    self.writes = multiprocessing_utils.get_context().Queue()
    self._baudrate = baudrate
    self._exit_flag = multiprocessing_utils.get_context().Event()
    self._fail_open = fail_open
    self._fail_read = fail_read
    self._generate_lines = generate_lines
    self._generate_raw_log_lines = generate_raw_log_lines
    self._properties = {}
    self._failure_message = failure_message
    self._transport_open = multiprocessing_utils.get_context().Event()
    self._write_read_func = write_read_func
    self._properties[transport_properties.OPEN_ON_START] = open_on_start
    # Note: if using read_only_if_raw_data_queue_enabled flag, your test must
    # call bind_raw_data_enabled_method().
    self._read_only_if_raw_data_queue_enabled = read_only_if_raw_data_queue_enabled
    self._raw_data_queue_enabled_method = None

  def __del__(self):
    self.close()

  def clear_open(self):
    if hasattr(self, "_transport_open"):
      self._transport_open.clear()

  def close(self):
    """Releases resources used by the class."""
    try:
      if hasattr(self, "_exit_flag"):
        self._exit_flag.set()
      if hasattr(self, "_generator"):
        self._generator.join()
      if hasattr(self, "close_count"):
        self.close_count.value += 1
      if hasattr(self, "_transport_open"):
        self.clear_open()
    except IOError:
      # Test probably failed and canceled the manager Event objects
      pass
    finally:
      # Always manually delete any multiprocess manager attributes so python's
      # garbage collector properly runs.
      attrs = [
          "_raw_data_queue_enabled_method", "bytes_per_second", "is_open_count",
          "open_count", "close_count", "read_size", "reads", "writes",
          "_properties", "_transport_open"
      ]
      for attr in attrs:
        if hasattr(self, attr):
          delattr(self, attr)

      # Always make "_exit_flag" last attribute to delete
      if hasattr(self, "_exit_flag"):
        delattr(self, "_exit_flag")

  def bind_raw_data_enabled_method(self, transport_process):
    """Add a reference to raw_data_enabled() method of transport_process.

    Args:
        transport_process (TransportProcess): the transport process using
          this fake transport.  Required in order to be able to read only
          when the raw data queue is enabled to avoid race conditions.
    """
    self._raw_data_queue_enabled_method = transport_process.raw_data_enabled

  def is_open(self):
    result = False
    try:
      if hasattr(self, "is_open_count"):
        self.is_open_count.value += 1
        result = self._transport_open.is_set()
    except IOError:
      # Test probably failed and canceled the manager Event objects
      pass
    return result

  def get_all_properties(self):
    return copy.deepcopy(self._properties)

  def get_property(self, key, value=None):
    if hasattr(self, "_properties"):
      if key in self._properties:
        return self._properties[key]
    return value

  def get_property_list(self):
    return list(self._properties.keys())

  def set_property(self, key, value):
    self._properties[key] = value

  def open(self):
    try:
      self.open_count.value += 1
      self.set_open()
    except IOError:
      # Test probably failed and canceled the manager Event objects
      pass
    if self._fail_open:
      raise Exception(self._failure_message)

  def set_open(self):
    self._transport_open.set()
    if self._generate_lines:
      self._generator = multiprocessing_utils.get_context().Process(
          target=_produce_data,
          args=(self._baudrate / 10, self.bytes_per_second, self._exit_flag,
                self._generate_raw_log_lines, self.reads))
      self.daemon = True
      self._generator.start()

  def _should_read(self):
    return (not self._read_only_if_raw_data_queue_enabled or
            (self._read_only_if_raw_data_queue_enabled and
             self._raw_data_queue_enabled_method is not None and
             self._raw_data_queue_enabled_method()))

  def read(self, size=1, timeout=None):
    """Reads from mock read queue or raises an error if fail_read is True."""
    try:
      self.read_size.value = size
    except IOError:
      # Test probably failed and canceled the manager Event objects
      pass
    if self._fail_read:
      raise Exception(self._failure_message)

    if self._should_read():
      return switchboard_process.get_message(self.reads, timeout=timeout)
    else:
      return None

  def write(self, data, timeout=None):
    self.writes.put(data, timeout=timeout)
    if self._write_read_func:
      responses = self._write_read_func(data)
      for response in responses:
        self.reads.put(response)

  def test_method(self, raise_error: bool = False) -> str:
    """A transport method which raises an error if raise_error=True."""
    del self  # Unused by the mock implementation
    if raise_error:
      raise RuntimeError("Something failed.")
    return "Some return"
