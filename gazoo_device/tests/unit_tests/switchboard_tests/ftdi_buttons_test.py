# Copyright 2023 Google LLC
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

"""This test script performs unit tests on functions and methods in the ftdi_buttons module."""
from unittest import mock
from gazoo_device.switchboard import ftdi_buttons
from gazoo_device.tests.unit_tests.utils import unit_test_case

_TEST_BUTTON_MAP = {
    "a_button": {
        "interface": 1,
        "pin": 3
    },
    "b_button": {
        "interface": 2,
        "pin": 5
    },
}


class _FakeBitBangDevice:
  """Stub for BitBangDevice."""

  def __init__(
      self,
      device_id,
      interface_select,
      direction,
  ):
    self.port = 0
    self.device_id = device_id
    self.interface_select = interface_select
    self.direction = direction

  def close(self):
    self.port = None
    self.device_id = None
    self.interface_select = None
    self.direction = None
    return


def _make_fake_bbd(device_id, interface_select=None, direction=None):
  return _FakeBitBangDevice(device_id, interface_select, direction)


class FTDIButtonsTests(unit_test_case.UnitTestCase):
  """Tests for ftdi_buttons.py."""

  @mock.patch("pylibftdi.BitBangDevice", side_effect=_make_fake_bbd)
  def test_buttons_initialize(self, mock_bitbangdevice):
    """Test buttons initialize."""
    fake_serial_num = "1"
    ftdi_buttons_inst = ftdi_buttons.FtdiButtons(fake_serial_num,
                                                 _TEST_BUTTON_MAP)
    self.assertTrue(ftdi_buttons_inst)


if __name__ == "__main__":
  unit_test_case.main()
