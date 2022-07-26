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

"""Unit tests for the raspberry_pi_matter_controller module."""
from unittest import mock
from absl.testing import parameterized

from gazoo_device import errors
from gazoo_device.auxiliary_devices import raspberry_pi_matter_controller
from gazoo_device.base_classes import raspbian_device
from gazoo_device.capabilities.matter_endpoints import dimmable_light
from gazoo_device.capabilities.matter_endpoints import occupancy_sensor
from gazoo_device.capabilities.matter_endpoints import on_off_light
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.tests.unit_tests.utils import raspberry_pi_matter_controller_device_logs
from gazoo_device.tests.unit_tests.utils import ssh_device_logs


class RaspberryPiMatterControllerTests(
    fake_device_test_case.FakeDeviceTestCase):
  """Test for RaspberryPiMatterController."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements("rpi_matter_controller-1234")
    self.device_config["persistent"]["console_port_name"] = "123.45.67.89"
    self.device_config["options"]["matter_node_id"] = 1234
    self.fake_responder.behavior_dict = (
        raspberry_pi_matter_controller_device_logs.DEFAULT_BEHAVIOR.copy())

    self.uut = raspberry_pi_matter_controller.RaspberryPiMatterController(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory)

  def test_create_raspberry_pi_matter_controller_object(self):
    """Verifies the successful creation of a rpi matter controller object."""
    self.assertIsNotNone(self.uut)
    self.assertIsInstance(self.uut, raspbian_device.RaspbianDevice)

  def test_has_chip_tool_command(self):
    self.assertTrue(self.uut.shell_capability.has_command("chip-tool"))

  def test_initialize_matter_controller_capability(self):
    self.assertIsNotNone(self.uut.matter_controller)

  def test_initialize_matter_endpoints_accessor_capability(self):
    self.assertIsNotNone(self.uut.matter_endpoints)

  def _update_descriptor_device_list_response(self,
                                              device_type_id: int) -> None:
    """Updates response for device list command to return device_type_id."""
    response = {
        "cmd":
            raspberry_pi_matter_controller_device_logs
            .DESCRIPTOR_DEVICE_LIST_COMMAND,
        "resp":
            raspberry_pi_matter_controller_device_logs
            .DESCRIPTOR_DEVICE_LIST_RESPONSE.format(
                DEVICE_TYPE_ID=device_type_id),
        "code":
            0,
    }
    self.fake_responder.behavior_dict.update(
        ssh_device_logs.make_device_responses((response,)))

  @parameterized.named_parameters([
      ("dimmable_light", dimmable_light.DimmableLightEndpoint),
      ("on_off_light", on_off_light.OnOffLightEndpoint),
      ("occupancy_sensor", occupancy_sensor.OccupancySensorEndpoint),
  ])
  def test_initialize_endpoint_alias(self, endpoint_class):
    """Tests initializing endpoint alias."""
    endpoint_alias = endpoint_class.__module__.split(".")[-1]
    self._update_descriptor_device_list_response(
        endpoint_class.DEVICE_TYPE_ID)
    self.assertIsInstance(getattr(self.uut, endpoint_alias), endpoint_class)

  def test_initialize_matter_endpoints_with_no_matter_node_id(self):
    """Tests matter_endpoints throws DeviceError with no commissioned device."""
    del self.device_config["options"]["matter_node_id"]
    with self.assertRaises(errors.DeviceError):
      _ = self.uut.matter_endpoints

  @mock.patch.object(raspberry_pi_matter_controller.RaspberryPiMatterController,
                     "factory_reset")
  def test_factory_reset(self, mock_factory_reset):
    self.uut.factory_reset()
    mock_factory_reset.assert_called_once()


if __name__ == "__main__":
  fake_device_test_case.main()
