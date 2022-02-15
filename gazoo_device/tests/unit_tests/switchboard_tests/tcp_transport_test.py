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

"""Tests the tcp_transport.py module."""
import socket
from unittest import mock

from gazoo_device.switchboard.transports import tcp_transport
from gazoo_device.tests.unit_tests.utils import unit_test_case

_LISTENING_SERVER_MESSAGE = "listening\n"
_SERVER_PORT = 4232  # Arbitrary non-privileged port not used by adb
_WRONG_SERVER_PORT = 9
_INVALID_SERVER_PORT = -1
_BOGUS_HOST_ADDR = "bad.host.zzz"


def mock_send(data):
  return len(data)


class TcpTransportTests(unit_test_case.UnitTestCase):

  def setUp(self):
    """Create server hostname."""
    super().setUp()
    self.server = "127.0.0.1"  # Server on THIS computer (loopback)
    self.uut = tcp_transport.TcpTransport(self.server, _SERVER_PORT)

  def test_001_transport_starts_closed(self):
    """Newly created transport starts closed."""
    self.assertFalse(self.uut.is_open(),
                     "Expected tcp transport connection to be closed")

  def test_002_transport_returns_property_dict(self):
    """TCP transport returns read-only property dict."""
    property_dict = self.uut.get_all_properties()
    self.assertTrue(
        property_dict,
        "Expected at least one property key, found 0.")
    test_key = list(property_dict.keys())[0]
    self.assertIsInstance(
        property_dict, dict,
        "Expected dictionary of properties found {}.".format(
            type(property_dict)))
    # Change one value in original dictionary returned
    property_dict[test_key] = _WRONG_SERVER_PORT
    property_dict2 = self.uut.get_all_properties()
    # Verify 2nd dictionary doesn't show changed value
    self.assertNotEqual(
        property_dict[test_key], property_dict2[test_key],
        "Expected read only dictionary to be returned. "
        "Found dictionary changes influences original.")

  def test_003_transport_returns_default_value_on_get_property(self):
    """TCP transport returns default value on get_property call."""
    default_value = "bogus value"
    value = self.uut.get_property("bogus_key", value=default_value)
    self.assertEqual(
        value, default_value,
        "Expected default value {} provided found {}.".format(
            default_value, value))

  def test_004_transport_returns_value_on_get_property(self):
    """TCP transport returns default value on get_property call."""
    property_dict = self.uut.get_all_properties()
    self.assertTrue(
        property_dict,
        "Expected at least one property key, found 0.")
    test_key = list(property_dict.keys())[0]
    value = self.uut.get_property(test_key)
    self.assertEqual(
        property_dict[test_key], value,
        "Expected value {} found {}".format(property_dict[test_key], value))

  def test_005_transport_returns_property_list(self):
    """TCP transport returns non-empty property list."""
    property_list = self.uut.get_property_list()
    self.assertTrue(
        property_list,
        "Expected property list length > 0 found {}".format(len(property_list)))

  def test_006_transport_can_set_all_properties(self):
    """TCP transport can set all properties to new values."""
    property_list = self.uut.get_property_list()
    for key in property_list:
      # Set all properties values to their key
      self.uut.set_property(key, key)
      value = self.uut.get_property(key)
      self.assertEqual(
          key, value,
          f"Expected property {key} value to be {key} found {value}.")

  def test_007_transport_cant_set_bogus_property(self):
    """TCP transport can't set a bogus property key."""
    with self.assertRaisesRegex(KeyError,
                                r"Property bogus key doesn't exist for"):
      self.uut.set_property("bogus key", "bogus value")

  def test_008_transport_read_returns_none(self):
    """TCP transport read returns None for unopened transport."""
    out = self.uut.read()
    self.assertIsNone(out,
                      "Expected None for read result found {}.".format(out))

  def test_009_transport_write_returns_none(self):
    """TCP transport write returns None for unopened transport."""
    data = "SOME DATA TO WRITE TO TRANSPORT"
    out = self.uut.write(data)
    self.assertIsNone(out,
                      "Expected None for write result found {}.".format(out))
    self.uut.close()
    self.assertFalse(
        self.uut.is_open(),
        "Expected tcp transport is_open to return False after call to close")

  def test_100_transport_cant_open_bogus_host(self):
    """TCP Transport can't open bogus host."""
    with self.assertRaisesRegex(ValueError,
                                r"Host Address bad\.host\.zzz not valid"):
      tcp_transport.TcpTransport(_BOGUS_HOST_ADDR, _SERVER_PORT)

  def test_101_transport_cant_open_invalid_port(self):
    """TCP Transport can't open invalid port."""
    with self.assertRaisesRegex(ValueError,
                                r"Port -1 out of range"):
      tcp_transport.TcpTransport(self.server, _INVALID_SERVER_PORT)

  @mock.patch("socket.socket")
  def test_102_transport_can_open_close(self, mock_socket):
    """TCP Transport can open and close."""
    self.uut.open()
    self.assertTrue(
        self.uut.is_open(),
        "Expected tcp transport is_open to return True after call to open")
    self.uut.close()
    self.assertFalse(
        self.uut.is_open(),
        "Expected tcp transport is_open to return False after call to close")

  @mock.patch("socket.socket")
  def test_103_transport_can_call_open_twice(self, mock_socket):
    """TCP transport can call open method twice."""
    self.uut.open()
    self.assertTrue(
        self.uut.is_open(),
        "Expected tcp transport is_open to return True after call to open")
    self.uut.open()
    self.assertTrue(
        self.uut.is_open(),
        "Expected tcp transport is_open to return True after call to open")
    self.uut.close()
    self.assertFalse(
        self.uut.is_open(),
        "Expected tcp transport is_open to return False after call to close")

  @mock.patch("socket.socket")
  def test_104_transport_can_call_close_twice(self, mock_socket):
    """TCP transport can call close method twice."""
    self.uut.open()
    self.assertTrue(
        self.uut.is_open(),
        "Expected tcp transport is_open to return True after call to open")
    self.uut.close()
    self.assertFalse(
        self.uut.is_open(),
        "Expected tcp transport is_open to return False after call to close")
    self.uut.close()
    self.assertFalse(
        self.uut.is_open(),
        "Expected tcp transport is_open to return False after call to close")

  @mock.patch("socket.socket")
  def test_105_transport_can_read(self, mock_socket):
    """TCP transport can read from server."""
    # mock the socket.recv() method to return a specific string
    mock_socket.return_value.recv.return_value = _LISTENING_SERVER_MESSAGE
    max_bytes = 64
    self.uut.open()
    self.assertTrue(
        self.uut.is_open(),
        "Expected tcp transport is_open to return True after call to open")
    echo_msg = self.uut.read(max_bytes, timeout=10.0)
    self.assertIn(
        _LISTENING_SERVER_MESSAGE, echo_msg,
        "Expected '{}' in message returned by read, instead got: {}".format(
            _LISTENING_SERVER_MESSAGE, echo_msg))
    self.uut.close()
    self.assertFalse(
        self.uut.is_open(),
        "Expected tcp transport is_open to return False after call to close")

  @mock.patch("socket.socket")
  def test_106_transport_can_write(self, mock_socket):
    """TCP transport can write to server."""
    mock_socket.return_value.send.side_effect = mock_send
    self.uut.open()
    self.assertTrue(
        self.uut.is_open(),
        "Expected tcp transport is_open to return True after call to open")
    num_bytes = self.uut.write("Dude!", timeout=10.0)
    self.assertEqual(
        num_bytes, len("Dude!"),
        "After call to write, expected num_bytes >= {} instead got {}".format(
            len("Dude!"), num_bytes))
    self.uut.close()
    self.assertFalse(
        self.uut.is_open(),
        "Expected tcp transport is_open to return False after call to close")

  @mock.patch("socket.socket")
  def test_107_transport_can_write_unicode(self, mock_socket):
    """TCP transport can write unicode."""
    mock_socket.return_value.send.side_effect = mock_send
    data = "SOME UNICODE DATA TO WRITE TO TRANSPORT \ufffd\n"
    data_encoded = data.encode("utf-8", errors="replace")
    self.assertNotEqual(len(data), len(data_encoded))
    self.uut.open()
    self.assertTrue(
        self.uut.is_open(),
        "Expected tcp transport is_open to return True after call to open")
    num_bytes = self.uut.write(data)
    self.assertEqual(
        num_bytes, len(data_encoded),
        "After call to write, expected num_bytes == {} instead got {}".format(
            len(data_encoded), num_bytes))
    self.uut.close()
    self.assertFalse(
        self.uut.is_open(),
        "Expected tcp transport is_open to return False after call to close")

  @mock.patch("socket.socket")
  def test_108_transport_returns_none_for_socket_read_timeout(
      self, mock_socket):
    """TCP transport returns None for socket read timeout."""
    mock_socket.return_value.recv.side_effect = socket.timeout
    max_bytes = 128
    quick_timeout = 0.01
    self.uut.open()
    self.assertTrue(
        self.uut.is_open(),
        "Expected tcp transport is_open to return True after call to open")
    message = self.uut.read(max_bytes, timeout=quick_timeout)
    self.assertFalse(
        message,
        "Expected empty string in message returned by read, instead got: {}"
        .format(message))


if __name__ == "__main__":
  unit_test_case.main()
