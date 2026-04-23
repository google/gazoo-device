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
"""Wpan related functionality for both linux-ot and nrf-ot.

There are multiple implementation sharing the same CLI syntax:
 * Linux ot-ctl command
 * NRF52840 serial CLI

This module defines the common part of CLIs.
"""

import abc
from collections.abc import Collection, Sequence
import contextlib
import dataclasses
import enum
import ipaddress
import itertools
import re
from typing import Any, Literal, Optional, Tuple, TypedDict, Union

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import wpan_base
from gazoo_device.utility import py311
from gazoo_device.utility import retry


logger = gdm_logger.get_logger()

PROPERTY_NOT_IMPLEMENTED = "Unknown: Error - unimplemented"


class Regexs(enum.Enum):
  """Class for Regexs patterns."""
  SRP_GET_SERVER_SERVICE_PATTERN = r"\[(.*)\]:(\d+)"
  SRP_CLIENT_SERVICE_PATTERN = re.compile(
      r'instance:"(.*)", name:"(.*)", state:(\S+), port:(\d+), priority:(\d+),'
      r" weight:(\d+)"
  )


class Commands(py311.StrEnum):
  """OpenThread CLI commands."""

  BACKBONE_ROUTER_CONFIG = "bbr config"
  BACKBONE_ROUTER_INFO = "bbr"
  BACKBONE_ROUTER_STATE = "bbr state"
  BR_DISABLE = "br disable"
  BR_ENABLE = "br enable"
  BR_NAT64_PREFIX = "br nat64prefix"
  DATASET = "dataset"
  DATASET_CLEAR = "dataset clear"
  DATASET_COMMIT = "dataset commit {}"
  DATASET_INIT = "dataset init"
  DATASET_NETWORKKEY = "dataset networkkey"
  DATASET_SET = "dataset set"
  DIAG_START = "diag start"
  DIAG_STOP = "diag stop"
  DEVICE_LOCALE = "diag factory sysenv get nlwirelessregdom"
  DNS_CLIENT_CONFIG = "dns config"
  DNS_CLIENT_BROWSE_SERVICES = "dns browse"
  DNS_CLIENT_RESOLVE_HOST = "dns resolve"
  DNS_CLIENT_RESOLVE4_HOST = "dns resolve4"
  DNS_CLIENT_RESOLVE_SERVICE = "dns service"
  DNS_CLIENT_COMPRESSION = "dns compression"
  DNS_CLIENT_COMPRESSION_ENABLE = "dns compression enable"
  DNS_CLIENT_COMPRESSION_DISABLE = "dns compression disable"
  FACTORY_RESET = "factoryreset"
  IFCONFIG = "ifconfig"
  IFCONFIG_UP = "ifconfig up"
  IFCONFIG_DOWN = "ifconfig down"
  IPV6_ALL_ADDRESSES = "ipaddr"
  IPV6_LINKLOCAL_ADDRESS = "ipaddr linklocal"
  IPV6_MLEID_ADDRESS = "ipaddr mleid"
  IPV6_RLOC_ADDRESS = "ipaddr rloc"
  LOCAL_OMR_PREFIX = "br omrprefix local"
  LOCAL_ONLINK_PREFIX = "br onlinkprefix local"
  LOCAL_NAT64_PREFIX = "br nat64prefix local"
  MODE = "mode"
  NAT64_COUNTERS = "nat64 counters"
  NAT64_DISABLE = "nat64 disable"
  NAT64_ENABLE = "nat64 enable"
  NAT64_MAPPINGS = "nat64 mappings"
  NAT64_STATE = "nat64 state"
  NCP_CHANNEL = "channel"
  API_VERSION = "version api"
  NCP_COUNTER_TX_ERR_CCA = "counters mac"
  NCP_COUNTER_TX_IP_DROPPED = "counters mac"
  NCP_COUNTER_TX_PKT_ACKED = "counters mac"
  NCP_COUNTER_MLE = "counters mle"
  NCP_MAC_ADDRESS = "extaddr"
  NCP_STATE = "state"
  NETDATA_SHOW = "netdata show"
  NETDATA_REGISTER = "netdata register"
  NETWORK_KEY = "networkkey"
  NETWORK_NAME = "networkname"
  NETWORK_PANID = "panid"
  NETWORK_PARTITION_ID = "partitionid"
  NETWORK_XPANID = "extpanid"
  PREFIX_ADD = "prefix add"
  PREFIX_REMOVE = "prefix remove"
  PING = "ping"
  POLL_PERIOD = "pollperiod"
  ROUTER_SELECTION_JITTER = "routerselectionjitter"
  ROUTER_ELIGIBLE_ENABLE = "routereligible enable"
  ROUTER_ELIGIBLE_DISABLE = "routereligible disable"
  REGION = "region"
  SCAN_ENERGY = "scan energy"
  SRP_CLIENT_ADD_SERVICE = "srp client service add"
  SRP_CLIENT_AUTOSTART = "srp client autostart"
  SRP_CLIENT_CALLBACK = "srp client callback"
  SRP_CLIENT_HOST_ADDRESS = "srp client host address"
  SRP_CLIENT_HOST_NAME = "srp client host name"
  SRP_CLIENT_HOST_STATE = "srp client host state"
  SRP_CLIENT_REMOVE_HOST = "srp client host remove"
  SRP_SERVER_SERVICE = "srp server service"
  THREAD_CHILD_TABLE = "child table"
  THREAD_NEIGHBOR_TABLE = "neighbor table"
  THREAD_NETWORK_DATA = "netdata show -x"
  THREAD_RLOC16 = "rloc16"
  THREAD_START = "thread start"
  THREAD_STOP = "thread stop"
  CSL_CHANNEL = "csl channel"
  CSL_PERIOD = "csl period"
  CSL_TIMEOUT = "csl timeout"
  LOG_LEVEL = "log level"
  UDP_OPEN = "udp open"
  UDP_BIND = "udp bind {interface} {ipaddr} {port}"
  UDP_CLOSE = "udp close"
  UDP_SEND = "udp send {ipaddr} {port} -t {text}"
  RADIO_STATS = "radio stats"
  RADIO_STATS_CLEAR = "radio stats clear"
  TCP_INIT = "tcp init"
  TCP_DEINIT = "tcp deinit"
  TCP_LISTEN = "tcp listen {ipaddr} {port}"
  TCP_CONNECT = "tcp connect {ipaddr} {port}"
  TCP_BENCHMARK_RUN = "tcp benchmark run {size}"
  TCP_BENCHMARK_RESULT = "tcp benchmark result"
  TXPOWER = "txpower"
  MACFILTER_ADDR_DISABLE = "macfilter addr disable"
  SRP_CLIENT_AUTOSTART_ENABLE = "srp client autostart enable"
  SRP_CLIENT_CALLBACK_ENABLE = "srp client callback enable"
  SRP_CLIENT_SERVICE = "srp client service"
  SRP_SERVER_ENABLE = "srp server enable"
  SRP_SERVER_DISABLE = "srp server disable"
  SRP_SERVER_STATE = "srp server state"
  SRP_SERVER_DOMAIN = "srp server domain"
  SRP_SERVER_HOST = "srp server host"
  SRP_SERVER_LEASE = "srp server lease"
  SRP_CLIENT_KEYLEASEINTERVAL = "srp client keyleaseinterval"
  SRP_CLIENT_HOST = "srp client host"
  MACFILTER_ADDR_REMOVE = "macfilter addr remove {addr}"
  SRP_CLIENT_STOP = "srp client stop"
  SRP_CLIENT_SERVICE_CLEAR = "srp client service clear {instance} {service}"
  SRP_CLIENT_SERVER = "srp client server"
  SRP_CLIENT_LEASE_INTERVAL = "srp client leaseinterval"
  TREL_ENABLE = "trel enable"
  TREL_DISABLE = "trel disable"
  RESET = "reset"
  IP_MADDR = "ipmaddr"
  IP_MADDR_ADD = "ipmaddr add {addr}"
  STOP_OTBR_AGENT = "stop otbr-agent"
  START_OTBR_AGENT = "start otbr-agent"
  BACKBONE_ROUTER_ENABLE = "bbr enable"
  BACKBONE_ROUTER_GET_MULTICAST_LISTENERS = "bbr mgmt mlr listener"


