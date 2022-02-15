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

"""Utility module for interaction with PwRPC (Pigweed RPC)."""
import enum
import importlib
import os
from typing import Callable, Generic, TypeVar

from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import switchboard_base
from gazoo_device.protos import button_service_pb2
from gazoo_device.protos import device_service_pb2
from gazoo_device.protos import lighting_service_pb2
from gazoo_device.protos import locking_service_pb2
from gazoo_device.switchboard.transports import pigweed_rpc_transport

_PWRPC_PROTOS = (button_service_pb2,
                 device_service_pb2,
                 lighting_service_pb2,
                 locking_service_pb2)
_ProtobufType = TypeVar("_ProtobufType")


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
        (ex: lighting_service_pb2.LightingColor(hue=0, saturation=0))
      decoder_path: The import path of the protobuf class.
        (ex: gazoo_device.protos.lighting_service_pb2.LightingColor)
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


class PigweedAppType(enum.Enum):
  NON_PIGWEED = "nonpigweed"
  LIGHTING = "lighting"
  LOCKING = "locking"

logger = gdm_logger.get_logger()


# Element format in _PIGWEED_APP_ENDPOINTS container:
# tuple of 3 elements: (method_args, method_kwargs, application_type)
# where method_args, method_kwargs are the input arguments
# to the PigweedRPCTransport.rpc,
# application_type is the Pigweed device type in string.
_PIGWEED_APP_ENDPOINTS = (
    (("Lighting", "Get"), {}, PigweedAppType.LIGHTING),
    (("Locking", "Get"), {}, PigweedAppType.LOCKING)
)


def get_application_type(
    address: str,
    log_path: str,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> str:
  """Returns Pigweed application type of the device.

  Args:
    address: Device serial address.
    log_path: Device log path.
    create_switchboard_func: Method to create the switchboard.

  Returns:
    Pigweed application type.
  """
  switchboard = create_switchboard_func(communication_address=address,
                                        communication_type="PigweedSerialComms",
                                        device_name=os.path.basename(log_path),
                                        log_path=log_path,
                                        protobufs=_PWRPC_PROTOS)
  try:
    for method_args, method_kwargs, app_type in _PIGWEED_APP_ENDPOINTS:
      try:
        method = pigweed_rpc_transport.PigweedRPCTransport.rpc
        switchboard.call(method=method,
                         method_args=method_args,
                         method_kwargs=method_kwargs)
        return app_type.value
      except errors.DeviceError:
        logger.info(f"Device {address} is not a Pigweed {app_type} device.")
  finally:
    switchboard.close()
  return PigweedAppType.NON_PIGWEED.value
