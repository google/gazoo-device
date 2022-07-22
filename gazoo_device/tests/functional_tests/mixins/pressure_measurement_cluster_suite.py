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

"""Mixin for Matter Pressure Measurement cluster test suite."""
from mobly import asserts


class PressureMeasurementClusterTestSuite:
  """Mixin for Matter Pressure Measurement cluster test suite.

  The mixin assumes self.endpoint is set.
  """

  def test_measured_value_attribute(self):
    """Tests the MeasuredValue attribute."""
    asserts.assert_is_instance(
        self.endpoint.pressure_measurement.measured_value, int,
        "MeasuredValue attribute must be the int type.")

  def test_min_measured_value_attribute(self):
    """Tests the MinMeasuredValue attribute."""
    asserts.assert_is_instance(
        self.endpoint.pressure_measurement.min_measured_value, int,
        "MinMeasuredValue attribute must be the int type.")

  def test_max_measured_value_attribute(self):
    """Tests the MaxMeasuredValue attribute."""
    asserts.assert_is_instance(
        self.endpoint.pressure_measurement.max_measured_value, int,
        "MaxMeasuredValue attribute must be the int type.")
