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
import logging
from typing import Type
from gazoo_device import errors
from gazoo_device.tests.functional_tests.utils import gdm_test_base
from mobly import asserts

# Hard-coded valid test constants
# Spake info are generated from the internal Matter auth_utils module
_PASSCODE = 61221323
_DISCRIMINATOR = 2203
_VERIFIER = b"\x07\tT$\xffL2\xf8\x9a\xe4\xf7H\xe4_\xcc;I{:\xfc\x80\x13\x9cj?\x15<\xaaG\xdf\x12c\x04\x0f\xa99\x15Yp\x19\x08R\xca5\xe9\x03\x12\x83\xb8\x05\xfaH\xc6@w\xf5_4\x14\xb81\x1e`\xd9[\xd8\r\xc8\xe7r_\x89\xc8ze\xfd<\xef\xadD\x89\xdbu\x99\x95\xe5`9\xe7D4\xfb\x8f\x06\xdab\xff"
_TLV_OTA_METADATA = b"\x15\xcc\x06`\x01\x00\x00\x00\x06SERIAL\xcc\x06`\x01\x00\x01\x00$98389552-3B89-44A5-980D-BA8685AF9EA3\x18"
_DEFAULT_VERIFIER_SALT = b"salt"
_DEFAULT_VERIFIER_ITERATIONS = 100


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

  def test_software_version(self):
    """Tests software_version property."""
    asserts.assert_is_instance(self.device.firmware_version, str)

  def test_qr_code(self):
    """Tests qr_code property."""
    asserts.assert_is_instance(self.device.qr_code, str)

  def test_qr_code_url(self):
    """Tests qr_code_url property."""
    asserts.assert_is_instance(self.device.qr_code_url, str)

  def test_set_pairing_code(self):
    """Tests set_pairing_info method for setting pairing code."""
    self.device.pw_rpc_common.set_pairing_info(code=_PASSCODE)
    asserts.assert_equal(_PASSCODE, self.device.pairing_code)

  def test_set_pairing_discriminator(self):
    """Tests set_pairing_info method for setting pairing discriminator."""
    self.device.pw_rpc_common.set_pairing_info(discriminator=_DISCRIMINATOR)
    asserts.assert_equal(_DISCRIMINATOR, self.device.pairing_discriminator)

  def test_set_and_get_spake_info(self):
    """Tests set_spake_info and get_spake_info for Spake information."""
    spake_info = self.device.pw_rpc_common.get_spake_info()
    salt = spake_info.salt or _DEFAULT_VERIFIER_SALT
    iteration_count = (
        spake_info.iteration_count or _DEFAULT_VERIFIER_ITERATIONS)
    self.device.pw_rpc_common.set_spake_info(
        verifier=_VERIFIER,
        salt=salt,
        iteration_count=iteration_count)
    spake_info = self.device.pw_rpc_common.get_spake_info()
    asserts.assert_equal(_VERIFIER, spake_info.verifier)
    asserts.assert_equal(salt, spake_info.salt)
    asserts.assert_equal(iteration_count, spake_info.iteration_count)

  def test_start_and_stop_advertising_for_commissioning(self):
    """Tests device commissioning advertisement."""
    if self.device.pw_rpc_common.is_advertising:
      self._stop_advertising_and_verify()
      self._start_advertising_and_verify()
    else:
      self._start_advertising_and_verify()
      self._stop_advertising_and_verify()

  def test_set_ota_metadata(self):
    """Tests set_ota_metadata API.

    It only works on device:
    1. which enables the OTA requestor compile options.
    2. which is already commissioned to an OTA provider.
    """
    try:
      self.device.pw_rpc_common.set_ota_metadata(_TLV_OTA_METADATA)
    except errors.DeviceError as e:
      if "UNIMPLEMENTED" in str(e):
        asserts.skip(f"{self.device} does not enable OTA requestor option.")
      elif "UNAVAILABLE" in str(e):
        logging.info(
            "%s is not commissioned to an OTA provider.", self.device)
      else:
        raise e

  def _start_advertising_and_verify(self):
    """Starts advertsiing and verifies the state."""
    self.device.pw_rpc_common.start_advertising()
    asserts.assert_true(self.device.pw_rpc_common.is_advertising,
                        "The device is not advertising.")

  def _stop_advertising_and_verify(self):
    """Stops advertsiing and verifies the state."""
    self.device.pw_rpc_common.stop_advertising()
    asserts.assert_false(self.device.pw_rpc_common.is_advertising,
                         "The device is still advertising.")


if __name__ == "__main__":
  gdm_test_base.main()
