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

"""Tests the communication type module."""
import os
import socket
from unittest import mock

from absl.testing import parameterized
import gazoo_device
from gazoo_device import data_types
from gazoo_device import errors
from gazoo_device import extensions
from gazoo_device.protos import device_service_pb2
from gazoo_device.switchboard import communication_types
from gazoo_device.switchboard.transports import pigweed_rpc_transport
from gazoo_device.switchboard.transports import ssh_transport
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import adb_utils
from gazoo_device.utility import host_utils
from gazoo_device.utility import usb_config
from gazoo_device.utility import usb_utils
import serial

_CAMBRIONIX_ADDRESS = "/dev/serial/by-id/usb-FTDI_FT230X_Basic_UART_DJ00JMN0-if00-port0"
_CAMBRIONIX_USB3_ADDRESS = "/dev/serial/by-id/usb-cambrionix_PS15-USB3_0000007567CE143A-if01"
_J_LINK_ADDRESS = "/dev/serial/by-id/usb-SEGGER_J-Link_000050130117-if00"
_J_LINK_ADDRESS_IF02 = "/dev/serial/by-id/usb-SEGGER_J-Link_000050130117-if02"
_M5STACK_ADDRESS = (
    "/dev/serial/by-id/"
    "usb-Silicon_Labs_CP2104_USB_to_UART_Bridge_Controller_01EDB69B-if00-port0")
_DOCKER_ID = "123abcdefghij"
_PTY_PROCESS_DIRECTORY = "/home/someuser/gazoo/gdm/pty_proc/some_device_dir"
_BAUDRATE = 115200
_PORT = 33000
_USB_SERIAL_NUMBER = "123789"
_ADB_SERIAL1 = "adb_serial1"
_ADB_SERIAL2 = "adb_serial2"

_MOCK_USB_MAP = {
    _CAMBRIONIX_ADDRESS:
        usb_config.UsbInfo(
            product_name="FT230X Basic UART",
            ftdi_interface=0,
            serial_number="DJ00JMN0",
            product_id="6015",
            address=_CAMBRIONIX_ADDRESS),
    _CAMBRIONIX_USB3_ADDRESS:
        usb_config.UsbInfo(
            product_name="PS15-USB3",
            ftdi_interface=1,
            serial_number="7567CE353A",
            product_id="0021",
            address=_CAMBRIONIX_USB3_ADDRESS
        ),
    "/dev/serial/by-id/usb-FTDI_FT230X_Basic_UART_DJ00JMN0-if02-port0":
        usb_config.UsbInfo(
            product_name="FT230X Basic UART",
            ftdi_interface=2,
            serial_number="DJ00JMN0",
            product_id="6015",
            address="/dev/serial/by-id/usb-FTDI_FT230X_Basic_UART_DJ00JMN0-if02-port0"
        ),
    "/dev/serial/by-id/usb-FTDI_FT230X_Basic_UART_DJ00JMN0-if03-port0":
        usb_config.UsbInfo(
            product_name="FT230X Basic UART",
            ftdi_interface=3,
            product_id="6015",
            serial_number="DJ00JMN0",
            address="/dev/serial/by-id/usb-FTDI_FT230X_Basic_UART_DJ00JMN0-if03-port0"
        ),
    _J_LINK_ADDRESS:
        usb_config.UsbInfo(
            product_name="J-Link",
            ftdi_interface=0,
            serial_number="56741",
            address=_J_LINK_ADDRESS),
    _J_LINK_ADDRESS_IF02:
        usb_config.UsbInfo(
            product_name="J-Link",
            ftdi_interface=2,
            serial_number="56741",
            address=_J_LINK_ADDRESS),
    _M5STACK_ADDRESS:
        usb_config.UsbInfo(
            product_name="CP2104",
            ftdi_interface=0,
            serial_number="12345",
            address=_M5STACK_ADDRESS),
}

