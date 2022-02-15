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

"""Unit tests for nrf52840 module."""
from unittest import mock

from gazoo_device.auxiliary_devices import nrf52840
from gazoo_device.base_classes import nrf_connect_sdk_device
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
import immutabledict

_FAKE_DEVICE_ID = "nrf52840-detect"
_FAKE_DEVICE_ADDRESS = "/dev/bus/usb/001/002"
_NRF_CONNECT_PERSISTENT_PROPERTIES = immutabledict.immutabledict({
    "os": "Zephyr RTOS",
    "platform": "nRF Connect",
    "serial_number": "FT2BSR6O",
    "name": "nrf52840_detect",
    "device_type": "nrf52840",
})


class NRF52840DeviceTests(fake_device_test_case.FakeDeviceTestCase):
  """Test for base class NRF52840."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements(_FAKE_DEVICE_ID)
    self.device_config["persistent"]["console_port_name"] = _FAKE_DEVICE_ADDRESS
    jlink_patcher = mock.patch("pylink.JLink")
    jlink_patcher.start()
    self.addCleanup(jlink_patcher.stop)
    self.uut = nrf52840.NRF52840(
                self.mock_manager,
                self.device_config,
                log_directory=self.artifacts_directory)

  def test_get_console_configuration(self):
    """Verifies nrf52840 get_console_configuration."""
    self.assertIsNotNone(self.uut.get_console_configuration())

  def test_nrf52840_attributes(self):
    """Verifies nrf52840 attributes."""
    self._test_get_detection_info(_FAKE_DEVICE_ADDRESS,
                                  nrf52840.NRF52840,
                                  _NRF_CONNECT_PERSISTENT_PROPERTIES)

  def test_jlink_flash_capability(self):
    """Verifies the initialization of j_link_flash capability."""
    self.assertTrue(self.uut.flash_build)

  @mock.patch.object(nrf_connect_sdk_device.os.path, "exists")
  def test_is_connected_true(self, mock_exists):
    """Verifies is_connected works as expected."""
    mock_exists.return_value = True
    self.assertTrue(nrf52840.NRF52840.is_connected(self.device_config))


if __name__ == "__main__":
  fake_device_test_case.main()
