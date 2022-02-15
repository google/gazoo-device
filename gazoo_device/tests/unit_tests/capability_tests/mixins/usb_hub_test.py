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

"""Mixin for test_usb_hub."""
from unittest import mock

from gazoo_device.auxiliary_devices import cambrionix
from gazoo_device.capabilities import switch_power_usb_with_charge
from gazoo_device.capabilities import usb_hub_default


class UsbHubTestMixin:
  """Mixin for common device unit tests of usb_hub capability.

  Assume self.uut, self.uut.device_usb_hub_name, and self.uut.device_usb_port
  are set.
  """

  def test_001_usb_hub_name(self):
    """Verify the usb_hub capability successfully returns the usb hub name."""
    self.assertEqual(self.uut.device_usb_hub_name, self.uut.usb_hub.name)

  def test_002_usb_hub_device_port(self):
    """Verify the usb_hub capability successfully returns the usb port number."""
    self.assertEqual(self.uut.device_usb_port, self.uut.usb_hub.device_port)

  @mock.patch.object(
      usb_hub_default.UsbHubDefault,
      "supported_modes",
      new_callable=mock.PropertyMock,
      return_value=["off", "sync", "charge"])
  def test_003_usb_hub_set_port_power(self, unused_mock_supported_modes):
    """Verify that set_port_power sets the usb hub to charge."""
    # Assuming the usb_hub is a Cambrionix object.
    mock_usb_power_with_charge = mock.MagicMock(
        switch_power_usb_with_charge.SwitchPowerUsbWithCharge)
    with mock.patch.object(
        cambrionix.Cambrionix,
        "switch_power",
        new_callable=mock.PropertyMock,
        side_effect=mock_usb_power_with_charge.set_mode(
            "charge", self.uut.usb_hub.device_port)):
      self.uut.usb_hub.set_device_power("charge")
      mock_usb_power_with_charge.set_mode.assert_called_once_with(
          "charge", self.uut.usb_hub.device_port)