ADB_CONNECTIONS = [_ADB_SERIAL1, _ADB_SERIAL2]
DOCKER_CONNECTIONS = [_DOCKER_ID]
PTY_PROCESS_CONNECTIONS = [_PTY_PROCESS_DIRECTORY]
STATIC_IPS = ["123.45.67.89"]
CONNECTIONS_DICT = {
    "AdbComms": ADB_CONNECTIONS,
    "DockerComms": [_DOCKER_ID],
    "JlinkSerialComms": [],
    "PigweedSerialComms": [_J_LINK_ADDRESS, _M5STACK_ADDRESS],
    "PigweedSocketComms": STATIC_IPS,
    "PtyProcessComms": [_PTY_PROCESS_DIRECTORY],
    "SerialComms": [_CAMBRIONIX_ADDRESS, _CAMBRIONIX_USB3_ADDRESS,
                    _M5STACK_ADDRESS],
    "SnmpComms": STATIC_IPS,
    "SshComms": STATIC_IPS,
    "UsbComms": [_USB_SERIAL_NUMBER],
    "YepkitComms": [],
}


class CommunicationTypeTests(unit_test_case.UnitTestCase):
  """Tests the communications type module."""

  def setUp(self):
    super().setUp()
    self.mock_out_transports()
    self.mock_out_usb_utils_methods()
    self.enter_context(mock.patch.object(
        usb_utils, "get_address_to_usb_info_dict", return_value=_MOCK_USB_MAP))
    self.manager = gazoo_device.manager.Manager()

  @mock.patch.object(pigweed_rpc_transport, "isinstance", return_value=True)
  @mock.patch.object(socket, "socket")
  @mock.patch.object(serial, "Serial")
  def test_001_able_to_get_args_for_all_communication_types(
      self, mock_serial, mock_socket, mock_isinstance):
    """Test creating Switchboard for each communication type."""
    for comms_type in extensions.communication_types:
      comms_address = _CAMBRIONIX_ADDRESS
      comms_kwargs = {}
      if "Jlink" in comms_type:
        comms_address = _J_LINK_ADDRESS
      elif "PigweedSerial" in comms_type:
        comms_kwargs["protobufs"] = (device_service_pb2,)
        comms_kwargs["baudrate"] = _BAUDRATE
      elif "PigweedSocket" in comms_type:
        comms_kwargs["protobufs"] = (device_service_pb2,)
        comms_kwargs["port"] = _PORT

      self.logger.info("Creating Switchboard for %s", comms_type)
      switchboard_inst = self.manager.create_switchboard(
          comms_address, comms_type, **comms_kwargs)
      switchboard_inst.close()

  def test_002_raise_error_for_bad_type(self):
    """Test raises error for bad type."""
    with self.assertRaisesRegex(errors.DeviceError,
                                "is not in supported types"):
      self.manager.create_switchboard(_CAMBRIONIX_ADDRESS,
                                      "nonexistent_comm_type")

  def test_003_ssh_initiation_works(self):
    """Test ssh initiation works."""
    self.manager.create_switchboard(
        "bogus_port", "SshComms", args="-H", log_cmd="logcat")
    ssh_transport.SSHTransport.assert_called_with(
        args="-H",
        comms_address="bogus_port",
        log_cmd="logcat",
        key_info=None,
        username="root")

  @mock.patch.object(host_utils, "get_all_snmp_ips", return_value=STATIC_IPS)
  @mock.patch.object(
      host_utils,
      "get_all_pty_process_directories",
      return_value=PTY_PROCESS_CONNECTIONS)
  @mock.patch.object(
      host_utils,
      "get_all_vdl_docker_connections",
      return_value=DOCKER_CONNECTIONS)
  @mock.patch.object(
      adb_utils,
      "get_adb_devices",
      return_value=ADB_CONNECTIONS)
  @mock.patch.object(host_utils, "get_all_yepkit_serials", return_value=[])
  @mock.patch.object(host_utils, "is_pingable", return_value=True)
  @mock.patch.object(host_utils, "is_sshable", return_value=True)
  @mock.patch.object(os, "access", return_value=True)
  def test_detection_works(
      self, mock_access, mock_sshable, mock_ping, mock_yepkit, mock_adb,
      mock_docker, mock_pty, mock_get_all_snmp_ips,
  ):

    # detection with warnings
    with mock.patch.object(
        host_utils, "verify_key", side_effect=ValueError):
      a_dict = communication_types.detect_connections(STATIC_IPS)

    # detection with missing keys
    mock_key = data_types.KeyInfo(
        "test_key", type=data_types.KeyType.SSH, package="test_package")
    download_key_error = errors.DownloadKeyError(
        mock_key, [RuntimeError("Something failed")])
    with mock.patch.object(
        host_utils, "verify_key", side_effect=download_key_error):
      a_dict = communication_types.detect_connections(STATIC_IPS)

    a_dict = communication_types.detect_connections(STATIC_IPS)
    self.assertEqual(set(a_dict.keys()), set(CONNECTIONS_DICT.keys()),
                     "Mismatch in detected communication types")
    for comm_type, connections in CONNECTIONS_DICT.items():
      self.assertCountEqual(connections, a_dict[comm_type],
                            "Mismatch in detected connections for "
                            f"communication type {comm_type!r}")

  @parameterized.named_parameters(
      ("specific_communication_types_success",
       {"comm_types": ["AdbComms"]}, {"AdbComms": ADB_CONNECTIONS}),
      ("specific_communication_types_success_case_insensitive",
       {"comm_types": ["adbcomms", "Invalid", "another_invalid"]},
       {"AdbComms": ADB_CONNECTIONS}),
      ("specific_communication_types_success_no_matches",
       {"comm_types": ["Invalid"]}, {}),
      ("specific_addresses_success",
       {"comm_types": ["AdbComms"], "addresses": [_ADB_SERIAL1]},
       {"AdbComms": [_ADB_SERIAL1]}),
      ("specific_addresses_success_no_matches",
       {"comm_types": ["AdbComms"], "addresses": ["Invalid"]},
       {"AdbComms": []}),
  )
  @mock.patch.object(
      adb_utils, "get_adb_devices", autospec=True, return_value=ADB_CONNECTIONS)
  def test_detect_specific_connections(
      self, kwargs, expected_connections, mock_get_adb_devices):
    """Tests detect_connections with restricted comm_types and addresses.

    Args:
      kwargs: Keyword arguments for the detect_connections() call.
      expected_connections: Connections which should be returned from the
        detect_connections() call.
      mock_get_adb_devices: Mock of adb_utils.get_adb_devices().

    Note that comm_types have to be limited to "AdbComms" since only ADB utils
    are mocked for the test.
    """
    connections = communication_types.detect_connections(**kwargs)
    # The returned connection dict will have all communication types.
    # There shouldn't be any detected connections for them.
    self.assertContainsSubset(expected_connections.keys(), connections.keys())
    for comm_type, addresses in connections.items():
      if comm_type in expected_connections:
        self.assertSequenceEqual(addresses, expected_connections[comm_type])
      else:
        self.assertFalse(addresses)

  def test_013_inaccessible_serial_works(self):
    """Test Inaccessible serial ports are removed from possible serial ports."""
    with mock.patch.object(os, "access", return_value=True):
      addresses = communication_types.SerialComms.get_comms_addresses()
      self.assertTrue(addresses)
    with mock.patch.object(os, "access", return_value=False):
      addresses = communication_types.SerialComms.get_comms_addresses()
      self.assertFalse(addresses)

  def test_020_usb_comms_addresses(self):
    """Tests UsbComms communication type."""
    addresses = communication_types.UsbComms.get_comms_addresses()
    self.assertIn(_USB_SERIAL_NUMBER, addresses)

  def test_021_usb_comms_transports(self):
    """Tests UsbComms transport list."""
    usb_comms = communication_types.UsbComms("123")
    self.assertEmpty(usb_comms.get_transport_list())


if __name__ == "__main__":
  unit_test_case.main()
