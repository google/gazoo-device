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
"""Capability unit test for Esptool flashing default capability."""
import os
import unittest
from unittest import mock

from gazoo_device import errors
from gazoo_device.capabilities import flash_build_esptool
from gazoo_device.capabilities import matter_endpoints_accessor_pw_rpc
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_MOCK_DEVICE_NAME = 'MOCK_DEVICE'
_MOCK_PORT = '/dev/ttymockport'
_MOCK_CHIP_NAME = 'esp32'
_MOCK_INVALID_CHIP_NAME = 'invalid_chip'
_MOCK_IMAGE_PATH = 'MOCK/IMAGE/PATH/APP.bin'
_MOCK_INVALID_IMAGE = 'MOCK/IMAGE/PATH/APP.hex'
_MOCK_OFFSET = '0x12000'
_MOCK_BAUDRATE = '115700'
_MOCK_BEFORE_FLASH = 'default_reset'
_MOCK_AFTER_FLASH = 'hard_reset'
_MOCK_FLASH_MODE = 'keep'
_MOCK_FLASH_FREQ = 'keep'
_MOCK_FLASH_SIZE = 'detect'
_MOCK_FLASH_FILE_OFFSET = '0x15000'

_MOCK_WRITE_COMMAND_ARGS = [
    '--port', _MOCK_PORT, '--baud', _MOCK_BAUDRATE, '--chip', _MOCK_CHIP_NAME
]
_MOCK_WRITE_COMMAND_ARGS_WITH_FLASH_FILE = [
    '--port', _MOCK_PORT, '--baud', '460800', '--chip', _MOCK_CHIP_NAME,
    '--before', 'default_reset', '--after', 'hard_reset', 'write_flash',
    '--flash_freq', '30m', '--flash_mode', 'dio', '--flash_size', '8MB',
    '--compress'
]


@unittest.skipUnless(flash_build_esptool._ESPTOOL_AVAILABLE,
                     'requires esptool installed')
