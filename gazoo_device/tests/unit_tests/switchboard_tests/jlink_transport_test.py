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

"""Tests the jlink_transport.py module."""
from unittest import mock

from gazoo_device import errors
from gazoo_device.switchboard.transports import jlink_transport
from gazoo_device.tests.unit_tests.utils import unit_test_case
import intelhex

_JLINK_SERIAL = "50129239"
_CHIP_NAME = "NRF52840_XXAA"

_BINARY_DATA = [102, 111, 111]  # ASCII bytes for "foo"
_STRING_DATA = b"foo"
_BINARY_DATA_UNICODE = [226, 130, 172]  # Unicode bytes for Euro symbol (U+20AC)
_STRING_DATA_UNICODE = b"\xe2\x82\xac".decode("utf-8")  # Euro symbol


class JLinkTransportTests(unit_test_case.UnitTestCase):

  def setUp(self):
    super().setUp()
    jlink_patcher = mock.patch("pylink.jlink.JLink")
    self.mock_jlink_class = jlink_patcher.start()
    self.addCleanup(jlink_patcher.stop)

    self.mock_jlink = self.mock_jlink_class.return_value
    self._set_jlink_opened_values(True, True,
                                  True)  # Set the transport to "open"

    self.uut = jlink_transport.JLinkTransport(_JLINK_SERIAL, _CHIP_NAME)

  def test_1_no_jlink_dll_raises_error(self):
    """Test that an actionable error is raised if the J-Link DLL is missing."""
    self.mock_jlink_class.side_effect = TypeError(
        "Expected to be given a valid DLL.")
    with self.assertRaisesRegex(
        errors.DependencyUnavailableError,
        "No J-Link DLL found. Install the J-Link SDK"):
      jlink_transport.JLinkTransport(_JLINK_SERIAL, _CHIP_NAME)

  def test_10_is_open_true(self):
    """Test a scenario in which is_open should return True."""
    self.assertTrue(self.uut.is_open())

  def test_11_is_open_false(self):
    """Test scenarios in which is_open should return False."""
    test_data = [(False, False, False), (True, False, False),
                 (True, True, False)]
    for values in test_data:
      self._set_jlink_opened_values(*values)
      self.assertFalse(self.uut.is_open())
      self._set_jlink_opened_values(True, True, True)  # Restore the values

  def test_20_open(self):
    """Test JLinkTransport.open."""
    self._set_jlink_opened_values(False, False, False)
    self.uut.open()
    expected_calls = [
        self.mock_jlink.open, self.mock_jlink.set_tif, self.mock_jlink.connect,
        self.mock_jlink.rtt_start
    ]
    for expected_call in expected_calls:
      expected_call.assert_called_once()

  def test_25_close(self):
    """Test JLinkTransport.close."""
    self.uut.close()
    self.mock_jlink.rtt_stop.assert_called_once()
    self.mock_jlink.close.assert_called_once()

  def test_26_close_not_opened(self):
    """Test JLinkTransport.close when JLink isn't open."""
    self._set_jlink_opened_values(False, False, False)
    self.uut.close()
    self.mock_jlink.rtt_stop.assert_not_called()
    self.mock_jlink.close.assert_not_called()

  def test_30_rtt_read(self):
    """Test that transport is able to read from RTT buffer."""
    self.mock_jlink.rtt_read.return_value = _BINARY_DATA
    read_value = self.uut.read()
    self.assertEqual(read_value, _STRING_DATA)

  def test_40_rtt_write(self):
    """Test that transport is able to write to RTT buffer."""
    self.mock_jlink.rtt_write.return_value = len(_STRING_DATA)
    bytes_written = self.uut.write(_STRING_DATA)
    self.mock_jlink.rtt_write.assert_called_once_with(0, _BINARY_DATA)
    self.assertEqual(bytes_written, len(_STRING_DATA))

  def test_41_rtt_write_unicode(self):
    """Test that transport is able to write unicode to RTT buffer."""
    self.mock_jlink.rtt_write.return_value = len(_BINARY_DATA_UNICODE)
    bytes_written = self.uut.write(_STRING_DATA_UNICODE)
    self.mock_jlink.rtt_write.assert_called_once_with(0, _BINARY_DATA_UNICODE)
    self.assertEqual(bytes_written, len(_BINARY_DATA_UNICODE))

  def test_50_reset(self):
    """Test JLinkTransport.reset."""
    self.uut.reset()
    self.mock_jlink.reset.assert_called_once()
    self.mock_jlink.restart.assert_called_once()

  def test_60_flash(self):
    """Test JLinkTransport.flash."""
    mock_image = mock.Mock()
    mock_segments = [(0, 10), (10, 20)]
    mock_binarray = mock.Mock()

    with mock.patch.object(intelhex, "IntelHex", return_value=mock_image):
      mock_image.segments.return_value = mock_segments
      mock_image.tobinarray.return_value = mock_binarray

      self.uut.flash("foo_path")
      self.mock_jlink.rtt_stop.assert_called_once()
      self.mock_jlink.halt.assert_called_once()

      mock_image.tobinarray.assert_has_calls(
          [mock.call(start=0, size=10),
           mock.call(start=10, size=10)])
      self.mock_jlink.flash_write8.assert_has_calls(
          [mock.call(0, mock_binarray),
           mock.call(10, mock_binarray)])

      self.mock_jlink.reset.assert_called_once()
      self.mock_jlink.restart.assert_called_once()
      self.mock_jlink.rtt_start.assert_called_once()

  def _set_jlink_opened_values(self, opened, connected, target_connected):
    """Set mock JLink's opened, connected, target_connected values."""
    self.mock_jlink.opened.return_value = opened
    self.mock_jlink.connected.return_value = connected
    self.mock_jlink.target_connected.return_value = target_connected


if __name__ == "__main__":
  unit_test_case.main()
