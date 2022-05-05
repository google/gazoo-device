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

"""Utility module for interacting with Matter devices via Pigweed RPC."""
import importlib
import logging
import os
from typing import Callable, Generic, TypeVar

from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import matter_endpoints_base
from gazoo_device.capabilities.interfaces import switchboard_base
from gazoo_device.protos import descriptor_service_pb2
from gazoo_device.switchboard.transports import pigweed_rpc_transport

_ProtobufType = TypeVar("_ProtobufType")
_DESCRIPTOR_SERVICE_NAME = "Descriptor"
_DESCRIPTOR_DEVICE_TYPE_RPC_NAME = "DeviceTypeList"
_DETECT_RETRY = 2
_RPC_TIMEOUT_SEC = 1

logger = gdm_logger.get_logger()


class PigweedProtoState(Generic[_ProtobufType]):
  """Pigweed proto state interface.

  The RPC can accept proto type objects as parameters, however, protobufs aren't
  picklable, so we'll need this class interface to store the encoded protobuf
  object (bytes) and decode it back to the protobuf type.
  """

  def __init__(self, proto_inst: _ProtobufType, decoder_path: str) -> None:
    """Constructor of the PigweedProtoState.

    Args:
      proto_inst: Protobuf instance.
        (ex: device_service_pb2.DeviceInfo(vendor_id=0, product_id=0))
      decoder_path: The import path of the protobuf class.
        (ex: gazoo_device.protos.device_service_pb2.DeviceInfo)
    """
    self._bytes = proto_inst.SerializeToString()
    self._decoder_path = decoder_path

  def _get_decoder(self) -> Callable[[bytes], _ProtobufType]:
    """Gets decoder method from decoder path."""
    module, proto_class = self._decoder_path.rsplit(".", 1)
    mod = importlib.import_module(module)
    return getattr(mod, proto_class).FromString

  def decode(self) -> _ProtobufType:
    """Decodes the encoded proto instance."""
    decoder = self._get_decoder()
    return decoder(self._bytes)


def is_matter_device(
    address: str,
    log_path: str,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase],
    detect_logger: logging.Logger
) -> bool:
  """Returns True if the device is a Matter device.

  Args:
    address: Device serial address.
    log_path: Device log path.
    create_switchboard_func: Method to create the switchboard.
    detect_logger: The logger of device interactions.

  Returns:
    True if the device is a Matter device, False otherwise.
  """
  switchboard = create_switchboard_func(communication_address=address,
                                        communication_type="PigweedSerialComms",
                                        device_name=os.path.basename(log_path),
                                        log_path=log_path,
                                        protobufs=(descriptor_service_pb2,))
  rpc_method = pigweed_rpc_transport.PigweedRPCTransport.rpc
  method_args = (_DESCRIPTOR_SERVICE_NAME, _DESCRIPTOR_DEVICE_TYPE_RPC_NAME)
  method_kwargs = {
      "endpoint": matter_endpoints_base.ROOT_NODE_ENDPOINT_ID,
      "pw_rpc_timeout_s": _RPC_TIMEOUT_SEC}
  is_matter = False
  try:
    # Retry is to avoid flakiness of the descriptor cluster on Matter devices.
    for _ in range(_DETECT_RETRY):
      try:
        ack, _ = switchboard.call(method=rpc_method,
                                  method_args=method_args,
                                  method_kwargs=method_kwargs)
        if ack:
          is_matter = True
          break
      except errors.DeviceError as e:
        detect_logger.info(f"Pigweed RPC failure for address {address}: {e}")
  finally:
    switchboard.close()

  return is_matter
