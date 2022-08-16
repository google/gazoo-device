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

"""Unit tests for the comm_power_default capability."""
from unittest import mock

from gazoo_device import errors
from gazoo_device import manager
from gazoo_device.auxiliary_devices import cambrionix
from gazoo_device.capabilities import comm_power_default
from gazoo_device.capabilities import switch_power_usb_with_charge
from gazoo_device.switchboard import switchboard
from gazoo_device.tests.unit_tests.utils import unit_test_case

_COMMUNICATION_ADDRESS = "/dev/ttyusb0"


class CommPowerDefaultTests(unit_test_case.UnitTestCase):
  """Test class to verify the behavior of the comm_power_default capability."""

  def setUp(self):
    super().setUp()
    self.add_time_mocks()
    self.name = "test_device-1234"
    self.mock_manager = mock.MagicMock(spec=manager.Manager)
    self.mock_switchboard = mock.MagicMock(spec=switchboard.SwitchboardDefault)
    self.get_switchboard_if_initialized = mock.MagicMock(
        return_value=self.mock_switchboard)

    self.props = {
        "persistent_identifiers": {
            "name": self.name
        },
        "optional": {
            "device_usb_hub_name": "cambrionix-1234",
            "device_usb_port": 3
        }
    }
    self.mock_cambrionix = mock.MagicMock(
        communication_address=_COMMUNICATION_ADDRESS,
        spec=cambrionix.Cambrionix)
    self.mock_cambrionix.switch_power = mock.MagicMock(
        spec=switch_power_usb_with_charge.SwitchPowerUsbWithCharge)
    self.mock_manager.create_device.return_value = self.mock_cambrionix
    self.uut = comm_power_default.CommPowerDefault(
        device_name=self.name,
        create_device_func=self.mock_manager.create_device,
        hub_type="cambrionix",
        props=self.props,
        settable=True,
        hub_name_prop="device_usb_hub_name",
        port_prop="device_usb_port",
        get_switchboard_if_initialized=self.get_switchboard_if_initialized,
        power_and_data_share_cable=False)

  def test_missing_device_usb_hub_name_property(self):
    """Verifies capability raises a error if device_usb_hub_name is not set."""
    err_msg = (f"{self.name} properties device_usb_hub_name are unset.")
    self.props["optional"]["device_usb_hub_name"] = None
    with self.assertRaisesRegex(errors.CapabilityNotReadyError, err_msg):
      self.uut.health_check()

  def test_unable_to_ready_device(self):
    """Verifies capability raises a error if manager is not set."""
    err_msg = (f"{self.name} cambrionix not responding")
    self.mock_manager.create_device.side_effect = errors.DeviceError(
        "cambrionix not responding")
    with self.assertRaisesRegex(errors.CapabilityNotReadyError, err_msg):
      self.uut.health_check()

  def test_works_with_bad_switchboard(self):
    """Verifies capability works without a Switchboard."""
    self.uut = comm_power_default.CommPowerDefault(
        device_name=self.name,
        create_device_func=self.mock_manager.create_device,
        hub_type="cambrionix",
        props=self.props,
        settable=True,
        hub_name_prop="device_usb_hub_name",
        port_prop="device_usb_port",
        get_switchboard_if_initialized=lambda: None,
        power_and_data_share_cable=False)
    self.uut.cycle()

  def test_on_waits_for_connection(self):
    """Verifies capability waits for connection if method provided."""
    mock_wait_for_connection = mock.Mock()
    self.uut = comm_power_default.CommPowerDefault(
        device_name=self.name,
        create_device_func=self.mock_manager.create_device,
        hub_type="cambrionix",
        props=self.props,
        settable=True,
        hub_name_prop="device_usb_hub_name",
        port_prop="device_usb_port",
        get_switchboard_if_initialized=lambda: None,
        power_and_data_share_cable=False,
        wait_for_connection_func=mock_wait_for_connection)
    self.uut.on()
    mock_wait_for_connection.assert_called_once()

  def test_switchboard_initialized_after_comm_power(self):
    """Test Switchboard methods called if Switchboard is initialized later."""
    self.get_switchboard_if_initialized.return_value = None
    self.uut = comm_power_default.CommPowerDefault(
        device_name=self.name,
        create_device_func=self.mock_manager.create_device,
        hub_type="cambrionix",
        props=self.props,
        settable=True,
        hub_name_prop="device_usb_hub_name",
        port_prop="device_usb_port",
        get_switchboard_if_initialized=self.get_switchboard_if_initialized,
        power_and_data_share_cable=False)
    self.get_switchboard_if_initialized.return_value = self.mock_switchboard
    self.uut.cycle()
    self.mock_switchboard.close_all_transports.assert_called_once()
    self.mock_switchboard.open_all_transports.assert_called_once()

  def test_hub_not_created_by_create_device_func(self):
    """Tests error raised when failing to create self._hub."""
    self.mock_manager.create_device.return_value = "invalid hub instance"
    err_msg = "'switch_power' capability is missing in hub device"
    with self.assertRaisesRegex(errors.CapabilityNotReadyError, err_msg):
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

  def test_ethernet_ip_address(self):
    """Tests getting the ethernet address."""
    self.assertEqual(self.uut.address, _COMMUNICATION_ADDRESS)

  def test_ethernet_ip_address_unhealthy(self):
    """Tests getting the ethernet address when device is unhealth."""
    type(self.uut).healthy = mock.PropertyMock(return_value=False)
    self.assertEqual(self.uut.address, _COMMUNICATION_ADDRESS)


if __name__ == "__main__":
  unit_test_case.main()
