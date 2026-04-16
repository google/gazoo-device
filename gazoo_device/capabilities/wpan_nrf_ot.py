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
"""The wpan OpenThread CLI capability for NRF platform."""

import ipaddress
import re

from typing import Callable, Iterable, Optional, Union
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities import wpan_ot_base
from gazoo_device.switchboard import expect_response

logger = gdm_logger.get_logger()

_COMMAND_RESPONSE_END = [r"(.*\n)?(Done|Error \d+:.*)\n"]
_SRP_CLIENT_HOST_PATTERN = re.compile(
    r'name:("(.*)"|(\(null\))), state:(\S+), addrs:\[(.*)\]')


class WpanNrfOt(wpan_ot_base.WpanOtBase):
  """The wpan OpenThread CLI capability for NRF platform."""

  def __init__(self, device_name: str, send: Callable[..., None],
               send_and_expect: Callable[..., expect_response.ExpectResponse]):
    """Initializes an instance of WpanNrfOt capability.

    Args:
      device_name: Name of device using this capability.
      send: Switchboard.send method.
      send_and_expect: Switchboard.send_and_expect method.
    """
    super().__init__(device_name=device_name)
    self._send = send
    self._send_and_expect = send_and_expect

  @decorators.CapabilityLogDecorator(logger)
  def factory_reset(self) -> None:
    """Factory resets the Thread board.

    Raises:
      DeviceError: when something wrong happens during the factory reset.

    Note:
      factory reset command resets the board so it does not output a "DONE"
      string.
    """
    self._send(wpan_ot_base.Commands.FACTORY_RESET.value)
    self.wait_for_state({"disabled"})

  @decorators.CapabilityLogDecorator(logger)
  def reset(self) -> None:
    """Resets the network."""
    self._send(wpan_ot_base.Commands.RESET.value)

  @decorators.DynamicProperty
  def csl_channel(self) -> int:
    """Gets the csl channel.

    Returns:
      The csl channel used on the device.
    """
    return int(self.call_command(wpan_ot_base.Commands.CSL_CHANNEL.value)[0])

  @decorators.CapabilityLogDecorator(logger)
  def set_csl_channel(self, csl_channel: int) -> None:
    """Sets the CSL channel.

    Args:
      csl_channel: The CSL channel used for CSL transmission.
    """
    self.call_command(
        f"{wpan_ot_base.Commands.CSL_CHANNEL.value} {csl_channel}"
    )

  @decorators.DynamicProperty
  def csl_period(self) -> int:
    """Returns the csl period for the device in unit of 10 symbols.

    Symbol means symbol duration time in radio transmission, which equals to
    (1 / symbol rate). The symbol rate for Thread (IEEE 802.15.4, 2450MHz) is
    62.5k symbol/s. Thus 10 symbols equals to 0.00016s.
    """
    return int(self.call_command(wpan_ot_base.Commands.CSL_PERIOD.value)[0])

  @decorators.CapabilityLogDecorator(logger)
  def set_csl_period(self, csl_period: int) -> None:
    """Sets the csl period for the device in unit of 10 symbols.

    Args:
      csl_period: The csl period in unit of 10 symbols.  Symbol means symbol
        duration time in radio transmission, which equals to (1 / symbol rate).
        The symbol rate for Thread (IEEE 802.15.4, 2450MHz) is 62.5k symbol/s.
        Thus 10 symbols equals to 0.00016s.
    """
    self.call_command(f"{wpan_ot_base.Commands.CSL_PERIOD.value} {csl_period}")

  @decorators.DynamicProperty
  def csl_timeout(self) -> int:
    """Gets the csl timeout for the device.

    Returns:
      The csl timeout in unit of seconds.
    """
    return int(self.call_command(wpan_ot_base.Commands.CSL_TIMEOUT.value)[0])

  @decorators.CapabilityLogDecorator(logger)
  def set_csl_timeout(self, csl_timeout: int) -> None:
    """Sets the csl timeout for the device.

    Args:
      csl_timeout: The csl timeout in unit of seconds.
    """
    self.call_command(
        f"{wpan_ot_base.Commands.CSL_TIMEOUT.value} {csl_timeout}"
    )

  @decorators.DynamicProperty
  def dns_client_config(self) -> wpan_ot_base.DnsConfig:
    """Gets DNS client query config.

    Returns:
      Ths DNS client query config.
    """

    return wpan_ot_base.parse_dns_config(
        self.call_command(wpan_ot_base.Commands.DNS_CLIENT_CONFIG)
    )

  @decorators.CapabilityLogDecorator(logger)
  def dns_client_set_config(
      self,
      server_address: str,
      port: int,
      response_timeout: Optional[int] = None,
      max_tx_attempts: Optional[int] = None,
      recursion_desired: Optional[bool] = None,
  ) -> None:
    """Sets DNS client query config."""
    args = f"{server_address} {port}"
    if response_timeout is not None:
      args += f" {response_timeout}"

    if max_tx_attempts is not None and response_timeout is None:
      raise ValueError(
          "must specify `response_timeout` if `max_tx_attempts` is specified."
      )

    if max_tx_attempts is not None:
      args += f" {max_tx_attempts}"

    if recursion_desired is not None and max_tx_attempts is None:
      raise ValueError(
          "must specify `max_tx_attempts` if `recursion_desired` is specified."
      )

    if recursion_desired is not None:
      args += f" {int(recursion_desired)}"

    self.call_command(
        f"{wpan_ot_base.Commands.DNS_CLIENT_CONFIG.value} {args}"
    )

  @decorators.CapabilityLogDecorator(logger)
  def dns_client_browse_services(
      self,
      service: str,
  ) -> list[wpan_ot_base.ResolvedService]:
    """Lets the DNS client browse service instances."""
    response = "\n".join(
        self.call_command(
            f"{wpan_ot_base.Commands.DNS_CLIENT_BROWSE_SERVICES.value} {service}",
            timeout=15,
        )
    )

    result: list[wpan_ot_base.ResolvedService] = []
    for (
        ins,
        port,
        priority,
        weight,
        srv_ttl,
        hostname,
        address,
        aaaa_ttl,
        txt_data,
        txt_ttl,
    ) in re.findall(
        (
            r"(.*?)\s+Port:(\d+), Priority:(\d+), Weight:(\d+),"
            r" TTL:(\d+)\s*Host:(\S+)\s+HostAddress:(\S+)"
            r" TTL:(\d+)\s+TXT:(\[.*?\]) TTL:(\d+)"
        ),
        response,
    ):
      result.append(
          wpan_ot_base.ResolvedService(
              instance=ins,
              service=service,
              port=int(port),
              priority=int(priority),
              weight=int(weight),
              host=hostname,
              address=ipaddress.IPv6Address(address),
              txt=wpan_ot_base.parse_srp_server_service_txt(txt_data),
              srv_ttl=int(srv_ttl),
              txt_ttl=int(txt_ttl),
              aaaa_ttl=int(aaaa_ttl),
          )
      )

    return result

  def parse_ipv6addr_list(
      self, ipv6_addresses: Iterable[str]
  ) -> list[ipaddress.IPv6Address]:
    """Returns a list of IPv6 addresses.

    IPv6Address objects example IPv6Address('2001:db8:85a3::8a2e:370:7334').

    Args:
      ipv6_addresses: list of ipv6 addresses.
    """
    return [ipaddress.IPv6Address(line) for line in ipv6_addresses]

  @decorators.CapabilityLogDecorator(logger)
  def get_srp_client_host_addresses(self) -> list[ipaddress.IPv6Address]:
    return self.parse_ipv6addr_list(
        self.call_command(wpan_ot_base.Commands.SRP_CLIENT_HOST_ADDRESS.value)
    )

  def parse_srp_client_service(
      self, srp_client_service_info: str
  ) -> wpan_ot_base.SrpClientService:
    """Parse a single line of SRP client service information.

    Args:
      srp_client_service_info: A string representing a line of SRP client
      service information. Ex: instance:"ins2", name:"_meshcop._udp",
      state:ToAdd, port:2000, priority:2, weight:2

    Raises:
      RuntimeError: If srp_client_service_info doesn't comply with the regex
                    it will raise a runtime error.
    Returns:
       Return object of SrpClientService class with srp client service
       information.
    """
    pattern = wpan_ot_base.Regexs.SRP_CLIENT_SERVICE_PATTERN.value
    output = pattern.match(srp_client_service_info)
    if output is None:
      raise RuntimeError(
          f"SRP client services are missing : {srp_client_service_info}."
      )

    instance, service, state, port, priority, weight = output.groups()
    return wpan_ot_base.SrpClientService(
        instance=instance,
        service=service,
        state=state,
        port=int(port),
        priority=int(priority),
        weight=int(weight),
    )

  @decorators.CapabilityLogDecorator(logger)
  def get_srp_client_services(self) -> list[wpan_ot_base.SrpClientService]:
    output = self.call_command(wpan_ot_base.Commands.SRP_CLIENT_SERVICE.value)
    return [self.parse_srp_client_service(line) for line in output]

  @decorators.CapabilityLogDecorator(logger)
  def get_srp_client_host_state(self) -> str:
    return self.call_command(wpan_ot_base.Commands.SRP_CLIENT_HOST_STATE.value)[
        0
    ]

  @decorators.CapabilityLogDecorator(logger)
  def enable_srp_client_autostart(self) -> None:
    self.call_command(wpan_ot_base.Commands.SRP_CLIENT_AUTOSTART_ENABLE.value)

  @decorators.CapabilityLogDecorator(logger)
  def enable_srp_client_callback(self) -> None:
    self.call_command(wpan_ot_base.Commands.SRP_CLIENT_CALLBACK_ENABLE.value)

  @decorators.CapabilityLogDecorator(logger)
  def dns_client_resolve_host(
      self, hostname: str, ipv4: bool = False
  ) -> list[wpan_ot_base.ResolvedHost]:
    """Lets the DNS client resolve a host name."""
    command = (
        wpan_ot_base.Commands.DNS_CLIENT_RESOLVE4_HOST.value
        if ipv4
        else wpan_ot_base.Commands.DNS_CLIENT_RESOLVE_HOST.value
    )
    response = self.call_command(f"{command} {hostname}", timeout=15)[0]
    addrs = response.strip().split(" - ")[1].split(" ")
    ips = [ipaddress.IPv6Address(item.strip()) for item in addrs[::2]]
    ttls = [int(item.split("TTL:")[1]) for item in addrs[1::2]]

    return [
        wpan_ot_base.ResolvedHost(address=ip, ttl=ttl)
        for ip, ttl in zip(ips, ttls)
    ]

  @decorators.CapabilityLogDecorator(logger)
  def dns_client_resolve_service(
      self, instance: str, service: str
  ) -> wpan_ot_base.ResolvedService:
    """Lets the DNS client resolve a service instance."""
    escaped_instance = wpan_ot_base.escape_escapable(instance)
    response = self.call_command(
        f"{wpan_ot_base.Commands.DNS_CLIENT_RESOLVE_SERVICE.value} {escaped_instance} {service}",
        timeout=15,
    )
    m = re.match(
        (
            r".*Port:(\d+), Priority:(\d+), Weight:(\d+), TTL:(\d+)\s+"
            r"Host:(.*?)\s+HostAddress:(\S+) TTL:(\d+)\s+"
            r"TXT:(\[.*?\]) TTL:(\d+)\s*"
        ),
        "\t".join(response),
    )
    if m:
      (
          port,
          priority,
          weight,
          srv_ttl,
          hostname,
          address,
          aaaa_ttl,
          txt_data,
          txt_ttl,
      ) = m.groups()
      return wpan_ot_base.ResolvedService(
          instance=instance,
          service=service,
          port=int(port),
          priority=int(priority),
          weight=int(weight),
          host=hostname,
          address=ipaddress.IPv6Address(address),
          txt=wpan_ot_base.parse_srp_server_service_txt(txt_data),
          srv_ttl=int(srv_ttl),
          txt_ttl=int(txt_ttl),
          aaaa_ttl=int(aaaa_ttl),
      )
    else:
      raise errors.DeviceError(
          f"Failed to parse the DNS response {response} to {self._device_name}"
      )

  @decorators.CapabilityLogDecorator(logger)
  def is_dns_compression_enabled(self) -> bool:
    """Checks if DNS compression is enabled.

    Returns:
      True if DNS compression is enabled, False otherwise.
    """
    return self.call_command(
        wpan_ot_base.Commands.DNS_CLIENT_COMPRESSION.value
    )[0] == "Enabled"

  @decorators.CapabilityLogDecorator(logger)
  def enable_dns_compression(self) -> None:
    """Enables the DNS compression."""
    self.call_command(
        f"{wpan_ot_base.Commands.DNS_CLIENT_COMPRESSION_ENABLE.value}"
    )

  @decorators.CapabilityLogDecorator(logger)
  def disable_dns_compression(self) -> None:
    """Disables the DNS compression."""
    self.call_command(
        f"{wpan_ot_base.Commands.DNS_CLIENT_COMPRESSION_DISABLE.value}"
    )

  @decorators.CapabilityLogDecorator(logger)
  def srp_client_autostart(self, enable: bool) -> None:
    """Enables/Disables the autostart mode for this SRP client."""
    action: str = "enable" if enable else "disable"
    self.call_command(
        f"{wpan_ot_base.Commands.SRP_CLIENT_AUTOSTART.value} {action}"
    )

  @decorators.CapabilityLogDecorator(logger)
  def srp_client_callback(self, enable: bool) -> None:
    """Enables/Disables the callback output for this SRP client."""
    action: str = "enable" if enable else "disable"
    self.call_command(
        f"{wpan_ot_base.Commands.SRP_CLIENT_CALLBACK.value} {action}"
    )

  @decorators.DynamicProperty
  def srp_client_host_name(self) -> str:
    """Returns the host name of this SRP client."""
    return self.call_command(wpan_ot_base.Commands.SRP_CLIENT_HOST_NAME.value)[
        0
    ]

  @decorators.CapabilityLogDecorator(logger)
  def srp_client_set_host_name(self, host_name: str) -> None:
    """Sets the host name of this SRP client."""
    self.call_command(
        f"{wpan_ot_base.Commands.SRP_CLIENT_HOST_NAME.value} {host_name}"
    )

  @decorators.CapabilityLogDecorator(logger)
  def srp_client_set_host_addresses(self, host_addresses: list[str]) -> None:
    """Sets the host addresses of this SRP client."""
    self.call_command(
        f"{wpan_ot_base.Commands.SRP_CLIENT_HOST_ADDRESS.value}"
        f" {''.join(host_addresses)}"
    )

  @decorators.CapabilityLogDecorator(logger)
  def srp_client_add_service(
      self,
      instance_name: str,
      service_type: str,
      port: int,
      priority: int = 0,
      weight: int = 0,
      txt: Optional[dict[str, Union[str, bytes, bool]]] = None,
  ) -> None:
    """Lets the SRP client add a service."""
    self.call_command(
        f"{wpan_ot_base.Commands.SRP_CLIENT_ADD_SERVICE.value} {instance_name} {service_type} {port} {priority} {weight} {wpan_ot_base.txt_to_hex(txt)}"
    )

  @decorators.CapabilityLogDecorator(logger)
  def srp_client_remove_host(self, remove_key_lease: bool = False) -> None:
    """Lets the SRP client remove the host."""
    command = f"{wpan_ot_base.Commands.SRP_CLIENT_REMOVE_HOST.value}"

    if remove_key_lease:
      command += " 1"

    self.call_command(command)

  @decorators.CapabilityLogDecorator(logger)
  def srp_client_remove_service(self, instance: str, service: str) -> None:
    """Removes a service from SRP client.

    Args:
      instance: Instance name of the service to be removed.
      service: Service type of the service to be removed.
    """
    self.call_command(f"{wpan_ot_base.Commands.SRP_CLIENT_SERVICE} "
                      f"remove {instance} {service}")

  @decorators.CapabilityLogDecorator(logger)
  def get_srp_client_key_lease_interval(self) -> int:
    """Gets SRP client key lease interval.

    Returns:
      The SRP client key lease interval in seconds.
    """
    return int(self.call_command(
        wpan_ot_base.Commands.SRP_CLIENT_KEYLEASEINTERVAL.value)[0], 10)

  def get_srp_client_host(self) -> wpan_ot_base.SrpClientHostInfo:
    """Gets SRP client host information like "host, state, and addresses".

    Raises:
      RuntimeError: If SRP client host information are missing.
    Returns:
      SRP client host information.
    """
    output = self.call_command(wpan_ot_base.Commands.SRP_CLIENT_HOST.value)[0]
    srp_client_host_info = re.match(_SRP_CLIENT_HOST_PATTERN, output)
    if not srp_client_host_info:
      raise RuntimeError(
          f"SRP client host information are missing : {srp_client_host_info}.")
    _, host, _, state, addresses = srp_client_host_info.groups()
    return wpan_ot_base.SrpClientHostInfo(
        host=host or "",
        state=state,
        addresses=[
            ipaddress.IPv6Address(ip) for ip in addresses.split(", ")
            ] if addresses else [],)

  @decorators.CapabilityLogDecorator(logger)
  def set_srp_client_lease_interval(self, interval: int) -> None:
    """Sets lease interval on the SRP client device.

    Args:
      interval: Lease interval to set on the SRP client device.
    """
    self.call_command(
        f"{wpan_ot_base.Commands.SRP_CLIENT_LEASE_INTERVAL.value} {interval}"
    )

  def call_command(
      self,
      command: str,
      timeout: float | None = None,
      pattern_list: list[str] | None = None,
  ) -> list[str]:
    """Helper method to send OTCLI command, check and return the responses.

    Args:
      command: The command to send to the device.
      timeout: The timeout to wait for the command to complete.
      pattern_list: The list of patterns to match in the response. If not
        provided, the default pattern will be used.
        Example
          > udp bind -u :: 1278
          Done
          >
          5 bytes from fd72:31ef:43af:1:57dc:c456:44fe:52d8 1278 RzGji

    Returns:
      The response from the device.
    """
    if pattern_list is None:
      pattern_list = _COMMAND_RESPONSE_END
    if timeout is None:
      timeout = 5.0

    response = self._send_and_expect(
        command=command, pattern_list=pattern_list, timeout=timeout
    )
    if response.timedout:
      error_message = response.before
      if "InvalidCommand" in response.before:
        raise errors.DeviceError(
            f"{self._device_name} Invalid command {command}: {error_message}"
        )
      else:
        raise errors.DeviceError(
            f"{self._device_name} timed out responding to command {command}"
            f"after {timeout} seconds: {error_message}"
        )
    lines = response.after.split("\n")[:-1]  # Strip the final empty line.
    if lines[-1] == "Done":
      # Command returns successfully
      return lines[1:-1]  # Strip echo back command and the status line.
    elif "bytes" in lines[0].split(" "):
      # Command returns a UDP message
      return lines
    else:
      # Command returns an error
      raise errors.DeviceError(
          f"{self._device_name} command {command} failed. "
          f"Response: {response.after}"
      )

  @decorators.CapabilityLogDecorator(logger)
  def udp_receive_msg(
      self,
      unspecified_address: str,
      port: int,
      bind_unspecified=True,
  ) -> str:
    """Opens and binds a port to receive udp message from another node.

    Args:
      unspecified_address: It carries "::" and to bind with port number.
        Which will allow device to receive a UDP message, irrespective of any
        particular IP address. Ex: udp bind :: 1234.
      port: Port to be used for udp transmission.
      bind_unspecified: If false, it binds the thread interface.
          else it binds all interfaces.

    Returns:
      Return udp received message.
    """
    self.udp_close()
    self.udp_open()
    response = self.call_command(
        wpan_ot_base.Commands.UDP_BIND.value.format(
            interface="-u" if bind_unspecified else "",
            ipaddr=unspecified_address,
            port=port,
        ),
        pattern_list=[r"\bbytes from\b"],
    )

    received_msg = response[0].split(" ")[-1]
    logger.info("UDP received message: %s.", received_msg)
    self.udp_close()
    return received_msg

  @decorators.CapabilityLogDecorator(logger)
  def add_multicast_address_and_verify(
      self, multicast_address: ipaddress.IPv6Address) -> None:
    """Sets multicast address and verifies the multicast address.

    Args:
      multicast_address: Multicast address to be set on the SRP client device.

    Raises:
      RuntimeError: If unable to add multicast address successfully.
    """
    self.add_ipmaddr(multicast_address)
    ipmaddrs = self.ipmaddress
    if ipaddress.IPv6Address(multicast_address) not in ipmaddrs:
      raise errors.DeviceError(
          f"Fail to add multicast address {multicast_address}.")
    logger.debug("Successfully added multicast address %s.",
                 multicast_address)
