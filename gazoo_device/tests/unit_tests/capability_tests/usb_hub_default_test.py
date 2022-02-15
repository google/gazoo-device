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

"""Unit tests for the usb_hub_default capability."""
from unittest import mock

from gazoo_device import errors
from gazoo_device.auxiliary_devices import cambrionix
from gazoo_device.capabilities import usb_hub_default
from gazoo_device.switchboard import switchboard
from gazoo_device.tests.unit_tests.utils import unit_test_case


class UsbHubDefaultTests(unit_test_case.UnitTestCase):
  """Test class to verify the behavior of the usb_hub_default capability."""

  def setUp(self):
    super().setUp()
    self._device_name = "test-device-0001"
    self._hub_name = "cambrionix-xx31"
    self._capability_name = "Usb Hub"
    self._mock_wait_for_bootup_complete = mock.Mock()
    self.cambrionix_mock = mock.MagicMock(spec=cambrionix.Cambrionix)
    self.cambrionix_mock.switch_power.get_mode.return_value = "sync"
    self.mock_switchboard = mock.MagicMock(spec=switchboard.SwitchboardDefault)
    self.get_switchboard_if_initialized = mock.MagicMock(
        return_value=self.mock_switchboard)
    self.manager_mock = mock.Mock()
    self.manager_mock.create_device.return_value = self.cambrionix_mock
    self.mock_get_manager = mock.Mock(return_value=self.manager_mock)
    self.usb_supported_modes_patch = mock.patch.object(
        usb_hub_default.UsbHubDefault,
        "supported_modes",
        new_callable=mock.PropertyMock,
        return_value=["off", "sync", "charge"])
    self.usb_supported_modes_patch.start()
    self.addCleanup(self.usb_supported_modes_patch.stop)
    self.uut = usb_hub_default.UsbHubDefault(
        self._device_name,
        get_manager=self.mock_get_manager,
        hub_name=self._hub_name,
        device_port=1,
        get_switchboard_if_initialized=self.get_switchboard_if_initialized)

  def test_001_usb_hub_argument_raises_error(self):
    """Verifies capability raises error if device parameter is None."""
    self.uut = usb_hub_default.UsbHubDefault(
        self._device_name,
        get_manager=self.mock_get_manager,
        hub_name=self._hub_name,
        device_port=None,
        get_switchboard_if_initialized=self.get_switchboard_if_initialized)
    with self.assertRaisesRegex(errors.CapabilityNotReadyError,
                                "device_usb_port"):
      self.uut.health_check()

  def test_002_usb_hub_get_name(self):
    """Verifies usb_hub.name is called."""
    name = self.uut.name
    self.assertEqual(name, self._hub_name)

  def test_003_usb_hub_get_device_port(self):
    """Verifies usb_hub.device_port is called."""
    port = self.uut.device_port
    self.assertEqual(port, 1)

  def test_004_usb_hub_get_device_power(self):
    """Verifies usb_hub.get_device_power is called."""
    usb_port_mode = self.uut.get_device_power()
    self.assertEqual(usb_port_mode, "sync")

  def test_006_usb_hub_set_device_power_off(self):
    """Verifies usb_hub.set_device_power mode 'off' calls switch_power."""
    self.uut.set_device_power("off")
    self.uut._usb_hub.switch_power.set_mode.assert_called_with("off", 1)

  def test_007_usb_hub_set_device_power_sync(self):
    """Verifies usb_hub.set_device_power mode 'sync' is called."""
    self.cambrionix_mock.switch_power.get_mode.return_value = "charge"
    self.uut.set_device_power("sync")
    self.uut._usb_hub.switch_power.set_mode.assert_called_with("sync", 1)

  def test_008_usb_hub_set_device_power_charge(self):
    """Verifies usb_hub.set_device_power mode 'charge' is called."""
    self.uut.set_device_power("charge")
    self.uut._usb_hub.switch_power.set_mode.assert_called_with("charge", 1)

  def test_009_switch_power_off(self):
    """Verifies usb_hub.power_off is called."""
    self.uut.power_off(port=1)
    self.uut._usb_hub.switch_power.set_mode.assert_called_with("off", 1)

  def test_010_switch_power_on(self):
    """Verifies usb_hub.power_on is called."""
    self.cambrionix_mock.switch_power.get_mode.return_value = "off"
    self.uut.power_on(port=1)
    self.uut._usb_hub.switch_power.set_mode.assert_called_with("sync", 1)

  def test_011_power_on_without_sync(self):
    """Verifies that charge mode is used when data_sync is False."""
    self.uut.power_on(1, data_sync=False)
    self.uut._usb_hub.switch_power.set_mode.assert_called_with("charge", 1)

  def test_020_make_device_ready(self):
    """Verify that the usb hub check_device_ready is called."""
    self.uut.check_device_ready()
    self.manager_mock.create_device.assert_called()

  def test_030_verify_add_log_note_called(self):
    """Verify that the add_log_note_fn is called with the power change note."""
    self.uut.power_off(port=1)
    self.mock_switchboard.add_log_note.assert_called_once_with(
        "Setting device USB power to 'off' for "
        "hub cambrionix-xx31 and port 1")

  def test_040_verify_log_note_added_for_change_triggers_reboot(self):
    """Verify that a note is logged if change_triggers_reboot is True."""
    self.uut = usb_hub_default.UsbHubDefault(
        self._device_name,
        get_manager=self.mock_get_manager,
        hub_name=self._hub_name,
        device_port=1,
        get_switchboard_if_initialized=self.get_switchboard_if_initialized,
        change_triggers_reboot=True,
        wait_for_bootup_complete_fn=self._mock_wait_for_bootup_complete)
    self.uut.power_off(port=1)
    self.mock_switchboard.add_log_note.assert_called_with(
        "GDM triggered reboot via USB power change.")

  def test_041_verify_wait_for_bootup_complete_fn_is_called(self):
    """Verify wait_for_bootup_complete_fn is called when expecting a reboot."""
    self.uut = usb_hub_default.UsbHubDefault(
        self._device_name,
        get_manager=self.mock_get_manager,
        hub_name=self._hub_name,
        device_port=1,
        get_switchboard_if_initialized=self.get_switchboard_if_initialized,
        change_triggers_reboot=True,
        wait_for_bootup_complete_fn=self._mock_wait_for_bootup_complete)
    self.uut.power_off(port=1)
    self._mock_wait_for_bootup_complete.assert_called_once()

  def test_close_doesnt_close_hub_instance_if_not_initialized(self):
    """Tests that close() doesn't close the hub instance if it's initialized."""
    self.uut.close()
    self.cambrionix_mock.close.assert_not_called()

  def test_close_closes_hub_instance_if_initialized(self):
    """Tests that close() closes the hub device instance if it's initialized."""
    self.uut.health_check()
    self.cambrionix_mock.close.assert_not_called()
    self.uut.close()
    self.cambrionix_mock.close.assert_called_once()


if __name__ == "__main__":
  unit_test_case.main()
