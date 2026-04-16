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
"""Capability unit test for wpan_nrf_ot module."""

import ipaddress
import unittest
from unittest import mock

from gazoo_device import package_registrar
from gazoo_device.auxiliary_devices import nrf_openthread
from gazoo_device.capabilities import wpan_ot_base
from gazoo_device.tests.unit_tests.capability_tests.mixins import wpan_cli_based_test
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.tests.unit_tests.utils import nrf_openthread_device_logs


class WpanNrfOtTest(
    fake_device_test_case.FakeDeviceTestCase,
    wpan_cli_based_test.WpanOtTestMixin,
):
  """Unit test for WpanNrfOt."""

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    package_registrar.register(nrf_openthread)

  def setUp(self):
    """Sets up fake device instance."""
    super().setUp()
    self.setup_fake_device_requirements("nrfopenthread-1234")
    self.fake_responder.behavior_dict = {
        **nrf_openthread_device_logs.DEFAULT_BEHAVIOR,
    }
    self.uut = nrf_openthread.NrfOpenThread(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory,
    )

  def use_neighbor_table_v2(self):
    """Makes fake responder switch to neighbor table v2."""
    self.fake_responder.behavior_dict.update(
        nrf_openthread_device_logs.NEIGHBOR_TABLE_V2_BEHAVIOR
    )

  def use_neighbor_table_v3(self):
    """Makes fake responder switch to neighbor table v3."""
    self.fake_responder.behavior_dict.update(
        nrf_openthread_device_logs.NEIGHBOR_TABLE_V3_BEHAVIOR
    )

  def use_state_disabled(self):
    """Makes fake responder switch to disabled state."""
    self.fake_responder.behavior_dict.update(
        nrf_openthread_device_logs.make_device_responses(
            [{"cmd": "state", "resp": "disabled\nDone\n", "code": 0}]
        )
    )

  def use_ifconfig_up(self):
    """Makes fake responder ifconfig returns up."""
    self.fake_responder.behavior_dict.update(
        nrf_openthread_device_logs.make_device_responses(
            [{"cmd": "ifconfig", "resp": "up\nDone\n", "code": 0}]
        )
    )

  def use_ifconfig_down(self):
    """Makes fake responder ifconfig returns down."""
    self.fake_responder.behavior_dict.update(
        nrf_openthread_device_logs.make_device_responses(
            [{"cmd": "ifconfig", "resp": "down\nDone\n", "code": 0}]
        )
    )

  def use_cli_normal_output(self):
    """Makes fake responder cli return normal output."""
    self.fake_responder.behavior_dict.update(
        nrf_openthread_device_logs.make_device_responses([{
            "cmd": "normal output",
            "resp": "line 1\nline 2\nDone\n",
            "code": 0,
        }])
    )

  def use_cli_error_output(self):
    """Makes fake responder cli return error output."""
    self.fake_responder.behavior_dict.update(
        nrf_openthread_device_logs.make_device_responses([{
            "cmd": "error output",
            "resp": "line 1\nline 2\nError 1: error\n",
            "code": 0,
        }])
    )

  def use_cli_malformed_output(self):
    """Makes fake responder cli return malformed output."""
    self.fake_responder.behavior_dict.update(
        nrf_openthread_device_logs.make_device_responses([{
            "cmd": "malformed output",
            "resp": "Malformed output\n",
            "code": 0,
        }])
    )

  def test_srp_client_get_server_none(self):
    """Verifies srp_client_get_server returns None."""
    self.fake_responder.behavior_dict.update(
        nrf_openthread_device_logs.make_device_responses([{
            "cmd": "srp client server",
            "resp": "[]\nDone\n",
            "code": 0,
        }])
    )
    self.assertIsNone(self.uut.wpan.srp_client_get_server())

  def test_remove_mac_from_allowlist_failed(self):
    """Tests remove mac from allowlist failure case."""
    self.fake_responder.behavior_dict.update(
        nrf_openthread_device_logs.make_device_responses([{
            "cmd": "macfilter addr remove fake_addr",
            "resp": "line 1\nline 2\nError 1: error\n",
            "code": 0,
        }])
    )
    with self.assertRaises(wpan_ot_base.errors.DeviceError):
      self.uut.wpan.remove_mac_from_allowlist("fake_addr")

  def test_srp_client_get_server(self):
    """Verifies srp_client_get_server on success."""
    self.assertEqual(
        self.uut.wpan.srp_client_get_server(),
        (ipaddress.IPv6Address("fd00:db8:85a3:8d00::1"), 12345),
    )

  def test_srp_client_stop_failed(self):
    """Test to verify srp_client_stop failure."""
    self.fake_responder.behavior_dict.update(
        nrf_openthread_device_logs.make_device_responses([{
            "cmd": "srp client stop",
            "resp": "line 1\nline 2\nError 1: error\n",
            "code": 0,
        }])
    )
    with self.assertRaises(wpan_ot_base.errors.DeviceError):
      self.uut.wpan.srp_client_stop()

  def test_csl_channel(self):
    """Verifies csl_channel on success."""
    self.assertEqual(self.uut.wpan.csl_channel, 11)

  def test_set_csl_channel(self):
    """Verifies set_csl_channel on success."""
    self.uut.wpan.set_csl_channel(11)

  def test_csl_period(self):
    """Verifies csl_period on success."""
    self.assertEqual(self.uut.wpan.csl_period, 3125)

  def test_set_csl_period(self):
    """Verifies set_csl_period on success."""
    self.uut.wpan.set_csl_period(3125)

  def test_csl_timeout(self):
    """Verifies csl_timeout on success."""
    self.assertEqual(self.uut.wpan.csl_timeout, 100)

  def test_set_csl_timeout(self):
    """Verifies set_csl_timeout on success."""
    self.uut.wpan.set_csl_timeout(100)

  def test_srp_client_remove_service(self):
    """Tests to verify removing a service for SRP client."""
    self.uut.wpan.srp_client_remove_service("fake_service", "_test._tcp")

  def test_get_srp_client_key_lease_interval(self):
    """Tests to verify getting the key lease interval for SRP client."""
    self.assertEqual(self.uut.wpan.get_srp_client_key_lease_interval(), 1234567)

  def test_get_srp_client_host(self):
    """Tests to verify getting the host for SRP client."""
    self.assertEqual(
        self.uut.wpan.get_srp_client_host(),
        {
            "host": "host",
            "state": "Registered",
            "addresses": [ipaddress.IPv6Address(
                "fd42:64cd:20b:1:1d7c:ce76:e16d:8574")],
        },
    )

  def test_get_srp_client_host_failed(self):
    """Tests to verify getting the host for SRP client failure case."""
    self.fake_responder.behavior_dict.update(
        nrf_openthread_device_logs.make_device_responses([{
            "cmd": "srp client host",
            "resp": "name:'', state:, addrs:[]\nDone\n",
            "code": 0,
        }])
    )
    with self.assertRaises(RuntimeError):
      self.uut.wpan.get_srp_client_host()

  def test_property_srp_client_host_name(self):
    """Tests getting the SRP client host name."""
    self.assertEqual(self.uut.wpan.srp_client_host_name, "host1")

  def test_dns_client_get_config(self):
    """Tests getting the DNS client's config."""
    self.assertEqual(
        self.uut.wpan.dns_client_config,
        wpan_ot_base.DnsConfig(
            server=(
                ipaddress.IPv6Address(
                    "fdd2:0e53:2b87:b93f:50ad:4eea:0450:f1bf"
                ),
                53,
            ),
            response_timeout_ms=6000,
            max_tx_attempts=3,
            recursion_desired=True,
        ),
    )

  def test_dns_client_set_config(self):
    """Tests setting the DNS client's config."""
    self.uut.wpan.dns_client_set_config("2002::1", 53, 6000, 3, False)

  def test_srp_client_get_host_state(self):
    """Tests getting the SRP client's host state."""
    self.assertEqual(self.uut.wpan.get_srp_client_host_state(), "Registered")

  def test_dns_client_browse_services(self):
    """Tests browsing services by DNS client."""
    self.assertEqual(
        self.uut.wpan.dns_client_browse_services(
            "_test._tcp.default.service.arpa"
        ),
        [
            wpan_ot_base.ResolvedService(
                instance="service1",
                service="_test._tcp.default.service.arpa",
                port=12345,
                priority=0,
                weight=0,
                host="host1.default.service.arpa.",
                address=ipaddress.IPv6Address("2002::1"),
                txt={"k1": b"v1", "k2": b"v2", "k3": True},
                srv_ttl=4177,
                txt_ttl=4177,
                aaaa_ttl=4177,
            )
        ],
    )

  def test_dns_client_resolve_host(self):
    """Tests resolving a host by DNS client."""
    self.assertEqual(
        self.uut.wpan.dns_client_resolve_host("host.default.service.arpa"),
        [
            wpan_ot_base.ResolvedHost(
                address=ipaddress.IPv6Address("2002::1"),
                ttl=869,
            )
        ],
    )
    self.assertEqual(
        self.uut.wpan.dns_client_resolve_host("dns.google", ipv4=True),
        [
            wpan_ot_base.ResolvedHost(
                address=ipaddress.IPv6Address("fd69:342:8482:2:0:0:808:808"),
                ttl=869,
            )
        ],
    )

  def test_dns_client_resolve_service(self):
    """Tests resolving a service by DNS client."""
    self.assertEqual(
        self.uut.wpan.dns_client_resolve_service(
            "service 1", "_test._tcp.default.service.arpa"
        ),
        wpan_ot_base.ResolvedService(
            instance="service 1",
            service="_test._tcp.default.service.arpa",
            port=12345,
            priority=0,
            weight=0,
            host="host1.default.service.arpa.",
            address=ipaddress.IPv6Address("2002::1"),
            txt={"k1": b"v1", "k2": b"v2"},
            srv_ttl=326,
            txt_ttl=326,
            aaaa_ttl=326,
        ),
    )

  def test_is_dns_compression_enabled(self):
    """Tests checking if DNS compression is enabled."""
    self.assertTrue(self.uut.wpan.is_dns_compression_enabled(),)

  def test_enable_dns_compression(self):
    """Tests enabling the DNS compression."""
    self.assertIsNone(self.uut.wpan.enable_dns_compression())

  def test_disable_dns_compression(self):
    """Tests disabling the DNS compression."""
    self.assertIsNone(self.uut.wpan.disable_dns_compression())

  def test_srp_client_autostart(self):
    """Tests enabling the autostart for SRP client."""
    self.uut.wpan.srp_client_autostart(True)

  def test_srp_client_get_host_addresses(self):
    """Tests to get host addresses for SRP client."""
    self.assertEqual(
        self.uut.wpan.get_srp_client_host_addresses(),
        [ipaddress.IPv6Address("fdae:2909:4851:1:8b5b:6507:a4fd:bea6")],
    )

  def test_enable_srp_client_autostart(self):
    """Tests enabling the autostart for SRP client."""
    self.assertIsNone(self.uut.wpan.enable_srp_client_autostart())

  def test_enable_srp_client_autostart_failed(self):
    """Tests enabling the autostart failure case for SRP client."""
    self.fake_responder.behavior_dict.update(
        nrf_openthread_device_logs.make_device_responses([{
            "cmd": "srp client autostart enable",
            "resp": "line 1\nline 2\nError 1: error\n",
            "code": 0,
        }])
    )
    with self.assertRaises(wpan_ot_base.errors.DeviceError):
      self.uut.wpan.enable_srp_client_autostart()

  def test_enable_srp_client_callback(self):
    """Tests enabling the callbacks for SRP client."""
    self.assertIsNone(self.uut.wpan.enable_srp_client_callback())

  def test_enable_srp_client_callback_failed(self):
    """Tests enabling the callbacks failure case for SRP client."""
    self.fake_responder.behavior_dict.update(
        nrf_openthread_device_logs.make_device_responses([{
            "cmd": "srp client callback enable",
            "resp": "line 1\nline 2\nError 1: error\n",
            "code": 0,
        }])
    )
    with self.assertRaises(wpan_ot_base.errors.DeviceError):
      self.uut.wpan.enable_srp_client_callback()

  def test_reset(self):
    """Tests reset network on SRP client."""
    self.assertIsNone(self.uut.wpan.reset())

  def test_reset_failure(self):
    """Tests negative scenario for reset network on SRP client."""
    self.uut.wpan._send = unittest.mock.MagicMock(side_effect=Exception(
        "/nError"))

    with self.assertRaises(Exception) as context:
      self.uut.wpan.reset()
    self.assertEqual(str(context.exception),
                     "nrfopenthread-1234 WpanNrfOt.reset failed. Exception:"
                     " /nError")

  def test_srp_client_get_services(self):
    """Tests getting the services for SRP client."""
    self.assertEqual(
        self.uut.wpan.get_srp_client_services(),
        [
            wpan_ot_base.SrpClientService(
                instance="locker3",
                service="_ipps._udp",
                state='"Adding"',
                port=12349,
                priority=0,
                weight=0,
            )
        ],
    )

  def test_srp_client_callback(self):
    """Tests enabling the callbacks for SRP client."""
    self.uut.wpan.srp_client_callback(True)

  def test_srp_client_set_host_name(self):
    """Tests setting the host name for SRP client."""
    self.uut.wpan.srp_client_set_host_name("host1")

  def test_srp_client_set_host_addresses(self):
    """Tests setting the host addresses for SRP client."""
    self.uut.wpan.srp_client_set_host_addresses(["2002::1"])

  def test_srp_client_remove_host(self):
    """Tests removing the host for SRP client."""
    self.uut.wpan.srp_client_remove_host(remove_key_lease=True)

  def test_set_srp_client_lease_interval(self):
    """Tests setting the lease interval for SRP client."""
    self.uut.wpan.set_srp_client_lease_interval(60)

  def test_srp_client_add_service(self):
    """Tests adding a service for SRP client."""
    self.uut.wpan.srp_client_add_service(
        "service1",
        "_test._tcp",
        12345,
        0,
        0,
        {"k1": b"v1", "k2": b"v2", "k3": True},
    )

  def test_parse_srp_server_services(self):
    text = (
        "test-1._test._tcp.default.service.arpa.",
        "    deleted: false",
        "    subtypes: (null)",
        "    port: 12345",
        "    priority: 0",
        "    weight: 0",
        "    ttl: 7200",
        "    lease: 7200",
        "    key-lease: 680400",
        "    TXT: [k1=7631, k2=7632, , k3]",
        "    host: host1.default.service.arpa.",
        "    addresses: [2002:0:0:0:0:0:0:1]",
    )
    self.assertEqual(
        wpan_ot_base.parse_srp_server_services(text),
        [
            wpan_ot_base.SrpService(
                instance_name="test-1._test._tcp.default.service.arpa.",
                deleted=False,
                subtypes=(),
                port=12345,
                priority=0,
                weight=0,
                ttl=7200,
                lease=7200,
                key_lease=680400,
                txt={"k1": b"v1", "k2": b"v2", "k3": True},
                host="host1.default.service.arpa.",
                addresses=(ipaddress.IPv6Address("2002::1"),),
            )
        ],
    )

  def test_radio_stats(self):
    """Tests getting radio stats on device."""
    radio_stats = self.uut.wpan.radio_stats()
    self.assertEqual(radio_stats.tx_time, 0.232640)
    self.assertEqual(radio_stats.tx_time_pct, 0.39)
    self.assertEqual(radio_stats.rx_time, 4.226110)
    self.assertEqual(radio_stats.rx_time_pct, 7.16)
    self.assertEqual(radio_stats.sleep_time, 54.494689)
    self.assertEqual(radio_stats.sleep_time_pct, 92.43)
    self.assertEqual(radio_stats.disabled_time, 0.000000)
    self.assertEqual(radio_stats.disabled_time_pct, 0.00)

  def test_radio_stats_clear(self):
    """Tests clearing radio stats on device."""
    self.uut.wpan.radio_stats_clear()

  def test_udp_receive_msg(self):
    """Verifies udp receive msg on nrf."""
    self.fake_responder.behavior_dict.update(
        nrf_openthread_device_logs.make_device_responses([{
            "cmd": "udp bind -u :: 12345",
            "resp": (
                "Done\nbytes from 10\nfd58:7663:456f:1:7439:730:5713:b727"
                " 1287 10"
            ),
            "code": 0,
        }])
    )
    self.uut.wpan.udp_close()
    self.uut.wpan.udp_open()
    response = self.uut.wpan.udp_receive_msg("::", 12345, bind_unspecified=True)
    self.assertEqual(response, "10")
    self.uut.wpan.udp_close()

  def test_add_multicast_address_and_verify(self):
    """Test verifies add multicast address and verify on device."""
    self.assertIsNone(self.uut.wpan.add_multicast_address_and_verify(
        "ff05::1234:777a:1"))

  def test_add_multicast_address_and_verify_failed(self):
    """Test verifies add multicast address and verify failure on device."""
    self.fake_responder.behavior_dict.update(
        nrf_openthread_device_logs.make_device_responses([{
            "cmd": "ipmaddr",
            "resp": "ff05::1234:776a:1'\nDone\n",
            "code": 0,
        }])
    )
    with self.assertRaises(wpan_ot_base.errors.DeviceError):
      self.uut.wpan.add_multicast_address_and_verify("ff05::1234:777a:1")

  def test_ipmaddress(self) -> None:
    """Tests get ipmaddress."""
    self.assertEqual(
        self.uut.wpan.ipmaddress, [ipaddress.IPv6Address("ff05::1234:777a:1")])

  def test_add_ipmaddr(self) -> None:
    """Tests add ipmaddr."""
    self.assertIsNone(
        self.uut.wpan.add_ipmaddr("ff05::1234:777a:1"))

  def test_add_ipmaddr_failed(self):
    """Test add ipmaddr on device failure."""
    self.fake_responder.behavior_dict.update(
        nrf_openthread_device_logs.make_device_responses([{
            "cmd": "ipmaddr add ff05::1234:777a:0",
            "resp": "line 1\nline 2\nError 1: error\n",
            "code": 0,
        }])
    )
    with self.assertRaises(wpan_ot_base.errors.DeviceError):
      self.uut.wpan.add_ipmaddr("ff05::1234:777a:0")

  @mock.patch.object(wpan_ot_base.WpanOtBase, "add_ipmaddr")
  def test_add_multicast_address_and_verify_failed_on_add_ipmaddr(
      self, mock_add_ipmaddr):
    """Test add multicast address and verify failure on add ipmaddr."""
    self.fake_responder.behavior_dict.update(
        nrf_openthread_device_logs.make_device_responses([{
            "cmd": "ipmaddr add ff05::1234:777a:0",
            "resp": "line 1\nline 2\nError 1: error\n",
            "code": 0,
        }])
    )
    with self.assertRaises(wpan_ot_base.errors.DeviceError):
      self.uut.wpan.add_multicast_address_and_verify("ff05::1234:777a:0")
    mock_add_ipmaddr.assert_called_once_with("ff05::1234:777a:0")

  def test_property_omr_addresses_empty_if_netdata_has_no_omr_prefixes(self):
    self.fake_responder.behavior_dict.update(
        nrf_openthread_device_logs.make_device_responses([{
            "cmd": "netdata show",
            "resp": (
                "Prefixes:\n"
                "Routes:\n"
                "Services:\n"
                "44970 01 36000500000e10 s 2000\n"
                "Done\n"
            ),
            "code": 0,
        }])
    )

    with self.assertLogs(level="ERROR") as logger:
      omr_addresses = self.uut.wpan.omr_addresses

    with self.subTest("omr_addresses_is_empty"):
      self.assertEmpty(omr_addresses)
    with self.subTest("exception message is logged"):
      self.assertIn(
          "failed to get omr prefixes",
          logger.output[0],
      )


if __name__ == "__main__":
  fake_device_test_case.main()
