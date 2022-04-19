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

"""Test suite for devices using the pw_rpc_common capability."""
from typing import Type
from gazoo_device.tests.functional_tests.utils import gdm_test_base
from mobly import asserts

_PAIRING_CODE = 108
_PAIRING_DISCRIMINATOR = 50


class PwRPCCommonTestSuite(gdm_test_base.GDMTestBase):
  """Tests for the pw_rpc_common capability."""

  @classmethod
  def is_applicable_to(cls, device_type: str,
                       device_class: Type[gdm_test_base.DeviceType],
                       device_name: str) -> bool:
    """Determines if this test suite can run on the given device."""
    return device_class.has_capabilities(["pw_rpc_common"])

  @classmethod
  def requires_pairing(cls) -> bool:
    """Returns True if the device must be paired to run this test suite."""
    return False

  def test_vendor_id(self):
    """Tests the vendor_id property."""
    asserts.assert_is_instance(self.device.pw_rpc_common.vendor_id, int)

  def test_product_id(self):
    """Tests product_id property."""
    asserts.assert_is_instance(self.device.pw_rpc_common.product_id, int)

  def test_software_version(self):
    """Tests software_version property."""
    asserts.assert_is_instance(self.device.pw_rpc_common.software_version, int)

  def test_qr_code(self):
    """Tests qr_code property."""
    asserts.assert_is_instance(self.device.pw_rpc_common.qr_code, str)

  def test_qr_code_url(self):
    """Tests qr_code_url property."""
    asserts.assert_is_instance(self.device.pw_rpc_common.qr_code_url, str)

  def test_set_pairing_code(self):
    """Tests set_pairing_info method for setting pairing code."""
    self.device.pw_rpc_common.set_pairing_info(code=_PAIRING_CODE)
    asserts.assert_equal(_PAIRING_CODE,
                         self.device.pw_rpc_common.pairing_info.code)

  def test_set_pairing_discriminator(self):
    """Tests set_pairing_info method for setting pairing discriminator."""
    self.device.pw_rpc_common.set_pairing_info(
        discriminator=_PAIRING_DISCRIMINATOR)
    asserts.assert_equal(_PAIRING_DISCRIMINATOR,
                         self.device.pw_rpc_common.pairing_info.discriminator)


if __name__ == "__main__":
  gdm_test_base.main()
