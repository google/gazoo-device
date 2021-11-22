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

"""Switchboard unit test for pigweed_rpc_transport module."""
import fcntl
import importlib
import queue
import select
import threading
from unittest import mock

from gazoo_device import errors
from gazoo_device.switchboard.transports import pigweed_rpc_transport
from gazoo_device.tests.unit_tests.utils import unit_test_case

import serial

_FAKE_DEVICE_ADDRESS = "/some/fake/device/address"
_FAKE_PROTO_IMPORT_PATH = ("gazoo_device.protos.some_proto_pb2",)
_FAKE_BAUDRATE = 115200
_FAKE_HDLC_LOG = "<inf> chip: 30673 [ZCL]Cluster callback: 6"
_FAKE_SERVICE = "fake_service"
_FAKE_EVENT = "fake_event"
_FAKE_SERIALIZED_BYTES = b"fake_bytes"
_FAKE_DATA = "fake-data"
_FAKE_FRAME = b"fake-frame"
_FAKE_FRAME_ADDRESS = 0
_STDOUT_ADDRESS = 1
_DEFAULT_ADDRESS = ord("R")

_FAKE_PROTO_MODULE_PATH = (
    "gazoo_device.switchboard.transports.pigweed_rpc_transport.python_protos")
_FAKE_CALLBACK_CLIENT_MODULE_PATH = (
    "gazoo_device.switchboard.transports.pigweed_rpc_transport.callback_client")
_FAKE_RPC_MODULE_PATH = (
    "gazoo_device.switchboard.transports.pigweed_rpc_transport.rpc")
_FAKE_CLIENT_MODULE_PATH = (
    "gazoo_device.switchboard.transports.pigweed_rpc_transport.client")
_FAKE_DECODE_MODULE_PATH = (
    "gazoo_device.switchboard.transports.pigweed_rpc_transport.decode")


