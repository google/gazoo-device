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

"""Pigweed RPC transport class."""
import fcntl
import importlib
import queue
import select
import socket
import threading
import typing
from typing import Any, Collection, Optional, Tuple, Union
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.switchboard.transports import transport_base
from gazoo_device.utility import pwrpc_utils
import serial

# pylint: disable=g-import-not-at-top
# pytype: disable=import-error
try:
  raise ImportError
except ImportError:
  from pw_rpc import client
  from pw_rpc import callback_client
  from pw_hdlc import rpc
  from pw_hdlc import decode
  from pw_protobuf_compiler import python_protos
# pylint: enable=g-import-not-at-top
# pytype: enable=import-error

_STDOUT_ADDRESS = 1
_DEFAULT_ADDRESS = ord("R")
_JOIN_TIMEOUT_SEC = 1  # seconds
_SELECT_TIMEOUT_SEC = 0.1  # seconds
_SERIAL_TIMEOUT_SEC = 0.01  # seconds
_RPC_CALLBACK_TIMEOUT_SEC = 1  # seconds
_NUM_OF_READ_BYTES = 4096
RPC_METHOD_NAME = "rpc"  # Pigweed RPC method name for switchboard call
logger = gdm_logger.get_logger()


def _is_primitive(var: Any) -> bool:
  """Checks if the given variable is of a primitive type."""
  primitive = (bool, bytes, float, int, str)
  return isinstance(var, primitive)


def _serialize(payload: Any) -> Any:
  """Serializes the given payload.

  Args:
    payload: The payload to serialize. Note that the payload type will be either
      primitive type, protobuf type, or the list type of the above combination.

  Returns:
    Serialized payload.
  """
  if _is_primitive(payload):
    return payload
  if not isinstance(payload, list):
    return payload.SerializeToString()
  return [_serialize(content) for content in payload]


class PwHdlcRpcClient:
  """Pigweed HDLC RPC Client.

  The RPC client class for sending RPC requests and receiving RPC responses.
  The client supports HDLC communication over serial and socket connection.

  Adapted from
  https://pigweed.googlesource.com/pigweed/pigweed/+/refs/heads/master/pw_hdlc/py/pw_hdlc/rpc.py.
  """

  def __init__(self,
               file_object: Union[serial.Serial, socket.socket],
               protobuf_import_paths: Collection[str]):
    """Creates an RPC client configured to communicate using HDLC.

    Args:
      file_object: File descriptor object to interact, can be serial interface
        instance or socket interface instance.
      protobuf_import_paths: Import paths of the RPC proto modules.
    """
    self._file_object = file_object
    self._protobuf_import_paths = protobuf_import_paths
    self._client = None
    self._stop_event = None
    self._worker = None
    self.log_queue = None

    # The read / write methods for 2 types of file descriptors
    if isinstance(self._file_object, serial.Serial):
      self._file_object = typing.cast(serial.Serial, self._file_object)
      self._write_method = self._file_object.write
      self._read_method = self._file_object.read
    elif isinstance(self._file_object, socket.socket):
      self._file_object = typing.cast(socket.socket, self._file_object)
      self._write_method = self._file_object.sendall
      self._read_method = self._file_object.recv
    else:
      raise errors.DeviceError(
          "Invalid file object type. Must be serial.Serial or "
          f"socket.socket. The given object is {type(self._file_object)}.")

  def is_alive(self) -> bool:
    """Returns true if the worker thread has started."""
    return self._worker is not None and self._worker.is_alive()

  def start(self) -> None:
    """Creates and starts the worker thread if it hasn't been created."""
    if self._worker is None:
      self._stop_event = threading.Event()
      self.log_queue = queue.Queue()
      proto_modules = [importlib.import_module(import_path)
                       for import_path in self._protobuf_import_paths]
      # Load compiled proto modules instead of the raw protos to avoid a
      # "protoc" dependency.
      protos = python_protos.Library.from_paths(proto_modules)
      client_impl = callback_client.Impl(
          default_unary_timeout_s=_RPC_CALLBACK_TIMEOUT_SEC,
          default_stream_timeout_s=_RPC_CALLBACK_TIMEOUT_SEC)
      channels = rpc.default_channels(self._write_method)
      self._client = client.Client.from_modules(client_impl,
                                                channels,
                                                protos.modules())
      self._worker = threading.Thread(target=self.read_and_process_data)
      self._worker.start()

  def close(self) -> None:
    """Sets the threading event and joins the worker thread."""
    if self._worker is not None:
      self._stop_event.set()
      self._worker.join(timeout=_JOIN_TIMEOUT_SEC)
      if self._worker.is_alive():
        raise errors.DeviceError(
            f"The child thread failed to join after {_JOIN_TIMEOUT_SEC} seconds"
            )
      self._worker = None
      self._client = None
      self._stop_event = None
      self.log_queue = None

  def rpcs(self, channel_id: Optional[int] = None) -> Any:
    """Returns object for accessing services on the specified channel.

    Args:
      channel_id: None or RPC channel id.

    Returns:
      RPC instance over the specificed channel.
    """
    if self._client is None:
      return None
    if channel_id is None:
      return next(iter(self._client.channels())).rpcs
    else:
      return self._client.channel(channel_id).rpcs

  def read_and_process_data(self) -> None:
    """Continuously reads and handles HDLC frames."""
    decoder = decode.FrameDecoder()
    while not self._stop_event.is_set():
      readfds, _, _ = select.select(
          [self._file_object], [], [], _SELECT_TIMEOUT_SEC)
      if readfds:
        try:
          data = self._read_method(_NUM_OF_READ_BYTES)
        except Exception:  # pylint: disable=broad-except
          logger.exception(
              "Exception occurred when reading in PwHdlcRpcClient thread.")
          data = None
        if data:
          for frame in decoder.process_valid_frames(data):
            self._handle_frame(frame)

  def _handle_rpc_packet(self, frame: Any) -> None:
    """Handler for processing HDLC frame.

    Args:
      frame: HDLC frame packet.
    """
    if not self._client.process_packet(frame.data):
      logger.error(f"Packet not handled by RPC client: {frame.data}")

  def _push_to_log_queue(self, frame: Any) -> None:
    """Pushes the HDLC log in frame into the log queue.

    Args:
      frame: HDLC frame packet.
    """
    self.log_queue.put(frame.data + b"\n")

  def _handle_frame(self, frame: Any) -> None:
    """Private method for processing HDLC frame.

    Args:
      frame: HDLC frame packet.
    """
    try:
      if not frame.ok():
        return
      if frame.address == _DEFAULT_ADDRESS:
        self._handle_rpc_packet(frame)
      elif frame.address == _STDOUT_ADDRESS:
        self._push_to_log_queue(frame)
      else:
        logger.warning(f"Unhandled frame for address {frame.address}: {frame}")
    except Exception:  # pylint: disable=broad-except
      logger.exception("Exception occurred in PwHdlcRpcClient.")


