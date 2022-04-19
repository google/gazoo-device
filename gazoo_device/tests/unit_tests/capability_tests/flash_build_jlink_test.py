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

"""Capability unit test for JLink flashing default capability."""
import os
from unittest import mock
from gazoo_device import config
from gazoo_device import errors
from gazoo_device.capabilities import flash_build_jlink
from gazoo_device.capabilities import matter_endpoints_accessor
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.utility import subprocess_utils
import intelhex
import pylink

_MOCK_DEVICE_NAME = "MOCK_DEVICE"
_MOCK_SERIAL_NUMBER = 123456789
_MOCK_CHIP_NAME = "TARGET_CHIP_NAME"
_MOCK_IMAGE_PATH = "MOCK/IMAGE/PATH/HEX.hex"


class JLinkFlashDefaultTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for JLinkFlashDefault."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements("efr32matter-1234")
    jlink_patcher = mock.patch("pylink.JLink")
    mock_jlink_class = jlink_patcher.start()
    self.addCleanup(jlink_patcher.stop)
    self.mock_jlink = mock_jlink_class.return_value
    self.mock_matter_endpoints_reset = mock.Mock(
        spec=matter_endpoints_accessor.MatterEndpointsAccessor.reset)
    self.uut = flash_build_jlink.FlashBuildJLink(
        device_name=_MOCK_DEVICE_NAME,
        serial_number=_MOCK_SERIAL_NUMBER,
        platform_name=_MOCK_CHIP_NAME,
        reset_endpoints_fn=self.mock_matter_endpoints_reset)

  def test_no_jlink_dll_raises_error(self):
    """Tests that an actionable error is raised if the J-Link DLL is missing."""
    with mock.patch.object(
        pylink, "JLink",
        side_effect=TypeError("Expected to be given a valid DLL.")):
      with self.assertRaisesRegex(
          errors.DependencyUnavailableError,
          "No J-Link DLL found. Install the J-Link SDK"):
        self.uut._jlink_flash(_MOCK_IMAGE_PATH)

  @mock.patch.object(os.path, "exists", return_value=True)
  def test_flash(self, mock_exists):
    """Tests JLinkFlashDefault.flash."""
    mock_image = mock.Mock()
    mock_segments = [(0, 10), (10, 20)]
    mock_binarray = mock.Mock()
    with mock.patch.object(intelhex, "IntelHex", return_value=mock_image):
      mock_image.segments.return_value = mock_segments
      mock_image.tobinarray.return_value = mock_binarray
      self.uut.upgrade(build_file=_MOCK_IMAGE_PATH)

    mock_exists.assert_any_call(_MOCK_IMAGE_PATH)
    mock_image.tobinarray.assert_has_calls(
        [mock.call(start=0, size=10), mock.call(start=10, size=10)])
    self.mock_jlink.flash_write8.assert_has_calls(
        [mock.call(0, mock_binarray), mock.call(10, mock_binarray)])
    self.mock_jlink.open.assert_called_once()
    self.mock_jlink.set_tif.assert_called_once()
    self.mock_jlink.connect.assert_called_once()
    self.mock_jlink.halt.assert_called_once()
    self.mock_jlink.reset.assert_called_once()
    self.mock_jlink.restart.assert_called_once()
    self.mock_jlink.close.assert_called_once()
    self.mock_matter_endpoints_reset.assert_called_once()

  def test_image_invalid(self):
    """Tests image invalid failure."""
    with self.assertRaises(errors.DeviceError):
      self.uut.upgrade(build_file=_MOCK_IMAGE_PATH)
    with self.assertRaises(errors.DeviceError):
      self.uut.upgrade(build_file="invalid.txt")
    with self.assertRaises(errors.DeviceError):
      self.uut.flash_device(["h1.hex", "h2.hex"])

  def test_get_firmware_version(self):
    """Tests that get_firmware_version() returns UNKNOWN."""
    self.assertEqual(self.uut.get_firmware_version(), flash_build_jlink.UNKNOWN)

  def test_get_firmware_type(self):
    """Tests that get_firmware_type() returns UNKNOWN."""
    self.assertEqual(self.uut.get_firmware_type(), flash_build_jlink.UNKNOWN)


if __name__ == "__main__":
  fake_device_test_case.main()
