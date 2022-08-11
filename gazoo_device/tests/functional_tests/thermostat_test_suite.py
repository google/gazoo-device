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

"""Test suite for Matter devices with Thermostat endpoint."""
from typing import Type
from gazoo_device.tests.functional_tests.mixins import occupancy_sensing_cluster_suite
from gazoo_device.tests.functional_tests.mixins import temperature_measurement_cluster_suite
from gazoo_device.tests.functional_tests.mixins import thermostat_cluster_suite
from gazoo_device.tests.functional_tests.utils import gdm_test_base


class ThermostatTestSuite(
    gdm_test_base.GDMTestBase,
    occupancy_sensing_cluster_suite.OccupancySensingClusterTestSuite,
    temperature_measurement_cluster_suite
    .TemperatureMeasurementClusterTestSuite,
    thermostat_cluster_suite.ThermostatClusterTestSuite):
  """Tests for the Thermostat endpoint."""

  def setup_class(self) -> None:
    """Sets the endpoint instance."""
    super().setup_class()
    self.endpoint = self.device.thermostat

  @classmethod
  def requires_pairing(cls) -> bool:
    """Returns True if the device must be paired to run this test suite."""
    return False

  @classmethod
  def is_applicable_to(cls, device_type: str,
                       device_class: Type[gdm_test_base.DeviceType],
                       device_name: str) -> bool:
    """Determines if this test suite can run on the given device."""
    return gdm_test_base.whether_implements_matter_endpoint(
        device_class, device_name, "thermostat")
