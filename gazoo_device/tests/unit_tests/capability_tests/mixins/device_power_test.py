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

"""Mixin for device_power capability."""
from unittest import mock


class DevicePowerTestMixin:
  """Mixin for common device unit tests of device power.

  Assumes self.uut is set.
  """

  def test_power_cycle(self):
    """Test self.uut.device_power.power_cycle is called."""
    with mock.patch.object(self.uut.device_power, "off"):
      with mock.patch.object(self.uut.device_power, "on"):
        self.uut.device_power.cycle()
        self.uut.device_power.off.assert_called_once()
        self.uut.device_power.on.assert_called_once()
