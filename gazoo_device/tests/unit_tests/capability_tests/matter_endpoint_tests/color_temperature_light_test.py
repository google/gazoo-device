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

"""Matter endpoint capability unit test for color_temperature_light module."""
from gazoo_device.capabilities.matter_endpoints import color_temperature_light
from gazoo_device.tests.unit_tests.capability_tests.mixins import matter_endpoint_light_test
from gazoo_device.tests.unit_tests.utils import fake_device_test_case


class ColorTemperatureLightEndpointTest(
    fake_device_test_case.FakeDeviceTestCase,
    matter_endpoint_light_test.LightEndpointTest):
  """Unit test for ColorTemperatureLight."""

  def setUp(self):
    super().setUp()
    self.uut = color_temperature_light.ColorTemperatureLightEndpoint(
        device_name=matter_endpoint_light_test.FAKE_DEVICE_NAME,
        identifier=matter_endpoint_light_test.FAKE_ENDPOINT_ID,
        supported_clusters=set(),
        switchboard_call=None,
        rpc_timeout_s=matter_endpoint_light_test.FAKE_RPC_TIMEOUT_S)


if __name__ == "__main__":
  fake_device_test_case.main()
