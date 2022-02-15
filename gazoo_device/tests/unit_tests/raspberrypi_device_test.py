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

"""Unit tests for the raspberry_pi module."""
from gazoo_device.auxiliary_devices import raspberry_pi
from gazoo_device.base_classes import raspbian_device
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.tests.unit_tests.utils import raspbian_device_logs


class RaspberryPiTests(fake_device_test_case.FakeDeviceTestCase):
  """Test for RaspberryPi."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements("raspberrypi-1234")
    self.device_config["persistent"]["console_port_name"] = "123.45.67.89"
    self.fake_responder.behavior_dict = (
        raspbian_device_logs.DEFAULT_BEHAVIOR.copy())

    self.uut = raspberry_pi.RaspberryPi(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory)

  def test_001_test_create_raspberry_pi_object(self):
    """Verifies the successful creation of a raspberrypi object."""
    self.assertIsNotNone(self.uut)
    self.assertIsInstance(self.uut, raspbian_device.RaspbianDevice)


if __name__ == "__main__":
  fake_device_test_case.main()
