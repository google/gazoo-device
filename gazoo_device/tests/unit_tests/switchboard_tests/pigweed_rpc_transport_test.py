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

"""Switchboard unit test for pigweed_rpc_transport module."""
import fcntl
import importlib
import queue
import select
import socket
import threading
from unittest import mock

from gazoo_device import errors
from gazoo_device.switchboard.transports import pigweed_rpc_transport
from gazoo_device.tests.unit_tests.utils import unit_test_case

import serial

_FAKE_DEVICE_ADDRESS = "/some/fake/device/address"
_FAKE_PROTO_IMPORT_PATH = ("gazoo_device.protos.some_proto_pb2",)
_FAKE_BAUDRATE = 115200
_FAKE_PORT = 33000
_FAKE_HDLC_LOG = "<inf> chip: 30673 [ZCL]Cluster callback: 6"
_FAKE_SERVICE = "fake_service"
_FAKE_EVENT = "fake_event"
_FAKE_SERIALIZED_BYTES = b"fake_bytes"
_FAKE_DATA = "fake-data"
_FAKE_FRAME = b"fake-frame"
_FAKE_FRAME_ADDRESS = 0
_STDOUT_ADDRESS = 1
_DEFAULT_ADDRESS = ord("R")
_FAKE_FILENO = 0
_FAKE_SIZE = 0
_FAKE_TIMEOUT = 0.01

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
        file_object=mock.Mock(spec=serial.Serial),
        protobuf_import_paths=_FAKE_PROTO_IMPORT_PATH)

  def test_serial_fd_instance(self):
    """Verifies serial instance for file descriptor."""
    client = pigweed_rpc_transport.PwHdlcRpcClient(
        file_object=mock.Mock(spec=serial.Serial),
        protobuf_import_paths=_FAKE_PROTO_IMPORT_PATH)
    self.assertIsNotNone(client)

  def test_socket_fd_instance(self):
    """Verifies socket instance for file descriptor."""
    client = pigweed_rpc_transport.PwHdlcRpcClient(
        file_object=mock.Mock(spec=socket.socket),
        protobuf_import_paths=_FAKE_PROTO_IMPORT_PATH)
    self.assertIsNotNone(client)

  def test_client_initialization_failure(self):
    """Verifies client initialization on failure with incorrect type."""
    with self.assertRaisesRegex(errors.DeviceError,
                                "Invalid file object type"):
      pigweed_rpc_transport.PwHdlcRpcClient(
          file_object=mock.Mock(),
          protobuf_import_paths=_FAKE_PROTO_IMPORT_PATH)

  def test_is_alive(self):
    """Verifies is_alive method returning True."""
    self.uut._worker = mock.Mock(spec=threading.Thread)
    self.uut._worker.is_alive.return_value = True
    self.assertTrue(self.uut.is_alive())

  @mock.patch.object(threading, "Thread")
  def test_start_on_success(self, mock_thread):
    """Verifies start method on success."""
    self.uut.start()
    mock_thread.assert_called_once()

  def test_close_on_success(self):
    """Verifies close method on success."""
    self.uut._stop_event = threading.Event()
    fake_worker = mock.Mock(threading.Thread)
    fake_worker.is_alive.return_value = False
    self.uut._worker = fake_worker
    self.uut.close()
    fake_worker.join.assert_called_once()
    fake_worker.is_alive.assert_called_once()
    self.assertIsNone(self.uut._worker)

  def test_close_on_failure(self):
    """Verifies close method on failure."""
    self.uut._stop_event = threading.Event()
    fake_worker = mock.Mock(threading.Thread)
    fake_worker.is_alive.return_value = True
    self.uut._worker = fake_worker
    error_regex = "The child thread failed to join"
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.close()

  def test_rpcs_returns_none_when_client_is_none(self):
    """Verifies rpcs method returns none when client is none."""
    self.uut._client = None
    self.assertIsNone(self.uut.rpcs())

  def test_rpcs_on_success_without_channel_id(self):
    """Verifies rpcs method on success without channel id."""
    self.uut._client = mock.Mock()
    self.uut._client.channels.return_value = [mock.Mock()]
    self.uut.rpcs(channel_id=None)
    self.uut._client.channels.assert_called_once()

  def test_rpcs_on_success_with_channel_id(self):
    """Verifies rpcs method on success with channel id."""
    self.uut._client = mock.Mock()
    fake_channel_id = 1
    self.uut.rpcs(channel_id=fake_channel_id)
    self.uut._client.channel.assert_called_once_with(fake_channel_id)

  @mock.patch.object(pigweed_rpc_transport.PwHdlcRpcClient, "_handle_frame")
  @mock.patch.object(select, "select")
  def test_read_and_process_data_on_success(self, mock_select, mock_handle):
    """Verifies read_and_process_data method on success."""
    self.uut._stop_event = mock.Mock(threading.Event)
    self.uut._stop_event.is_set.side_effect = [False, True]
    fake_fd = mock.Mock(serial.Serial)
    fake_fd.read.return_value = _FAKE_DATA
    mock_select.return_value = [fake_fd], [], []
    self.fake_decoder.process_valid_frames.return_value = [_FAKE_FRAME]

    self.uut.read_and_process_data()

    self.assertEqual(2, self.uut._stop_event.is_set.call_count)
    self.uut._file_object.read.assert_called_once()
    mock_select.assert_called_once()
    mock_handle.assert_called_once()

  @mock.patch.object(pigweed_rpc_transport, "logger")
  @mock.patch.object(select, "select")
  def test_read_and_process_data_exception(self, mock_select, mock_logger):
    """Verifies read_and_process_data method with exception."""
    self.uut._stop_event = mock.Mock(threading.Event)
    self.uut._stop_event.is_set.side_effect = [False, True]
    fake_fd = mock.Mock(serial.Serial)
    self.uut._file_object.read.side_effect = RuntimeError
    mock_select.return_value = [fake_fd], [], []

    self.uut.read_and_process_data()

    mock_logger.exception.assert_called_once()

  @mock.patch.object(pigweed_rpc_transport, "logger")
  def test_handle_rpc_packet_logs_error(self, mock_logger):
    """Verifies handle_rpc_packet method logging error."""
    self.uut._client = mock.Mock()
    self.uut._client.process_packet.return_value = False
    fake_frame = mock.Mock()

    self.uut._handle_rpc_packet(fake_frame)

    mock_logger.error.assert_called_once()

  def test_push_to_log_queue(self):
    """Verifies push_to_log_queue on success."""
    self.uut.log_queue = queue.Queue()
    fake_frame = mock.Mock(data=_FAKE_FRAME)

    self.uut._push_to_log_queue(fake_frame)

    self.assertFalse(self.uut.log_queue.empty())
    self.assertEqual(_FAKE_FRAME + b"\n", self.uut.log_queue.queue[-1])

  @mock.patch.object(
      pigweed_rpc_transport.PwHdlcRpcClient, "_handle_rpc_packet")
  def test_handle_frame_default_address_on_success(self, mock_handle):
    """Verifies handle_frame method on success with default address."""
    fake_frame = mock.Mock(address=_DEFAULT_ADDRESS)
    fake_frame.ok.return_value = True

    self.uut._handle_frame(fake_frame)

    mock_handle.assert_called_once_with(fake_frame)

  @mock.patch.object(
      pigweed_rpc_transport.PwHdlcRpcClient, "_push_to_log_queue")
  def test_handle_frame_stdout_address_on_success(self, mock_push):
    """Verifies handle_frame method on success with stdout address."""
    fake_frame = mock.Mock(address=_STDOUT_ADDRESS)
    fake_frame.ok.return_value = True

    self.uut._handle_frame(fake_frame)

    mock_push.assert_called_once_with(fake_frame)

  def test_handle_frame_not_ok(self):
    """Verifies handle_frame method handling not ok frame."""
    fake_frame = mock.Mock()
    fake_frame.ok.return_value = False
    self.uut._handle_frame(fake_frame)

  @mock.patch.object(pigweed_rpc_transport, "logger")
  def test_handle_frame_on_failure_invalid_frame_address(self, mock_logger):
    """Verifies handle_frame method on failure with invalid frame address."""
    fake_frame = mock.Mock(address=_FAKE_FRAME_ADDRESS)
    fake_frame.ok.return_value = True

    self.uut._handle_frame(fake_frame)

    mock_logger.warning.assert_called_once()

  @mock.patch.object(pigweed_rpc_transport, "logger")
  def test_handle_frame_on_failure_exception(self, mock_logger):
    """Verifies handle_frame method on failure with unexpected exception."""
    fake_frame = mock.Mock()
    fake_frame.ok.side_effect = RuntimeError

    self.uut._handle_frame(fake_frame)

    mock_logger.exception.assert_called_once()