def _rpc(hdlc_client: PwHdlcRpcClient,
         service_name: str,
         event_name: str,
         **kwargs: Any) -> Tuple[bool, Optional[bytes]]:
  """RPC call to the Matter endpoint with given service and event name.

  Args:
    hdlc_client: HDLC client instance.
    service_name: PwRPC service name.
    event_name: Event name in the given service instance.
    **kwargs: Arguments for the event method.

  Returns:
    RPC ack value, RPC encoded payload in bytes
  """
  if not hdlc_client.is_alive():
    return False, None
  client_channel = hdlc_client.rpcs().chip.rpc
  service = getattr(client_channel, service_name)
  event = getattr(service, event_name)
  kwargs = {
      param_name:
      param.decode() if isinstance(param, pwrpc_utils.PigweedProtoState)
      else param for param_name, param in kwargs.items()}
  ack, payload = event(**kwargs)
  return ack.ok(), _serialize(payload)


class PigweedRpcSerialTransport(transport_base.TransportBase):
  """Pigweed RPC transport over serial connection via UART."""

  def __init__(self,
               comms_address: str,
               protobuf_import_paths: Collection[str],
               baudrate: int,
               auto_reopen: bool = True,
               open_on_start: bool = True):
    """Initializes a PigweedRpcSerialTransport instance.

    Args:
      comms_address: Serial port path on the host.
      protobuf_import_paths: Module import paths of the compiled device
        communication protobufs. For example,
        ["gazoo_device.protos.device_service_pb2"].
        Proto module objects are not serializable, so their import paths are
        stored instead. Transport processes import the proto modules from these
        paths.
      baudrate: Serial baud rate.
      auto_reopen: Whether to automatically reopen the transport if it closes
        unexpectedly.
      open_on_start: Whether to open the transport during TransportProcess
        start.
    """
    super().__init__(
        auto_reopen=auto_reopen,
        open_on_start=open_on_start)
    self.comms_address = comms_address
    self._serial = serial.Serial()
    self._serial.port = comms_address
    self._serial.baudrate = baudrate
    self._serial.timeout = _SERIAL_TIMEOUT_SEC
    self._hdlc_client = PwHdlcRpcClient(self._serial, protobuf_import_paths)

  def is_open(self) -> bool:
    """Returns True if the PwRPC transport is connected to the target.

    Returns:
      True if transport is open, False otherwise.
    """
    return self._serial.isOpen() and self._hdlc_client.is_alive()

  def _close(self) -> None:
    """Closes the PwRPC transport."""
    self._hdlc_client.close()
    fcntl.flock(self._serial.fileno(), fcntl.LOCK_UN)
    self._serial.close()

  def _open(self) -> None:
    """Opens the PwRPC transport."""
    self._serial.open()
    fd = self._serial.fileno()
    flags = fcntl.fcntl(fd, fcntl.F_GETFD)
    fcntl.fcntl(fd, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)
    self._hdlc_client.start()

  def _read(self, size: int, timeout: float) -> bytes:
    """Returns Pigweed log from the HDLC channel 1.

    Args:
      size: Not used.
      timeout: Maximum seconds to wait to read bytes.

    Returns:
      bytes read from transport or None if no bytes were read
    """
    # Retrieving logs from queue doesn't support size configuration.
    del size  # not used
    try:
      return self._hdlc_client.log_queue.get(timeout=timeout)
    except queue.Empty:
      return b""

  def _write(self, data: str, timeout: Optional[float] = None) -> int:
    """Dummy method for the abstract parent class."""
    del data  # not used
    del timeout  # not used
    return 0

  def rpc(self,
          service_name: str,
          event_name: str,
          **kwargs: Any) -> Tuple[bool, Optional[bytes]]:
    """RPC call to the Matter endpoint with given service and event name."""
    return _rpc(self._hdlc_client, service_name, event_name, **kwargs)


