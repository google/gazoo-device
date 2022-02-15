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

"""Tests the adb_transport.py module."""
from unittest import mock

from gazoo_device.switchboard.transports import adb_transport
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import adb_utils

_TEST_ADB_PATH = "/usr/bin/adb_fake"
_TEST_FASTBOOT_PATH = "/usr/bin/fastboot_fake"


class AdbTransportTests(unit_test_case.UnitTestCase):

  def setUp(self):
    super().setUp()

    get_fastboot_path_patch = mock.patch.object(
        adb_utils, "get_fastboot_path", return_value=_TEST_FASTBOOT_PATH)
    self.mock_get_fastboot_path = get_fastboot_path_patch.start()
    self.addCleanup(get_fastboot_path_patch.stop)

    get_adb_path_patch = mock.patch.object(
        adb_utils, "get_adb_path", return_value=_TEST_ADB_PATH)
    self.mock_get_adb_path = get_adb_path_patch.start()
    self.addCleanup(get_adb_path_patch.stop)

  def test_001_transport_calls_get_adb_path(self):
    """AdbTransport calls get_adb_path to get adb_path."""
    adb_serial = "bogus"
    uut = adb_transport.AdbTransport(adb_serial)
    self.assertEqual(
        _TEST_ADB_PATH, uut._adb_path,
        "Expected adb path {} found {}".format(_TEST_ADB_PATH, uut._adb_path))
    self.mock_get_adb_path.assert_called()
    self.mock_get_fastboot_path.assert_called()

  def test_002_transport_uses_alternative_adb_path(self):
    """AdbTransport skips get_adb_path to get adb_path."""
    adb_serial = "bogus"
    adb_path = "/some/bogus/path"
    uut = adb_transport.AdbTransport(adb_serial, adb_path=adb_path)
    self.assertNotEqual(
        _TEST_ADB_PATH, uut._adb_path,
        "Expected adb path {} to not equal {}".format(_TEST_ADB_PATH,
                                                      uut._adb_path))
    self.mock_get_adb_path.assert_not_called()
    self.mock_get_fastboot_path.assert_called()

  def test_003_transport_calls_get_fastboot_path(self):
    """AdbTransport calls get_fastboot_path to get fastboot_path."""
    adb_serial = "bogus"
    uut = adb_transport.AdbTransport(adb_serial)
    self.assertEqual(
        _TEST_ADB_PATH, uut._adb_path,
        "Expected adb path {} found {}".format(_TEST_ADB_PATH, uut._adb_path))
    self.mock_get_adb_path.assert_called()
    self.mock_get_fastboot_path.assert_called()

  def test_004_transport_uses_alternative_fastboot_path(self):
    """AdbTransport skips get_fastboot_path to get fastboot_path."""
    adb_serial = "bogus"
    fastboot_path = "/some/bogus/path"
    uut = adb_transport.AdbTransport(adb_serial, fastboot_path=fastboot_path)
    self.assertNotEqual(
        _TEST_FASTBOOT_PATH, uut._fastboot_path,
        "Expected fastboot path {} to not equal {}".format(
            _TEST_FASTBOOT_PATH, uut._fastboot_path))
    self.mock_get_adb_path.assert_called()
    self.mock_get_fastboot_path.assert_not_called()

  def test_005_transport_uses_shell_in_args(self):
    """AdbTransport uses shell in args."""
    adb_serial = "bogus"
    uut = adb_transport.AdbTransport(adb_serial)
    self.assertIn(
        adb_serial, uut._args,
        "Expected {} in args found {}".format(adb_serial, uut._args))
    self.assertIn("shell", uut._args,
                  "Expected shell in args found {}".format(uut._args))
    self.mock_get_fastboot_path.assert_called()

  def test_006_transport_uses_logcat_in_args(self):
    """AdbTransport uses logcat in args if log_only=True."""
    adb_serial = "bogus"
    uut = adb_transport.AdbTransport(adb_serial, command="logcat -v threadtime")
    self.assertIn(
        adb_serial, uut._args,
        "Expected {} in args found {}".format(adb_serial, uut._args))
    self.assertIn("logcat", uut._args,
                  "Expected logcat in args found {}".format(uut._args))
    self.mock_get_fastboot_path.assert_called()

  @mock.patch.object(adb_utils, "is_device_online", return_value=True)
  def test_020_transport_calls_is_device_online_yes(self,
                                                    mock_is_device_online):
    """AdbTransport calls is_device_online and returns True."""
    adb_serial = "bogus"
    uut = adb_transport.AdbTransport(adb_serial)
    self.assertTrue(uut._is_ready_to_open(),
                    "Expected transport is ready to open")
    self.mock_get_fastboot_path.assert_called()
    mock_is_device_online.assert_called()


if __name__ == "__main__":
  unit_test_case.main()
