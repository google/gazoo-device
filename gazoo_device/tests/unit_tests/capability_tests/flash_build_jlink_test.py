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
from gazoo_device import errors
from gazoo_device.base_classes import matter_device_base
from gazoo_device.capabilities import flash_build_jlink
from gazoo_device.capabilities import matter_endpoints_accessor_pw_rpc
from gazoo_device.switchboard import switchboard
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.utility import subprocess_utils
import intelhex
import pylink

_MOCK_DEVICE_NAME = "MOCK_DEVICE"
_MOCK_SERIAL_NUMBER = "123456789"
_MOCK_CHIP_NAME = "NRF52840_XXAA"
_MOCK_IMAGE_PATH = "MOCK/IMAGE/PATH/HEX.hex"
_MOCK_SEGMENT_START = 0
_MOCK_SEGMENT_END = 10


class JLinkFlashDefaultTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for JLinkFlashDefault."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements("efr32matter-1234")
    jlink_patcher = mock.patch("pylink.JLink")
    mock_jlink_class = jlink_patcher.start()
    self.addCleanup(jlink_patcher.stop)
    self.mock_jlink = mock_jlink_class.return_value
    mock_matter_endpoints_reset = mock.Mock(
        spec=matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc.reset
    )
    mock_switchboard = mock.Mock(spec=switchboard.SwitchboardDefault)
    mock_wait_for_bootup_complete = mock.Mock(
        spec=matter_device_base.MatterDeviceBase.wait_for_bootup_complete)
    self.uut = flash_build_jlink.FlashBuildJLink(
        device_name=_MOCK_DEVICE_NAME,
        serial_number=_MOCK_SERIAL_NUMBER,
        platform_name=_MOCK_CHIP_NAME,
        reset_endpoints_fn=mock_matter_endpoints_reset,
        switchboard=mock_switchboard,
        wait_for_bootup_complete_fn=mock_wait_for_bootup_complete)
    self.mock_flash_method = mock.Mock(
        spec=flash_build_jlink.FlashBuildJLink._flash_device)
    self.uut._flash_method_map = {
        True: self.mock_flash_method, False: self.mock_flash_method}

  @mock.patch.object(os.path, "exists", return_value=True)
  def test_flash_device_success(
      self,
      mock_exists):
    """Verifies flash_device on success."""
    self.uut.flash_device(["xxx.hex"])
    self.mock_flash_method.assert_called_once()

  def test_flash_device_failure_incorrect_number_of_image(self):
    """Verifies flash_device on failure for incorrect number of images."""
    with self.assertRaisesRegex(errors.DeviceError, "Only one hex file"):
      self.uut.flash_device(["one.hex", "two.hex"])

  def test_flash_device_failure_incorrect_image_format(self):
    """Verifies flash_device on failure for incorrect image format."""
    with self.assertRaisesRegex(errors.DeviceError, "Only hex type"):
      self.uut.flash_device(["image.jpg"])

  def test_flash_device_failure_image_not_exists(self):
    """Verifies flash_device on failure for inexistent image."""
    with self.assertRaisesRegex(errors.DeviceError, "does not exist"):
      self.uut.flash_device([_MOCK_IMAGE_PATH])

  def test_flash_device_no_jlink_dll_raises_error(self):
    """Tests that an actionable error is raised if the J-Link DLL is missing."""
    with mock.patch.object(
        pylink, "JLink",
        side_effect=TypeError("Expected to be given a valid DLL.")):
      with self.assertRaisesRegex(
          errors.DependencyUnavailableError,
          "No J-Link DLL found. Install the J-Link SDK"):
        self.uut._flash_device(_MOCK_IMAGE_PATH, True)

  @mock.patch.object(flash_build_jlink.FlashBuildJLink, "_post_flashing")
  @mock.patch.object(flash_build_jlink.FlashBuildJLink, "_flash_image")
  @mock.patch.object(flash_build_jlink.FlashBuildJLink, "_pre_flashing")
  def test_flash_device_on_success(
      self,
      mock_pre_flashing,
      mock_flash_image,
      mock_post_flashing):
    """Verifies _flash_device on success."""
    self.uut._flash_device(image_path=_MOCK_IMAGE_PATH, verify_flash=True)
    mock_pre_flashing.assert_called_once()
    mock_flash_image.assert_called_once()
    mock_post_flashing.assert_called_once()

  @mock.patch.object(flash_build_jlink.FlashBuildJLink, "flash_device")
  def test_upgrade(self, mock_flash_device):
    """Tests upgrade method success."""
    self.uut.upgrade(build_file=_MOCK_IMAGE_PATH)
    mock_flash_device.assert_called_once()

  def test_pre_flashing(self):
    """Tests _pre_flashing on success."""
    self.uut._pre_flashing(self.mock_jlink)

    self.mock_jlink.open.assert_called_once()
    self.mock_jlink.set_tif.assert_called_once()
    self.mock_jlink.connect.assert_called_once()
    self.mock_jlink.halt.assert_called_once()

  def test_post_flashing(self):
    """Tests _post_flashing on success."""
    self.uut._post_flashing(self.mock_jlink)

    self.mock_jlink.reset.assert_called_once()
    self.mock_jlink.restart.assert_called_once()
    self.mock_jlink.close.assert_called_once()

  @mock.patch.object(intelhex, "IntelHex")
  def test_flash_image(self, mock_intelhex):
    """Tests _flash_image on success."""
    mock_intelhex.return_value.segments.return_value = [
        (_MOCK_SEGMENT_START, _MOCK_SEGMENT_END)]
    self.uut._flash_image(self.mock_jlink, _MOCK_IMAGE_PATH)
    self.mock_jlink.flash_file.assert_called_once()


if __name__ == "__main__":
  fake_device_test_case.main()
