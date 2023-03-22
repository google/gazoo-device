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

"""Unit tests for device class NrfOpenThread."""
from unittest import mock

from gazoo_device import errors
from gazoo_device.auxiliary_devices import nrf_openthread
from gazoo_device.switchboard import expect_response
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_FAKE_DEVICE_ID = "nrfopenthread-1234"
_FAKE_DEVICE_ADDRESS = "fake-device-address"


class NrfOpenThreadTests(fake_device_test_case.FakeDeviceTestCase):
  """Unit tests for device class NrfOpenThread."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements(_FAKE_DEVICE_ID)
    self.device_config["persistent"]["console_port_name"] = _FAKE_DEVICE_ADDRESS
    self.uut = nrf_openthread.NrfOpenThread(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory)

  def test_health_checks_not_empty(self):
    """Verifies the health checks is not empty."""
    self.assertTrue(self.uut.health_checks)

  @mock.patch.object(nrf_openthread.NrfOpenThread, "switchboard")
  def test_check_otcli_on_failure(self, mock_switchboard):
    """Verfies the check_otcli on failure."""
    mock_switchboard.send_and_expect.return_value = mock.MagicMock(
        timedout=True, spec=expect_response.ExpectResponse)
    with self.assertRaisesRegex(
        errors.DeviceBinaryMissingError,
        "The OpenThread CLI library is not working"):
      self.uut.check_otcli()

  def test_switchboard_instance(self):
    """Verifies the initialization of switchboard."""
    self.assertIsNotNone(self.uut.switchboard)

  def test_wpan_instance(self):
    """Verifies the initialization of wpan capability."""
    self.assertIsNotNone(self.uut.wpan)


if __name__ == "__main__":
  fake_device_test_case.main()
