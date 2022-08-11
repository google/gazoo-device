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

"""Mixin for Matter Illuminance Measurement cluster test suite."""
from mobly import asserts

_FAKE_DATA1 = 108
_FAKE_DATA2 = 999
_FAKE_DATA3 = 10


class IlluminanceMeasurementClusterTestSuite:
  """Mixin for Matter Illuminance Measurement cluster test suite.

  The mixin assumes self.endpoint is set.
  """

  def test_measured_value_attribute(self):
    """Tests the MeasuredValue attribute."""
    self.endpoint.illuminance_measurement.measured_value = _FAKE_DATA1
    asserts.assert_equal(
        _FAKE_DATA1,
        self.endpoint.illuminance_measurement.measured_value)

  def test_min_measured_value_attribute(self):
    """Tests the MinMeasuredValue attribute."""
    self.endpoint.illuminance_measurement.min_measured_value = _FAKE_DATA2
    asserts.assert_equal(
        _FAKE_DATA2,
        self.endpoint.illuminance_measurement.min_measured_value)

  def test_max_measured_value_attribute(self):
    """Tests the MaxMeasuredValue attribute."""
    self.endpoint.illuminance_measurement.max_measured_value = _FAKE_DATA3
    asserts.assert_equal(
        _FAKE_DATA3,
        self.endpoint.illuminance_measurement.max_measured_value)
