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

"""Test suite for Matter devices with on off light endpoint capability."""
from typing import Type

from gazoo_device.tests.functional_tests.mixins import level_control_cluster_suite
from gazoo_device.tests.functional_tests.mixins import on_off_cluster_suite
from gazoo_device.tests.functional_tests.utils import gdm_test_base
from mobly import asserts


class OnOffLightTestSuite(
    on_off_cluster_suite.OnOffClusterTestSuite,
    level_control_cluster_suite.LevelControlTestSuite):
  """Tests for the on off light endpoint capability."""

  def setup_class(self) -> None:
    """Sets the endpoint instance."""
    super().setup_class()
    self.endpoint = self.device.on_off_light

  @classmethod
  def requires_pairing(cls) -> bool:
    """Returns True if the device must be paired to run this test suite."""
    return False

  @classmethod
  def is_applicable_to(cls, device_type: str,
                       device_class: Type[gdm_test_base.DeviceType],
                       device_name: str) -> bool:
    """Determines if this test suite can run on the given device."""
    return device_class.has_capabilities(["on_off_light"])

  def test_move_to_level_command_and_current_level_attribute(self):
    """Tests the Level Control cluster.

    Wraps exception handler for testing level control cluster as level control
    cluster is an optional cluster for on_off_light.
    """
    try:
      super().test_move_to_level_command_and_current_level_attribute()
    except NotImplementedError:
      asserts.skip(
          f"{self.device.name} does not implement the Level Control cluster.")