class PigweedRpcSocketTransport(transport_base.TransportBase):
  """Pigweed RPC Transport over socket connection."""

  def __init__(self,
               comms_address: str,
               protobuf_import_paths: Collection[str],
               port: int,
               auto_reopen: bool = True,
               open_on_start: bool = True):
    """Initializes a PigweedRpcSocketTransport instance.

    Args:
      comms_address: Serial port path on the host.
      protobuf_import_paths: Module import paths of the compiled device
        communication protobufs.
      port: Socket connection port.
      auto_reopen: Whether to automatically reopen the transport if it closes
        unexpectedly.
      open_on_start: Whether to open the transport during TransportProcess
        start.
    """
    super().__init__(
        auto_reopen=auto_reopen,
        open_on_start=open_on_start)
    self.comms_address = comms_address
    self._protobuf_import_paths = protobuf_import_paths
    self._address = (comms_address, port)
    self._socket = None
    self._hdlc_client = None

  def is_open(self) -> bool:
    """Returns True if the PwRPC transport is connected to the target.

    Returns:
      True if transport is open, False otherwise.
    """
    return self._hdlc_client is not None and self._hdlc_client.is_alive()

  def _close(self) -> None:
    """Closes the PwRPC transport."""
    self._hdlc_client.close()
    self._socket.close()

  def _open(self) -> None:
    """Opens the PwRPC transport."""
    # We always create new socket instance given that reconnecting to a closed
    # socket is not allowed:
    # https://docs.python.org/2/library/socket.html#socket.socket.close
    self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self._hdlc_client = PwHdlcRpcClient(
        self._socket, self._protobuf_import_paths)
    self._socket.connect(self._address)
    self._hdlc_client.start()

  def _read(self, size: int, timeout: float) -> bytes:
    """Returns Pigweed log from the HDLC channel 1.

    Args:
      size: Not used.
      timeout: Maximum seconds to wait to read bytes.

    Returns:
      bytes read from transport or None if no bytes were read
    """
    # Retrieving logs from queue doesn't support size configuration.
    del size  # not used
    try:
      return self._hdlc_client.log_queue.get(timeout=timeout)
    except queue.Empty:
      return b""

  def _write(self, data: str, timeout: Optional[float] = None) -> int:
    """Dummy method for the abstract parent class."""
    del data  # not used
    del timeout  # not used
    return 0

  def rpc(self,
          service_name: str,
          event_name: str,
          **kwargs: Any) -> Tuple[bool, Optional[bytes]]:
    """RPC call to the Matter endpoint with given service and event name."""
    return _rpc(self._hdlc_client, service_name, event_name, **kwargs)
