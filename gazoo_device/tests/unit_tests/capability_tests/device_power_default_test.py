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
"""Unit tests for device_power_default capability."""
from unittest import mock

from absl.testing import parameterized
from gazoo_device import errors
from gazoo_device import manager
from gazoo_device.auxiliary_devices import cambrionix
from gazoo_device.base_classes import gazoo_device_base
from gazoo_device.capabilities import device_power_default
from gazoo_device.switchboard import switchboard
from gazoo_device.tests.unit_tests.utils import unit_test_case


class DevicePowerDefaultTests(unit_test_case.UnitTestCase):
  """Unit tests for device_power_default capability."""

  def setUp(self):
    super().setUp()
    self.name = "test_device-1234"
    self.mock_manager = mock.MagicMock(spec=manager.Manager)
    self.mock_switchboard = mock.MagicMock(spec=switchboard.SwitchboardDefault)
    self.port_num = 3
    self.add_time_mocks()
    self.props = {
        "persistent_identifiers": {
            "name": self.name
        },
        "optional": {
            "device_usb_hub_name": "cambrionix-1234",
            "device_usb_port": self.port_num
        }
    }
    self.mock_cambrionix = mock.MagicMock(spec=cambrionix.Cambrionix)
    self.mock_manager.create_device.return_value = self.mock_cambrionix
    gazoo_device_base_instance_spec = mock.create_autospec(
        spec=gazoo_device_base.GazooDeviceBase, instance=True)
    self.wait_until_connected = mock.MagicMock(
        spec=gazoo_device_base_instance_spec.wait_until_connected)
    self.get_switchboard_if_initialized = mock.MagicMock(
        spec=gazoo_device_base_instance_spec._get_switchboard_if_initialized,
        return_value=self.mock_switchboard)
    self.wait_for_bootup_complete = mock.MagicMock(
        spec=gazoo_device_base_instance_spec.wait_for_bootup_complete)
    # To verify the call sequence of unrelated mocks, attach them to a common
    # mock and assert on the call sequence of the common mock.
    self.mock_call_sequence_tracker = mock.MagicMock()
    self.mock_call_sequence_tracker.attach_mock(
        self.mock_cambrionix.switch_power.power_on, "power_on")
    self.mock_call_sequence_tracker.attach_mock(
        self.mock_cambrionix.switch_power.power_off, "power_off")
    self.mock_call_sequence_tracker.attach_mock(
        self.mock_switchboard.open_all_transports, "open_all_transports")
    self.mock_call_sequence_tracker.attach_mock(
        self.mock_switchboard.close_all_transports, "close_all_transports")
    self.mock_call_sequence_tracker.attach_mock(
        self.wait_until_connected, "wait_until_connected")
    self.mock_call_sequence_tracker.attach_mock(
        self.wait_for_bootup_complete, "wait_for_bootup_complete")

    self.uut = device_power_default.DevicePowerDefault(
        device_name=self.name,
        create_device_func=self.mock_manager.create_device,
        default_hub_type="cambrionix",
        props=self.props,
        usb_ports_discovered=False,
        wait_until_connected_fn=self.wait_until_connected,
        wait_for_bootup_complete_fn=self.wait_for_bootup_complete,
        get_switchboard_if_initialized=self.get_switchboard_if_initialized,
        change_triggers_reboot=False)

  def test_off(self):
    """Verifies device_power.off calls switch_power."""
    self.uut.off()
    self.mock_call_sequence_tracker.assert_has_calls([
        mock.call.close_all_transports(),
        mock.call.power_off(self.port_num),
    ])

  def test_power_on(self):
    """Verifies device_power.on calls switch_power."""
    self.uut.on()
    self.mock_call_sequence_tracker.assert_has_calls([
        mock.call.power_on(self.port_num),
        mock.call.wait_until_connected(),
        mock.call.open_all_transports(),
        mock.call.wait_for_bootup_complete(),
    ])

  @parameterized.named_parameters(
      ("not_initialized", None),
      ("not_health_checked", mock.MagicMock(
          spec=switchboard.SwitchboardDefault,
          health_checked=False,
          healthy=mock.PropertyMock(
              side_effect=AssertionError(
                  "'healthy' attribute should not have been accessed")))),
      ("not_healthy", mock.MagicMock(
          spec=switchboard.SwitchboardDefault,
          health_checked=True,
          healthy=False)),
  )
  def test_power_on_uninitialized_or_unhealthy_switchboard(
      self, mock_get_switchboard_return_value):
    """Verifies device_power.on doesn't call switchboard if it's unhealthy or uninitialized."""
    self.uut.health_check()
    self.get_switchboard_if_initialized.return_value = (
        mock_get_switchboard_return_value)
    self.uut._change_triggers_reboot = False
    self.uut.on(no_wait=True)
    self.mock_cambrionix.switch_power.power_on.assert_called_once_with(
        self.port_num)
    self.wait_until_connected.assert_not_called()
    self.mock_switchboard.open_all_transports.assert_not_called()
    self.wait_for_bootup_complete.assert_not_called()

  def test_power_off_noop(self):
    """Verifies device_power.off doesn't do anything if state is already off."""
    self.uut.health_check()
    self.mock_cambrionix.switch_power.get_mode.return_value = "off"
    self.uut.off()
    self.mock_cambrionix.switch_power.power_off.assert_not_called()

  def test_on_with_no_wait_true(self):
    """Verifies wait_for_boot_up_complete is skipped if no_wait is False."""
    self.uut.on(no_wait=True)
    self.mock_cambrionix.switch_power.power_on.assert_called_once_with(
        self.port_num)
    self.wait_until_connected.assert_not_called()
    self.wait_for_bootup_complete.assert_not_called()

  def test_power_cycle(self):
    """Verifies device_power.power_cycle calls off and on methods."""
    self.uut.cycle()
    self.mock_call_sequence_tracker.assert_has_calls([
        mock.call.close_all_transports(),
        mock.call.power_off(self.port_num),
        mock.call.power_on(self.port_num),
        mock.call.wait_until_connected(),
        mock.call.open_all_transports(),
        mock.call.wait_for_bootup_complete(),
    ])

  def test_off_change_triggers_reboot_true(self):
    """Verifies off calls switch_power and does not close transports."""
    self.uut._change_triggers_reboot = True
    self.uut.off()
    self.mock_cambrionix.switch_power.power_off.assert_called_once_with(
        self.port_num)
    self.mock_switchboard.close_all_transports.assert_not_called()
    self.wait_for_bootup_complete.assert_called_once()

  def test_power_on_change_trigger_reboot_true(self):
    """Verifies on calls switch_power and does not open transports."""
    self.uut._change_triggers_reboot = True
    self.uut.on()
    self.mock_cambrionix.switch_power.power_on.assert_called_once_with(
        self.port_num)
    self.mock_switchboard.open_all_transports.assert_not_called()
    self.wait_for_bootup_complete.assert_called_once()

  def test_missing_device_usb_hub_name_property(self):
    """Verifies capability raises a error if device_usb_hub_name is not set."""
    err_msg = (f"{self.name} properties device_usb_hub_name are unset. "
               "If device is connected to cambrionix, set them")
    self.props["optional"]["device_usb_hub_name"] = None

    self.uut = device_power_default.DevicePowerDefault(
        device_name=self.name,
        create_device_func=self.mock_manager.create_device,
        default_hub_type="cambrionix",
        props=self.props,
        usb_ports_discovered=False,
        wait_until_connected_fn=self.wait_until_connected,
        wait_for_bootup_complete_fn=self.wait_for_bootup_complete,
        get_switchboard_if_initialized=self.get_switchboard_if_initialized,
        change_triggers_reboot=False)
    with self.assertRaisesRegex(errors.DeviceError, err_msg):
      self.uut.health_check()

  def test_missing_manager(self):
    """Verifies capability raises a error if manager is not set."""
    err_msg = f"{self.name} failed to create cambrionix."
    self.mock_manager.create_device.side_effect = errors.DeviceError(
        "failed to create cambrionix")
    self.uut = device_power_default.DevicePowerDefault(
        device_name=self.name,
        create_device_func=self.mock_manager.create_device,
        default_hub_type="cambrionix",
        props=self.props,
        usb_ports_discovered=False,
        wait_until_connected_fn=self.wait_until_connected,
        wait_for_bootup_complete_fn=self.wait_for_bootup_complete,
        get_switchboard_if_initialized=self.get_switchboard_if_initialized,
        change_triggers_reboot=False)
    with self.assertRaisesRegex(errors.DeviceError, err_msg):
      self.uut.health_check()

  def test_close_doesnt_close_hub_instance_if_not_initialized(self):
    """Tests that close() doesn't close the hub instance if it's initialized."""
    self.uut.close()
    self.mock_cambrionix.close.assert_not_called()

  def test_close_closes_hub_instance_if_initialized(self):
    """Tests that close() closes the hub device instance if it's initialized."""
    self.uut.health_check()
    self.mock_cambrionix.close.assert_not_called()
    self.uut.close()
    self.mock_cambrionix.close.assert_called_once()

  def test_exception_raised_for_invalid_hub_type(self):
    """Tests that a ValueError is raised for an invalid hub_type."""
    self.props["optional"]["device_power_hub_type"] = "foo"
    with self.assertRaisesRegex(ValueError, "Hub type foo is not supported"):
      self.uut = device_power_default.DevicePowerDefault(
          device_name=self.name,
          create_device_func=self.mock_manager.create_device,
          default_hub_type="cambrionix",
          props=self.props,
          usb_ports_discovered=True,
          wait_until_connected_fn=self.wait_until_connected,
          wait_for_bootup_complete_fn=self.wait_for_bootup_complete,
          get_switchboard_if_initialized=self.get_switchboard_if_initialized)

  def test_usb_ports_detected_true_raises_with_redetect_message(self):
    """Tests that the error message indicates to use gdm redetect."""
    self.uut = device_power_default.DevicePowerDefault(
        device_name=self.name,
        create_device_func=self.mock_manager.create_device,
        default_hub_type="cambrionix",
        props=self.props,
        usb_ports_discovered=True,
        wait_until_connected_fn=self.wait_until_connected,
        wait_for_bootup_complete_fn=self.wait_for_bootup_complete,
        get_switchboard_if_initialized=self.get_switchboard_if_initialized,
        usb_hub_name_prop="different_usb_hub_name",
        usb_port_prop="different_usb_port")
    error_msg = f"set them via 'gdm redetect {self.name}'"
    with self.assertRaisesRegex(errors.DeviceError, error_msg):
      self.uut.health_check()


if __name__ == "__main__":
  unit_test_case.main()
