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
"""Mixin for OpenThread CLI based wpan capabilities."""

import abc
import ipaddress

from gazoo_device import errors
from gazoo_device.capabilities import wpan_ot_base
from gazoo_device.tests.unit_tests.utils import unit_test_case


class WpanOtTestMixin(unit_test_case.UnitTestCase):
  """Mixin for OpenThread CLI based wpan capabilities."""

  @abc.abstractmethod
  def use_neighbor_table_v2(self):
    """Makes fake responder switch to neighbor table v2."""

  @abc.abstractmethod
  def use_neighbor_table_v3(self):
    """Makes fake responder switch to neighbor table v3."""

  @abc.abstractmethod
  def use_state_disabled(self):
    """Makes fake responder switch to disabled state."""

  @abc.abstractmethod
  def use_ifconfig_up(self):
    """Makes fake responder ifconfig returns up."""

  @abc.abstractmethod
  def use_ifconfig_down(self):
    """Makes fake responder ifconfig returns down."""

  @abc.abstractmethod
  def use_cli_normal_output(self):
    """Makes fake responder cli return normal output."""

  @abc.abstractmethod
  def use_cli_error_output(self):
    """Makes fake responder cli return error output."""

  @abc.abstractmethod
  def use_cli_malformed_output(self):
    """Makes fake responder cli return malformed output."""

  def test_property_ncp_channel(self):
    """Test getting ncp channel."""
    response = self.uut.wpan.ncp_channel
    self.assertEqual(response, 11)

  def test_property_network_is_commissioned(self):
    """Test getting network_is_commissioned."""
    self.assertTrue(self.uut.wpan.network_is_commissioned)

  def test_property_ncp_mac_address(self):
    """Test getting ncp mac address."""
    response = self.uut.wpan.ncp_mac_address
    self.assertEqual(response, "18B43000003D23F6")

  def test_property_network_key(self):
    """Test getting network key."""
    response = self.uut.wpan.network_key
    self.assertEqual(response, "00112233445566778899AABBCCDDEEFF")

  def test_property_network_name(self):
    """Test getting network name."""
    response = self.uut.wpan.network_name
    self.assertEqual(response, "PAN-2342")

  def test_property_network_node_type(self):
    """Test getting network node type."""
    response = self.uut.wpan.network_node_type
    self.assertEqual(response, "leader")

  def test_property_network_panid(self):
    """Test getting network panid."""
    response = self.uut.wpan.network_panid
    self.assertEqual(response, "0x1234")

  def test_property_network_partition_id(self):
    """Test getting network partition id."""
    response = self.uut.wpan.network_partition_id
    self.assertEqual(response, "0")

  def test_property_network_xpanid(self):
    """Test getting network xpanid."""
    response = self.uut.wpan.network_xpanid
    self.assertEqual(response, "0xDEAD00BEEF00CAFE")

  def test_property_ncp_state(self):
    """Test getting network node type."""
    response = self.uut.wpan.ncp_state
    self.assertEqual(response, "leader")

  def test_property_thread_neighbor_table(self):
    """verify expected thread_neighbor_table is returned."""
    expected_result = {
        "RLOC16": "b801",
        "FullNetData": "no",
        "Age": "152",
        "RxOnIdle": "yes",
        "FTD": "no",
        "SecDataReq": "yes",
        "Id": "BA1FA59BE77D24BA",
        "LastRssi": "-20",
        "AveRssi": "-20",
        "IsChild": "yes",
    }
    result = self.uut.wpan.thread_neighbor_table
    self.assertEqual(len(result), 1)
    for k, v in expected_result.items():
      self.assertEqual(v, result[0][k])

  def test_property_thread_network_data(self):
    """Test getting network node type."""
    response = self.uut.wpan.thread_network_data
    self.assertEqual(response, "08040b02c502")

  def test_property_thread_rloc16(self):
    """Test getting network node type."""
    response = self.uut.wpan.thread_rloc16
    self.assertEqual(response, "0xB800")

  def test_property_thread_router_id(self):
    """Test getting network node type."""
    response = self.uut.wpan.thread_router_id
    self.assertEqual(response, "0xB8")

  def test_property_ncp_counter_tx_err_cca(self):
    """Test getting network node type."""
    response = self.uut.wpan.ncp_counter_tx_err_cca
    self.assertEqual(response, 0)

  def test_property_ncp_counter_tx_ip_dropped(self):
    """Test getting network node type."""
    response = self.uut.wpan.ncp_counter_tx_ip_dropped
    self.assertEqual(response, 0)

  def test_property_ncp_counter_tx_pkt_acked(self):
    """Test getting network node type."""
    response = self.uut.wpan.ncp_counter_tx_pkt_acked
    self.assertEqual(response, 5)

  def test_property_thread_child_table(self):
    """Verify expected thread child table is returned."""
    expected_result = {
        "RLOC16": "b801",
        "FullNetData": "no",
        "NetDataVer": "253",
        "LQIn": "3",
        "Age": "48",
        "RxOnIdle": "yes",
        "FTD": "no",
        "Timeout": "240",
        "SecDataReq": "yes",
        "Id": "BA1FA59BE77D24BA",
    }
    result = self.uut.wpan.thread_child_table
    self.assertEqual(len(result), 1)
    for k, v in expected_result.items():
      self.assertEqual(v, result[0][k])

  def test_property_ipv6_all_addresses(self):
    """Verify expected ipv6 address are returned."""
    expected_addresses = [
        "fdde:ad00:beef:0:0:ff:fe00:fc00",
        "fdb7:5223:be73:1::1455",
        "fdde:ad00:beef:0:0:ff:fe00:b800",
        "fdde:ad00:beef:0:a55:2885:3ba1:656e",
        "fe80:0:0:0:24cc:59fd:b37:bd8c",
    ]
    self.assertListEqual(expected_addresses, self.uut.wpan.ipv6_all_addresses)

  def test_unimplemented_features(self):
    """verify unimplemented properties return expected error."""
    property_not_implemented = "Unknown: Error - unimplemented"
    unimplemented_properties = [
        "ncp_rssi",
        "thread_leader_address",
        "thread_leader_local_weight",
        "thread_leader_network_data",
        "thread_leader_router_id",
        "thread_leader_stable_network_data",
        "thread_leader_weight",
        "thread_stable_network_data",
        "thread_stable_network_data_version",
    ]
    for prop in unimplemented_properties:
      self.assertEqual(getattr(self.uut.wpan, prop), property_not_implemented)

  def test_property_thread_neighbor_table_v2(self):
    """verify expected thread_neighbor_table is returned."""
    self.use_neighbor_table_v2()
    expected_result = {
        "RLOC16": "7801",
        "FullNetData": "no",
        "Age": "136",
        "RxOnIdle": "yes",
        "FTD": "no",
        "Id": "5EA6BE302FED82D0",
        "LastRssi": "-28",
        "AveRssi": "-29",
        "IsChild": "yes",
    }

    result = self.uut.wpan.thread_neighbor_table
    self.assertEqual(len(result), 1)
    for k, v in expected_result.items():
      self.assertEqual(v, result[0][k])

  def test_property_thread_child_table_v2(self):
    """Verify expected thread child table is returned."""
    self.use_neighbor_table_v2()
    expected_result = {
        "RLOC16": "1c01",
        "FullNetData": "no",
        "NetDataVer": "68",
        "LQIn": "3",
        "Age": "17",
        "RxOnIdle": "yes",
        "FTD": "no",
        "Timeout": "240",
        "Id": "6AE0664FDC316F66",
    }
    result = self.uut.wpan.thread_child_table
    self.assertEqual(len(result), 1)
    for k, v in expected_result.items():
      self.assertEqual(v, result[0][k])

  def test_property_thread_child_table_v3(self):
    """Verify expected thread child table is returned."""
    self.use_neighbor_table_v3()
    expected_result = {
        "RLOC16": "b001",
        "FullNetData": "no",
        "NetDataVer": "168",
        "LQIn": "3",
        "Age": "12",
        "RxOnIdle": "yes",
        "FTD": "no",
        "Timeout": "240",
        "Id": "9AB3267C95E504B9",
    }
    result = self.uut.wpan.thread_child_table
    self.assertEqual(len(result), 1)
    for k, v in expected_result.items():
      self.assertEqual(v, result[0][k])

  def test_property_network_partition_id_v2(self):
    """Test getting network partition id."""
    self.use_neighbor_table_v2()
    response = self.uut.wpan.network_partition_id
    self.assertEqual(response, "1")

  def test_property_router_selection_jitter(self):
    """Test getting the router selection jitter."""
    self.assertEqual(self.uut.wpan.router_selection_jitter, 120)

  def test_property_local_omr_prefix(self):
    """Test getting the local OMR prefix."""
    self.assertEqual(self.uut.wpan.local_omr_prefix, "fdfc:1ff5:1512:5622::/64")

  def test_property_local_onlink_prefix(self):
    """Test getting the local On-Link prefix."""
    self.assertEqual(
        self.uut.wpan.local_onlink_prefix, "2600::0:1234:da12::/64"
    )

  def test_property_network_data_omr_prefixes(self):
    """Test getting the OMR prefixes from network data."""
    self.assertEqual(
        self.uut.wpan.network_data_omr_prefixes,
        [(
            ipaddress.IPv6Network("fdb7:5223:be73:1::/64"),
            "paos",
            "low",
            0x2000,
        )],
    )

  def test_property_omr_addresses(self):
    """Test getting the local OMR addresses."""
    self.assertEqual(self.uut.wpan.omr_addresses, ["fdb7:5223:be73:1::1455"])

  def test_thread_start(self):
    """Verifies thread_stop on success."""
    self.uut.wpan.thread_start()

  def test_thread_stop(self):
    """Verifies thread_stop on success."""
    self.uut.wpan.thread_stop()

  def test_ping(self):
    """Verifies ping on success."""
    response = self.uut.wpan.ping("fd00:db8:0:0:76b:6a05:3ae9:a61a")
    self.assertEqual(
        response,
        {
            "transmitted_packets": 1,
            "received_packets": 1,
            "packet_loss": 0.0,
            "round_trip_time": {"min": 2, "avg": 2.0, "max": 2},
        },
    )

  def test_scan_energy(self):
    """Verifies scan_energy on success."""
    response = self.uut.wpan.scan_energy
    self.assertEqual(
        response,
        {
            11: -98,
            12: -97,
            13: -98,
            14: -97,
            15: -98,
            16: -87,
            17: -97,
            18: -99,
            19: -99,
            20: -98,
            21: -94,
            22: -75,
            23: -78,
            24: -97,
            25: -100,
            26: -98,
        },
    )

  def test_factory_reset(self):
    """Verifies factory_reset on success."""
    self.use_state_disabled()
    self.uut.wpan.factory_reset()

  def test_wait_for_state(self):
    """Verifies wait_for_state on success."""
    self.uut.wpan.wait_for_state({"leader"})

  def test_dataset_init(self):
    """Verifies dataset_init on success."""
    self.uut.wpan.dataset_init(wpan_ot_base.Dataset.NEW)

  def test_dataset_clear(self):
    """Verifies dataset_clear on success."""
    self.uut.wpan.dataset_clear()

  def test_dataset_commit(self):
    """Verifies dataset_commit on success."""
    self.uut.wpan.dataset_commit(wpan_ot_base.Dataset.ACTIVE)
    self.uut.wpan.dataset_commit(wpan_ot_base.Dataset.PENDING)

  def test_set_dataset_string(self):
    """Verifies set_dataset_string on success."""
    self.uut.wpan.set_dataset_string(wpan_ot_base.Dataset.ACTIVE, "DATA5E6")

  def test_get_mode(self):
    """Verifies get_mode on success."""
    self.assertEqual(self.uut.wpan.get_mode(), "rdn")

  def test_set_mode(self):
    """Verifies set_mode on success."""
    self.uut.wpan.set_mode("rdn")

  def test_ifconfig(self):
    """Verifies ifconfig up/down on success."""
    self.uut.wpan.ifconfig_up()
    self.uut.wpan.ifconfig_down()

  def test_get_ifconfig_state(self):
    """Verifies get_ifconfig_state on success."""
    self.use_ifconfig_up()
    self.assertEqual(self.uut.wpan.get_ifconfig_state(), True)

    self.use_ifconfig_down()
    self.assertEqual(self.uut.wpan.get_ifconfig_state(), False)

  def test_disable_border_routing(self):
    """Verifies disable_border_routing on success."""
    self.uut.wpan.disable_border_routing()

  def test_ipaddr_mleid(self):
    """Verifies ipaddr_mleid on success."""
    self.assertEqual(
        self.uut.wpan.ipaddr_mleid, "fdde:ad00:beef:0:221:163b:894b:865e"
    )

  def test_ipaddr_linklocal(self):
    """Verifies ipaddr_linklocal on success."""
    self.assertEqual(
        self.uut.wpan.ipaddr_linklocal, "fe80:0:0:0:8ce2:7666:2f9a:b8a4"
    )

  def test_ipaddr_rloc(self):
    """Verifies ipaddr_rloc on success."""
    self.assertEqual(self.uut.wpan.ipaddr_rloc, "fdde:ad00:beef:0:0:ff:fe00:0")

  def test_poll_period(self):
    """Verifies poll_period on success."""
    self.assertEqual(self.uut.wpan.poll_period, 236000)

  def test_set_poll_period(self):
    """Verifies set_poll_period on success."""
    self.uut.wpan.set_poll_period(236000)

  def test_get_device_locale(self):
    """Verifies get_device_locale on success."""
    self.assertEqual(self.uut.wpan.get_device_locale(), ["A2"])

  def test_network_data(self):
    """Verifies network_data on success."""
    self.assertEqual(
        self.uut.wpan.network_data,
        {
            "prefixes": [(
                ipaddress.IPv6Network("fdb7:5223:be73:1::/64"),
                "paos",
                "low",
                0x2000,
            )],
            "routes": [
                (
                    ipaddress.IPv6Network("fd11:4df3:4cd3:b39c::/64"),
                    frozenset({wpan_ot_base.RouteFlags.STABLE}),
                    "med",
                    0x2000,
                ),
                (
                    ipaddress.IPv6Network("fd11:4df3:4cd3:b39c::/64"),
                    frozenset(),
                    "med",
                    0x2000,
                ),
            ],
            "services": [
                (44970, b"\x01", b"\x36\x00\x05\x00\x00\x0e\x10", True, 0x2000),
                (
                    44970,
                    b"\x01",
                    b"\x36\x00\x05\x00\x00\x0e\x10",
                    False,
                    0x2000,
                ),
                (
                    44970,
                    b"\x5d",
                    b"\xfd\x58\xd2\x85\xd0\x77\xa3\x90\xc7\x67\x5b\xeb\x38\x0c\x6b\x54\xd1\x1f",
                    True,
                    0x2000,
                ),
            ],
        },
    )

  def test_udp(self):
    """Verifies udp open/bind/send/close on success."""
    self.uut.wpan.udp_open()
    self.uut.wpan.udp_bind(ipaddr="::", port=12345, bind_unspecified=True)
    self.uut.wpan.udp_send(num_bytes=10, ipaddr="fd01::1", port=54321)
    self.uut.wpan.udp_close()

    with self.uut.wpan.open_udp_and_bind(
        ipaddr="::", port=12345, bind_unspecified=True
    ):
      self.uut.wpan.udp_send(num_bytes=10, ipaddr="fd01::1", port=54321)

  def test_set_router_selection_jitter(self):
    """Verifies set_router_election_jitter on success."""
    self.uut.wpan.set_router_selection_jitter(120)

  def test_call_command(self):
    """Verifies send_otcli_command on success and failure."""
    self.use_cli_normal_output()
    self.assertEqual(
        self.uut.wpan.call_command("normal output"), ["line 1", "line 2"]
    )

    self.use_cli_error_output()
    with self.assertRaises(errors.DeviceError):
      self.uut.wpan.call_command("error output")

    self.use_cli_malformed_output()
    with self.assertRaises(errors.DeviceError):
      self.uut.wpan.call_command("malformed output")