class PwHdlcRpcClientTest(unit_test_case.UnitTestCase):
  """Unit test for PwHdlcRpcClient."""

  def setUp(self):
    super().setUp()
    for module_path in [
        _FAKE_PROTO_MODULE_PATH,
        _FAKE_CALLBACK_CLIENT_MODULE_PATH,
        _FAKE_RPC_MODULE_PATH,
        _FAKE_CLIENT_MODULE_PATH]:
      patcher = mock.patch(module_path)
      patcher.start()
      self.addCleanup(patcher.stop)
    import_patcher = mock.patch.object(importlib, "import_module")
    import_patcher.start()
    self.addCleanup(import_patcher.stop)
    decode_patcher = mock.patch(_FAKE_DECODE_MODULE_PATH)
    fake_decode = decode_patcher.start()
    self.addCleanup(decode_patcher.stop)
    self.fake_decoder = fake_decode.FrameDecoder.return_value
    self.uut = pigweed_rpc_transport.PwHdlcRpcClient(
        serial_instance=mock.Mock(spec=serial.Serial),
        protobuf_import_paths=_FAKE_PROTO_IMPORT_PATH)

  def test_001_is_alive(self):
    """Verifies is_alive method returning True."""
    self.uut._worker = mock.Mock(spec=threading.Thread)
    self.uut._worker.is_alive.return_value = True
    self.assertTrue(self.uut.is_alive())

  @mock.patch.object(threading, "Thread")
  def test_002_start_on_success(self, mock_thread):
    """Verifies start method on success."""
    self.uut.start()
    mock_thread.assert_called_once()

  def test_003_close_on_success(self):
    """Verifies close method on success."""
    self.uut._stop_event = threading.Event()
    fake_worker = mock.Mock(threading.Thread)
    fake_worker.is_alive.return_value = False
    self.uut._worker = fake_worker
    self.uut.close()
    fake_worker.join.assert_called_once()
    fake_worker.is_alive.assert_called_once()
    self.assertIsNone(self.uut._worker)

  def test_004_close_on_failure(self):
    """Verifies close method on failure."""
    self.uut._stop_event = threading.Event()
    fake_worker = mock.Mock(threading.Thread)
    fake_worker.is_alive.return_value = True
    self.uut._worker = fake_worker
    error_regex = "The child thread failed to join"
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.close()

  def test_005_rpcs_on_success_without_channel_id(self):
    """Verifies rpcs method on success without channel id."""
    self.uut._client = mock.Mock()
    self.uut._client.channels.return_value = [mock.Mock()]
    self.uut.rpcs(channel_id=None)
    self.uut._client.channels.assert_called_once()

  def test_005_rpcs_on_success_with_channel_id(self):
    """Verifies rpcs method on success with channel id."""
    self.uut._client = mock.Mock()
    fake_channel_id = 1
    self.uut.rpcs(channel_id=fake_channel_id)
    self.uut._client.channel.assert_called_once_with(fake_channel_id)

  @mock.patch.object(pigweed_rpc_transport.PwHdlcRpcClient, "_handle_frame")
  @mock.patch.object(select, "select")
  def test_006_read_and_process_data_on_success(self, mock_select, mock_handle):
    """Verifies read_and_process_data method on success."""
    self.uut._stop_event = mock.Mock(threading.Event)
    self.uut._stop_event.is_set.side_effect = [False, True]
    fake_fd = mock.Mock(serial.Serial)
    fake_fd.read.return_value = _FAKE_DATA
    mock_select.return_value = [fake_fd], [], []
    self.fake_decoder.process_valid_frames.return_value = [_FAKE_FRAME]

    self.uut.read_and_process_data()

    self.assertEqual(2, self.uut._stop_event.is_set.call_count)
    fake_fd.read.assert_called_once()
    mock_select.assert_called_once()
    mock_handle.assert_called_once()

  @mock.patch.object(pigweed_rpc_transport, "logger")
  @mock.patch.object(select, "select")
  def test_006_read_and_process_data_exception(self, mock_select, mock_logger):
    """Verifies read_and_process_data method with exception."""
    self.uut._stop_event = mock.Mock(threading.Event)
    self.uut._stop_event.is_set.side_effect = [False, True]
    fake_fd = mock.Mock(serial.Serial)
    fake_fd.read.side_effect = RuntimeError
    mock_select.return_value = [fake_fd], [], []

    self.uut.read_and_process_data()

    mock_logger.exception.assert_called_once()

  @mock.patch.object(pigweed_rpc_transport, "logger")
  def test_007_handle_rpc_packet_logs_error(self, mock_logger):
    """Verifies handle_rpc_packet method logging error."""
    self.uut._client = mock.Mock()
    self.uut._client.process_packet.return_value = False
    fake_frame = mock.Mock()

    self.uut._handle_rpc_packet(fake_frame)

    mock_logger.error.assert_called_once()

  def test_008_push_to_log_queue(self):
    """Verifies push_to_log_queue on success."""
    self.uut.log_queue = queue.Queue()
    fake_frame = mock.Mock(data=_FAKE_FRAME)

    self.uut._push_to_log_queue(fake_frame)

    self.assertFalse(self.uut.log_queue.empty())
    self.assertEqual(_FAKE_FRAME + b"\n", self.uut.log_queue.queue[-1])

  @mock.patch.object(
      pigweed_rpc_transport.PwHdlcRpcClient, "_handle_rpc_packet")
  def test_009_handle_frame_default_address_on_success(self, mock_handle):
    """Verifies handle_frame method on success with default address."""
    fake_frame = mock.Mock(address=_DEFAULT_ADDRESS)
    fake_frame.ok.return_value = True

    self.uut._handle_frame(fake_frame)

    mock_handle.assert_called_once_with(fake_frame)

  @mock.patch.object(
      pigweed_rpc_transport.PwHdlcRpcClient, "_push_to_log_queue")
  def test_009_handle_frame_stdout_address_on_success(self, mock_push):
    """Verifies handle_frame method on success with stdout address."""
    fake_frame = mock.Mock(address=_STDOUT_ADDRESS)
    fake_frame.ok.return_value = True

    self.uut._handle_frame(fake_frame)

    mock_push.assert_called_once_with(fake_frame)

  def test_009_handle_frame_not_ok(self):
    """Verifies handle_frame method handling not ok frame."""
    fake_frame = mock.Mock()
    fake_frame.ok.return_value = False
    self.uut._handle_frame(fake_frame)

  @mock.patch.object(pigweed_rpc_transport, "logger")
  def test_009_handle_frame_on_failure_invalid_frame_address(self, mock_logger):
    """Verifies handle_frame method on failure with invalid frame address."""
    fake_frame = mock.Mock(address=_FAKE_FRAME_ADDRESS)
    fake_frame.ok.return_value = True

    self.uut._handle_frame(fake_frame)

    mock_logger.warning.assert_called_once()

  @mock.patch.object(pigweed_rpc_transport, "logger")
  def test_009_handle_frame_on_failure_exception(self, mock_logger):
    """Verifies handle_frame method on failure with unexpected exception."""
    fake_frame = mock.Mock()
    fake_frame.ok.side_effect = RuntimeError

    self.uut._handle_frame(fake_frame)

    mock_logger.exception.assert_called_once()


