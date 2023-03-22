# Copyright 2023 Google LLC
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

"""Capability unit test for nrfjprog flashing capability."""
import os
import tempfile
import typing
from unittest import mock

from gazoo_device import errors
from gazoo_device.base_classes import matter_device_base
from gazoo_device.capabilities import device_power_default
from gazoo_device.capabilities import flash_build_nrfjprog
from gazoo_device.capabilities import matter_endpoints_accessor_pw_rpc
from gazoo_device.switchboard import switchboard
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.utility import host_utils
from gazoo_device.utility import subprocess_utils

_MOCK_DEVICE_NAME = "MOCK_DEVICE"
_MOCK_SERIAL_NUMBER = "123456789"
_MOCK_IMAGE_PATH = "MOCK/IMAGE/PATH/HEX.hex"


class FlashBuildNrfjprogTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for FlashBuildNrfjprog."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements("nrfmatter-1234")
    mock_matter_endpoints_reset = mock.Mock(
        spec=matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc.reset
    )
    mock_switchboard = mock.Mock(spec=switchboard.SwitchboardDefault)
    mock_wait_for_bootup_complete = mock.Mock(
        spec=matter_device_base.MatterDeviceBase.wait_for_bootup_complete)
    self.mock_power_cycle = mock.Mock(
        spec=device_power_default.DevicePowerDefault.cycle)
    self.uut = flash_build_nrfjprog.FlashBuildNrfjprog(
        device_name=_MOCK_DEVICE_NAME,
        serial_number=_MOCK_SERIAL_NUMBER,
        power_cycle_fn=self.mock_power_cycle,
        reset_endpoints_fn=mock_matter_endpoints_reset,
        switchboard=mock_switchboard,
        wait_for_bootup_complete_fn=mock_wait_for_bootup_complete)

  @mock.patch.object(
      host_utils, "has_command", return_value=False, autospec=True)
  def test_health_check_on_failure(self, mock_has_command):
    """Verifies health check on failure."""
    with self.assertRaisesRegex(
        errors.DependencyUnavailableError, "nrfjprog is not installed"):
      self.uut.health_check()

  @mock.patch.object(
      flash_build_nrfjprog.FlashBuildNrfjprog, "_disable_msd", autospec=True)
  @mock.patch.object(
      host_utils, "has_command", return_value=True, autospec=True)
  def test_health_check_on_success(self, mock_has_command, mock_disable_msd):
    """Verifies health check on success."""
    self.uut.health_check()
    mock_disable_msd.assert_called_once()

  @mock.patch.object(
      flash_build_nrfjprog.FlashBuildNrfjprog,
      "_nrfjprog_flash",
      return_value=(1, ""),
      autospec=True)
  @mock.patch.object(flash_build_nrfjprog.FlashBuildNrfjprog, "recover_device")
  @mock.patch.object(os.path, "exists", return_value=True)
  @mock.patch.object(flash_build_nrfjprog.FlashBuildNrfjprog, "health_check")
  def test_flash_device_on_failure(
      self,
      mock_health_check,
      mock_exists,
      mock_recover_device,
      mock_nrfjprog_flash):
    """Verifies flash_device on failure."""
    with self.assertRaisesRegex(
        errors.DeviceError, "flash command with binary flasher failed"):
      self.uut.flash_device([_MOCK_IMAGE_PATH])

  @mock.patch.object(
      subprocess_utils,
      "run_and_stream_output",
      return_value=(0, ""),
      autospec=True)
  def test_nrfjprog_flash(self, mock_run_and_stream_output):
    """Verifies _nrfjprog_flash on success."""
    self.uut._nrfjprog_flash(_MOCK_IMAGE_PATH)
    mock_run_and_stream_output.assert_called_once()

  @mock.patch.object(
      subprocess_utils,
      "run_and_stream_output",
      return_value=(1, ""),
      autospec=True)
  @mock.patch.object(flash_build_nrfjprog.FlashBuildNrfjprog, "health_check")
  def test_recover_device_on_failure(
      self, mock_health_check, mock_run_and_stream_output):
    """Verifies recover_device on failure."""
    with self.assertRaisesRegex(errors.DeviceError, "Failed to recover"):
      self.uut.recover_device()

  @mock.patch.object(
      flash_build_nrfjprog.FlashBuildNrfjprog, "flash_device", autospec=True)
  def test_upgrade(self, mock_flash_device):
    """Tests upgrade method success."""
    self.uut.upgrade(build_file=_MOCK_IMAGE_PATH)
    mock_flash_device.assert_called_once()

  @mock.patch.object(
      host_utils, "has_command", return_value=False, autospec=True)
  def test_disable_msd_jlink_binary_not_exists_failure(
      self, mock_has_command):
    """Verifies _disable_msd on failure when binary not exists."""
    with self.assertRaisesRegex(
        errors.DependencyUnavailableError, "JLinkExe is not installed"):
      self.uut._disable_msd()

  @mock.patch.object(
      subprocess_utils,
      "run_and_stream_output",
      return_value=(1, ""),
      autospec=True)
  @mock.patch.object(flash_build_nrfjprog, "open")
  @mock.patch.object(tempfile, "TemporaryDirectory")
  @mock.patch.object(
      host_utils, "has_command", return_value=True, autospec=True)
  def test_disable_msd_subprocess_call_failure(
      self,
      mock_has_command,
      mock_temp_directory,
      mock_open,
      mock_run_and_stream_output):
    """Verifies _disable_msd on failure when subprocess call fails."""
    mock_temp_directory.return_value.__enter__.return_value = "/host/dir"
    mock_open.return_value.__enter__.return_value = mock.Mock(
        spec=typing.TextIO)
    with self.assertRaisesRegex(
        errors.DeviceError, "failed to disable the MSD setting"):
      self.uut._disable_msd()

  @mock.patch.object(
      subprocess_utils,
      "run_and_stream_output",
      return_value=(0, ""),
      autospec=True)
  @mock.patch.object(flash_build_nrfjprog, "open")
  @mock.patch.object(tempfile, "TemporaryDirectory")
  @mock.patch.object(
      host_utils, "has_command", return_value=True, autospec=True)
  def test_disable_msd_power_cycle_failure(
      self,
      mock_has_command,
      mock_temp_directory,
      mock_open,
      mock_run_and_stream_output):
    """Verifies _disable_msd on success."""
    self.mock_power_cycle.side_effect = errors.CapabilityNotReadyError(
        _MOCK_DEVICE_NAME, "device power cycle error")
    with self.assertRaisesRegex(errors.DeviceError, "cannot be powered cycle"):
      self.uut._disable_msd()

  @mock.patch.object(
      subprocess_utils,
      "run_and_stream_output",
      return_value=(0, ""),
      autospec=True)
  @mock.patch.object(flash_build_nrfjprog, "open")
  @mock.patch.object(tempfile, "TemporaryDirectory")
  @mock.patch.object(
      host_utils, "has_command", return_value=True, autospec=True)
  def test_disable_msd_on_success(
      self,
      mock_has_command,
      mock_temp_directory,
      mock_open,
      mock_run_and_stream_output):
    """Verifies _disable_msd on success."""
    self.uut._disable_msd()
    self.mock_power_cycle.assert_called_once()


if __name__ == "__main__":
  fake_device_test_case.main()
