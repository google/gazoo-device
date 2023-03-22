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

"""Matter cluster capability unit test for fan_control_pw_rpc module."""
from unittest import mock

from gazoo_device import errors
from gazoo_device.capabilities import matter_endpoints_accessor_pw_rpc
from gazoo_device.capabilities.matter_clusters import fan_control_pw_rpc
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_FAKE_DATA = 0


class FanControlClusterPwRpcTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for FanControlClusterPwRpc."""

  def setUp(self):
    super().setUp()
    self.fake_read = mock.Mock(spec=matter_endpoints_accessor_pw_rpc
                               .MatterEndpointsAccessorPwRpc.read)
    self.fake_read.return_value = mock.Mock(data_uint8=_FAKE_DATA)
    self.fake_write = mock.Mock(spec=matter_endpoints_accessor_pw_rpc
                                .MatterEndpointsAccessorPwRpc.write)
    self.uut = fan_control_pw_rpc.FanControlClusterPwRpc(
        device_name="fake-device-name",
        endpoint_id=1,
        read=self.fake_read,
        write=self.fake_write)

  def test_fan_mode(self):
    """Verifies fan_mode property."""
    self.assertEqual(_FAKE_DATA, self.uut.fan_mode)

  def test_fan_mode_setter(self):
    """Verifies fan_mode setter."""
    self.uut.fan_mode = _FAKE_DATA
    self.fake_write.assert_called_once()

  def test_fan_mode_setter_failure(self):
    """Verifies fan_mode setter failure."""
    with self.assertRaisesRegex(
        errors.DeviceError, f"didn't change to {_FAKE_DATA+1}"):
      self.uut.fan_mode = _FAKE_DATA + 1

  def test_fan_mode_sequence(self):
    """Verifies fan_mode_sequence property."""
    self.assertEqual(_FAKE_DATA, self.uut.fan_mode_sequence)

  def test_fan_mode_sequence_setter(self):
    """Verifies fan_mode_sequence setter."""
    self.uut.fan_mode_sequence = _FAKE_DATA
    self.fake_write.assert_called_once()

  def test_percent_setting(self):
    """Verifies percent_setting property."""
    self.assertEqual(_FAKE_DATA, self.uut.percent_setting)

  def test_percent_setting_setter(self):
    """Verifies percent_setting setter."""
    self.uut.percent_setting = _FAKE_DATA
    self.fake_write.assert_called_once()

  def test_percent_current(self):
    """Verifies percent_current property."""
    self.assertEqual(_FAKE_DATA, self.uut.percent_current)

  def test_percent_current_setter(self):
    """Verifies percent_current setter."""
    self.uut.percent_current = _FAKE_DATA
    self.fake_write.assert_called_once()

  def test_speed_max(self):
    """Verifies speed_max property."""
    self.assertEqual(_FAKE_DATA, self.uut.speed_max)

  def test_speed_max_setter(self):
    """Verifies speed_max setter."""
    self.uut.speed_max = _FAKE_DATA
    self.fake_write.assert_called_once()

  def test_speed_setting(self):
    """Verifies speed_setting property."""
    self.assertEqual(_FAKE_DATA, self.uut.speed_setting)

  def test_speed_setting_setter(self):
    """Verifies speed_setting setter."""
    self.uut.speed_setting = _FAKE_DATA
    self.fake_write.assert_called_once()

  def test_speed_current(self):
    """Verifies speed_current property."""
    self.assertEqual(_FAKE_DATA, self.uut.speed_current)

  def test_speed_current_setter(self):
    """Verifies speed_current setter."""
    self.uut.speed_current = _FAKE_DATA
    self.fake_write.assert_called_once()


if __name__ == "__main__":
  fake_device_test_case.main()
