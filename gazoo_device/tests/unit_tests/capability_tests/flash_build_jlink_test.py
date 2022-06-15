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
from gazoo_device.capabilities import matter_endpoints_accessor_pw_rpc
from gazoo_device.switchboard import switchboard
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.utility import retry
from gazoo_device.utility import subprocess_utils
import intelhex
import pylink

_MOCK_DEVICE_NAME = "MOCK_DEVICE"
_MOCK_SERIAL_NUMBER = 123456789
_MOCK_CHIP_NAME = "TARGET_CHIP_NAME"
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
    self.mock_matter_endpoints_reset = mock.Mock(
        spec=matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc.reset
    )
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

  @mock.patch.object(flash_build_jlink.FlashBuildJLink, "_jlink_flash")
  @mock.patch.object(
      flash_build_jlink.FlashBuildJLink, "_poll_until_device_is_ready")
  @mock.patch.object(os.path, "exists", return_value=True)
  def test_upgrade(
      self, mock_exists, mock_poll_until_device_is_ready, mock_jlink_flash):
    """Tests upgrade() success."""
    self.uut.upgrade(build_file=_MOCK_IMAGE_PATH)

    mock_exists.assert_any_call(_MOCK_IMAGE_PATH)
    mock_jlink_flash.assert_called_once()
    self.mock_matter_endpoints_reset.assert_called_once()
    mock_poll_until_device_is_ready.assert_called_once()

  @mock.patch.object(flash_build_jlink.FlashBuildJLink, "_post_flashing")
  @mock.patch.object(
      flash_build_jlink.FlashBuildJLink,
      "_flash_image", side_effect=(
          pylink.errors.JLinkFlashException(
              code=pylink.enums.JLinkGlobalErrors.FLASH_PROG_PROGRAM_FAILED),
          None))
  @mock.patch.object(flash_build_jlink.FlashBuildJLink, "_pre_flashing")
  def test_jlink_flash_2_attemps(
      self, mock_pre_flash, mock_flash_image, mock_post_flash):
    """Tests _jlink_flash flashing for 2 attemps on success."""
    self.uut._jlink_flash(_MOCK_IMAGE_PATH)

    self.assertEqual(2, mock_pre_flash.call_count)
    self.assertEqual(2, mock_flash_image.call_count)
    self.assertEqual(2, mock_post_flash.call_count)

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

  def test_get_firmware_version(self):
    """Tests that get_firmware_version() returns UNKNOWN."""
    self.assertEqual(self.uut.get_firmware_version(), flash_build_jlink.UNKNOWN)

  def test_get_firmware_type(self):
    """Tests that get_firmware_type() returns UNKNOWN."""
    self.assertEqual(self.uut.get_firmware_type(), flash_build_jlink.UNKNOWN)

  @mock.patch.object(retry, "retry")
  def test_poll_until_device_is_ready_on_success(self, mock_retry):
    """Verifies _poll_until_device_is_ready method on success."""
    mock_switchboard = mock.Mock(spec=switchboard.SwitchboardDefault)
    mock_switchboard.call.return_value = True, None
    self.uut._switchboard = mock_switchboard

    self.uut._poll_until_device_is_ready()

    mock_retry.assert_called_once()

  @mock.patch.object(retry, "retry")
  def test_poll_until_device_is_ready_bypass(self, mock_retry):
    """Verifies _poll_until_device_is_ready bypasses for non-Matter device."""
    self.uut._switchboard = None

    self.uut._poll_until_device_is_ready()

    mock_retry.assert_not_called()


if __name__ == "__main__":
  fake_device_test_case.main()