class PigweedRpcModuleMethodsTest(unit_test_case.UnitTestCase):
  """Unit test for pigweed_rpc_transport module methods."""

  def test_is_primitive_return_true(self):
    """Verifies _is_primitive method returning true for primitive data type."""
    self.assertTrue(pigweed_rpc_transport._is_primitive(_FAKE_DATA))

  def test_is_primitive_return_false(self):
    """Verifies _is_primitive method returning false for complex data type."""
    complex_fake_data = mock.Mock()
    self.assertFalse(pigweed_rpc_transport._is_primitive(complex_fake_data))

  def test_serialize(self):
    """Verifies _serialize method on success for a list type input."""
    fake_protobuf_data = mock.Mock()
    fake_protobuf_data.SerializeToString.return_value = _FAKE_SERIALIZED_BYTES
    fake_payload = [_FAKE_DATA, fake_protobuf_data]

    self.assertEqual([_FAKE_DATA, _FAKE_SERIALIZED_BYTES],
                     pigweed_rpc_transport._serialize(fake_payload))

  @mock.patch.object(pigweed_rpc_transport, "_serialize")
  def test_rpc_hdlc_client_on_success(self, mock_serialize):
    """Verifies rpc method on success."""
    fake_ack = mock.Mock()
    fake_ack.ok.return_value = True
    fake_channel = mock.Mock()
    fake_channel.fake_service.fake_event.return_value = fake_ack, None
    fake_client = mock.Mock(spec=pigweed_rpc_transport.PwHdlcRpcClient)
    fake_client.is_alive.return_value = True
    fake_client.rpcs.return_value.chip.rpc = fake_channel
    mock_serialize.return_value = _FAKE_SERIALIZED_BYTES

    payload = pigweed_rpc_transport._rpc(
        hdlc_client=fake_client,
        service_name=_FAKE_SERVICE,
        event_name=_FAKE_EVENT)

    self.assertEqual(_FAKE_SERIALIZED_BYTES, payload)

  def test_rpc_hdlc_client_ack_value_not_ok(self):
    """Verifies rpc method on failure with not ok ack value."""
    fake_ack = mock.Mock()
    fake_ack.ok.return_value = False
    fake_ack.name = "fake-error-message"
    fake_ack.value = "fake-error-code"
    fake_channel = mock.Mock()
    fake_channel.fake_service.fake_event.return_value = fake_ack, None
    fake_client = mock.Mock(spec=pigweed_rpc_transport.PwHdlcRpcClient)
    fake_client.is_alive.return_value = True
    fake_client.rpcs.return_value.chip.rpc = fake_channel

    with self.assertRaisesRegex(
        errors.DeviceError,
        "Error message: fake-error-message. Error code: fake-error-code"):
      pigweed_rpc_transport._rpc(
          hdlc_client=fake_client,
          service_name=_FAKE_SERVICE,
          event_name=_FAKE_EVENT)

  def test_transport_rpc_hdlc_client_not_alive(self):
    """Verifies rpc method on failure with not alive hdlc client."""
    fake_client = mock.Mock(spec=pigweed_rpc_transport.PwHdlcRpcClient)
    fake_client.is_alive.return_value = False

    with self.assertRaisesRegex(errors.DeviceError, "HLDC client is not alive"):
      pigweed_rpc_transport._rpc(
          hdlc_client=fake_client,
          service_name=_FAKE_SERVICE,
          event_name=_FAKE_EVENT)


