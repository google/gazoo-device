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

"""A fake playback class to enable mocks for detection tests."""

from typing import Any, Collection, Optional, Sequence
from unittest import mock

from gazoo_device.tests.unit_tests.utils import fake_responder
import immutabledict
import usb

ADB_DEVICE_BEHAVIORS = immutabledict.immutabledict({})

ALT_POE_BEHAVIORS = immutabledict.immutabledict({
    "unifi_switch": {
        "mca-cli-op info":
            """
        Model:       US-8-150W
        Version:     5.43.23.12533
        MAC Address: 12:34:56:78:90:ab
        IP Address:  192.168.2.60
        Hostname:    US-8-150W
        Uptime:      43210 seconds

        Status:      Connected (http://192.168.2.60:8080/inform)
        """
    }
})

JLINK_DEVICE_BEHAVIORS = immutabledict.immutabledict({})

SERIAL_DEVICE_BEHAVIORS = immutabledict.immutabledict({
    "cambrionix": {
        "product_name": "FT230X Basic UART",
    },
})

SINGLETON_DEVICES = immutabledict.immutabledict({
    "yepkit": "YepkitComms",
})

SNMP_DEVICE_BEHAVIORS = immutabledict.immutabledict({
    "dlink_switch": {
        "snmpget -v 2c -c private 192.168.2.65:161 1.3.6.1.2.1.1.1.0":
            "iso.3.6.1.2.1.1.1.0 = STRING: \"DGS-1100-05 Gigabit Ethernet Switch\"",
    },
})

SSH_DEVICE_BEHAVIORS = immutabledict.immutabledict({
    "powerswitch": {
        "http://192.168.2.65/restapi/config/=brand_name/": [
            "Web Power Switch",
            207,
        ]
    },
    "raspberrypi": {
        "cat /proc/device-tree/model": "Raspberry Pi 3 Model B Rev 1.1",
    },
    "rpi_matter_controller": {
        "cat /proc/device-tree/model": "Raspberry Pi 4 Model B Rev 1.4",
        "which chip-tool": "/usr/bin/chip-tool",
    },
    "unifi_switch": {
        "mca-cli-op info":
            """
        Model:       USW-8P-150
        Version:     4.3.13.11253
        MAC Address: 12:34:56:78:90:ab
        IP Address:  192.168.2.61
        Hostname:    UBNT
        Uptime:      44625 seconds

        Status:      Unknown[11] (http://192.168.2.63:8080/inform)
        """
    },
})

USB_DEVICE_BEHAVIORS = immutabledict.immutabledict({})


class ResponseObject:
  """HTTP response container."""

  def __init__(self, text, status_code=200, json=None):
    self.text = text
    self.status_code = status_code
    self.json_dict = json or {}

  def json(self):
    return self.json_dict


class FakeDetectPlayback:
  """Enables mocking of shell, http, and other forms of communication."""

  def __init__(self):
    self.behavior = {}
    self.debug = False
    self.responder = fake_responder.FakeResponder()
    self.responder.behavior_dict = {}
    self.responder.debug = self.debug

  def check_output(self, args: Sequence[str], **kwargs: Any) -> str:
    """Mocks subprocess.check_output().

    Args:
      args: Command to invoke.
      **kwargs: No op.

    Raises:
      RuntimeError: If command not found in behavior dictionary.

    Returns:
      Mock response to subprocess.check_output() command.
    """
    del kwargs  # Unused
    command = " ".join(args)
    if self.debug:
      print("FAKEPLAYBACK: check_output command: {}".format(command))
    if command in self.behavior:
      if self.debug:
        print("FAKEPLAYBACK: Response: {}".format(self.behavior[command]))
      return self.behavior[command]
    raise RuntimeError("Command {command!r} failed")

  def ssh_command(self,
                  ip_address: str,
                  command: str,
                  **kwargs: Any) -> str:
    """Mocks ssh command.

    Args:
      ip_address: IP address.
      command: The command to send to the provided IP address.
      **kwargs: No op.

    Returns:
      The value in behavior dictionary for the given command.

    Raises:
      RuntimeError: A command was not found in behavior dictionary.
    """
    del ip_address, kwargs  # Unused
    if self.debug:
      print("FAKEPLAYBACK: Ssh command: {}".format(command))
    if command in self.behavior:
      if self.debug:
        print("FAKEPLAYBACK: Response: {}".format(self.behavior[command]))
      return self.behavior[command]
    raise RuntimeError("Command failed")

  def send_http_get(self,
                    url: str,
                    valid_return_codes: Optional[Collection[int]] = None,
                    **kwargs: Any) -> ResponseObject:
    """Mocks send http get.

    Args:
      url: URL to send http call to.
      valid_return_codes (list): Valid return codes for http call.
      **kwargs: No op.

    Returns:
      A ResponseObject with the response and return code as values.

    Raises:
      RuntimeError: If URL not found in behavior dict or invalid return code.
    """
    del kwargs  # Unused
    valid_return_codes = valid_return_codes or [200, 206, 207]
    if self.debug:
      print("FAKEPLAYBACK: http_get url: {}, valid_return_codes: {}".format(
          url, valid_return_codes))
    if url in self.behavior:
      response = self.behavior[url]
      if self.debug:
        print("FAKEPLAYBACK: Response: {}".format(response))
      if response[1] not in valid_return_codes:
        if self.debug:
          print("FAKEPLAYBACK: {} not in {}".format(response[1],
                                                    valid_return_codes))
        raise RuntimeError("Invalid code")
      return ResponseObject(*response)
    raise RuntimeError("Connection Refused")

  def get_device_info(self, address):
    del address  # Unused
    return self.behavior["device_info"]

  def get_product_name(self, address: str) -> str:
    del address  # Unused
    return self.behavior["product_name"]

  def get_serial_number(self, address: str) -> str:
    del address  # Unused
    return self.behavior["serial_number"]

  def adb_shell(self, address: str, command: str) -> str:
    """Mocks adb_shell.

    Args:
      address: adb serial.
      command: Command to send.

    Returns:
      The value in behavior dict if available, empty if not.
    """
    del address  # Unused
    if self.debug:
      print("FAKEPLAYBACK: adb_shell: {}".format(command))
    if command in self.behavior:
      response = self.behavior[command]
      if self.debug:
        print("FAKEPLAYBACK: Response: {}".format(response))
      return response
    return ""

  def get_usb_device_from_serial_number(
      self, serial_number: str) -> mock.MagicMock:
    del serial_number  # Unused
    return mock.create_autospec(
        idProduct=self.behavior["product_id"],
        idVendor=self.behavior["vendor_id"],
        langids=(1033,),
        serial_number=self.behavior["serial_number"],
        product=self.behavior["product"],
        spec=usb.core.Device,
        )