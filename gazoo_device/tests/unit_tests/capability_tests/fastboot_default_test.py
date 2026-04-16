# Copyright 2023 Google LLC
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

"""Testing the fastboot default capability."""
from unittest import mock

from gazoo_device import errors
from gazoo_device.capabilities import fastboot_default
from gazoo_device.capabilities.interfaces import switchboard_base
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import adb_utils
import immutabledict

_TIMEOUTS = immutabledict.immutabledict({
    "ONLINE": 30,
})
_ADB_SERIAL = "1234abcd"


class FastbootDefaultTests(unit_test_case.UnitTestCase):
  """Test class to verify the behavior of the fastboot default capability."""

  def setUp(self):
    super().setUp()
    self._name = "mock_device"
    self._fastboot_serial = _ADB_SERIAL
    self._add_log_note_fn = mock.MagicMock(
        switchboard_base.SwitchboardBase.add_log_note)
    self._verify_reboot = mock.MagicMock()
    self._root_device_fn = mock.MagicMock()
    self.add_time_mocks()

    self.uut = fastboot_default.FastbootDefault(
        device_name=self._name,
        communication_address=self._fastboot_serial,
        fastboot_serial=self._fastboot_serial,
        timeouts_dict=_TIMEOUTS,
        add_log_note_fn=self._add_log_note_fn,
        verify_reboot_fn=self._verify_reboot,
        root_device_fn=self._root_device_fn)

  # fastboot enter
  @mock.patch.object(adb_utils, "enter_fastboot")
  @mock.patch.object(adb_utils, "is_fastboot_mode", return_value=True)
  def test_fastboot_enter_already_in_fastboot(
      self, mock_is_fastboot_mode, mock_enter_fastboot):
    """Verify fastboot.enter skips enter_fastboot if already in fastboot."""
    self.uut.enter()
    self.assertTrue(mock_is_fastboot_mode.called)
    self.assertFalse(self.uut._add_log_note_fn.called)
    self.assertFalse(mock_enter_fastboot.called)
    self.assertFalse(self.uut._verify_reboot_fn.called)

  @mock.patch.object(
      adb_utils, "enter_fastboot", return_value="enter fastboot output")
  @mock.patch.object(
      adb_utils, "is_fastboot_mode", side_effect=iter([False, True]))
  def test_fastboot_enter_enters_fastboot_mode(
      self, mock_is_fastboot_mode, mock_enter_fastboot):
    """Verify fastboot.enter enters fastboot mode."""
    mock_is_fastboot_mode.__name__ = "mock_is_fastboot_mode"
    self.uut.enter()
    self.assertTrue(mock_is_fastboot_mode.called)
    self.assertTrue(self.uut._add_log_note_fn.called)
    self.assertTrue(mock_enter_fastboot.called)

  @mock.patch.object(
      adb_utils, "enter_fastboot", return_value="enter fastboot output")
  @mock.patch.object(adb_utils, "is_fastboot_mode", return_value=False)
  def test_fastboot_enter_failure(self, mock_is_fastboot_mode,
                                  mock_enter_fastboot):
    """Verify fastboot.enter raise execption on failure."""
    mock_is_fastboot_mode.__name__ = "mock_is_fastboot_mode"
    with self.assertRaisesRegex(errors.DeviceError,
                                "failed to enter fastboot mode"):
      self.uut.enter()
    self.assertEqual(1, mock_enter_fastboot.call_count)
    self.assertTrue(self.uut._add_log_note_fn.called)
    self.assertTrue(mock_is_fastboot_mode.called)

  # fastboot exit
  @mock.patch.object(adb_utils, "exit_fastboot")
  @mock.patch.object(adb_utils, "is_fastboot_mode", return_value=False)
  def test_fastboot_exit_not_in_fastboot(
      self, mock_is_fastboot_mode, mock_exit_fastboot):
    """Verify fastboot.exit skips exit_fastboot if not in fastboot."""
    self.uut.exit()
    self.assertTrue(mock_is_fastboot_mode.called)
    self.assertFalse(self.uut._add_log_note_fn.called)
    self.assertFalse(mock_exit_fastboot.called)
    self.assertFalse(self.uut._verify_reboot_fn.called)

  @mock.patch.object(
      adb_utils, "exit_fastboot", return_value="exit fastboot output")
  @mock.patch.object(adb_utils, "is_fastboot_mode", return_value=True)
  def test_fastboot_exit_not_rooted(
      self, mock_is_fastboot_mode, mock_exit_fastboot):
    """Veriy fastboot.exit exits fastboot mode not rooted."""
    self.uut._root_device_fn.return_value = True
    self.uut.exit()
    self.assertTrue(mock_is_fastboot_mode.called)
    self.assertTrue(self.uut._add_log_note_fn.called)
    self.assertTrue(mock_exit_fastboot.called)
    self.assertTrue(self.uut._verify_reboot_fn.called)
    self.assertTrue(self.uut._root_device_fn.called)

  @mock.patch.object(
      adb_utils, "exit_fastboot", return_value="exit fastboot output")
  @mock.patch.object(adb_utils, "is_fastboot_mode", return_value=True)
  def test_fastboot_exit_is_rooted(
      self, mock_is_fastboot_mode, mock_exit_fastboot):
    """Verify fastboot.exit exits fastboot mode is rooted."""
    self.uut._root_device_fn.return_value = False
    self.uut.exit()
    self.assertTrue(mock_is_fastboot_mode.called)
    self.assertTrue(self.uut._add_log_note_fn.called)
    self.assertTrue(mock_exit_fastboot.called)
    self.assertTrue(self.uut._verify_reboot_fn.called)


if __name__ == "__main__":
  unit_test_case.main()
