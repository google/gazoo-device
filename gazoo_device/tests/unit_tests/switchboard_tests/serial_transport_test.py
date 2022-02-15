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

"""Tests the serial_transport.py module."""
import fcntl
import os
import pty
from unittest import mock

from gazoo_device.switchboard.transports import serial_transport
from gazoo_device.tests.unit_tests.utils import unit_test_case
import serial


class SerialTransportTests(unit_test_case.UnitTestCase):

  def test_001_transport_starts_closed_and_close_works(self):
    """Newly created transports start closed."""
    uut = serial_transport.SerialTransport("/some/fake/path")
    self.assertFalse(uut.is_open())
    uut.close()

  def test_002_transport_returns_property_dict(self):
    """Transport returns read-only property dict."""
    uut = serial_transport.SerialTransport("/some/fake/path")
    property_dict = uut.get_all_properties()
    self.assertTrue(
        property_dict,
        "Expected at least one property key, found 0.")
    test_key = list(property_dict.keys())[0]
    self.assertIsInstance(
        property_dict, dict,
        "Expected dictionary of properties found {}.".format(
            type(property_dict)))
    # Change one value in original dictionary returned
    property_dict[test_key] = "new value"
    property_dict2 = uut.get_all_properties()
    # Verify 2nd dictionary doesn't show changed value
    self.assertNotEqual(
        property_dict[test_key], property_dict2[test_key],
        "Expected read only dictionary to be returned. "
        "Found dictionary changes influences original.")

  def test_003_transport_returns_default_value_on_get_property(self):
    """Transport returns default value on get_property call."""
    uut = serial_transport.SerialTransport("/some/fake/path")
    default_value = "bogus value"
    value = uut.get_property("bogus_key", value=default_value)
    self.assertEqual(
        value, default_value,
        "Expected default value {} provided found {}.".format(
            default_value, value))

  def test_004_transport_returns_value_on_get_property(self):
    """Transport returns default value on get_property call."""
    uut = serial_transport.SerialTransport("/some/fake/path")
    property_dict = uut.get_all_properties()
    self.assertTrue(
        property_dict,
        "Expected at least one property key, found 0.")
    test_key = list(property_dict.keys())[0]
    value = uut.get_property(test_key)
    self.assertEqual(
        property_dict[test_key], value,
        "Expected value {} found {}".format(property_dict[test_key], value))

  def test_005_transport_returns_property_list(self):
    """Transports return non-empty property list."""
    uut = serial_transport.SerialTransport("/some/fake/path")
    property_list = uut.get_property_list()
    self.assertTrue(
        property_list,
        "Expected property list length > 0 found {}".format(len(property_list)))

  def test_006_transport_can_set_all_properties(self):
    """Transports can set all properties to new values."""
    uut = serial_transport.SerialTransport("/some/fake/path")
    property_list = uut.get_property_list()
    for key in property_list:
      # Set all properties values to their key
      uut.set_property(key, key)
      value = uut.get_property(key)
      self.assertEqual(
          key, value,
          f"Expected property {key} value to be {key} found {value}.")

  def test_007_transport_cant_set_bogus_property(self):
    """Transports cant set a bogus property key."""
    uut = serial_transport.SerialTransport("/some/fake/path")
    with self.assertRaisesRegex(KeyError,
                                r"Property bogus key doesn't exist for"):
      uut.set_property("bogus key", "bogus value")

  def test_008_transport_read_returns_none(self):
    """Serial transport read returns None for unopened transport."""
    uut = serial_transport.SerialTransport("/some/fake/path")
    out = uut.read()
    self.assertIsNone(out,
                      "Expected None for read result found {}.".format(out))

  def test_009_transport_write_returns_none(self):
    """Serial transport write returns None for unopened transport."""
    uut = serial_transport.SerialTransport("/some/fake/path")
    data = "SOME DATA TO WRITE TO TRANSPORT"
    out = uut.write(data)
    self.assertIsNone(out,
                      "Expected None for write result found {}.".format(out))

  def test_100_transport_cant_open_bogus_path(self):
    """Serial transport can't open bogus serial path."""
    uut = serial_transport.SerialTransport("/some/fake/path")
    with self.assertRaisesRegex(serial.SerialException, r"could not open port"):
      uut.open()

  def test_101_transport_cant_open_exclusively_locked_path(self):
    """Serial transport can't open same path twice."""
    _, secondary = pty.openpty()
    locked = serial_transport.SerialTransport(os.ttyname(secondary))
    locked.open()
    uut = serial_transport.SerialTransport(os.ttyname(secondary))
    with self.assertRaisesRegex(serial.SerialException,
                                r"Could not exclusively lock port"):
      uut.open()
    locked.close()

  def test_102_transport_can_open_close(self):
    """Serial transport can open and close pty (fake serial port) path."""
    _, secondary = pty.openpty()
    uut = serial_transport.SerialTransport(os.ttyname(secondary))
    uut.open()
    uut.close()

  def test_103_transport_can_call_open_twice(self):
    """Serial transport can call open method twice."""
    _, secondary = pty.openpty()
    uut = serial_transport.SerialTransport(os.ttyname(secondary))
    uut.open()
    uut.open()
    uut.close()

  def test_104_transport_can_call_close_twice(self):
    """Serial transport can call close method twice."""
    _, secondary = pty.openpty()
    uut = serial_transport.SerialTransport(os.ttyname(secondary))
    uut.open()
    uut.close()
    uut.close()

  def test_105_transport_can_read(self):
    """Serial transport can read from pty (fake serial port) path."""
    primary, secondary = pty.openpty()
    uut = serial_transport.SerialTransport(os.ttyname(secondary))
    uut.open()
    data = "SOME DATA BYTES TO READ FROM TRANSPORT\n"
    data_in = data.encode("utf-8", "replace")
    with os.fdopen(primary, "wb") as fd:
      fd.write(data_in)
      fd.flush()
      out = uut.read(size=len(data)).decode("utf-8", "replace")
      self.assertEqual(data, out, "Expected {} found {}.".format(data, out))
    uut.close()

  def test_106_transport_can_write(self):
    """Serial transport can write to pty (fake serial port) path."""
    primary, secondary = pty.openpty()
    uut = serial_transport.SerialTransport(os.ttyname(secondary))
    uut.open()
    data = b"SOME DATA BYTES TO WRITE TO TRANSPORT\n"
    with os.fdopen(primary, "rb") as fd:
      out = uut.write(data)
      self.assertEqual(
          len(data), out,
          "Expected {} bytes written found {}.".format(len(data), out))
      data_in = fd.read(len(data))
      self.assertEqual(data, data_in,
                       "Expected {} found {}.".format(data, data_in))
    uut.close()

  def test_107_transport_can_write_unicode(self):
    """Serial transport can write unicode to pty (fake serial port) path."""
    primary, secondary = pty.openpty()
    uut = serial_transport.SerialTransport(os.ttyname(secondary))
    uut.open()
    data = "SOME UNICODE DATA TO WRITE TO TRANSPORT \ufffd\n"
    data_encoded = data.encode("utf-8", errors="replace")
    with os.fdopen(primary, "rb") as fd:
      out = uut.write(data)
      self.assertEqual(
          len(data_encoded), out,
          "Expected {} bytes written found {}.".format(len(data_encoded), out))
      data_in = fd.read(len(data_encoded))
      self.assertEqual(data_encoded, data_in,
                       "Expected {} found {}.".format(data_encoded, data_in))
    uut.close()

  def test_108_transport_returns_empty_string_for_read_timeout(self):
    """Serial transport returns empty string for read timeout."""
    primary, secondary = pty.openpty()
    uut = serial_transport.SerialTransport(os.ttyname(secondary))
    uut.open()
    out = uut.read(size=1, timeout=0.1).decode("utf-8", "replace")
    self.assertEqual(
        "", out,
        "Expected Empty string for read timeout found {!r}.".format(out))
    uut.close()
    os.close(primary)
    os.close(secondary)

  def test_200_transport_fails_recovery_from_read_no_data(self):
    """Serial transport recovers from read no data exception."""
    with mock.patch.object(serial.Serial, "read", autospec=True) as mock_read:
      mock_read.side_effect = serial.SerialException(
          "device reports readiness to read but returned no data "
          "(device disconnected or multiple access on port?)")
      _, secondary = pty.openpty()
      uut = serial_transport.SerialTransport(os.ttyname(secondary))
      uut.open()
      with self.assertRaisesRegex(serial.SerialException,
                                  r"read but returned no data"):
        uut.read(size=1, timeout=0.1)

  def test_201_transport_recovers_from_read_no_data(self):
    """Serial transport recovers from read no data exception."""
    with mock.patch.object(serial.Serial, "read", autospec=True) as mock_read:
      mock_read.side_effect = [
          serial.SerialException(
              "device reports readiness to read but returned no data "
              "(device disconnected or multiple access on port?)"), None, None
      ]
      _, secondary = pty.openpty()
      uut = serial_transport.SerialTransport(os.ttyname(secondary))
      uut.open()
      uut.read(size=1, timeout=0.1)

  def test_300_transport_propagates_baudrate_property_when_open(self):
    """Serial transport propagates baudrate set_property calls when open."""
    _, secondary = pty.openpty()
    uut = serial_transport.SerialTransport(os.ttyname(secondary))
    uut.open()
    with mock.patch(
        "serial.Serial.baudrate", new_callable=mock.PropertyMock) as mock_prop:
      uut.set_property("baudrate", 921600)
      mock_prop.assert_called_once_with(921600)
    uut.close()

  def test_301_transport_propagates_bytesize_property_when_open(self):
    """Serial transport propagates bytesize set_property calls when open."""
    _, secondary = pty.openpty()
    uut = serial_transport.SerialTransport(os.ttyname(secondary))
    uut.open()
    with mock.patch(
        "serial.Serial.bytesize", new_callable=mock.PropertyMock) as mock_prop:
      uut.set_property("bytesize", 8)
      mock_prop.assert_called_once_with(8)
    uut.close()

  def test_302_transport_propagates_parity_property_when_open(self):
    """Serial transport propagates parity set_property calls when open."""
    _, secondary = pty.openpty()
    uut = serial_transport.SerialTransport(os.ttyname(secondary))
    uut.open()
    with mock.patch(
        "serial.Serial.parity", new_callable=mock.PropertyMock) as mock_prop:
      uut.set_property("parity", "N")
      mock_prop.assert_called_once_with("N")
    uut.close()

  def test_303_transport_propagates_stopbits_property_when_open(self):
    """Serial transport propagates stopbits set_property calls when open."""
    _, secondary = pty.openpty()
    uut = serial_transport.SerialTransport(os.ttyname(secondary))
    uut.open()
    with mock.patch(
        "serial.Serial.stopbits", new_callable=mock.PropertyMock) as mock_prop:
      uut.set_property("stopbits", 2)
      mock_prop.assert_called_once_with(2)
    uut.close()

  def test_304_transport_propagates_xonxoff_property_when_open(self):
    """Serial transport propagates xonxoff set_property calls when open."""
    _, secondary = pty.openpty()
    uut = serial_transport.SerialTransport(os.ttyname(secondary))
    uut.open()
    with mock.patch(
        "serial.Serial.xonxoff", new_callable=mock.PropertyMock) as mock_prop:
      uut.set_property("xonxoff", True)
      mock_prop.assert_called_once_with(True)
    uut.close()

  def test_305_transport_propagates_rtscts_property_when_open(self):
    """Serial transport propagates rtscts set_property calls when open."""
    _, secondary = pty.openpty()
    uut = serial_transport.SerialTransport(os.ttyname(secondary))
    uut.open()
    with mock.patch(
        "serial.Serial.rtscts", new_callable=mock.PropertyMock) as mock_prop:
      uut.set_property("rtscts", True)
      mock_prop.assert_called_once_with(True)
    uut.close()

  def test_306_transport_propagates_dsrdtr_property_when_open(self):
    """Serial transport propagates dsrdtr set_property calls when open."""
    _, secondary = pty.openpty()
    uut = serial_transport.SerialTransport(os.ttyname(secondary))
    uut.open()
    with mock.patch(
        "serial.Serial.dsrdtr", new_callable=mock.PropertyMock) as mock_prop:
      uut.set_property("dsrdtr", True)
      mock_prop.assert_called_once_with(True)
    uut.close()

  def test_307_transport_propagates_exclusive_property_when_open(self):
    """Serial transport propagates exclusive set_property calls when open."""
    _, secondary = pty.openpty()
    uut = serial_transport.SerialTransport(os.ttyname(secondary))
    uut.open()
    with mock.patch(
        "serial.Serial.exclusive", new_callable=mock.PropertyMock) as mock_prop:
      uut.set_property("exclusive", False)
      mock_prop.assert_called_once_with(False)
    uut.close()

  def test_310_transport_flush_buffers(self):
    """Serial transport flushes buffers."""
    _, secondary = pty.openpty()
    uut = serial_transport.SerialTransport(os.ttyname(secondary))
    uut.open()
    with mock.patch("serial.Serial.flush") as mock_flush:
      with mock.patch("serial.Serial.reset_input_buffer") as mock_reset_in:
        with mock.patch("serial.Serial.reset_output_buffer") as mock_reset_out:
          uut.flush_buffers()
          mock_flush.assert_called_once()
          mock_reset_in.assert_called_once()
          mock_reset_out.assert_called_once()
    uut.close()

  def test_311_transport_send_xon_xoff(self):
    """Serial transport sends xon and xoff."""
    _, secondary = pty.openpty()
    uut = serial_transport.SerialTransport(os.ttyname(secondary))
    uut.open()
    with mock.patch("serial.Serial.set_input_flow_control") as mock_input_flow:
      uut.send_xon()
      mock_input_flow.assert_called_with(enable=True)
      uut.send_xoff()
      mock_input_flow.assert_called_with(enable=False)
    uut.close()

  def test_312_transport_send_break_byte(self):
    """Serial transport sends break byte."""
    _, secondary = pty.openpty()
    uut = serial_transport.SerialTransport(os.ttyname(secondary))
    uut.open()
    with mock.patch("serial.Serial.write") as mock_write:
      uut.send_break_byte()
      mock_write.assert_called_once_with(b"\x03")
    uut.close()

  def test_320_write_high_baudrate_flow_control(self):
    """Tests write() sends XOFF, XON flow control characters when requested."""
    test_cases = (
        # Low baudrate, flag is False -> XOFF, XON should not be sent
        (115200, False, False),
        # High baudrate, flag is False -> XOFF, XON should not be sent
        (921600, False, False),
        # Low baudrate, flag is True -> XOFF, XON should not be sent
        (115200, True, False),
        # High baudrate, flag is True -> XOFF, XON should be sent
        (921600, True, True),
    )

    for baudrate, use_high_baudrate_flow_control, use_xoff_xon in test_cases:
      mock_serial = mock.Mock()
      with mock.patch.multiple(fcntl, fcntl=mock.DEFAULT, flock=mock.DEFAULT):
        with mock.patch.object(serial, "Serial", return_value=mock_serial):
          uut = serial_transport.SerialTransport(
              "some_path",
              baudrate=baudrate,
              use_high_baudrate_flow_control=use_high_baudrate_flow_control
          )

          uut.open()
          uut.write("foo")
          mock_serial.write.assert_called_once_with(b"foo")

          if use_xoff_xon:
            mock_serial.set_input_flow_control.assert_has_calls(
                [mock.call(enable=False),
                 mock.call(enable=True)])
          else:
            mock_serial.set_input_flow_control.assert_not_called()

          del uut


if __name__ == "__main__":
  unit_test_case.main()
