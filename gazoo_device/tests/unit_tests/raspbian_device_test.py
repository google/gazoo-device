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

"""This test script performs unit tests on functions and methods in the raspbian_device module."""
from unittest import mock

from gazoo_device import errors
from gazoo_device.auxiliary_devices import raspberry_pi
from gazoo_device.base_classes import raspbian_device
from gazoo_device.tests.unit_tests.capability_tests.mixins import file_transfer_test
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.tests.unit_tests.utils import raspbian_device_logs
from gazoo_device.utility import host_utils
import immutabledict


_PERSISTENT_PROPERTIES = immutabledict.immutabledict({
    "model": "3 Model B Rev 1.1",
    "serial_number": "000000001234abcd",
    "ip_address": "123.45.67.89",
    "communication_address": "123.45.67.89",
})
_DYNAMIC_PROPERTIES = immutabledict.immutabledict({
    "firmware_version": "10 (buster)",
    "kernel_version": "4.19.75-v7+",
})


class RaspbianDeviceTests(fake_device_test_case.FakeDeviceTestCase,
                          file_transfer_test.TestFileTransfer):
  """Tests for Raspbian Device base class."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements("raspberrypi-1234")
    self.device_config["persistent"]["console_port_name"] = "123.45.67.89"
    self.fake_responder.behavior_dict = {
        **raspbian_device_logs.DEFAULT_BEHAVIOR}
    self.enter_context(
        mock.patch.object(
            host_utils, "is_pingable", autospec=True, return_value=True))
    self.uut = raspberry_pi.RaspberryPi(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory)

  def test_get_dynamic_properties(self):
    self.validate_dynamic_properties(_DYNAMIC_PROPERTIES)

  def test_get_detection_info_for_raspbian_device(self):
    self._test_get_detection_info(
        self.device_config["persistent"]["console_port_name"],
        device_class=raspberry_pi.RaspberryPi,
        persistent_properties=_PERSISTENT_PROPERTIES)

  def test_recover_fails_as_device_never_goes_offline(self):
    with self.assertRaisesRegex(errors.DeviceError,
                                "Failed to go offline within .*s"):
      self.uut.recover(errors.DeviceNotResponsiveError(self.uut.name, ""))

  @mock.patch.object(host_utils, "is_pingable", return_value=False)
  def test_reboot_fails_as_device_never_goes_online(self, mock_ping):
    regex = (f"{self.uut.name} boot up failed. "
             "Device failed to become pingable in .*s.")
    with self.assertRaisesRegex(errors.DeviceError, regex):
      self.uut.reboot()

  def test_is_connected_true(self):
    """Verify is_connected works as expected."""
    self.assertTrue(
        raspbian_device.RaspbianDevice.is_connected(self.device_config))

  @mock.patch.object(host_utils, "is_pingable", return_value=False)
  def test_is_connected_false(self, mock_ping):
    """Verify is_connected works as expected."""
    self.assertFalse(
        raspbian_device.RaspbianDevice.is_connected(self.device_config))

  @mock.patch.object(host_utils, "is_pingable", return_value=False)
  def test_recover_raises_error(self, mock_is_pingable):
    """Verify recover raises error."""
    err_msg = "{device_name} experienced some error".format(
        device_name=self.uut.name)
    with self.assertRaisesRegex(errors.DeviceError, err_msg):
      self.uut.recover(errors.DeviceError(err_msg))

  @mock.patch.object(
      raspbian_device.RaspbianDevice, "shell", return_value=("degraded", 1))
  def test_ensure_device_is_online_unresponsive(self, mock_shell_result):
    """Verify method "_ensure_device_is_online" raises a DeviceError if unresponsive."""
    self.fake_responder.behavior_dict = {}
    err_msg = (
        "Failed to come online and respond to {!r} in {}s. Response: {}".format(
            raspbian_device.COMMANDS["BOOTUP_COMPLETE"].replace("\n", "\\n"),
            raspbian_device.TIMEOUTS["ONLINE"],
            "degraded"))
    with self.assertRaisesRegex(errors.DeviceError, err_msg):
      self.uut._ensure_device_is_online()

  @mock.patch.object(
      raspbian_device.RaspbianDevice,
      "shell",
      side_effect=iter([("degraded", 1), (None, 0), (None, 0)]))
  def test_ensure_device_is_online_responsive(self, mock_shell_result):
    """Verify method "_ensure_device_is_online" works properly if responsive."""
    self.uut._ensure_device_is_online()

  def test_check_device_ready_device_unresponsive(self):
    """Check that check_device_responsiveness() raises an error if device is unresponsive."""
    del self.fake_responder.behavior_dict[
        raspbian_device_logs.generate_command("echo 'GDM-HELLO'")]
    with self.assertRaisesRegex(errors.DeviceNotResponsiveError,
                                "unable to execute command"):
      self.uut.check_device_ready()


if __name__ == "__main__":
  fake_device_test_case.main()
