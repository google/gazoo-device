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

"""Test suite for Matter devices with Contact Sensor endpoint."""
from typing import Type
from gazoo_device.tests.functional_tests.mixins import boolean_state_cluster_suite
from gazoo_device.tests.functional_tests.utils import gdm_test_base


class ContactSensorTestSuite(gdm_test_base.GDMTestBase,
                             boolean_state_cluster_suite.BooleanStateTestSuite):
  """Tests for the Contact Sensor endpoint."""

  def setup_class(self) -> None:
    """Sets the endpoint instance."""
    super().setup_class()
    self.endpoint = self.device.contact_sensor

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
        device_class, device_name, "contact_sensor")
