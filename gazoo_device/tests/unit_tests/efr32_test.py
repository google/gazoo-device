# Copyright 2021 Google LLC
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
from unittest import mock

from gazoo_device import errors
from gazoo_device.auxiliary_devices import efr32
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
import immutabledict


_EFR32_PERSISTENT_PROPERTIES = immutabledict.immutabledict({
    "os": "FreeRTOS",
    "platform": "EFR32MG",
    "serial_number": "123456",
})


class EFR32DeviceTests(fake_device_test_case.FakeDeviceTestCase):
  """Unit tests for base class EFR32."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements("efr32-1234")
    self.device_config["persistent"]["console_port_name"] = (
        r"/dev/bus/usb/001/002")
    jlink_patcher = mock.patch("pylink.JLink")
    jlink_patcher.start()
    self.addCleanup(jlink_patcher.stop)
    self.uut = efr32.EFR32(
                self.mock_manager,
                self.device_config,
                log_directory=self.artifacts_directory)

  def test_001_create_efr32_device(self):
    """Verify create_device works as expected."""
    self.assertIsNotNone(self.uut)

  def test_002_efr32_attributes(self):
    """Verify efr32 attributes."""
    self.assertEqual(self.uut.os, _EFR32_PERSISTENT_PROPERTIES["os"])
    self.assertEqual(self.uut.platform,
                     _EFR32_PERSISTENT_PROPERTIES["platform"])
    self.assertEqual(self.uut.serial_number,
                     _EFR32_PERSISTENT_PROPERTIES["serial_number"])

  def test_003_get_detection_info(self):
    """Verify get_detection_info."""
    persistent_dict, _ = self.uut.get_detection_info()
    self.assertEqual(persistent_dict["name"], "efr32-1234")
    self.assertEqual(persistent_dict["device_type"], "efr32")

  def test_004_recover(self):
    """Verify recover method."""
    with self.assertRaises(errors.DeviceError):
      self.uut.recover(None)

  def test_005_switchboard(self):
    """Verify the deactive switchboard in efr32."""
    with self.assertRaises(errors.DeviceError):
      self.uut.switchboard.send()

  def test_006_jlink_flash_capability(self):
    """Verify the initialization of flash_build capability."""
    self.assertTrue(self.uut.flash_build)


if __name__ == "__main__":
  fake_device_test_case.main()
