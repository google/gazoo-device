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
"""Unit tests for the MatterControllerChipTool capability."""

from gazoo_device import errors
from gazoo_device.auxiliary_devices import raspberry_pi_matter_controller
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.tests.unit_tests.utils import raspberry_pi_matter_controller_device_logs


class MatterControllerChipToolCapabilityTests(
    fake_device_test_case.FakeDeviceTestCase):
  """Unit test for MatterControllerChipTool capability implementation."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements("rpi_matter_controller-1234")
    self.device_config["persistent"]["console_port_name"] = "123.45.67.89"
    self.fake_responder.behavior_dict = (
        raspberry_pi_matter_controller_device_logs.DEFAULT_BEHAVIOR.copy())

    self.uut = raspberry_pi_matter_controller.RaspberryPiMatterController(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory)
    self._node_id = 1234
    self._setup_code = 20202021
    self._long_discriminator = 3840
    self._endpoint_id = 1
    self._cluster = "onoff"

  def test_matter_sdk_version(self):
    self.assertEqual(self.uut.matter_controller.version,
                     "92f834375b2075e6c1c93d12b373b663d4b9250b")

  def test_commission_over_ble_wifi(self):
    self.uut.matter_controller.commission(
        node_id=self._node_id,
        ssid="wifi-ssid",
        password="wifi-password",
        setup_code=self._setup_code,
        long_discriminator=self._long_discriminator)

  def test_commission_over_ble_wifi_with_hex(self):
    self.uut.matter_controller.commission(
        node_id=self._node_id,
        ssid="hex:776966692d73736964",
        password="hex:776966692d70617373776f7264",
        setup_code=self._setup_code,
        long_discriminator=self._long_discriminator)

  def test_commission_on_network(self):
    self.uut.matter_controller.commission(
        node_id=self._node_id, setup_code=self._setup_code)

  def test_commission_on_network_long(self):
    self.uut.matter_controller.commission(
        node_id=self._node_id,
        setup_code=self._setup_code,
        long_discriminator=self._long_discriminator)

  def test_commission_over_ble_thread(self):
    self.uut.matter_controller.commission(
        node_id=self._node_id,
        setup_code=self._setup_code,
        long_discriminator=self._long_discriminator,
        operational_dataset="abcd")

  def test_commission_timeout_failure(self):
    """Commission method should raise DeviceError when setup code is invalid."""
    invalid_setup_code = "00000000"
    with self.assertRaises(errors.DeviceError):
      self.uut.matter_controller.commission(
          node_id=self._node_id, setup_code=invalid_setup_code)

  def test_commission_over_ble_wifi_without_password(self):
    with self.assertRaises(errors.DeviceError):
      self.uut.matter_controller.commission(
          node_id=self._node_id,
          ssid="wifi-ssid",
          setup_code=self._setup_code,
          long_discriminator=self._long_discriminator)

  def test_decommission(self):
    self.uut.matter_controller.decommission(node_id=self._node_id)

  def test_decommission_timeout_failure(self):
    """Decommission method should raise DeviceError when node id is invalid."""
    invalid_node_id = "0000"
    with self.assertRaises(errors.DeviceError):
      self.uut.matter_controller.decommission(node_id=invalid_node_id)

  def test_read_attribute_integer(self):
    self.assertEqual(
        self.uut.matter_controller.read(self._node_id, self._endpoint_id,
                                        self._cluster, "on-time"), 0)

  def test_read_attribute_boolean(self):
    self.assertTrue(
        self.uut.matter_controller.read(self._node_id, self._endpoint_id,
                                        self._cluster, "on-off"))

  def test_write_attribute(self):
    self.uut.matter_controller.write(self._node_id, self._endpoint_id,
                                     self._cluster, "on-time", 100)

  def test_send_command(self):
    self.uut.matter_controller.send(self._node_id, self._endpoint_id,
                                    self._cluster, "toggle", [])

  def test_write_attribute_non_zero_status_code(self):
    with self.assertRaises(errors.DeviceError):
      self.uut.matter_controller.write(self._node_id, self._endpoint_id,
                                       self._cluster, "non-existent-attr", 0)

  def test_send_command_non_zero_status_code(self):
    with self.assertRaises(errors.DeviceError):
      self.uut.matter_controller.write(self._node_id, self._endpoint_id,
                                       self._cluster, "non-existent-cmd", [])


if __name__ == "__main__":
  fake_device_test_case.main()