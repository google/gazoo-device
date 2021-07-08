# Copyright 2021 Google LLC
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

"""Tests the pigweed_rpc_transport.py module."""
import fcntl
import queue
from unittest import mock

from gazoo_device.switchboard.transports import pigweed_rpc_transport
from gazoo_device.tests.unit_tests.utils import unit_test_case
import serial

_MOCK_DEVICE_ADDRESS = r"/some/fake/device/address"
_MOCK_PROTO_FILE_PATH = {"LightingService": r"/some/fake/proto/path"}
_MOCK_BAUDRATE = 115200
_MOCK_HDLC_LOG = r"<inf> chip: 30673 [ZCL]Cluster callback: 6"
_MOCK_ECHO_MSG = "pigweed rpc echo message"


class DummyStatus:
  """Mock RPC status."""
  # pylint: disable=invalid-name

  def __init__(self, is_echo_rpc, msg=""):
    if is_echo_rpc:
      self.msg = msg

  def ok(self):
    return True

  def SerializeToString(self):
    return True


class DummyService:
  """Mock RPC service."""
  # pylint: disable=invalid-name

  def Set(self, on):
    del on
    dummy_status = DummyStatus(is_echo_rpc=False)
    return dummy_status, dummy_status

  def Get(self):
    dummy_status = DummyStatus(is_echo_rpc=False)
    return dummy_status, dummy_status

  def Echo(self, msg):
    dummy_status = DummyStatus(is_echo_rpc=True, msg=msg)
    return dummy_status, dummy_status


class DummyChannel:
  # pylint: disable=invalid-name
  Lighting = DummyService()
  EchoService = DummyService()


class DummyNamespace:

  rpc = DummyChannel()


class DummyHdlcRpcClient:
  """Mock HDLC RPC client."""

  def __init__(self):
    self.thread_alive = True
    self.log_queue = queue.Queue()
    self.chip = DummyNamespace()
    self.pw = DummyNamespace()

  def rpcs(self):
    return self

  def is_alive(self):
    return self.thread_alive

  def start(self):
    self.thread_alive = True

  def close(self):
    self.thread_alive = False


class PigweedRPCTransportTest(unit_test_case.UnitTestCase):
  """Unit Test module for Pigweed RPC Transport."""

  def setUp(self):
    super().setUp()
    client_patcher = mock.patch.object(pigweed_rpc_transport,
                                       "PwHdlcRpcClient",
                                       return_value=DummyHdlcRpcClient())
    serial_patcher = mock.patch.object(serial, "Serial")
    client_patcher.start()
    serial_patcher.start()
    self.addCleanup(client_patcher.stop)
    self.addCleanup(serial_patcher.stop)
    self.uut = pigweed_rpc_transport.PigweedRPCTransport(_MOCK_DEVICE_ADDRESS,
                                                         _MOCK_PROTO_FILE_PATH,
                                                         _MOCK_BAUDRATE)

  @mock.patch.object(fcntl, "fcntl")
  @mock.patch.object(fcntl, "flock")
  def test_001_transport_open_close(self, mock_flock, mock_fcntl):
    """Tests PwRPC transport opening and closing."""
    self.uut.close()
    self.assertFalse(self.uut.is_open())
    self.uut.open()
    self.assertTrue(self.uut.is_open())

  def test_002_transport_read(self):
    """Tests PwRPC transport read method."""
    self.uut._hdlc_client.log_queue.put(_MOCK_HDLC_LOG)
    self.assertEqual(self.uut.read(None, 0.01), _MOCK_HDLC_LOG)
    self.assertEqual(self.uut.read(None, 0.01), b"")

  def test_003_transport_rpc(self):
    """Tests PwRPC transport calling rpc."""
    ack, _ = self.uut.rpc("Lighting", "Set", on=True)
    self.assertTrue(ack)
    ack, state = self.uut.rpc("Lighting", "Get")
    self.assertTrue(ack)
    self.assertTrue(state)

  def test_004_transport_echo_rpc(self):
    """Tests PwRPC transport calling echo rpc."""
    ack, echo_msg = self.uut.echo_rpc(_MOCK_ECHO_MSG)
    self.assertTrue(ack)
    self.assertEqual(echo_msg, _MOCK_ECHO_MSG)


if __name__ == "__main__":
  unit_test_case.main()
