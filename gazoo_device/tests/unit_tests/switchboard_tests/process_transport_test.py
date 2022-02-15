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

"""Tests the process_transport.py module."""
import os
import time
from unittest import mock

from gazoo_device.switchboard.transports import process_transport
from gazoo_device.switchboard.transports import pty_transport
from gazoo_device.tests.unit_tests.utils import unit_test_case


class ProcessTransportTests(unit_test_case.MultiprocessingTestCase):
  """Tests the process_transport.py module."""
  _TRANSPORT_CLASS = process_transport.ProcessTransport

  def tearDown(self):
    if hasattr(self, "uut"):
      self.uut.close()
    super().tearDown()

  def test_001_transport_starts_closed_and_close_works(self):
    """Newly created transports start closed."""
    process_command = "/some/fake/executable"
    self.uut = self._TRANSPORT_CLASS(process_command)
    self.assertFalse(self.uut.is_open())

  def test_002_transport_returns_property_dict(self):
    """Transport returns read-only property dict."""
    process_command = "/some/fake/executable"
    self.uut = self._TRANSPORT_CLASS(process_command)
    property_dict = self.uut.get_all_properties()
    self.assertTrue(property_dict,
                    "Expected at least one property key, found 0.")
    test_key = list(property_dict.keys())[0]
    self.assertIsInstance(
        property_dict, dict,
        "Expected dictionary of properties found {}.".format(
            type(property_dict)))
    # Change one value in original dictionary returned
    property_dict[test_key] = "new value"
    property_dict2 = self.uut.get_all_properties()
    # Verify 2nd dictionary doesn't show changed value
    self.assertNotEqual(
        property_dict[test_key], property_dict2[test_key],
        "Expected read only dictionary to be returned. "
        "Found dictionary changes influences original.")

  def test_003_transport_returns_default_value_on_get_property(self):
    """Transport returns default value on get_property call."""
    process_command = "/some/fake/executable"
    self.uut = self._TRANSPORT_CLASS(process_command)
    default_value = "bogus value"
    value = self.uut.get_property("bogus_key", value=default_value)

    self.assertEqual(
        value, default_value,
        "Expected default value {} provided found {}.".format(
            default_value, value))

  def test_004_transport_returns_value_on_get_property(self):
    """Transport returns default value on get_property call."""
    process_command = "/some/fake/executable"
    self.uut = self._TRANSPORT_CLASS(process_command)
    property_dict = self.uut.get_all_properties()
    self.assertTrue(property_dict,
                    "Expected at least one property key, found 0.")
    test_key = list(property_dict.keys())[0]
    value = self.uut.get_property(test_key)
    self.assertEqual(
        property_dict[test_key], value,
        "Expected value {} found {}".format(property_dict[test_key], value))

  def test_005_transport_returns_property_list(self):
    """Transports return non-empty property list."""
    process_command = "/some/fake/executable"
    self.uut = self._TRANSPORT_CLASS(process_command)
    property_list = self.uut.get_property_list()
    self.assertTrue(
        property_list,
        "Expected property list length > 0 found {}".format(len(property_list)))

  def test_006_transport_can_set_all_properties(self):
    """Transports can set all properties to new values."""
    process_command = "/some/fake/executable"
    self.uut = self._TRANSPORT_CLASS(process_command)
    property_list = self.uut.get_property_list()
    for key in property_list:
      # Set all properties values to their key
      self.uut.set_property(key, key)
      value = self.uut.get_property(key)
      self.assertEqual(
          key, value,
          f"Expected property {key} value to be {key} found {value}.")

  def test_007_transport_cant_set_bogus_property(self):
    """Transports can't set a bogus property key."""
    process_command = "/some/fake/executable"
    self.uut = self._TRANSPORT_CLASS(process_command)
    with self.assertRaisesRegex(KeyError,
                                "Property bogus key doesn't exist for"):
      self.uut.set_property("bogus key", "bogus value")

  def test_008_transport_read_returns_none(self):
    """Process Transport read returns None for unopened transport."""
    process_command = "/some/fake/executable"
    self.uut = self._TRANSPORT_CLASS(process_command)
    out = self.uut.read()
    self.assertIsNone(out,
                      "Expected None for read result found {}.".format(out))

  def test_009_transport_write_returns_none(self):
    """Process transport write returns None for unopened transport."""
    process_command = "/some/fake/executable"
    self.uut = self._TRANSPORT_CLASS(process_command)
    data = "SOME DATA TO WRITE TO TRANSPORT"
    out = self.uut.write(data)
    self.assertIsNone(out,
                      "Expected None for write result found {}.".format(out))

  def test_100_transport_cant_open_bogus_path(self):
    """Process transport can't open bogus serial path."""
    process_command = "/some/fake/executable"
    self.uut = self._TRANSPORT_CLASS(process_command)
    with self.assertRaisesRegex(OSError, "No such file or directory"):
      self.uut.open()
    time.sleep(1)

  def test_102_transport_can_open_close(self):
    """Process transport can open and close pty (fake serial port) path."""
    self.uut = self._TRANSPORT_CLASS("cat", "dev/kmsg")
    self.uut.open()
    self.uut.close()

  def test_103_transport_can_call_open_twice(self):
    """Process transport can call open method twice."""
    process_command = "true"
    self.uut = self._TRANSPORT_CLASS(process_command)
    self.uut.open()
    self.uut.open()

  def test_104_transport_can_call_close_twice(self):
    """Process transport can call close method twice."""
    self.uut = self._TRANSPORT_CLASS("cat", "dev/kmsg")
    self.uut.open()
    self.uut.close()
    self.uut.close()

  def test_105_transport_can_read(self):
    """Process transport can read from pty (fake serial port) path."""
    message = "hi mom"
    test_file = os.path.join(self.artifacts_directory,
                             self._testMethodName + ".txt")
    with open(test_file, "w") as out_file:
      out_file.write(message)

    self.uut = self._TRANSPORT_CLASS("tail", "-f " + test_file)
    self.uut.open()
    out = self.uut.read(size=len(message))
    self.assertEqual(message, out.decode(),
                     "Expected {!r} found {!r}.".format(message, out))

  def test_106_transport_can_write(self):
    """Process transport can write to pty (fake serial port) path."""
    self.uut = self._TRANSPORT_CLASS("cat", "-")
    self.uut.open()
    data = b"SOME DATA BYTES TO WRITE TO TRANSPORT\n"
    out = self.uut.write(data)
    self.assertEqual(
        len(data), out,
        "Expected {} bytes written found {}.".format(len(data), out))
    data_in = self.uut.read(len(data))
    self.assertEqual(data, data_in,
                     "Expected {} found {}.".format(data, data_in))

  def test_107_transport_can_write_unicode(self):
    """Process transport can write unicode to pty (fake serial port) path."""
    self.uut = self._TRANSPORT_CLASS("cat", "-")
    self.uut.open()
    data = "SOME UNICODE DATA TO WRITE TO TRANSPORT \ufffd\n"
    data_encoded = data.encode("utf-8", errors="replace")
    out = self.uut.write(data, timeout=5)
    self.assertEqual(
        len(data_encoded), out,
        "Expected {} bytes written found {}.".format(len(data_encoded), out))
    # This was showing intermittent failures for partial reads
    time.sleep(0.5)
    data_in = self.uut.read(len(data_encoded))
    self.assertEqual(data_encoded, data_in,
                     "Expected {!r} found {!r}.".format(data_encoded, data_in))

  def test_108_transport_returns_empty_string_for_read_timeout(self):
    """Process transport returns empty string for read timeout."""
    test_file = os.path.join(self.artifacts_directory,
                             self._testMethodName + ".txt")
    with open(test_file, "w") as out_file:
      out_file.write("")

    self.uut = self._TRANSPORT_CLASS("tail", "-f " + test_file)
    self.uut.open()
    out = self.uut.read(size=1, timeout=0.1)
    self.assertEqual(
        "", out.decode(),
        "Expected Empty string for read timeout found {!r}.".format(out))