class Dataset(py311.StrEnum):
  ACTIVE = "active"
  NEW = "new"
  PENDING = "pending"


StateStr = Literal["disabled", "detached", "child", "router", "leader"]

# Parses "0 packets transmitted, 0 packets received. ...(extra info)"
_PING_STATISTICS_PATTERN = re.compile(
    r"^(?P<transmitted>\d+) packets transmitted,"
    r" (?P<received>\d+) packets received."
    r"(?: Packet loss = (?P<loss>\d+\.\d+)%.)?"
    r"(?: Round-trip min/avg/max = (?P<min>\d+)/(?P<avg>\d+\.\d+)/(?P<max>\d+)"
    r" ms.)?$"
)

"""Parses radio statistics

For example:
  Tx Time: 0.022944s (0.03%)
  Rx Time: 1.482353s (2.18%)
  Sleep Time: 66.251128s (97.77%)
  Disabled Time: 0.000080s (0.00%)
"""
_RADIO_STATISTICS_PATTERN = re.compile(
    r".*Tx Time: (?P<tx_time>\d+\.\d+)s \((?P<tx_time_pct>.+)%\).*Rx Time:"
    r" (?P<rx_time>\d+\.\d+)s"
    r" \((?P<rx_time_pct>.+)%\).*Sleep Time: (?P<sleep_time>\d+\.\d+)s"
    r" \((?P<sleep_time_pct>.+)%\).*Disabled Time:"
    r" (?P<disable_time>\d+\.\d+)s \((?P<disable_time_pct>.+)%\)"
)

"""Parses TCP benchmark result.

For example:
TCP Benchmark Status: Completed
TCP Benchmark Complete: Transferred 73728 bytes in 7056 milliseconds
TCP Goodput: 83.592 kb/s

Or

TCP Benchmark Status: Ongoing
"""
_TCP_BENCHMARK_STATUS_PATTERN = re.compile(
    r"TCP Benchmark Status: (?P<status>\w+)"
)
_TCP_BENCHMARK_RESULT_PATTERN = re.compile(
    r"TCP Benchmark Complete: Transferred (?P<bytes>.*) bytes in"
    r" (?P<time>\d+) milliseconds.*TCP Goodput: (?P<tput>\d+\.\d+) kb/s",
    re.DOTALL,
)


class RouteFlags(py311.StrEnum):
  STABLE = "s"
  NAT64 = "n"


class Nat64StateValue(py311.StrEnum):
  UNKNOWN = "Unknown"
  DISABLED = "Disabled"
  NOT_RUNNING = "NotRunning"
  IDLE = "Idle"
  ACTIVE = "Active"


@dataclasses.dataclass(frozen=True)
class Nat64ComponentStates(TypedDict):
  """OpenThread Nat64 ComponentStates."""

  prefix_manager: Nat64StateValue
  translator: Nat64StateValue


Rloc16 = int
Prefix = tuple[ipaddress.IPv6Network, str, str, Rloc16]
Route = tuple[ipaddress.IPv6Network, frozenset[RouteFlags], str, Rloc16]
Service = tuple[int, bytes, bytes, bool, Rloc16]


class SrpClientHostInfo(TypedDict):
  host: str
  state: str
  addresses: list[ipaddress.IPv6Address]


class NetworkData(TypedDict):
  prefixes: list[Prefix]
  routes: list[Route]
  services: list[Service]


@dataclasses.dataclass(frozen=True, kw_only=True)
class ActiveOperationalDataset:
  active_timestamp: int
  channel: int
  wakeup_channel: int | None = None
  channel_mask: str
  ext_pan_id: str
  mesh_local_prefix: str
  network_key: str
  network_name: str
  pan_id: str
  pskc: str
  security_policy: str


def _parse_dataset_active(
    command_output: list[str]) -> ActiveOperationalDataset:
  """Parses the output of "dataset active" command and returns a dict."""
  data = {}
  for line in command_output:
    raw_key, raw_value = line.split(": ")
    key = raw_key.strip().lower().replace(" ", "_").replace("-", "")
    if key in ("active_timestamp", "channel", "wakeup_channel"):
      data[key] = int(raw_value)
    else:
      data[key] = raw_value
  return ActiveOperationalDataset(**data)


def _validate_hex(hexstr: str) -> None:
  """Validates that the input string in a hex string.

  Args:
    hexstr: the input string to be validated.

  Raises:
    ValueError: If the input string is not a hex string.
  """
  if len(hexstr) % 2 != 0:
    raise ValueError(f"the length of input string is not even: {hexstr}")

  for i in range(0, len(hexstr), 2):
    int(hexstr[i : i + 2], 16)


def _hex_to_bytes(hexstr: str) -> bytes:
  r"""Converts the input hex string into bytes.

  Args:
    hexstr: the input string to be converted.

  Returns:
    The result bytes.

  Example:
    Converts "36000500000e10" to b"\x36\x00\x05\x00\x00\x0e\x10"
  """
  _validate_hex(hexstr)
  return bytes(int(hexstr[i : i + 2], 16) for i in range(0, len(hexstr), 2))


def _parse_prefix(text: str) -> Prefix:
  """Parses the input text into a Thread prefix.

  Args:
    text: the input text to be parsed.

  Returns:
    The result Thread prefix

  Example:
    Parses "fdb7:5223:be73:1::/64 paos low 2000" to
    (ipaddress.IPv6Network("fdb7:5223:be73:1::/64"), "paos", "low", 0x2000)
  """
  prefix, flags, prf, rloc16 = text.removeprefix("- ").split()[:4]
  return (ipaddress.IPv6Network(prefix), flags, prf, int(rloc16, 16))


def _parse_route(text: str) -> Route:
  """Parses the input text into a Thread route.

  Args:
    text: the input text to be parsed.

  Returns:
    The result Thread route

  Example:
    Parses "fd11:4df3:4cd3:b39c::/64 s med 2000" to
    (ipaddress.IPv6Network("fd11:4df3:4cd3:b39c::/64"), True, "med", 0x2000)
  """
  line = text.split()
  if len(line) == 4:
    prefix, flag_text, prf, rloc16 = line
    # Use list to convert RouteFlags to flags list due to bug b/265366266
    flags = frozenset({flag for flag in list(RouteFlags) if flag in flag_text})
  else:
    prefix, prf, rloc16 = line
    flags: frozenset[RouteFlags] = frozenset()

  return (ipaddress.IPv6Network(prefix), flags, prf, int(rloc16, 16))


def _parse_service(text: str) -> Service:
  r"""Parses the input text into a Thread service.

  Args:
    text: the input text to be parsed.

  Returns:
    The result Thread service

  Example:
    Parses "44970 01 36000500000e10 s 2000" to
    (44970, b"\x01", b"\x36\x00\x05\x00\x00\x0e\x10", True, 0x2000)
  """
  line = text.split()

  enterprise_number, service_data, server_data = line[:3]
  if line[3] == "s":  # The third column is an optional "s" of stable flag.
    stable, rloc16 = True, line[4]
  else:
    stable, rloc16 = False, line[3]

  enterprise_number = int(enterprise_number)
  service_data = _hex_to_bytes(service_data)
  server_data = _hex_to_bytes(server_data)
  rloc16 = int(rloc16, 16)

  return (enterprise_number, service_data, server_data, stable, rloc16)

TxtDict = dict[str, Union[bytes, bool]]


@dataclasses.dataclass
class SrpService:
  """Details of an SRP server service."""

  instance_name: str
  deleted: bool = False
  subtypes: tuple[str, ...] = ()
  port: int = 0
  priority: int = 0
  weight: int = 0
  ttl: int = 0
  lease: int = 0
  key_lease: int = 0
  txt: TxtDict = dataclasses.field(default_factory=dict)
  host: str = ""
  addresses: tuple[ipaddress.IPv6Address, ...] = ()


@dataclasses.dataclass
class SrpClientService:
  """Details of an SRP client service."""

  instance: str
  service: str
  port: int
  state: str | None = None
  priority: int | None = None
  weight: int | None = None
  txt_records: list[str] | None = None


@dataclasses.dataclass
class ResolvedService:
  """Details of a service resolved via DNS query."""

  instance: str
  service: str
  port: int
  priority: int
  weight: int
  host: str
  address: ipaddress.IPv6Address
  txt: TxtDict
  srv_ttl: int
  txt_ttl: int
  aaaa_ttl: int