class PigweedRPCTransportTest(unit_test_case.UnitTestCase):
  """Unit test for Pigweed RPC Transport."""

  def setUp(self):
    super().setUp()
    client_patcher = mock.patch.object(pigweed_rpc_transport, "PwHdlcRpcClient")
    serial_patcher = mock.patch.object(serial, "Serial")
    client_class = client_patcher.start()
    serial_class = serial_patcher.start()
    self.fake_client = client_class.return_value
    self.fake_serial = serial_class.return_value
    self.addCleanup(client_patcher.stop)
    self.addCleanup(serial_patcher.stop)
    self.uut = pigweed_rpc_transport.PigweedRPCTransport(
        _FAKE_DEVICE_ADDRESS, _FAKE_PROTO_IMPORT_PATH, _FAKE_BAUDRATE)

  def test_001_transport_is_open(self):
    """Verifies PwRPC transport is_open method on success."""
    self.fake_client.is_alive.return_value = True
    self.fake_serial.isOpen.return_value = True
    self.assertTrue(self.uut.is_open())
    self.fake_client.is_alive.assert_called_once()
    self.fake_serial.isOpen.assert_called_once()

  @mock.patch.object(fcntl, "flock")
  def test_002_transport_close(self, mock_flock):
    """Verifies PwRPC transport close method on success."""
    self.uut._close()
    self.fake_client.close.assert_called_once()
    self.fake_serial.fileno.assert_called_once()
    self.fake_serial.close.assert_called_once()
    mock_flock.assert_called_once()

  @mock.patch.object(fcntl, "fcntl")
  def test_003_transport_open(self, mock_fcntl):
    """Verifies PwRPC transport open method on success."""
    self.uut._open()
    self.fake_serial.open.assert_called_once()
    self.fake_serial.fileno.assert_called_once()
    self.fake_client.start.assert_called_once()
    self.assertEqual(2, mock_fcntl.call_count)

  def test_004_transport_read(self):
    """Verifies PwRPC transport read method."""
    self.fake_client.log_queue.get.side_effect = [_FAKE_HDLC_LOG, queue.Empty]
    self.assertEqual(_FAKE_HDLC_LOG, self.uut.read(0, 0.01))
    self.assertEqual(b"", self.uut.read(0, 0.01))

  def test_005_transport_write(self):
    """Verifies PwRPC transport write method."""
    self.assertEqual(0, self.uut._write(""))

  def test_006_transport_rpc(self):
    """Verifies PwRPC transport general rpc method."""
    fake_ack = mock.Mock()
    fake_ack.ok.return_value = True
    fake_payload = mock.Mock()
    fake_payload.SerializeToString.return_value = _FAKE_SERIALIZED_BYTES
    fake_channel = mock.Mock()
    fake_channel.fake_service.fake_event.return_value = fake_ack, fake_payload
    self.fake_client.rpcs.return_value.chip.rpc = fake_channel
    ack, payload = self.uut.rpc(service_name=_FAKE_SERVICE,
                                event_name=_FAKE_EVENT)
    self.assertTrue(ack)
    self.assertEqual(_FAKE_SERIALIZED_BYTES, payload)


if __name__ == "__main__":
  unit_test_case.main()