class PtyProcessTransportTests(ProcessTransportTests):
  """Tests the pty_transport.py module."""
  _TRANSPORT_CLASS = pty_transport.PtyTransport

  def test_106_transport_can_write(self):
    """Process transport can write to pty (fake serial port) path."""
    self.uut = self._TRANSPORT_CLASS(comms_address="cat", args="-")
    self.uut.open()
    data = b"SOME DATA BYTES TO WRITE TO TRANSPORT"
    out = self.uut.write(data)
    self.assertEqual(
        len(data), out,
        "Expected {} bytes written found {}.".format(len(data), out))
    data_in = self.uut.read(1024, timeout=2)
    self.assertEqual(data, data_in,
                     "Expected {} found {}.".format(data, data_in))

  def test_107_transport_can_write_unicode(self):
    """Process transport can write unicode to pty (fake serial port) path."""
    self.uut = self._TRANSPORT_CLASS(comms_address="cat", args="-")
    self.uut.open()
    data = "SOME UNICODE DATA TO WRITE TO TRANSPORT \ufffd"
    data_encoded = data.encode("utf-8", errors="replace")
    out = self.uut.write(data_encoded, timeout=5)
    self.assertEqual(
        len(data_encoded), out,
        "Expected {} bytes written found {}.".format(len(data_encoded), out))
    data_in = self.uut.read(len(data_encoded), timeout=2)
    self.assertEqual(data, data_in.decode("utf-8", errors="replace"),
                     "Expected {!r} found {!r}.".format(data_encoded, data_in))

  def test_109_launch_bash(self):
    self.uut = self._TRANSPORT_CLASS(comms_address="/bin/bash", args="-i")
    self.uut.open()

    # Clear out the input
    data_in = self.uut.read(1024, timeout=1)
    data = "echo Hello from Umang\n"
    out = self.uut.write(data)
    self.assertEqual(
        len(data), out,
        "Expected {} bytes written found {}.".format(len(data), out))
    data_in = self.uut.read(1024, timeout=1)
    count = data_in.count(b"Hello")
    self.assertEqual(
        count, 2, "Expected 2 found {}. Data read: {!r}".format(count, data_in))

  @mock.patch.object(
      os, "read", side_effect=[b""] + 200 * [OSError("Input/Output error")])
  def test_110_read_error(self, mock_read):
    self.uut = self._TRANSPORT_CLASS(comms_address="/bin/bash", args="-i")
    self.uut.open()
    # verify error caught and empty string returned
    data_in = self.uut.read(1024, timeout=.001)
    self.assertEqual(
        len(data_in), 0,
        "Expected {} bytes written found {}.".format(len(data_in), 0))
    mock_read.assert_called()

  def test_111_write_number(self):
    self.uut = self._TRANSPORT_CLASS(comms_address="/bin/bash", args="-i")
    self.uut.open()
    self.uut.write(134)  # assure no errors


if __name__ == "__main__":
  unit_test_case.main()