@dataclasses.dataclass
class ResolvedHost:
  """Details of a host resolved via DNS query."""

  address: ipaddress.IPv6Address
  ttl: int


def parse_srp_server_service_txt(text: str) -> TxtDict:
  """Parses the input text into a TXT record as dictionary.

  Args:
    text: The input text to be parsed.

  Returns:
    The TXT record as a dictionary.

  Example:
    "[key1=76616c7565,key2=76616c7565]" is parsed as
    {"key1": b"value", "key2": b"value"}.

  Raises:
    ValueError: The input text is not a valid TXT record.
  """
  if not text.startswith("[") or not text.endswith("]"):
    raise ValueError(f"Malformed TXT string {text}")

  txt_dict: TxtDict = {}

  for entry in text[1:-1].split(", "):
    if not entry:
      continue
    if "=" in entry:
      k, v = entry.split("=")
      # Converts the hex string to bytes
      txt_dict[k] = bytes(int(v[i : i + 2], 16) for i in range(0, len(v), 2))
    else:
      txt_dict[entry] = True

  return txt_dict


def parse_srp_server_services(
    text: list[str],
) -> list[SrpService]:
  """Parses the input text into a service registered on an SRP server.

  Args:
    text: the input text to be parsed.

  Returns:
    The result service

  Example:
    test1._test._udp.default.service.arpa.
      deleted: false
      subtypes: (null)
      port: 12345
      priority: 0
      weight: 0
      ttl: 7200
      lease: 7200
      key-lease: 680400
      TXT: [key=76616c7565]
      host: host1.default.service.arpa.
      addresses: [2201:0:0:0:0:0:0:1]
  is parsed as
    {'instance': 'test1._test._udp.default.service.arpa.', 'deleted': False,
    'subtypes': [], 'port': 12345, 'priority': 0, 'weight': 0, 'ttl': 7200,
    'lease': 7200, 'key-lease': 680400, 'txt': {'key': b'value'}, 'host':
    'host1.default.service.arpa.', 'addresses': [IPv6Address('2201::1')]}

  Raises:
    ValueError: If the input text doesn't represent a valid SRP service.
  """
  result: list[SrpService] = []
  info: SrpService = SrpService("")
  for line in text:
    if not line.startswith(" "):
      info = SrpService(instance_name=line)
      result.append(info)
    else:
      k, v = line.strip().split(": ")
      if k == "deleted":
        if v not in ("true", "false"):
          raise ValueError(
              f"Malformed srp server service return value {result}"
          )
        info.deleted = v == "true"
      elif k == "addresses":
        if not v.startswith("[") or not v.endswith("]"):
          raise ValueError(
              f"Malformed srp server service return value {result}"
          )
        v = v[1:-1]
        info.addresses = tuple(map(ipaddress.IPv6Address, v.split(", ")))
      elif k == "subtypes":
        info.subtypes = () if v == "(null)" else tuple(v.split(","))
      elif k in ("port", "weight", "priority", "ttl", "lease", "key-lease"):
        setattr(info, k.replace("-", "_"), int(v))
      elif k == "host":
        info.host = v
      elif k == "TXT":
        info.txt = parse_srp_server_service_txt(v)
      else:
        raise ValueError(f"Malformed srp server service return value {result}")

  return result


@dataclasses.dataclass(frozen=True)
class DnsConfig:
  """DNS config on the device."""

  server: tuple[ipaddress.IPv6Address, int]
  response_timeout_ms: int
  max_tx_attempts: int
  recursion_desired: bool


def parse_dns_config(text: Sequence[str]) -> DnsConfig:
  """Parses the input text into the dns config on the device.

  Args:
    text: the input text to be parsed.

  Returns:
    The parsed dns config.

  Example:
    Server: [fdd2:0e53:2b87:b93f:50ad:4eea:0450:f1bf]:53
    ResponseTimeout: 6000 ms
    MaxTxAttempts: 3
    RecursionDesired: yes
  is parsed as
    {"server": (IPv6Address('fdd2:0e53:2b87:b93f:50ad:4eea:0450:f1bf'), 53),
     "response_timeout_ms": 6000,
     "max_tx_attempts": 3,
     "recursion_desired": True}

  Raises:
    ValueError: If the input text doesn't represent a valid DNS config.
  """
  res = {}
  for line in text:
    k, v = line.strip().split(": ")
    if k == "Server":
      match_result = re.fullmatch(r"\[([0-9a-f:]+)\]:(\d+)", v)
      if match_result is None:
        raise ValueError(f"{v} is not a valid DNS server.")
      address, port = match_result[1], match_result[2]
      res["server"] = (ipaddress.IPv6Address(address), int(port))
    elif k == "ResponseTimeout":
      res["response_timeout_ms"] = int(v[:-3])
    elif k == "MaxTxAttempts":
      res["max_tx_attempts"] = int(v)
    elif k == "RecursionDesired":
      res["recursion_desired"] = v == "yes"
  return DnsConfig(**res)


def txt_to_hex(txt: Optional[dict[str, Union[str, bytes, bool]]]) -> str:
  """Converts the TXT record to hex string."""
  txt_bin = b""
  if txt is not None:
    for k, v in txt.items():
      if "=" in k:
        raise ValueError("TXT key must not contain `=`")

      if isinstance(v, str):
        entry = f"{k}={v}".encode("utf8")
      elif isinstance(v, bytes):
        entry = f"{k}=".encode("utf8") + v
      elif isinstance(v, bool) and v:
        entry = k.encode("utf8")
      else:
        raise ValueError(f"TXT val must be str or bytes or True. Found: {v}")

      if len(entry) > 255:
        raise ValueError(f"TXT entry is too long: {entry}")

      txt_bin += bytes([len(entry)])
      txt_bin += entry

  return "".join(f"{b:02x}" for b in txt_bin)


def escape_escapable(s: str) -> str:
  """Escape CLI escapable characters in the given string."""
  escapable_chars = "\\ \t\r\n"
  for char in escapable_chars:
    s = s.replace(char, f"\\{char}")
  return s


@dataclasses.dataclass(frozen=True)
class RadioStats:
  """Data class containing the data of radio statistics."""

  tx_time: float
  tx_time_pct: float
  rx_time: float
  rx_time_pct: float
  sleep_time: float
  sleep_time_pct: float
  disabled_time: float
  disabled_time_pct: float


def parse_radio_stats(result: str) -> RadioStats:
  """Parses radio stats."""
  match = _RADIO_STATISTICS_PATTERN.search(result)
  if match is not None:
    radio_stats_group_dict = match.groupdict()
  else:
    raise ValueError(f"Malformed radio stats {result}")
  return RadioStats(
      tx_time=float(radio_stats_group_dict["tx_time"]),
      tx_time_pct=float(radio_stats_group_dict["tx_time_pct"]),
      rx_time=float(radio_stats_group_dict["rx_time"]),
      rx_time_pct=float(radio_stats_group_dict["rx_time_pct"]),
      sleep_time=float(radio_stats_group_dict["sleep_time"]),
      sleep_time_pct=float(radio_stats_group_dict["sleep_time_pct"]),
      disabled_time=float(radio_stats_group_dict["disable_time"]),
      disabled_time_pct=float(radio_stats_group_dict["disable_time_pct"]),
  )

TcpBenchmarkStatus = Literal["Untested", "Ongoing", "Completed"]


@dataclasses.dataclass(frozen=True)
class TcpBenchmarkResult:
  """Data class containing the result of TCP Benchmark."""

  status: TcpBenchmarkStatus
  bytes_transferred: Optional[int]
  time_used_ms: Optional[int]
  throughput_kbps: Optional[float]


def parse_tcp_benchmark_result(result: str) -> TcpBenchmarkResult:
  """Parses the result of TCP Benchmark.

  Args:
    result: The result to parse.

  Returns:
    An object of TcpBenchmarkResult

  Raises:
    ValueError: The result has unexpected format or value.
  """
  match = _TCP_BENCHMARK_STATUS_PATTERN.search(result)
  if match is None:
    raise ValueError(
        f"Malformed TCP Benchmark result {result}, cannot identify Status"
    )

  status = match.groupdict()["status"]
  if status == "Completed":
    match = _TCP_BENCHMARK_RESULT_PATTERN.search(result)
    if match is None:
      raise ValueError(
          f"Malformed TCP Benchmark result {result}, incorrect result format"
      )
    match_group_dict = match.groupdict()
    return TcpBenchmarkResult(
        status=status,
        bytes_transferred=int(match_group_dict["bytes"]),
        time_used_ms=int(match_group_dict["time"]),
        throughput_kbps=float(match_group_dict["tput"]),
    )
  elif status in ["Untested", "Ongoing"]:
    return TcpBenchmarkResult(
        status=status,
        bytes_transferred=None,
        time_used_ms=None,
        throughput_kbps=None,
    )
  else:
    raise ValueError(
        f"Malformed TCP Benchmark result {result}, unexpected status"
    )


