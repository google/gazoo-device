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

"""Unit tests for the MatterControllerChipTool on host capability."""

from gazoo_device import package_registrar
from gazoo_device.auxiliary_devices import chip_tool
from gazoo_device.tests.unit_tests.capability_tests.mixins import matter_endpoint_accessor_test
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.tests.unit_tests.utils import matter_controller_device_logs


class MatterEndpointsAccessorChipToolOnHostCapabilityTests(
    fake_device_test_case.FakeDeviceTestCase,
    matter_endpoint_accessor_test.MatterEndpointAccessorTestMixin,
):
  """Unit tests for the MatterControllerChipTool on host capability implementation."""

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    package_registrar.register(chip_tool)

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements("chip_tool-1234")
    self.device_config["persistent"]["console_port_name"] = "123.45.67.89"
    self.fake_responder.behavior_dict = {
        **matter_controller_device_logs.LINUX_BEHAVIOR
    }

    self.uut = chip_tool.ChipTool(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory,
    )
    self._node_id = 1234
    self._endpoint = 1
    self.device_config["options"]["matter_node_id"] = self._node_id


if __name__ == "__main__":
  fake_device_test_case.main()
