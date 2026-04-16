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

"""Device logs for NRF openthread devices."""
import immutabledict


def generate_command(cmd):
  """Generates otcli command."""
  return cmd + "\n"


def generate_response(cmd, resp):
  """Generates otcli response."""
  return f"{cmd}\n{resp}"


def make_device_responses(raw_responses):
  """Returns device behaviors made from the given shell responses."""
  device_responses = {}
  for entry in raw_responses:
    device_responses.update(
        {
            generate_command(entry["cmd"]): generate_response(
                entry["cmd"], entry["resp"]
            )
        }
    )
  return immutabledict.immutabledict(device_responses)


DEFAULT_BEHAVIOR = make_device_responses([
    {
        "cmd": "ipaddr",
        "resp": (
            "fdde:ad00:beef:0:0:ff:fe00:fc00\n"
            "fdb7:5223:be73:1::1455\n"
            "fdde:ad00:beef:0:0:ff:fe00:b800\n"
            "fdde:ad00:beef:0:a55:2885:3ba1:656e\n"
            "fe80:0:0:0:24cc:59fd:b37:bd8c\n"
            "Done\n"
        ),
        "code": 0,
    },
    {
        "cmd": "ipaddr linklocal",
        "resp": "fe80:0:0:0:8ce2:7666:2f9a:b8a4\nDone\n",
        "code": 0,
    },
    {
        "cmd": "ipaddr mleid",
        "resp": "fdde:ad00:beef:0:221:163b:894b:865e\nDone\n",
        "code": 0,
    },
    {
        "cmd": "srp client host address",
        "resp": "fdae:2909:4851:1:8b5b:6507:a4fd:bea6\nDone\n",
        "code": 0,
    },
    {
        "cmd": "srp client autostart enable",
        "resp": "Done\n",
        "code": 0,
    },
    {
        "cmd": "srp client callback enable",
        "resp": "Done\n",
        "code": 0,
    },
    {
        "cmd": "srp client service",
        "resp": (
            'instance:"locker3", name:"_ipps._udp",'
            ' state:"Adding", port:12349, priority:0, weight:0\nDone\n"'
        ),
        "code": 0,
    },
    {
        "cmd": "ipaddr rloc",
        "resp": "fdde:ad00:beef:0:0:ff:fe00:0\nDone\n",
        "code": 0,
    },
    {
        "cmd": "netdata register",
        "resp": "Done\n",
        "code": 0,
    },
    {
        "cmd": "macfilter addr remove 18B43000003D23F6",
        "resp": "Done\n",
        "code": 0,
    },
    {
        "cmd": "srp client stop",
        "resp": "Done\n",
        "code": 0,
    },
    {
        "cmd": "srp client service clear fake_instance _fake_service._udp",
        "resp": "Done\n",
        "code": 0,
    },
    {
        "cmd": "srp client server",
        "resp": "[fd00:db8:85a3:8d00::1]:12345\nDone\n",
        "code": 0,
    },
    {
        "cmd": "prefix remove fdbd:df6c:b080:1:a196:d468:6a5e:47d5::/64",
        "resp": "Done\n",
        "code": 0,
    },
    {
        "cmd": "prefix add fdb7:5223:be73:1::/64 paosr med",
        "resp": "fdb7:5223:be73:1::/64 paos med f800\nDone\n",
        "code": 0,
    },
    {"cmd": "br enable", "resp": "Done\n", "code": 0},
    {"cmd": "br disable", "resp": "Done\n", "code": 0},
    {"cmd": "channel", "resp": "11\nDone\n", "code": 0},
    {"cmd": "channel supported", "resp": "0x3fff800\nDone\n", "code": 0},
    {"cmd": "channel preferred", "resp": "0x3fff800\nDone\n", "code": 0},
    {"cmd": "region US", "resp": "Done\n", "code": 0},
    {"cmd": "txpower", "resp": "20 dBm\nDone\n", "code": 0},
    {
        "cmd": "counters mac",
        "resp": (
            "TxTotal: 30\n"
            "TxUnicast: 5\n"
            "TxBroadcast: 25\n"
            "TxAckRequested: 5\n"
            "TxAcked: 5\n"
            "TxNoAckRequested: 25\n"
            "TxData: 30\n"
            "TxDataPoll: 0\n"
            "TxBeacon: 0\n"
            "TxBeaconRequest: 0\n"
            "TxOther: 0\n"
            "TxRetry: 0\n"
            "TxErrCca: 0\n"
            "TxErrBusyChannel: 0\n"
            "RxTotal: 2\n"
            "RxUnicast: 1\n"
            "RxBroadcast: 1\n"
            "RxData: 2\n"
            "RxDataPoll: 0\n"
            "RxBeacon: 0\n"
            "RxBeaconRequest: 0\n"
            "RxOther: 0\n"
            "RxAddressFiltered: 0\n"
            "RxDestAddrFiltered: 0\n"
            "RxDuplicated: 0\n"
            "RxErrNoFrame: 0\n"
            "RxErrNoUnknownNeighbor: 0\n"
            "RxErrInvalidSrcAddr: 0\n"
            "RxErrSec: 0\n"
            "RxErrFcs: 0\n"
            "RxErrOther: 0\n"
            "Done\n"
        ),
        "code": 0,
    },
    {
        "cmd": "counters mle",
        "resp": (
            "Role Disabled: 0\n"
            "Role Detached: 1\n"
            "Role Child: 0\n"
            "Role Router: 0\n"
            "Role Leader: 1\n"
            "Attach Attempts: 1\n"
            "Partition Id Changes: 1\n"
            "Better Partition Attach Attempts: 0\n"
            "Parent Changes: 0\n"
            "Time Disabled Milli: 1056\n"
            "Time Detached Milli: 6855\n"
            "Time Child Milli: 0\n"
            "Time Router Milli: 0\n"
            "Time Leader Milli: 1337943\n"
            "Time Tracked Milli: 1345854\n"
            "Done\n"
        ),
        "code": 0,
    },
    {"cmd": "extaddr", "resp": "18b43000003d23f6\nDone\n", "code": 0},
    {"cmd": "state", "resp": "leader\nDone\n", "code": 0},
    {
        "cmd": "networkkey",
        "resp": "00112233445566778899aabbccddeeff\nDone\n",
        "code": 0,
    },
    {"cmd": "networkname", "resp": "PAN-2342\nDone\n", "code": 0},
    {"cmd": "panid", "resp": "0x1234\nDone\n", "code": 0},
    {"cmd": "partitionid", "resp": "0\nDone\n", "code": 0},
    {"cmd": "extpanid", "resp": "dead00beef00cafe\nDone\n", "code": 0},
    {
        "cmd": "child table",
        "resp": (
            "| ID  | RLOC16 | Timeout    | Age        | LQ In | C_VN |R|S|D|N|"
            " Extended MAC    "
            " |\n+-----+--------+------------+------------+-------+------+-+-+-+-+------------------+\n|"
            "   1 | 0xb801 |        240 |         48 |     3 |  253 |1|1|0|0|"
            " ba1fa59be77d24ba |\n\nDone\n"
        ),
        "code": 0,
    },
    {
        "cmd": "version api",
        "resp": "433\nDone\n",
        "code": 0,
    },
    {
        "cmd": "macfilter addr add 18B43000003D23F6",
        "resp": "Done\n",
        "code": 0,
    },
    {
        "cmd": "macfilter addr add 12:34:56:78:90:AB -50",
        "resp": "Done\n",
        "code": 0,
    },
    {
        "cmd": "macfilter addr allowlist",
        "resp": "Done\n",
        "code": 0,
    },
    {
        "cmd": "macfilter addr disable",
        "resp": "Done\n",
        "code": 0,
    },
    {
        "cmd": "neighbor table",
        "resp": (
            "| Role | RLOC16 | Age | Avg RSSI | Last RSSI |R|S|D|N| Extended"
            " MAC    "
            " |\n+------+--------+-----+----------+-----------+-+-+-+-+------------------+\n|"
            "   C  | 0xb801 | 152 |      -20 |       -20 |1|1|0|0|"
            " ba1fa59be77d24ba |\n\nDone\n"
        ),
        "code": 0,
    },
    {"cmd": "netdata show -x", "resp": "08040b02c502\nDone\n", "code": 0},
    {"cmd": "rloc16", "resp": "b800\nDone\n", "code": 0},
    {
        "cmd": "diag factory sysenv get nlwirelessregdom",
        "resp": "A2\nDone\n",
        "code": 0,
    },
    {"cmd": "thread start", "resp": "Done\n", "code": 0},
    {"cmd": "thread stop", "resp": "Done\n", "code": 0},
    {"cmd": "diag start", "resp": "Done\n", "code": 0},
    {"cmd": "diag stop", "resp": "Done\n", "code": 0},
    {
        "cmd": "dataset active",
        "resp": (
            "Active Timestamp: 1\n"
            "Channel: 15\n"
            "Wake-up Channel: 16\n"
            "Channel Mask: 0x07fff800\n"
            "Ext PAN ID: 39758ec8144b07fb\n"
            "Mesh Local Prefix: fdf1:f1ad:d079:7dc0::/64\n"
            "Network Key: f366cec7a446bab978d90d27abe38f23\n"
            "Network Name: OpenThread-5938\n"
            "PAN ID: 0x5938\n"
            "PSKc: 3ca67c969efb0d0c74a4d8ee923b576c\n"
            "Security Policy: 672 onrc 0\n"
            "Done\n"
        ),
        "code": 0,
    },
    {"cmd": "dataset active -x", "resp": "0da6a5e6\nDone\n", "code": 0},
    {"cmd": "dataset init new", "resp": "Done\n", "code": 0},
    {"cmd": "dataset clear", "resp": "Done\n", "code": 0},
    {"cmd": "dataset commit active", "resp": "Done\n", "code": 0},
    {"cmd": "dataset commit pending", "resp": "Done\n", "code": 0},
    {"cmd": "dataset set active DATA5E6", "resp": "Done\n", "code": 0},
    {"cmd": "mode", "resp": "rdn\nDone\n", "code": 0},
    {"cmd": "mode rdn", "resp": "Done\n", "code": 0},
    {"cmd": "ifconfig up", "resp": "Done\n", "code": 0},
    {"cmd": "ifconfig down", "resp": "Done\n", "code": 0},
    {
        "cmd": "scan energy",
        "resp": (
            "| Ch | RSSI |\n"
            "+----+------+\n"
            "| 11 |  -98 |\n"
            "| 12 |  -97 |\n"
            "| 13 |  -98 |\n"
            "| 14 |  -97 |\n"
            "| 15 |  -98 |\n"
            "| 16 |  -87 |\n"
            "| 17 |  -97 |\n"
            "| 18 |  -99 |\n"
            "| 19 |  -99 |\n"
            "| 20 |  -98 |\n"
            "| 21 |  -94 |\n"
            "| 22 |  -75 |\n"
            "| 23 |  -78 |\n"
            "| 24 |  -97 |\n"
            "| 25 | -100 |\n"
            "| 26 |  -98 |\n"
            "Done\n"
        ),
        "code": 0,
    },
    {
        "cmd": "ping fd00:db8:0:0:76b:6a05:3ae9:a61a 60 1 1.0 64 3.0",
        "resp": (
            "16 bytes from fd00:db8:0:0:76b:6a05:3ae9:a61a:"
            " icmp_seq=5 hlim=64 time=0ms\n"
            "1 packets transmitted, 1 packets received. Packet loss = 0.0%."
            " Round-trip min/avg/max = 2/2.0/2 ms.\n"
            "Done\n"
        ),
        "code": 0,
    },
    {"cmd": "pollperiod", "resp": "236000\nDone\n", "code": 0},
    {"cmd": "pollperiod 236000", "resp": "Done\n", "code": 0},
    {"cmd": "csl channel", "resp": "11\nDone\n", "code": 0},
    {"cmd": "csl channel 11", "resp": "Done\n", "code": 0},
    {"cmd": "csl period", "resp": "3125\nDone\n", "code": 0},
    {"cmd": "csl period 3125", "resp": "Done\n", "code": 0},
    {"cmd": "csl timeout", "resp": "100\nDone\n", "code": 0},
    {"cmd": "csl timeout 100", "resp": "Done\n", "code": 0},
    {"cmd": "log level", "resp": "5\nDone\n", "code": 0},
    {"cmd": "log level 5", "resp": "Done\n", "code": 0},
    {
        "cmd": "netdata show",
        "resp": (
            "Prefixes:\n"
            "fdb7:5223:be73:1::/64 paos low 2000\n"
            "Routes:\n"
            "fd11:4df3:4cd3:b39c::/64 s med 2000\n"
            "fd11:4df3:4cd3:b39c::/64 med 2000\n"
            "Services:\n"
            "44970 01 36000500000e10 s 2000\n"
            "44970 01 36000500000e10 2000\n"
            "44970 5d fd58d285d077a390c7675beb380c6b54d11f s 2000\n"
            "Contexts:\n"
            "fd81:dc7c:61cf:1::/64 1 c\n"
            "Done\n"
        ),
        "code": 0,
    },
    {"cmd": "udp open", "resp": "Done\n", "code": 0},
    {"cmd": "udp close", "resp": "Done\n", "code": 0},
    {"cmd": "udp bind -u :: 12345", "resp": "Done\n", "code": 0},
    {"cmd": "udp send fd01::1 54321 -t hello", "resp": "Done\n", "code": 0},
    {"cmd": "factoryreset", "resp": "", "code": 0},
    {"cmd": "reset", "resp": "", "code": 0},
    {
        "cmd": "routerselectionjitter",
        "resp": "120\nDone\n",
        "code": 0,
    },
    {
        "cmd": "routerselectionjitter 120",
        "resp": "Done\n",
        "code": 0,
    },
    {
        "cmd": "br onlinkprefix local",
        "resp": "2600::0:1234:da12::/64\nDone\n",
        "code": 0,
    },
    {
        "cmd": "br omrprefix local",
        "resp": "fdfc:1ff5:1512:5622::/64\nDone\n",
        "code": 0,
    },
    {
        "cmd": "br nat64prefix local",
        "resp": "fd69:342:8482:2:0:0::/96\nDone\n",
        "code": 0,
    },
    {
        "cmd": "dns config 2002::1 53 6000 3 0",
        "resp": "Done\n",
        "code": 0,
    },
    {
        "cmd": "dns config",
        "resp": (
            "Server: [fdd2:0e53:2b87:b93f:50ad:4eea:0450:f1bf]:53\n"
            "ResponseTimeout: 6000 ms\n"
            "MaxTxAttempts: 3\n"
            "RecursionDesired: yes\n"
            "Done\n"
        ),
    },
    {
        "cmd": "dns browse _test._tcp.default.service.arpa",
        "resp": (
            "service1\n"
            "    Port:12345, Priority:0, Weight:0, TTL:4177\n"
            "    Host:host1.default.service.arpa.\n"
            "    HostAddress:2002:0:0:0:0:0:0:1 TTL:4177\n"
            "    TXT:[k1=7631, k2=7632, , k3] TTL:4177\n"
            "\n"
            "Done\n"
        ),
        "code": 0,
    },
    {
        "cmd": "dns resolve host.default.service.arpa",
        "resp": (
            "DNS response for host.default.service.arpa. - "
            "2002:0:0:0:0:0:0:1 TTL:869\n"
            "Done\n"
        ),
        "code": 0,
    },
    {
        "cmd": "dns resolve4 dns.google",
        "resp": (
            "DNS response for dns.google. - "
            "fd69:342:8482:2:0:0:808:808 TTL:869\n"
            "Done\n"
        ),
        "code": 0,
    },
    {
        "cmd": r"dns service service\ 1 _test._tcp.default.service.arpa",
        "resp": (
            "DNS service resolution response for service 1 for service "
            "_test._tcp.default.service.arpa.\n"
            "Port:12345, Priority:0, Weight:0, TTL:326\n"
            "Host:host1.default.service.arpa.\n"
            "HostAddress:2002:0:0:0:0:0:0:1 TTL:326\n"
            "TXT:[k1=7631, k2=7632] TTL:326\n"
            "\n"
            "Done\n"
        ),
        "code": 0,
    },
    {
        "cmd": "srp client host name",
        "resp": "host1\nDone\n",
        "code": 0,
    },
    {
        "cmd": "srp client host name host1",
        "resp": "Done\n",
        "code": 0,
    },
    {
        "cmd": "ipmaddr add ff05::1234:777a:1",
        "resp": "Done\n",
        "code": 0,
    },
    {
        "cmd": "ipmaddr",
        "resp": "ff05:0:0:0:0:1234:777a:1\nDone\n",
        "code": 0,
    },
    {
        "cmd": "srp client host name",
        "resp": "host1\nDone\n",
        "code": 0,
    },
    {
        "cmd": "srp client host name host1",
        "resp": "Done\n",
        "code": 0,
    },
    {
        "cmd": "srp client host address 2002::1",
        "resp": "Done\n",
        "code": 0,
    },
    {
        "cmd": "srp client host remove 1",
        "resp": "Done\n",
        "code": 0,
    },
    {
        "cmd": "srp client host state",
        "resp": "Registered\nDone\n",
        "code": 0,
    },
    {
        "cmd": "srp client service remove fake_service _test._tcp",
        "resp": "Done\n",
        "code": 0,
    },
    {
        "cmd": "srp client keyleaseinterval",
        "resp": "1234567\nDone\n",
        "code": 0,
    },
    {
        "cmd": "srp client host",
        "resp": (
            'name:"host", state:Registered,'
            " addrs:[fd42:64cd:20b:1:1d7c:ce76:e16d:8574]\nDone\n"
        ),
        "code": 0,
    },
    {
        "cmd": "srp client leaseinterval 60",
        "resp": "Done\n",
        "code": 0,
    },
    {
        "cmd": (
            "srp client service add service1 _test._tcp 12345 "
            "0 0 056b313d7631056b323d7632026b33"
        ),
        "resp": "Done\n",
        "code": 0,
    },
    {
        "cmd": "radio stats",
        "resp": (
            "Total Time: 58.953s Tx Time: 0.232640s (0.39%) Rx Time:"
            " 4.226110s (7.16%) Sleep Time: 54.494689s (92.43%) Disabled"
            " Time: 0.000000s (0.00%)\n"
            "Done\n"
        ),
        "code": 0,
    },
    {"cmd": "radio stats clear", "resp": "Done\n", "code": 0},
    {"cmd": "tcp init", "resp": "Done\n", "code": 0},
    {"cmd": "tcp deinit", "resp": "Done\n", "code": 0},
    {"cmd": "tcp listen :: 30000", "resp": "Done\n", "code": 0},
    {
        "cmd": "tcp connect fe80:0:0:0:a8df:580a:860:ffa4 30000",
        "resp": "Done\n",
        "code": 0,
    },
    {"cmd": "tcp benchmark run 73728", "resp": "Done\n", "code": 0},
    {
        "cmd": "tcp benchmark result",
        "resp": (
            "TCP Benchmark Status: Completed\n"
            "TCP Benchmark Complete: Transferred 73728 bytes in 7056 "
            "milliseconds\n"
            "TCP Goodput: 83.592 kb/s\n"
            "Done\n"
        ),
        "code": 0,
    },
    {
        "cmd": "dns compression",
        "resp": "Enabled\nDone\n",
        "code": 0,
    },
    {
        "cmd": "dns compression enable",
        "resp": "Done\n",
        "code": 0,
    },
    {
        "cmd": "dns compression disable",
        "resp": "Done\n",
        "code": 0,
    },
])

