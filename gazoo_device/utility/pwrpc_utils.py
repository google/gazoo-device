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

"""Utility module for interaction with PwRPC (Pigweed RPC)."""
import enum
import os
from typing import Callable

from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import switchboard_base
from gazoo_device.protos import echo_service_pb2
from gazoo_device.switchboard.transports import pigweed_rpc_transport

# TODO(b/185956488): Remove conditional imports of Pigweed
try:
  # pylint: disable=g-import-not-at-top
  # pytype: disable=import-error
  from button_service import button_service_pb2
  from device_service import device_service_pb2
  from lighting_service import lighting_service_pb2
  # pytype: enable=import-error
  _PWRPC_PROTOS = (button_service_pb2,
                   device_service_pb2,
                   lighting_service_pb2,
                   echo_service_pb2)
except ImportError:
  _PWRPC_PROTOS = None


class PigweedAppType(enum.Enum):
  NON_PIGWEED = "nonpigweed"
  LIGHTING = "lighting"
  ECHO = "echo"

logger = gdm_logger.get_logger()


# Element format in _PIGWEED_APP_ENDPOINTS container:
# tuple of 3 elements: (method_args, method_kwargs, application_type)
# where method_args, method_kwargs are the input arguments
# to the PigweedRPCTransport.rpc,
# application_type is the Pigweed device type in string.
_PIGWEED_APP_ENDPOINTS = (
    (("Lighting", "Get"), {}, PigweedAppType.LIGHTING),
    (("msg",), {}, PigweedAppType.ECHO)
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
  if _PWRPC_PROTOS is None:
    logger.warning(
        "Pigweed python packages are not available in this environment.")
    return PigweedAppType.NON_PIGWEED.value

  switchboard = create_switchboard_func(communication_address=address,
                                        communication_type="PigweedSerialComms",
                                        device_name=os.path.basename(log_path),
                                        log_path=log_path,
                                        protobufs=_PWRPC_PROTOS)
  try:
    for method_args, method_kwargs, app_type in _PIGWEED_APP_ENDPOINTS:
      try:
        if app_type == PigweedAppType.ECHO:
          method = pigweed_rpc_transport.PigweedRPCTransport.echo_rpc
        else:
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