class WpanOtBase(wpan_base.WpanBase, abc.ABC):
  """Class for interacting with OpenThread CLI command and getting props."""

  @classmethod
  def get_capability_name(cls) -> str:
    """Returns the name under which capability is accessible in device class."""
    # Use parent interface's capability name (wpan) for derived flavors rather
    # than the capability name derived from this interface (wpan_ot).
    # Refer to the parent class explicitly. super() doesn't work here.
    return wpan_base.WpanBase.get_capability_name()

  @abc.abstractmethod
  def call_command(
      self,
      command: str,
      timeout: float | None = None,
      pattern_list: list[str] | None = None,
  ) -> list[str]:
    """Calls an OpenThread CLI command and returns the response."""

  @abc.abstractmethod
  def factory_reset(self) -> None:
    """Factory resets the Thread devices."""

  @decorators.DynamicProperty
  def ncp_channel(self) -> int:
    """Gets the ncp channel."""
    return int(self.call_command(Commands.NCP_CHANNEL.value)[0])

  @decorators.DynamicProperty
  def ncp_channel_preferred(self) -> str:
    """Gets the preferred NCP channel."""
    return self.call_command(f"{Commands.NCP_CHANNEL.value} preferred")[0]

  @decorators.DynamicProperty
  def ncp_channel_supported(self) -> str:
    """Gets the supported NCP channel."""
    return self.call_command(f"{Commands.NCP_CHANNEL.value} supported")[0]

  @decorators.DynamicProperty
  def network_is_commissioned(self) -> bool:
    """Returns whether the device is connected to a Thread network."""
    role = self.call_command(Commands.NCP_STATE.value)[0]
    return role in {"leader", "router", "child"}

  @decorators.DynamicProperty
  def ncp_mac_address(self) -> str:
    """Gets the ncp mac address."""
    return self.call_command(Commands.NCP_MAC_ADDRESS.value)[0].upper()

  @decorators.DynamicProperty
  def network_key(self) -> str:
    """Gets the Thread network master key in hex format."""
    return self.call_command(Commands.NETWORK_KEY.value)[0].upper()

  @decorators.DynamicProperty
  def network_name(self) -> str:
    """Gets the Thread network name."""
    return self.call_command(Commands.NETWORK_NAME.value)[0]

  @decorators.DynamicProperty
  def network_node_type(self) -> StateStr:
    """Gets the current node type."""
    return self.call_command(Commands.NCP_STATE.value)[0]

  @decorators.DynamicProperty
  def network_panid(self) -> str:
    """Gets the current node panid in hex format."""
    panid = int(self.call_command(Commands.NETWORK_PANID.value)[0], 16)
    return "0x{:04X}".format(panid)

  @decorators.DynamicProperty
  def network_partition_id(self) -> str:
    """Gets the Thread network partition ID.

    Returns:
      string: decimal string representation of current partition id

    Example output:
      $ ot-ctl partitionid
      577020633
      Done
    """
    return self.call_command(Commands.NETWORK_PARTITION_ID.value)[0]

  @decorators.DynamicProperty
  def ncp_rssi(self) -> str:
    # TODO(gdm-authors)
    return PROPERTY_NOT_IMPLEMENTED

  @decorators.DynamicProperty
  def ncp_state(self) -> StateStr:
    """Gets the current node state."""
    return self.call_command(Commands.NCP_STATE.value)[0]

  @decorators.DynamicProperty
  def network_xpanid(self) -> str:
    """Gets the extended PAN id in hex format."""
    return "0x" + self.call_command(Commands.NETWORK_XPANID.value)[0].upper()

  @decorators.DynamicProperty
  def router_selection_jitter(self) -> int:
    """Gets the router selection jitter duration in seconds."""
    return int(self.call_command(Commands.ROUTER_SELECTION_JITTER.value)[0])

  @decorators.CapabilityLogDecorator(logger)
  def set_router_selection_jitter(self, router_selection_jitter: int) -> None:
    """Sets the router selection jitter duration in seconds."""
    self.call_command(
        f"{Commands.ROUTER_SELECTION_JITTER.value} {router_selection_jitter}"
    )

  @decorators.CapabilityLogDecorator(logger)
  def router_eligible_enable(self) -> None:
    """Enables router eligible."""
    self.call_command(Commands.ROUTER_ELIGIBLE_ENABLE.value)

  @decorators.CapabilityLogDecorator(logger)
  def router_eligible_disable(self) -> None:
    """Disables router eligible."""
    self.call_command(Commands.ROUTER_ELIGIBLE_DISABLE.value)

  @decorators.DynamicProperty
  def region(self) -> str:
    """Gets the region."""
    return self.call_command(Commands.REGION.value)[0].upper()

  @decorators.CapabilityLogDecorator(logger)
  def set_region(self, region: str) -> None:
    """Sets the region."""
    self.call_command(f"{Commands.REGION.value} {region}")

  @decorators.DynamicProperty
  def thread_leader_address(self) -> str:
    # TODO(gdm-authors)
    return PROPERTY_NOT_IMPLEMENTED

  @decorators.DynamicProperty
  def thread_leader_local_weight(self) -> str:
    # TODO(gdm-authors)
    return PROPERTY_NOT_IMPLEMENTED

  @decorators.DynamicProperty
  def thread_leader_network_data(self) -> str:
    # TODO(gdm-authors)
    return PROPERTY_NOT_IMPLEMENTED

  @decorators.DynamicProperty
  def thread_leader_router_id(self) -> str:
    # TODO(gdm-authors)
    return PROPERTY_NOT_IMPLEMENTED

  @decorators.DynamicProperty
  def thread_leader_stable_network_data(self) -> str:
    # TODO(gdm-authors)
    return PROPERTY_NOT_IMPLEMENTED

  @decorators.DynamicProperty
  def thread_leader_weight(self) -> str:
    # TODO(gdm-authors)
    return PROPERTY_NOT_IMPLEMENTED

  @decorators.DynamicProperty
  def thread_neighbor_table(self) -> list[dict[str, str]]:
    # TODO(gdm-authors) Add missing entries
    """Returns thread_neighbor table as list.

    Note:
      (1) Thread neighbor table output format version 1:
      > neighbor table
      | Role | RLOC16 | Age | Avg RSSI | Last RSSI |R|S|D|N| Extended MAC
      |
      +------+--------+-----+----------+-----------+-+-+-+-+------------------+
      |   C  | 0x6801 |   9 |      -20 |       -20 |1|1|1|1|
      d613f05fcacd04b8 |

      Done
      (2) Thread neighbor table output format version 2 (b/172644856):
      > neighbor table
      | Role | RLOC16 | Age | Avg RSSI | Last RSSI |R|D|N| Extended MAC
      |
      +------+--------+-----+----------+-----------+-+-+-+------------------+
      |   C  | 0x7801 | 136 |      -29 |       -28 |1|0|0| 5ea6be302fed82d0
      |

      Done
    """
    neighbor_table_lines = self.call_command(
        Commands.THREAD_NEIGHBOR_TABLE.value
    )
    headers = [header.strip() for header in neighbor_table_lines[0].split("|")]
    neighbor_list = []

    for row in neighbor_table_lines[2:]:
      # The last line is an empty line.
      if not row:
        break

      values = [value.strip() for value in row.split("|")]

      neighbor_entry = {
          "RLOC16": PROPERTY_NOT_IMPLEMENTED,
          "FullNetData": PROPERTY_NOT_IMPLEMENTED,
          "LinkFC": PROPERTY_NOT_IMPLEMENTED,
          "LQIn": PROPERTY_NOT_IMPLEMENTED,
          "Age": PROPERTY_NOT_IMPLEMENTED,
          "RxOnIdle": PROPERTY_NOT_IMPLEMENTED,
          "Id": PROPERTY_NOT_IMPLEMENTED,
          "FTD": PROPERTY_NOT_IMPLEMENTED,
          "LastRssi": PROPERTY_NOT_IMPLEMENTED,
          "MleFC": PROPERTY_NOT_IMPLEMENTED,
          "SecDataReq": PROPERTY_NOT_IMPLEMENTED,
          "AveRssi": PROPERTY_NOT_IMPLEMENTED,
          "IsChild": PROPERTY_NOT_IMPLEMENTED,
      }

      for key, value in zip(headers, values):
        if key == "Role":
          neighbor_entry["IsChild"] = "yes" if value == "C" else "no"
        elif key == "RLOC16":
          neighbor_entry["RLOC16"] = "{:04x}".format(
              int(value, 16)
          )  # Remove the 0x
        elif key == "Age":
          neighbor_entry["Age"] = value
        elif key == "Avg RSSI":
          neighbor_entry["AveRssi"] = value
        elif key == "Last RSSI":
          neighbor_entry["LastRssi"] = value
        elif key == "R":
          neighbor_entry["RxOnIdle"] = "yes" if value == "1" else "no"
        elif key == "S":
          neighbor_entry["SecDataReq"] = "yes" if value == "1" else "no"
        elif key == "D":
          neighbor_entry["FTD"] = "yes" if value == "1" else "no"
        elif key == "N":
          neighbor_entry["FullNetData"] = "yes" if value == "1" else "no"
        elif key == "Extended MAC":
          neighbor_entry["Id"] = value.upper()

      neighbor_list.append(neighbor_entry)

    return neighbor_list

  @decorators.DynamicProperty
  def thread_network_data(self) -> str:
    """Returns the network data in the hex format.

    Example output:
      # ot-ctl netdata show -x
      08040b024d5c0b0e8001010d090c0068000500000e1003140040fd49f7e80076000105040c00f10007021140030f0040fd65aa133519275f01030c00000b1981015d0d140c00fdd2cb0d665f000023a57c9f08424339d11f
      Done
    """
    response = self.call_command(Commands.THREAD_NETWORK_DATA.value)
    if response:
      return response[0]
    else:
      return ""

  @decorators.DynamicProperty
  def thread_rloc16(self) -> str:
    """Gets the node's routing locator in hex format."""
    return "0x" + self.call_command(Commands.THREAD_RLOC16.value)[0].upper()

  @decorators.DynamicProperty
  def thread_router_id(self) -> str:
    """Gets the node's router id in hex format."""
    rloc = int(self.thread_rloc16, 16)
    # rloc's uppper byte is router id
    return "0x{:02X}".format(rloc >> 8)

  @decorators.DynamicProperty
  def thread_stable_network_data(self) -> str:
    # TODO(gdm-authors)
    return PROPERTY_NOT_IMPLEMENTED

  @decorators.DynamicProperty
  def thread_stable_network_data_version(self) -> str:
    # TODO(gdm-authors)
    return PROPERTY_NOT_IMPLEMENTED

  @decorators.DynamicProperty
  def ncp_counter_tx_err_cca(self) -> int:
    """Gets the number of sent packets that failed with cca error."""
    counters = self.call_command(Commands.NCP_COUNTER_TX_ERR_CCA.value)
    acked = next(c for c in counters if c.find("TxErrCca") >= 0)
    return int(acked.split()[-1])

  @decorators.DynamicProperty
  def ncp_counter_tx_ip_dropped(self) -> int:
    """Gets the number of dropped sent packets."""
    counters = self.call_command(Commands.NCP_COUNTER_TX_IP_DROPPED.value)
    acked = next(c for c in counters if c.find("TxErrBusyChannel") >= 0)
    return int(acked.split()[-1])

  @decorators.DynamicProperty
  def ncp_counter_tx_pkt_acked(self) -> int:
    """Gets the number of acknowledged sent packets."""
    counters = self.call_command(Commands.NCP_COUNTER_TX_PKT_ACKED.value)
    acked = next(c for c in counters if c.find("TxAcked") >= 0)
    return int(acked.split()[-1])

  @decorators.DynamicProperty
  def ncp_counter_attach_attempts(self) -> int:
    """Gets the number of attach attempts."""
    counters = self.call_command(Commands.NCP_COUNTER_MLE.value)
    attach_attempts = next(
        c for c in counters if "Attach Attempts" in c
    )
    return int(attach_attempts.split()[-1])

  @decorators.DynamicProperty
  def thread_child_table(self) -> list[dict[str, str]]:
    """Returns thread_child_table as list of lines.

    Note:
      (1) Thread child table format version 1:

      > child table
      | ID  | RLOC16 | Timeout    | Age        | LQ In | C_VN |R|S|D|N|
      Extended MAC     |
      +-----+--------+------------+------------+-------+------+-+-+-+-+------------------+
      |   1 | 0x5c01 |        240 |         11 |     3 |  127 |1|1|0|0|
      521ae942170d88ed |

      Done

      (2) Thread child table format version 2 (b/172644856):
      > child table
      | ID  | RLOC16 | Timeout    | Age        | LQ In | C_VN |R|D|N|
      Extended MAC     |
      +-----+--------+------------+------------+-------+------+-+-+-+------------------+
      |   1 | 0x1c01 |        240 |         17 |     3 |   68 |1|0|0|
      6ae0664fdc316f66 |

      Done

      (3) Thread child table format version 3 (b/172644856):
      > child table
      | ID  | RLOC16 | Timeout    | Age        | LQ In | C_VN
      |R|D|N|Ver|CSL|QMsgCnt|
      +-----+--------+------------+------------+-------+------+-+-+-+---+---+-------+
      |   1 | 0xb001 |        240 |         12 |     3 |  168 |1|0|0|  2| 0
      |     0 |

      Done

       Extended MAC     |
      ------------------+
       9ab3267c95e504b9 |
    """
    # TODO(gdm-authors) Add missing entries
    child_table_lines = self.call_command(Commands.THREAD_CHILD_TABLE.value)
    headers = [header.strip() for header in child_table_lines[0].split("|")]
    children_list = []

    for row in child_table_lines[2:]:
      # The last line is an empty line.
      if not row:
        break

      values = [value.strip() for value in row.split("|")]

      child_entry = {
          "RLOC16": PROPERTY_NOT_IMPLEMENTED,
          "FullNetData": PROPERTY_NOT_IMPLEMENTED,
          "NetDataVer": PROPERTY_NOT_IMPLEMENTED,
          "LQIn": PROPERTY_NOT_IMPLEMENTED,
          "Age": PROPERTY_NOT_IMPLEMENTED,
          "RxOnIdle": PROPERTY_NOT_IMPLEMENTED,
          "FTD": PROPERTY_NOT_IMPLEMENTED,
          "LastRssi": PROPERTY_NOT_IMPLEMENTED,
          "Timeout": PROPERTY_NOT_IMPLEMENTED,
          "SecDataReq": PROPERTY_NOT_IMPLEMENTED,
          "AveRssi": PROPERTY_NOT_IMPLEMENTED,
          "Id": PROPERTY_NOT_IMPLEMENTED,
      }

      for key, value in zip(headers, values):
        if key == "RLOC16":
          child_entry["RLOC16"] = "{:04x}".format(
              int(value, 16)
          )  # Remove the 0x
        elif key == "Timeout":
          child_entry["Timeout"] = value
        elif key == "Age":
          child_entry["Age"] = value
        elif key == "LQ In":
          child_entry["LQIn"] = value
        elif key == "C_VN":
          child_entry["NetDataVer"] = value
        elif key == "R":
          child_entry["RxOnIdle"] = "yes" if value == "1" else "no"
        elif key == "S":
          child_entry["SecDataReq"] = "yes" if value == "1" else "no"
        elif key == "D":
          child_entry["FTD"] = "yes" if value == "1" else "no"
        elif key == "N":
          child_entry["FullNetData"] = "yes" if value == "1" else "no"
        elif key == "Extended MAC":
          child_entry["Id"] = value.upper()

      children_list.append(child_entry)

    return children_list

  @decorators.DynamicProperty
  def ipv6_all_addresses(self) -> list[str]:
    """Returns ipv6:AllAddresses as list of lines."""
    return self.call_command(Commands.IPV6_ALL_ADDRESSES.value)

  @decorators.DynamicProperty
  def scan_energy(self) -> dict[int, int]:
    """Returns a dict from channel to RSSI.

    Note:
      % ot-ctl scan energy
      returns a table like

      | Ch | RSSI |
      +----+------+
      | 11 |  -42 |
      | 12 |  -84 |
      | 13 |  -86 |
      | 14 |  -89 |

      Will be converted to:

      {
        11: -42,
        12: -84,
        13: -86,
        14: -89
      }
    """
    lines = self.call_command(Commands.SCAN_ENERGY.value)

    def line_to_tuple(line: str):
      data = line.split("|")
      return int(data[1]), int(data[2])

    return dict(map(line_to_tuple, lines[2:]))

  @decorators.CapabilityLogDecorator(logger)
  def dataset_init(self, dataset: Dataset) -> None:
    """Initializes operational dataset."""
    self.call_command(f"{Commands.DATASET_INIT.value} {dataset.value}")

  @decorators.CapabilityLogDecorator(logger)
  def dataset_clear(self) -> None:
    """Clears operational dataset buffer."""
    self.call_command(Commands.DATASET_CLEAR.value)

  @decorators.CapabilityLogDecorator(logger)
  def dataset_commit(self, dataset: Dataset) -> None:
    """Commits operational dataset."""
    if dataset in (Dataset.ACTIVE, Dataset.PENDING):
      self.call_command(Commands.DATASET_COMMIT.value.format(dataset.value))
    else:
      raise ValueError(f"{self._device_name} invalid dataset: {dataset}.")

  def get_mode(self) -> str:
    """Gets the Thread Device Mode value.

    Returns:
      A string containing combination of following characters.
        "-": no flags set.
        "r": rx-on-when-idle.
        "d": Full Thread Device.
        "n": Full Network Data.
    """
    return self.call_command(Commands.MODE.value)[0]

  @decorators.CapabilityLogDecorator(logger)
  def set_mode(self, mode: str) -> None:
    """Sets the Thread Device Mode value.

    Args:
      mode: combination of following characters. "-": no flags set. "r":
        rx-on-when-idle. "d": Full Thread Device. "n": Full Network Data.
    """
    self.call_command(f"{Commands.MODE.value} {mode}")

  @decorators.CapabilityLogDecorator(logger)
  def ifconfig_up(self) -> None:
    """Bring up the IPv6 interface."""
    self.call_command(Commands.IFCONFIG_UP.value)

  @decorators.CapabilityLogDecorator(logger)
  def ifconfig_down(self) -> None:
    """Bring down the IPv6 interface."""
    self.call_command(Commands.IFCONFIG_DOWN.value)

  def get_ifconfig_state(self) -> bool:
    """Gets the status of the IPv6 interface."""
    result = self.call_command(Commands.IFCONFIG.value)[-1]
    if result not in ("up", "down"):
      raise errors.DeviceError(
          f"{self._device_name} Malformed ifconfig return value {result}"
      )

    return result == "up"

  @decorators.CapabilityLogDecorator(logger)
  def add_prefix(
      self, prefix: str, flags: str = "paosr", prf: str = "med") -> None:
    """Add a valid prefix to the Network Data."""
    self.call_command(f"{Commands.PREFIX_ADD.value} {prefix} {flags} {prf}")

  @decorators.CapabilityLogDecorator(logger)
  def remove_prefix(self, prefix: str):
    """Removes a prefix in the Network Data."""
    self.call_command(f"{Commands.PREFIX_REMOVE.value} {prefix}")

  @decorators.CapabilityLogDecorator(logger)
  def api_version(self) -> int:
    """Returns the thread version of the device."""
    return int(self.call_command(Commands.API_VERSION.value)[0])

  @decorators.CapabilityLogDecorator(logger)
  def detect_allowlist_cmd(self) -> str:
    """Returns the allowlist command based on the API versions."""
    return "allowlist" if self.api_version() >= 28 else ""

  @decorators.CapabilityLogDecorator(logger)
  def enable_allowlist(self) -> None:
    """Enables the allowlist."""
    self.call_command(f"macfilter addr {self.detect_allowlist_cmd()}")

  @decorators.CapabilityLogDecorator(logger)
  def add_allowlist(self, addr: str, rssi: Optional[int] = None) -> None:
    """Add MAC address into the allowlist of a respective device.

    Args:
      addr: MAC address of device.
      rssi: RSSI of the device.
    """
    cmd = f"macfilter addr add {addr}"
    if rssi is not None:
      cmd += f" {rssi}"
    self.call_command(cmd)

  @decorators.CapabilityLogDecorator(logger)
  def remove_mac_from_allowlist(self, mac_address: str) -> None:
    """Removes MAC address from the allowlist of a respective device.

    Args:
      mac_address: MAC address of device.
    """
    self.call_command(
        Commands.MACFILTER_ADDR_REMOVE.value.format(addr=mac_address))

  @decorators.CapabilityLogDecorator(logger)
  def srp_client_stop(self)-> None:
    """Removes SRP client."""
    self.call_command(Commands.SRP_CLIENT_STOP.value)

  @decorators.CapabilityLogDecorator(logger)
  def srp_client_clear_service(self, instance: str, service: str)-> None:
    """Clear a service from SRP client.

    Clear a service with a give instance name and service name (unlike service
    remove, with service clear no update is sent to server and the entry is
    immediately removed from client list)

    Args:
      instance: SRP client instance.
      service: Service to remove.
    """
    self.call_command(Commands.SRP_CLIENT_SERVICE_CLEAR.value.format(
        instance=instance, service=service))

  @decorators.CapabilityLogDecorator(logger)
  def srp_client_get_server(self) -> Union[None,
                                           Tuple[ipaddress.IPv6Address, int]]:
    """Returns the SRP server IP address and port number.

    Returns:
      A tuple of (ipaddress.IPv6Address, int) representing the SRP server
      IP address and port number.
    """
    result = self.call_command(Commands.SRP_CLIENT_SERVER.value)
    srp_client_server_output = re.match(
        Regexs.SRP_GET_SERVER_SERVICE_PATTERN.value, result[0])
    if srp_client_server_output:
      ip, port = srp_client_server_output.groups()
      return (ipaddress.IPv6Address(ip), int(port))
    return None

  @decorators.CapabilityLogDecorator(logger)
  def disable_allowlist(self)-> None:
    """Disables the allowlist."""
    self.call_command(Commands.MACFILTER_ADDR_DISABLE.value)

  @decorators.CapabilityLogDecorator(logger)
  def register_network_data(self) -> None:
    """Register the Network Data."""
    self.call_command(Commands.NETDATA_REGISTER.value)

  @decorators.CapabilityLogDecorator(logger)
  def thread_start(self) -> None:
    """Enable Thread protocol operation and attach to a Thread network."""
    self.call_command(Commands.THREAD_START.value)

  @decorators.CapabilityLogDecorator(logger)
  def thread_stop(self) -> None:
    """Disable Thread protocol operation and detach from a Thread network."""
    self.call_command(Commands.THREAD_STOP.value)

  @decorators.DynamicProperty
  def active_operational_dataset(self) -> ActiveOperationalDataset:
    """Gets the active operational dataset."""
    command_output = self.call_command(f"{Commands.DATASET} {Dataset.ACTIVE}")
    return _parse_dataset_active(command_output)

  @decorators.CapabilityLogDecorator(logger)
  def get_dataset_string(
      self, dataset: Literal[Dataset.ACTIVE, Dataset.PENDING]
  ) -> str:
    return self.call_command(f"{Commands.DATASET.value} {dataset.value} -x")[0]

  @decorators.CapabilityLogDecorator(logger)
  def set_dataset_string(
      self, dataset: Literal[Dataset.ACTIVE, Dataset.PENDING], data: str
  ) -> None:
    self.call_command(f"{Commands.DATASET_SET.value} {dataset.value} {data}")

  @decorators.CapabilityLogDecorator(logger)
  def set_dataset_buffer(self, buffer_name: str, value: Any) -> None:
    """Sets the custom values on active dataset buffer.

    Args:
      buffer_name: A name of the property that needs to be updated.
      value: New value of the property.
    """
    self.call_command(f"{Commands.DATASET.value} {buffer_name} {value}")

  @decorators.DynamicProperty
  def network_data(self) -> NetworkData:
    r"""Returns the network data.

    Example output:
      {
        "prefixes": [(
          ipaddress.IPv6Network("fdb7:5223:be73:1::/64"), "paos", "low", 0x2000
        )],
        "routes": [(
          ipaddress.IPv6Network("fd11:4df3:4cd3:b39c::/64"), True, "med", 0x2000
        )],
        "services": [
          (44970, b"\x01", b"\x36\x00\x05\x00\x00\x0e\x10", True, 0x2000),
        ],
      }
    """
    output = self.call_command(Commands.NETDATA_SHOW.value)
    iterator = iter(output)

    netdata: NetworkData = {
        "prefixes": [],
        "routes": [],
        "services": [],
    }

    if next(iterator) != "Prefixes:":
      raise errors.DeviceError(
          f"{self._device_name} Malformed network_data result {output}"
      )

    netdata["prefixes"] = [
        _parse_prefix(line)
        for line in itertools.takewhile(lambda v: v != "Routes:", iterator)
    ]

    netdata["routes"] = [
        _parse_route(line)
        for line in itertools.takewhile(lambda v: v != "Services:", iterator)
    ]

    netdata["services"] = [
        _parse_service(line)
        for line in itertools.takewhile(lambda v: v != "Contexts:", iterator)
    ]

    return netdata

  @decorators.DynamicProperty
  def local_omr_prefix(self) -> str:
    """Returns the local OMR (Off-Mesh-Routable) prefix."""
    return self.call_command(Commands.LOCAL_OMR_PREFIX.value)[0].split(" ")[0]

  @decorators.DynamicProperty
  def local_onlink_prefix(self) -> str:
    """Returns the local On-Link prefix."""
    return self.call_command(Commands.LOCAL_ONLINK_PREFIX.value)[0]

  @decorators.DynamicProperty
  def local_nat64_prefix(self) -> str:
    """Returns the local On-Link prefix."""
    return self.call_command(Commands.LOCAL_NAT64_PREFIX.value)[0]

  @decorators.DynamicProperty
  def network_data_omr_prefixes(self) -> list[Prefix]:
    """Returns the OMR (Off-Mesh-Routable) prefixes in network data.

    Most of the time the list should only have 1 entry.

    Example output:
      [(
          ipaddress.IPv6Network("fdb7:5223:be73:1::/64"), "paos", "med", 0x2000
      ),]
    """
    prefixes: list[Prefix] = self.network_data["prefixes"]
    result: list[Prefix] = []

    for prefix in prefixes:
      _, flags, _, _ = prefix
      if (
          "s" in flags
          and "o" in flags
          and "a" in flags
          and "d" not in flags
          and "N" not in flags
          and "D" not in flags
      ):
        result.append(prefix)

    return result

  @decorators.DynamicProperty
  def omr_addresses(self) -> list[str]:
    """Returns the OMR (Off-Mesh-Routable) addresses of this device.

    Most of the time the list should only have 1 entry.

    Example output:
      ["fd90:573a:2fcc:1239:2a44:f384:c14d:bb59",]
    """
    poll_timeout = 60
    try:
      omr_prefixes: list[Prefix] = retry.retry(
          func=lambda: self.network_data_omr_prefixes,
          is_successful=bool,
          timeout=poll_timeout,
          reraise=False,
          exc_type=errors.CommunicationTimeoutError,
      )
    except errors.CommunicationTimeoutError:
      logger.exception(
          "%s failed to get omr prefixes within %d seconds.",
          self._device_name,
          poll_timeout,
      )
      return []

    def _fetch_omr_addresses() -> list[str]:
      result: list[str] = []
      for address in self.ipv6_all_addresses:
        if any([
            ipaddress.ip_address(address) in prefix[0]
            for prefix in omr_prefixes
        ]):
          result.append(address)
      return result

    # TODO(gdm-authors): Retry is a workaround when the CLI output is missing
    # data.
    try:
      result = retry.retry(
          func=_fetch_omr_addresses,
          reraise=False,
          timeout=10,
          interval=1,
      )
    except errors.CommunicationTimeoutError:
      result = []
    return result

  @decorators.CapabilityLogDecorator(logger)
  def wait_for_state(
      self, states: Collection[StateStr], timeout: float = 30
  ) -> None:
    """Waits for the board going to the expected state.

    Args:
      states: A set of expected states chosen from "disabled", "detached",
        "child", "router", "leader"
      timeout: Max time to wait
    """
    retry.retry(
        func=lambda: self.ncp_state,
        is_successful=lambda state: state in states,
        reraise=False,
        timeout=timeout,
        interval=1,
    )

  @decorators.DynamicProperty
  def active_dataset(self) -> str:
    """Returns the active dataset in hex format.

    Example output:
      # ot-ctl dataset active -x
      0e080000000000010000000300001335060004001fffc00208a4b829ec0e6d24cd0708fda2c4980319febe051092a727e1abd0ed40f50c548a2b5b7edd030f4f70656e5468726561642d3462316201024b1b0410881d7f8c09a3d9d72b9540152fc32ff60c0402a0f7f8
      Done
    """
    return self.get_dataset_string(Dataset.ACTIVE)

  def _parse_ping_result(self, result: str) -> dict[str, Any]:
    """Parses ping result."""
    statistics = {}
    match = _PING_STATISTICS_PATTERN.match(result)
    if match is not None:
      if match.group("transmitted") is not None:
        statistics["transmitted_packets"] = int(match.group("transmitted"))
        statistics["received_packets"] = int(match.group("received"))
      if match.group("loss") is not None:
        statistics["packet_loss"] = float(match.group("loss")) / 100
      if match.group("min") is not None:
        statistics["round_trip_time"] = {
            "min": int(match.group("min")),
            "avg": float(match.group("avg")),
            "max": int(match.group("max")),
        }
    else:
      raise errors.DeviceError(
          f"{self._device_name} Malformed ping result {result}"
      )
    return statistics

  def ping(
      self,
      ipaddr: str,
      size: int = 60,
      count: int = 1,
      interval: float = 1.0,
      hoplimit: int = 64,
      timeout: float = 3.0,
  ) -> dict[str, Any]:
    """Runs ping command on the board.

    Args:
      ipaddr: destination to ping.
      size: ping packet size.
      count: number of ping packets.
      interval: interval between sending ping request.
      hoplimit: TTL in the ping packet.
      timeout: total timeout for the ping command.

    Returns:
      A dict of ping result. Example:
        {
          "transmitted_packets": 1,
          "received_packets": 1,
          "packet_loss": 0.0,
          "round_trip_time": {
            "min": 2,
            "avg": 2.0,
            "max": 2
          }
        }
    """

    timeout_allowance = 3
    cli_timeout = (count - 1) * interval + timeout + timeout_allowance
    cmd = (
        f"{Commands.PING.value} {ipaddr} {size} {count} {interval} {hoplimit}"
        f" {timeout}"
    )

    result = self.call_command(cmd, timeout=cli_timeout)[-1]
    return self._parse_ping_result(result)

  @decorators.DynamicProperty
  def ipaddr_mleid(self) -> str:
    """Get Thread Mesh Local EID address."""
    return self.call_command(Commands.IPV6_MLEID_ADDRESS.value)[0]

  @decorators.DynamicProperty
  def ipaddr_linklocal(self) -> str:
    """Get Thread link-local IPv6 address."""
    return self.call_command(Commands.IPV6_LINKLOCAL_ADDRESS.value)[0]

  @decorators.DynamicProperty
  def ipaddr_rloc(self) -> str:
    """Get Thread Routing Locator (RLOC) address."""
    return self.call_command(Commands.IPV6_RLOC_ADDRESS.value)[0]

  @decorators.CapabilityLogDecorator(logger)
  def disable_border_routing(self) -> None:
    """Disables border routing."""
    self.call_command(Commands.BR_DISABLE.value)

  @decorators.CapabilityLogDecorator(logger)
  def enable_border_routing(self) -> None:
    """Enables border routing."""
    self.call_command(Commands.BR_ENABLE.value)

  @decorators.DynamicProperty
  def poll_period(self) -> int:
    """Gets the customized data poll period for the device.

    Returns:
      The data poll period in milliseconds.
    """
    return int(self.call_command(Commands.POLL_PERIOD.value)[0])

  @decorators.CapabilityLogDecorator(logger)
  def set_poll_period(self, poll_period: int) -> None:
    """Sets the customized data poll period for the device.

    Args:
      poll_period: The data poll period in milliseconds.
    """
    self.call_command(f"{Commands.POLL_PERIOD.value} {poll_period}")

  @decorators.DynamicProperty
  def log_level(self) -> int:
    """Gets the Thread log level for the device.

    Returns:
      The Thread log level (from 1-5).
    """
    return int(self.call_command(Commands.LOG_LEVEL.value)[0])

  @decorators.CapabilityLogDecorator(logger)
  def set_log_level(self, log_level: int) -> None:
    """Sets the Thread log level for the device.

    Args:
      log_level: The log level (from 1-5).
    """
    self.call_command(f"{Commands.LOG_LEVEL.value} {log_level}")

  @decorators.CapabilityLogDecorator(logger)
  def get_device_locale(self) -> list[str]:
    """Returns the Device Locale information.

    Note:
      get_device_locale can only fetch in right after a factory reset, it will
      raise an InvalidState error when called in a wrong state.
    """
    self.call_command(Commands.DIAG_START.value)
    device_locale_info = self.call_command(Commands.DEVICE_LOCALE.value)
    self.call_command(Commands.DIAG_STOP.value)
    return device_locale_info

  @decorators.CapabilityLogDecorator(logger)
  def udp_open(self) -> None:
    """Opens the UDP socket."""
    self.call_command(Commands.UDP_OPEN.value)

  @decorators.CapabilityLogDecorator(logger)
  def udp_bind(
      self, ipaddr: str, port: int, bind_unspecified: bool = False
  ) -> None:
    """Binds the UDP socket to the specific address and port.

    Args:
      ipaddr: The local address to bind.
      port: The local port to bind.
      bind_unspecified: Whether to bind all interfaces on the device. False for
        binding to Thread interface only, True for binding to all interfaces.
    """
    # TODO(gdm-authors): The OpenThread CLI does not return the actual port
    # bound. Return a pair of (address, port) after OpenThread CLI prints the
    # address and port for `udp bind`.
    self.call_command(
        Commands.UDP_BIND.value.format(
            interface="-u" if bind_unspecified else "",
            ipaddr=ipaddr,
            port=port,
        )
    )

  @decorators.CapabilityLogDecorator(logger)
  def udp_close(self) -> None:
    """Closes the UDP socket."""
    self.call_command(Commands.UDP_CLOSE.value)

  @decorators.CapabilityLogDecorator(logger)
  def udp_send(self, message: str, ipaddr: str, port: int) -> None:
    """Sends a udp packet to the given address and port.

    Args:
      message: Message to be sent.
      ipaddr: The destination address.
      port: The destination port.
    """
    self.call_command(
        Commands.UDP_SEND.value.format(
            ipaddr=ipaddr, port=port, text=message
        )
    )

  @contextlib.contextmanager
  @decorators.CapabilityLogDecorator(logger)
  def open_udp_and_bind(
      self, ipaddr: str, port: int, bind_unspecified: bool = False
  ):
    """Binds the UDP socket to the specific address and port.

    This function is expected to work with `with` statement. The UDP socket on
    device will be closed automatically.

    ```
    with device.wpan.open_udp_and_bind("::", 12345):
      # Do something
      # device.wpan.udp_close() will be called automatically.
    ```

    Args:
      ipaddr: The local address to bind.
      port: The local port to bind.
      bind_unspecified: Whether to bind all interfaces on the device. False for
        binding to Thread interface only, True for binding to all interfaces.

    Yields:
      `None`
    """
    self.udp_open()
    try:
      yield self.udp_bind(ipaddr, port, bind_unspecified)
    finally:
      self.udp_close()

  @decorators.CapabilityLogDecorator(logger)
  def tcp_init(self) -> None:
    """Initializes the example TCP listener and the example TCP endpoint."""
    self.call_command(Commands.TCP_INIT.value)

  @decorators.CapabilityLogDecorator(logger)
  def tcp_deinit(self) -> None:
    """Deinitializes the example TCP listener and the example TCP endpoint."""
    self.call_command(Commands.TCP_DEINIT.value)

  @decorators.CapabilityLogDecorator(logger)
  def tcp_listen(self, port: int, ipaddr: Optional[str] = None) -> None:
    """Uses the example TCP listener to listen for incoming connections.

    If no TCP connection is associated with the example TCP endpoint, then any
    incoming connections matching the specified name are accepted and associated
    with the example TCP endpoint.

    Args:
      port: The local port to bind.
      ipaddr: The local address to bind. If this is None, it is unspecified and
        any addresses will be matched.
    """
    ipaddr = ipaddr or "::"
    self.call_command(
        Commands.TCP_LISTEN.value.format(ipaddr=ipaddr, port=port)
    )

  @decorators.CapabilityLogDecorator(logger)
  def tcp_connect(self, ipaddr: str, port: int) -> None:
    """Establishes a connection with the specified peer.

    If the connection establishment is successful, the resulting TCP connection
    is associated with the example TCP endpoint.

    Args:
      ipaddr: The peer's IP address.
      port: The peer's TCP port.
    """
    self.call_command(
        Commands.TCP_CONNECT.value.format(ipaddr=ipaddr, port=port)
    )

  @decorators.CapabilityLogDecorator(logger)
  def tcp_benchmark_run(self, size: Optional[int] = None):
    """Test TCP performance of current TCP connection.

    Transfers the specified number of bytes using the TCP connection
    currently associated with the example TCP endpoint (this TCP connection
    must be established before using this command).

    Args:
      size: the number of bytes to send for the benchmark. If it is left
        unspecified, the default size is used.
    """
    self.call_command(
        Commands.TCP_BENCHMARK_RUN.value.format(size=(size or ""))
    )

  @decorators.CapabilityLogDecorator(logger)
  def tcp_benchmark_result(self) -> TcpBenchmarkResult:
    """Query the benchmark status and result."""
    result = " ".join(self.call_command(Commands.TCP_BENCHMARK_RESULT.value))

    return parse_tcp_benchmark_result(result)

  @decorators.CapabilityLogDecorator(logger)
  def radio_stats(self) -> RadioStats:
    """Gets the radio statistics.

    Returns:
      The radio statistics
    """
    result = " ".join(
        self.call_command(Commands.RADIO_STATS.value)
    )
    return parse_radio_stats(result)

  @decorators.CapabilityLogDecorator(logger)
  def radio_stats_clear(self) -> None:
    """Clears the radio statistics."""
    self.call_command(Commands.RADIO_STATS_CLEAR.value)

  @decorators.DynamicProperty
  def txpower(self) -> int:
    """Returns the Tx Power set for Thread."""
    return int(self.call_command(Commands.TXPOWER.value)[0].split()[0])

  @decorators.CapabilityLogDecorator(logger)
  def udp_send_msg(self, src_ip: str, send_port: int, port: int, dest_ip: str,
                   message: str, bind_unspecified=True):
    """Binds a port on source and sends udp message to destination.

    While sending udp message to infrastructure link host udp bind on thread BR
    is must.

    Args:
      src_ip: Source IPv6 address.
      send_port: Destination udp port to be used by udp_send.
      port: Source udp port to be used by udp_bind.
      dest_ip: Destination IPv6 address for which udp transmission needs
      to be sent.
      message: Message to be sent.
      bind_unspecified: Whether to bind all interfaces on the device. False for
        binding to Thread interface only, True for binding to all interfaces.
    """
    with self.open_udp_and_bind(
        ipaddr=src_ip, port=port, bind_unspecified=bind_unspecified):
      self.udp_send(message=message, ipaddr=dest_ip, port=send_port)

  @decorators.DynamicProperty
  def ipmaddress(self) -> list[ipaddress.IPv6Address]:
    """Returns the multicast IP address of the device."""
    ipmaddress = self.call_command(Commands.IP_MADDR.value)
    address = [ipaddress.IPv6Address(addr) for addr in ipmaddress]
    return address

  @decorators.CapabilityLogDecorator(logger)
  def add_ipmaddr(self, ipmaddr: ipaddress.IPv6Address) -> None:
    """Set ipmaddr to the device.

    Args:
      ipmaddr: The ipmaddress of the device.
    """
    self.call_command(Commands.IP_MADDR_ADD.value.format(addr=ipmaddr))