NEIGHBOR_TABLE_V2_BEHAVIOR = make_device_responses([
    {
        "cmd": "child table",
        "resp": (
            "| ID  | RLOC16 | Timeout    | Age        | LQ In | C_VN |R|D|N|"
            " Extended MAC    "
            " |\n+-----+--------+------------+------------+-------+------+-+-+-+------------------+\n|"
            "   1 | 0x1c01 |        240 |         17 |     3 |   68 |1|0|0|"
            " 6ae0664fdc316f66 |\nDone\n"
        ),
        "code": 0,
    },
    {
        "cmd": "neighbor table",
        "resp": (
            "| Role | RLOC16 | Age | Avg RSSI | Last RSSI |R|D|N| Extended MAC "
            "    |\n+------+--------+-----+----------+-----------+-+-+-+------------------+\n|"
            "   C  | 0x7801 | 136 |      -29 |       -28 |1|0|0|"
            " 5ea6be302fed82d0 |\n\nDone\n"
        ),
        "code": 0,
    },
    {"cmd": "partitionid", "resp": "1\nDone\n", "code": 0},
])

NEIGHBOR_TABLE_V3_BEHAVIOR = make_device_responses([{
    "cmd": "child table",
    "resp": (
        "| ID  | RLOC16 | Timeout    | Age        | LQ In | C_VN"
        " |R|D|N|Ver|CSL|QMsgCnt| Extended MAC    "
        " |\n+-----+--------+------------+------------+-------+------+-+-+-+---+---+-------+------------------+\n|"
        "   1 | 0xb001 |        240 |         12 |     3 |  168 |1|0|0|  2| 0 |"
        "     0 | 9ab3267c95e504b9 |\n\nDone\n"
    ),
    "code": 0,
}])
