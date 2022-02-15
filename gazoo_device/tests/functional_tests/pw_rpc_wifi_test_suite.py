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

"""Test suite for devices using the pw_rpc_wifi capability."""
import time
from typing import Type

from gazoo_device.tests.functional_tests.utils import gdm_test_base
from mobly import asserts

_NULL_IP_ADDRESS = "0.0.0.0"
_IP_ADDRESS_RETRY_ATTEMPTS = 3
_IP_ADDRESS_RETRY_WAIT_SECODS = 2


class PwRPCWifiTestSuite(gdm_test_base.GDMTestBase):
  """Tests for the pw_rpc_wifi capability."""

  @classmethod
  def is_applicable_to(cls, device_type: str,
                       device_class: Type[gdm_test_base.DeviceType],
                       device_name: str) -> bool:
    """Determines if this test suite can run on the given device."""
    return device_class.has_capabilities(["pw_rpc_wifi"])

  @classmethod
  def requires_pairing(cls) -> bool:
    """Returns True if the device must be paired to run this test suite."""
    return False

  def test_wifi_mac_address(self):
    """Tests the mac_address property."""
    resp = self.device.pw_rpc_wifi.mac_address
    asserts.assert_is_instance(resp, str)

  def test_wifi_disconnect(self):
    """Tests wifi disconnect method."""
    self.device.pw_rpc_wifi.disconnect()
    asserts.assert_equal(self.device.pw_rpc_wifi.ipv4_address, _NULL_IP_ADDRESS)
    asserts.assert_equal(self.device.pw_rpc_wifi.ssid, "")

  def test_wifi_connect_and_properties(self):
    """Tests wifi connect method, channel, ipv4 address, ssid properties."""
    require_properties = ["wifi_ssid", "wifi_security_type", "wifi_password"]
    if not all(prop in self.testing_properties for prop in require_properties):
      asserts.skip(reason=f"Wi-Fi testing properties {require_properties} are"
                   "missing from the testbed config file.")
    self.device.pw_rpc_wifi.connect(
        ssid=self.testing_properties["wifi_ssid"],
        security_type=self.testing_properties["wifi_security_type"],
        secret=self.testing_properties["wifi_password"])

    channel = self.device.pw_rpc_wifi.channel
    asserts.assert_is_instance(channel, int)
    ssid = self.device.pw_rpc_wifi.ssid
    asserts.assert_equal(ssid, self.testing_properties["wifi_ssid"])

    # Retry until device acquires a ipv4 address from dhcp server.
    for _ in range(_IP_ADDRESS_RETRY_ATTEMPTS):
      time.sleep(_IP_ADDRESS_RETRY_WAIT_SECODS)
      ipv4_address = self.device.pw_rpc_wifi.ipv4_address
      if ipv4_address != _NULL_IP_ADDRESS:
        break
    asserts.assert_is_instance(ipv4_address, str)
    asserts.assert_not_equal(ipv4_address, _NULL_IP_ADDRESS)


if __name__ == "__main__":
  gdm_test_base.main()
