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

_PAIRING_CODE = 108
_PAIRING_DISCRIMINATOR = 50
_FAKE_VERIFIER = b"fake-verifier"
_FAKE_SALT = b"fake-salt"
_FAKE_ITERATION = 10
# TODO(b/241698162): Include a utility for TLV metadata generation.
_TLV_OTA_METADATA = b"\x15\xcc\x06`\x01\x00\x00\x00\x06SERIAL\xcc\x06`\x01\x00\x01\x00$98389552-3B89-44A5-980D-BA8685AF9EA3\x18"


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
    self.device.pw_rpc_common.set_pairing_info(code=_PAIRING_CODE)
    asserts.assert_equal(_PAIRING_CODE, self.device.pairing_code)

  def test_set_pairing_discriminator(self):
    """Tests set_pairing_info method for setting pairing discriminator."""
    self.device.pw_rpc_common.set_pairing_info(
        discriminator=_PAIRING_DISCRIMINATOR)
    asserts.assert_equal(_PAIRING_DISCRIMINATOR,
                         self.device.pairing_discriminator)

  def test_set_and_get_spake_info(self):
    """Tests set_spake_info and get_spake_info for Spake information."""
    self.device.pw_rpc_common.set_spake_info(
        verifier=_FAKE_VERIFIER,
        salt=_FAKE_SALT,
        iteration_count=_FAKE_ITERATION)
    spake_info = self.device.pw_rpc_common.get_spake_info()
    asserts.assert_equal(_FAKE_VERIFIER, spake_info.verifier)
    asserts.assert_equal(_FAKE_SALT, spake_info.salt)
    asserts.assert_equal(_FAKE_ITERATION, spake_info.iteration_count)

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