class PigweedRpcSerialTransportTest(unit_test_case.UnitTestCase):
  """Unit test for Pigweed RPC serial transport."""

  def setUp(self):
    super().setUp()
    client_patcher = mock.patch.object(pigweed_rpc_transport, "PwHdlcRpcClient")
    serial_patcher = mock.patch.object(serial, "Serial")
    client_class = client_patcher.start()
    serial_class = serial_patcher.start()
    self.fake_client = client_class.return_value
    self.fake_serial = serial_class.return_value
    self.fake_serial.fileno.return_value = _FAKE_FILENO
    self.addCleanup(client_patcher.stop)
    self.addCleanup(serial_patcher.stop)
    self.uut = pigweed_rpc_transport.PigweedRpcSerialTransport(
        comms_address=_FAKE_DEVICE_ADDRESS,
        protobuf_import_paths=_FAKE_PROTO_IMPORT_PATH,
        baudrate=_FAKE_BAUDRATE)

  def test_transport_is_open(self):
    """Verifies PwRPC transport is_open method on success."""
    self.fake_client.is_alive.return_value = True
    self.fake_serial.isOpen.return_value = True
    self.assertTrue(self.uut.is_open())
    self.fake_client.is_alive.assert_called_once()
    self.fake_serial.isOpen.assert_called_once()

  @mock.patch.object(fcntl, "flock")
  def test_transport_close(self, mock_flock):
    """Verifies PwRPC transport close method on success."""
    self.uut._close()
    self.fake_client.close.assert_called_once()
    self.fake_serial.fileno.assert_called_once()
    self.fake_serial.close.assert_called_once()
    mock_flock.assert_called_once()

  @mock.patch.object(fcntl, "fcntl")
  def test_transport_open_on_success(self, mock_fcntl):
    """Verifies PwRPC transport open method on success."""
    self.uut._open()
    self.fake_serial.open.assert_called_once()
    self.fake_serial.fileno.assert_called_once()
    self.fake_client.start.assert_called_once()
    self.assertEqual(2, mock_fcntl.call_count)

  def test_transport_read(self):
    """Verifies PwRPC transport read method."""
    self.fake_client.log_queue.get.side_effect = [_FAKE_HDLC_LOG, queue.Empty]
    self.assertEqual(_FAKE_HDLC_LOG, self.uut.read(_FAKE_SIZE, _FAKE_TIMEOUT))
    self.assertEqual(b"", self.uut.read(_FAKE_SIZE, _FAKE_TIMEOUT))

  def test_transport_write(self):
    """Verifies PwRPC transport write method."""
    self.assertEqual(0, self.uut._write(""))

  @mock.patch.object(pigweed_rpc_transport, "_rpc")
  def test_transport_rpc(self, mock_rpc):
    """Verifies the transport rpc method on success."""
    self.uut.rpc(service_name=_FAKE_SERVICE, event_name=_FAKE_EVENT)
    mock_rpc.assert_called_once()


