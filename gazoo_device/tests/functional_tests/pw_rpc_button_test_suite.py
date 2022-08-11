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

"""Test suite for devices using the pw_rpc_button capability."""
from typing import Type
from gazoo_device import errors
from gazoo_device.tests.functional_tests.utils import gdm_test_base
from mobly import asserts

# Pressing button 1 changes the lighting state of the board if it's a lighting
# app. Should be no-op if it's a locking app.
_BUTTON_ID_1 = 1


class PwRPCButtonTestSuite(gdm_test_base.GDMTestBase):
  """Tests for pw_rpc_button capability."""

  @classmethod
  def is_applicable_to(cls, device_type: str,
                       device_class: Type[gdm_test_base.DeviceType],
                       device_name: str) -> bool:
    """Determines if this test suite can run on the given device."""
    return device_class.has_capabilities(["pw_rpc_button"])

  @classmethod
  def requires_pairing(cls) -> bool:
    """Returns True if the device must be paired to run this test suite."""
    return False

  def test_button_push(self):
    """Tests button push method."""
    try:
      self.device.pw_rpc_button.push(button_id=_BUTTON_ID_1)
    except errors.DeviceError as e:
      if "Status.NOT_FOUND: the RPC server does not support this RPC" in str(e):
        asserts.skip(f"{self.device.name} does not support button RPCs.")
      else:
        raise


if __name__ == "__main__":
  gdm_test_base.main()
