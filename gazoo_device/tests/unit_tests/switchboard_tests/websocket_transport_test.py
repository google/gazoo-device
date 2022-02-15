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
"""Tests the websocket_transport.py module."""
from unittest import mock

from gazoo_device import gdm_logger
from gazoo_device.switchboard.transports import websocket_transport
from gazoo_device.tests.unit_tests.utils import unit_test_case
import websocket

logger = gdm_logger.get_logger()

_BOGUS_URL = "ws://bogushost:1234/bogusbogusbogus"


class WebSocketTransportTests(unit_test_case.UnitTestCase):

  def setUp(self):
    super().setUp()
    self.uut = websocket_transport.WebSocketTransport(_BOGUS_URL)

  def test_001_transport_closed(self):
    """Test calling transport methods when transport is closed."""
    self.assertFalse(self.uut.is_open(),
                     "Expected websocket transport to be closed")
    self.assertIs(None, self.uut.read())
    self.assertIs(None, self.uut.write("bogusdata"))
    self.assertIs(None, self.uut.close())

  def test_002_transport_cannot_connect(self):
    """Test open() raises an exception when URL is invalid."""
    with self.assertRaises(Exception):
      transport = websocket_transport.WebSocketTransport("ws://somehost:8888")
      transport.open()

  def test_003_transport_cannot_connect(self):
    """Test open() raises an exception when nobody is listening on that port."""
    with self.assertRaisesRegexp(Exception, "Connection refused"):
      transport = websocket_transport.WebSocketTransport("ws://localhost:8888")
      transport.open()

  def test_010_get_all_properties(self):
    """get_all_properties is a dict of non-zero length."""
    transport_props = self.uut.get_all_properties()
    self.assertTrue(transport_props)
    prop_keys = self.uut.get_property_list()
    self.assertTrue(prop_keys)

  def test_011_get_property_list(self):
    """get_property_list is a list of non-zero length."""
    prop_keys = self.uut.get_property_list()
    self.assertTrue(prop_keys)

  def test_012_properties_read_only(self):
    """That that property dict returned by get_all_properties is read-only."""
    transport_props = self.uut.get_all_properties()
    test_key = list(transport_props.keys())[0]
    transport_props[test_key] = "test_value"
    self.assertNotEqual(transport_props[test_key],
                        self.uut.get_property(test_key))

  def test_013_can_set_valid_props(self):
    """Test setting properties defined in the transport."""
    for idx, prop_key in enumerate(self.uut.get_property_list()):
      self.uut.set_property(prop_key, idx)
      self.assertEqual(self.uut.get_property(prop_key), idx)

  def test_014_cant_set_invalid_props(self):
    """Test setting a property not defined in transport properties."""
    bogus_prop = "bogus_prop"
    with self.assertRaisesRegexp(
        KeyError, "Property {} doesn't exist".format(bogus_prop)):
      self.uut.set_property(bogus_prop, "bogus_val")

  @mock.patch("websocket.create_connection")
  def test_100_transport_can_open_close(self, mock_websocket):
    """WebSocketTransport can open and close."""
    self.uut.open()
    self.assertTrue(self.uut.is_open())
    self.uut.close()
    self.assertFalse(self.uut.is_open())
    self.assertIsNone(self.uut._websocket)

  def test_101_transport_closed_read_write(self):
    """read, write return None if transport is closed."""
    self.assertIsNone(self.uut.read())
    self.assertIsNone(self.uut.write("somedata"))

  @mock.patch("websocket.create_connection")
  def test_102_transport_open_close_repeated_calls(self, mock_websocket):
    """Repeated calls to open or close do nothing."""
    self.uut.open()
    self.assertTrue(self.uut.is_open())
    self.uut.open()
    self.assertTrue(self.uut.is_open())

    self.uut.close()
    self.assertFalse(self.uut.is_open())
    self.uut.close()
    self.assertFalse(self.uut.is_open())

  @mock.patch("websocket.create_connection")
  def test_103_transport_can_read(self, mock_create_connection):
    """WebSocketTransport can read."""
    read_expected = "somedata"
    mock_create_connection.return_value.recv.return_value = read_expected

    self.uut.open()
    read_actual = self.uut.read()
    self.assertEqual(read_expected, read_actual)
    self.uut.close()

  @mock.patch("websocket.create_connection")
  def test_104_transport_can_write(self, mock_create_connection):
    """WebSocketTransport can write."""
    write_data = "somedata"
    mock_create_connection.return_value.send.side_effect = len

    self.uut.open()
    bytes_written = self.uut.write(write_data)
    mock_create_connection.return_value.send.assert_called_with(write_data)
    self.assertEqual(bytes_written, len(write_data))
    self.uut.close()

  @mock.patch("websocket.create_connection")
  @mock.patch.object(websocket_transport.logger, "debug")
  def test_105_transport_read_exception(self, mock_debug,
                                        mock_create_connection):
    """Test that read exceptions are logged and empty string is returned."""
    mock_create_connection.return_value.recv.side_effect = websocket.WebSocketProtocolException

    self.uut.open()
    read_bytes = self.uut.read()
    self.assertEqual("", read_bytes)
    self.uut.close()
    mock_debug.assert_any_call(
        "_read() from websocket with URL {} failed due to an error.".format(
            _BOGUS_URL))

  @mock.patch("websocket.create_connection")
  @mock.patch.object(websocket_transport.logger, "debug")
  def test_106_transport_write_exception(self, mock_debug,
                                         mock_create_connection):
    """Test that write exceptions are logged and 0 is returned."""
    mock_create_connection.return_value.send.side_effect = websocket.WebSocketProtocolException

    self.uut.open()
    bytes_sent = self.uut.write("somedata")
    self.assertEqual(0, bytes_sent)
    self.uut.close()
    mock_debug.assert_any_call(
        "_write() to websocket with URL {} failed due to an error.".format(
            _BOGUS_URL))

  @mock.patch("websocket.create_connection")
  @mock.patch.object(websocket_transport.logger, "debug")
  def test_110_transport_read_timeout(self, mock_debug, mock_create_connection):
    """Test that read timeout exceptions are not logged."""
    mock_create_connection.return_value.recv.side_effect = websocket.WebSocketTimeoutException

    self.uut.open()
    read_bytes = self.uut.read()
    self.assertEqual("", read_bytes)
    self.uut.close()

    mock_debug.assert_not_called()

  @mock.patch("websocket.create_connection")
  @mock.patch.object(websocket_transport.logger, "debug")
  def test_111_transport_write_timeout(self, mock_debug,
                                       mock_create_connection):
    """Test that write timeout exceptions are not logged and 0 is returned."""
    mock_create_connection.return_value.send.side_effect = websocket.WebSocketTimeoutException

    self.uut.open()
    bytes_sent = self.uut.write("somedata")
    self.assertEqual(0, bytes_sent)
    self.uut.close()

    mock_debug.assert_not_called()


if __name__ == "__main__":
  unit_test_case.main()