class PigweedRpcSocketTransportTest(unit_test_case.UnitTestCase):
  """Unit test for Pigweed RPC socket transport."""

  def setUp(self):
    super().setUp()
    client_patcher = mock.patch.object(pigweed_rpc_transport, "PwHdlcRpcClient")
    socket_patcher = mock.patch.object(socket, "socket")
    client_class = client_patcher.start()
    socket_class = socket_patcher.start()
    self.fake_client = client_class.return_value
    self.fake_socket = socket_class.return_value
    self.addCleanup(client_patcher.stop)
    self.addCleanup(socket_patcher.stop)
    self.uut = pigweed_rpc_transport.PigweedRpcSocketTransport(
        comms_address=_FAKE_DEVICE_ADDRESS,
        protobuf_import_paths=_FAKE_PROTO_IMPORT_PATH,
        port=_FAKE_PORT)

  def test_transport_is_open(self):
    """Verifies if the transport is_open method on success."""
    self.uut._open()
    self.fake_client.is_alive.return_value = True
    self.assertTrue(self.uut.is_open())

  def test_transport_close(self):
    """Verifies if the transport _close method on success."""
    self.uut._open()

    self.uut._close()

    self.fake_client.close.assert_called_once()
    self.fake_socket.close.assert_called_once()

  def test_transport_open(self):
    """Verifies if the transport _open method on success."""
    self.uut._open()
    self.fake_client.start.assert_called_once()
    self.fake_socket.connect.assert_called_once()

  def test_transport_read(self):
    """Verifies the transport read method on success."""
    self.uut._open()
    self.fake_client.log_queue.get.side_effect = [_FAKE_HDLC_LOG, queue.Empty]
    self.assertEqual(_FAKE_HDLC_LOG, self.uut.read(_FAKE_SIZE, _FAKE_TIMEOUT))
    self.assertEqual(b"", self.uut.read(_FAKE_SIZE, _FAKE_TIMEOUT))

  def test_transport_write(self):
    """Verifies the transport write method on success.."""
    self.assertEqual(0, self.uut._write(""))

  @mock.patch.object(pigweed_rpc_transport, "_rpc")
  def test_transport_rpc(self, mock_rpc):
    """Verifies the transport rpc method on success."""
    self.uut.rpc(service_name=_FAKE_SERVICE, event_name=_FAKE_EVENT)
    mock_rpc.assert_called_once()


if __name__ == "__main__":
  unit_test_case.main()