class FlashBuildEsptoolTests(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for FlashBuildEsptool capability initialization."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements('esp32-1234')
    self.mock_esptool = self.enter_context(
        mock.patch.object(flash_build_esptool.esptool, 'main', autospec=True))

  def test_flash_build_esptool_raise_dependency_unavailable_error(self):
    """Test DependencyUnavailableError is raised if esptool is not installed."""
    with mock.patch.object(flash_build_esptool, '_ESPTOOL_AVAILABLE', False):
      with self.assertRaises(errors.DependencyUnavailableError):
        flash_build_esptool.FlashBuildEsptool(
            device_name=_MOCK_DEVICE_NAME,
            chip_type=_MOCK_CHIP_NAME,
            serial_port=_MOCK_PORT,
            switchboard=self.mock_switchboard)

  def test_flash_build_esptool_raise_value_error(self):
    """Test ValueError is raised if unsupported chip type is used."""
    with mock.patch.object(flash_build_esptool, '_ESPTOOL_AVAILABLE', True):
      with self.assertRaises(ValueError):
        flash_build_esptool.FlashBuildEsptool(
            device_name=_MOCK_DEVICE_NAME,
            chip_type=_MOCK_INVALID_CHIP_NAME,
            serial_port=_MOCK_PORT,
            switchboard=self.mock_switchboard)


@unittest.skipUnless(flash_build_esptool._ESPTOOL_AVAILABLE,
                     'requires esptool installed')
class FlashBuildEsptoolCapabilityTests(fake_device_test_case.FakeDeviceTestCase
                                      ):
  """Unit test for FlashBuildEsptool capability methods."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements('esp32-1234')
    self.mock_flash_settings_file = self.get_resource(
        os.path.join('testdata', 'esp32_flash_settings.flash'))
    self.mock_esptool = self.enter_context(
        mock.patch.object(flash_build_esptool.esptool, 'main', autospec=True))
    self.uut = flash_build_esptool.FlashBuildEsptool(
        device_name=_MOCK_DEVICE_NAME,
        chip_type=_MOCK_CHIP_NAME,
        serial_port=_MOCK_PORT,
        switchboard=self.mock_switchboard,
        baud=_MOCK_BAUDRATE,
        reset_endpoints_fn=mock.Mock(spec=matter_endpoints_accessor_pw_rpc
                                     .MatterEndpointsAccessorPwRpc.reset))

  @mock.patch.object(
      flash_build_esptool.FlashBuildEsptool, '_verify_file', autospec=True)
  @mock.patch.object(
      flash_build_esptool.FlashBuildEsptool,
      '_get_write_command_arguments',
      autospec=True)
  def test_upgrade_success(self, mock_write_command_args, mock_verify_file):
    """Test FlashBuildEsptool.flash_device."""
    mock_write_command_args.return_value = _MOCK_WRITE_COMMAND_ARGS.copy()
    self.uut.upgrade(
        build_file=_MOCK_IMAGE_PATH, application_offset=_MOCK_OFFSET)
    mock_write_command_args.assert_called_once()
    mock_verify_file.assert_called_once()
    self.mock_esptool.assert_called_once_with(
        _MOCK_WRITE_COMMAND_ARGS + [_MOCK_OFFSET, _MOCK_IMAGE_PATH])
    self.mock_switchboard.close_all_transports.assert_called_once()
    self.mock_switchboard.open_all_transports.assert_called_once()

  @mock.patch.object(
      flash_build_esptool.FlashBuildEsptool, '_verify_file', autospec=True)
  def test_update_flashing_arguments_via_flash_settings_file(
      self, mock_verify_file):
    """Test upgrade method with *.flash.py file."""
    del mock_verify_file
    self.uut.upgrade(
        build_file=_MOCK_IMAGE_PATH,
        flash_settings_file=self.mock_flash_settings_file)
    self.mock_esptool.assert_called_once_with(
        _MOCK_WRITE_COMMAND_ARGS_WITH_FLASH_FILE +
        [_MOCK_FLASH_FILE_OFFSET, _MOCK_IMAGE_PATH])

  @mock.patch.object(
      flash_build_esptool.FlashBuildEsptool, '_verify_file', autospec=True)
  def test_override_flashing_arguments_from_flash_settings_file(
      self, mock_verify_file):
    """Test upgrade method override settings from with *.flash.py file."""
    del mock_verify_file
    self.uut.upgrade(
        build_file=_MOCK_IMAGE_PATH,
        flash_settings_file=self.mock_flash_settings_file,
        application_offset=_MOCK_OFFSET)
    self.mock_esptool.assert_called_once_with(
        _MOCK_WRITE_COMMAND_ARGS_WITH_FLASH_FILE +
        [_MOCK_OFFSET, _MOCK_IMAGE_PATH])

  def test_flash_device_raise_error(self):
    """Test invalid length for list of files failure."""
    with self.assertRaises(errors.DeviceError):
      self.uut.flash_device(list_of_files=[_MOCK_IMAGE_PATH] * 4)
    with self.assertRaises(errors.DeviceError):
      self.uut.flash_device(list_of_files=[])

  def test_get_write_command_arguments(self):
    """Test get write command method."""
    expected_command_args = [
        '--port', _MOCK_PORT, '--baud', _MOCK_BAUDRATE, '--chip',
        _MOCK_CHIP_NAME, '--before', _MOCK_BEFORE_FLASH, '--after',
        _MOCK_AFTER_FLASH, 'write_flash', '--flash_freq', _MOCK_FLASH_FREQ,
        '--flash_mode', _MOCK_FLASH_MODE, '--flash_size', _MOCK_FLASH_SIZE,
        '--compress', '--erase-all'
    ]
    command_args = self.uut._get_write_command_arguments(erase=True)
    self.assertEqual(command_args, expected_command_args)

  @mock.patch.object(os.path, 'exists', autospec=True, return_value=True)
  def test_verify_file_success(self, mock_fn):
    """Test verify file helper method."""
    self.uut._verify_file(image_path=_MOCK_IMAGE_PATH)

  def test_verify_file_raise_error(self):
    """Test verify file method invalid image failure."""
    with self.assertRaises(errors.DeviceError):
      self.uut._verify_file(image_path=_MOCK_INVALID_IMAGE)
    with self.assertRaises(errors.DeviceError):
      self.uut._verify_file(image_path=_MOCK_IMAGE_PATH)


if __name__ == '__main__':
  fake_device_test_case.main()
