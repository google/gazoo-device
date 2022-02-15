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

"""Unit tests for efr32 module."""
import os
from unittest import mock

from gazoo_device.auxiliary_devices import efr32
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

import immutabledict

_FAKE_DEVICE_ID = "efr32-detect"
_FAKE_DEVICE_ADDRESS = "/dev/bus/usb/001/002"
_EFR32_PERSISTENT_PROPERTIES = immutabledict.immutabledict({
    "os": "FreeRTOS",
    "platform": "EFR32MG",
    "serial_number": "FT2BSR6O",
    "name": "efr32_detect",
    "device_type": "efr32",
})


class EFR32DeviceTests(fake_device_test_case.FakeDeviceTestCase):
  """Unit tests for base class EFR32."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements(_FAKE_DEVICE_ID)
    self.device_config["persistent"]["console_port_name"] = _FAKE_DEVICE_ADDRESS
    jlink_patcher = mock.patch("pylink.JLink")
    jlink_patcher.start()
    self.addCleanup(jlink_patcher.stop)
    self.uut = efr32.EFR32(
                self.mock_manager,
                self.device_config,
                log_directory=self.artifacts_directory)

  def test_get_console_configuration(self):
    """Verifies efr32 get_console_configuration."""
    self.assertIsNotNone(self.uut.get_console_configuration())

  def test_efr32_attributes(self):
    """Verifies efr32 attributes."""
    self._test_get_detection_info(_FAKE_DEVICE_ADDRESS,
                                  efr32.EFR32,
                                  _EFR32_PERSISTENT_PROPERTIES)

  def test_jlink_flash_capability(self):
    """Verifies the initialization of flash_build capability."""
    self.assertTrue(self.uut.flash_build)

  @mock.patch.object(os.path, "exists", return_value=True)
  def test_is_connected_true(self, mock_exists):
    """Verifies is_connected works as expected."""
    self.assertTrue(efr32.EFR32.is_connected(self.device_config))


if __name__ == "__main__":
  fake_device_test_case.main()
