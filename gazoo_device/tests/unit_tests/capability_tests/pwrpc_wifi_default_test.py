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

"""Capability unit test for pwrpc_wifi_default module."""
from unittest import mock

from gazoo_device import errors
from gazoo_device.capabilities import pwrpc_wifi_default
from gazoo_device.protos import wifi_service_pb2
from gazoo_device.switchboard import switchboard
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_FAKE_DEVICE_NAME = "wifi_device"
_WIFI_SECURITY_TYPE = "WIFI_AUTH_WPA2_PSK"


class PwRPCWifiDefaultTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit test for PwRPCWifiDefault."""

  def setUp(self):
    super().setUp()
    self.switchboard_call_mock = mock.Mock(
        spec=switchboard.SwitchboardDefault.call)
    self.uut = pwrpc_wifi_default.PwRPCWifiDefault(
        device_name=_FAKE_DEVICE_NAME,
        switchboard_call=self.switchboard_call_mock)

  def test_channel(self):
    """Verifies get wifi channel."""
    wifi_channel = 1
    channel_to_bytes = wifi_service_pb2.Channel(
        channel=wifi_channel).SerializeToString()
    self.switchboard_call_mock.return_value = channel_to_bytes
    self.assertEqual(self.uut.channel, wifi_channel)
    self.switchboard_call_mock.assert_called_once()

  def test_ssid(self):
    """Verifies get wifi ssid."""
    wifi_ssid = b"TEST"
    ssid_to_bytes = wifi_service_pb2.Ssid(
        ssid=wifi_ssid).SerializeToString()
    self.switchboard_call_mock.return_value = ssid_to_bytes
    self.assertEqual(self.uut.ssid, wifi_ssid.decode("utf-8"))
    self.switchboard_call_mock.assert_called_once()

  def test_mac_address(self):
    """Verifies get wifi mac address."""
    wifi_mac = "AA:AA:AA:AA:AA:AA"
    mac_address_to_bytes = wifi_service_pb2.MacAddress(
        mac_address=wifi_mac).SerializeToString()
    self.switchboard_call_mock.return_value = mac_address_to_bytes
    self.assertEqual(self.uut.mac_address, wifi_mac)
    self.switchboard_call_mock.assert_called_once()

  def test_wifi_interface(self):
    """Verifies get wifi interface."""
    wifi_interface = "wlan0"
    interface_to_bytes = wifi_service_pb2.WiFiInterface(
        interface=wifi_interface).SerializeToString()
    self.switchboard_call_mock.return_value = interface_to_bytes
    self.assertEqual(self.uut.wifi_interface, wifi_interface)
    self.switchboard_call_mock.assert_called_once()

  def test_ipv4_address(self):
    """Verifies get wifi ipv4 address."""
    wifi_ipv4_address = "192.168.100.120"
    address_to_bytes = wifi_service_pb2.IP4Address(
        address=wifi_ipv4_address).SerializeToString()
    self.switchboard_call_mock.return_value = address_to_bytes
    self.assertEqual(self.uut.ipv4_address, wifi_ipv4_address)
    self.switchboard_call_mock.assert_called_once()

  def test_connect_success(self):
    """Verifies wifi connection is successful."""
    ssid = "TEST"
    security_type = _WIFI_SECURITY_TYPE
    connection_result = wifi_service_pb2.CONNECTION_ERROR.OK
    connection_result_bytes = wifi_service_pb2.ConnectionResult(
        error=connection_result).SerializeToString()
    self.switchboard_call_mock.return_value = connection_result_bytes
    self.uut.connect(ssid=ssid, security_type=security_type)
    self.switchboard_call_mock.assert_called_once()

  def test_connect_failure(self):
    """Verifies device error in case of wifi connection is unsuccessful."""
    ssid = "TEST"
    security_type = _WIFI_SECURITY_TYPE
    connection_result = wifi_service_pb2.CONNECTION_ERROR.AUTH_EXPIRE
    connection_result_bytes = wifi_service_pb2.ConnectionResult(
        error=connection_result).SerializeToString()

    self.switchboard_call_mock.return_value = connection_result_bytes
    with self.assertRaisesWithLiteralMatch(
        errors.DeviceError,
        f"{_FAKE_DEVICE_NAME} failed to connect to wifi with {connection_result}"
    ):
      self.uut.connect(ssid=ssid, security_type=security_type)
    self.switchboard_call_mock.assert_called_once()

  def test_disconnect_success(self):
    """Verifies wifi disconnect is successful."""
    self.uut.disconnect()
    self.switchboard_call_mock.assert_called_once()


if __name__ == "__main__":
  fake_device_test_case.main()
